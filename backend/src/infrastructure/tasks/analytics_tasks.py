"""
Analytics and reporting tasks for FlyEsports.

This module contains asynchronous tasks for data analysis,
report generation, and statistical calculations.
"""

from celery import Task
from typing import Dict, Any, List, Optional
import asyncio
import structlog
from datetime import datetime, timedelta

from .celery_app import celery_app
from src.infrastructure.database.connection import database_manager

logger = structlog.get_logger(__name__)


class BaseAnalyticsTask(Task):
    """
    Base task class for analytics operations.
    
    Provides common functionality for analytics tasks.
    """
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 2, "countdown": 60}
    retry_backoff = True


@celery_app.task(bind=True, base=BaseAnalyticsTask, queue="low_priority")
def generate_daily_report(self, region_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate daily analytics report for regions.
    
    Args:
        region_id: Specific region ID (optional, generates for all if None)
        
    Returns:
        Dict containing report generation summary
    """
    try:
        async def _generate_report() -> Dict[str, Any]:
            async with database_manager.get_session() as session:
                from src.infrastructure.repositories.region import RegionRepository
                from src.domain.repositories.player_repository import PlayerRepository
                
                region_repo = RegionRepository(session)
                player_repo = PlayerRepository(session)
                
                # Get target regions
                if region_id:
                    regions = [await region_repo.get_by_id(region_id)]
                else:
                    regions = await region_repo.get_active_regions()
                
                generated_reports = []
                yesterday = datetime.utcnow().date() - timedelta(days=1)
                
                for region in regions:
                    if not region:
                        continue
                    
                    try:
                        # Collect daily metrics
                        metrics = await _collect_daily_metrics(
                            session, region.id, yesterday
                        )
                        
                        # Store report in database
                        report = await _store_daily_report(
                            session, region.id, yesterday, metrics
                        )
                        
                        generated_reports.append({
                            "region_id": region.id,
                            "region_name": region.name,
                            "report_id": report.id,
                            "metrics": metrics
                        })
                        
                        logger.info(
                            "Daily report generated",
                            region_id=region.id,
                            date=yesterday.isoformat(),
                            report_id=report.id
                        )
                        
                    except Exception as e:
                        logger.error(
                            "Failed to generate daily report",
                            region_id=region.id,
                            exception=str(e)
                        )
                
                return {
                    "generated_reports": generated_reports,
                    "report_count": len(generated_reports),
                    "date": yesterday.isoformat(),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return asyncio.run(_generate_report())
        
    except Exception as exc:
        logger.error(
            "Daily report generation failed",
            region_id=region_id,
            exception=str(exc)
        )
        raise self.retry(exc=exc)


@celery_app.task(bind=True, base=BaseAnalyticsTask, queue="low_priority")
def analyze_rating_trends(
    self,
    region_id: str,
    days_back: int = 30
) -> Dict[str, Any]:
    """
    Analyze rating trends for a region over specified period.
    
    Args:
        region_id: Region ID to analyze
        days_back: Number of days to analyze
        
    Returns:
        Dict containing trend analysis
    """
    try:
        async def _analyze_trends() -> Dict[str, Any]:
            async with database_manager.get_session() as session:
                from src.domain.repositories.player_repository import PlayerRepository
                
                player_repo = PlayerRepository(session)
                
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days_back)
                
                # Get rating history for all players in region
                rating_trends = await player_repo.get_rating_trends(
                    region_id, start_date, end_date
                )
                
                # Analyze trends
                trend_analysis = {
                    "region_id": region_id,
                    "period_days": days_back,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "total_players": len(rating_trends),
                    "rising_players": 0,
                    "falling_players": 0,
                    "stable_players": 0,
                    "avg_rating_change": 0.0,
                    "position_trends": {}
                }
                
                total_change = 0.0
                position_changes = {}
                
                for trend in rating_trends:
                    rating_change = trend["final_rating"] - trend["initial_rating"]
                    total_change += rating_change
                    
                    # Categorize trend
                    if rating_change > 3.0:
                        trend_analysis["rising_players"] += 1
                    elif rating_change < -3.0:
                        trend_analysis["falling_players"] += 1
                    else:
                        trend_analysis["stable_players"] += 1
                    
                    # Position-based trends
                    position = trend["position"]
                    if position not in position_changes:
                        position_changes[position] = []
                    position_changes[position].append(rating_change)
                
                # Calculate averages
                if trend_analysis["total_players"] > 0:
                    trend_analysis["avg_rating_change"] = total_change / trend_analysis["total_players"]
                
                # Position trend analysis
                for position, changes in position_changes.items():
                    if changes:
                        trend_analysis["position_trends"][position] = {
                            "avg_change": sum(changes) / len(changes),
                            "player_count": len(changes),
                            "rising_count": sum(1 for c in changes if c > 3.0),
                            "falling_count": sum(1 for c in changes if c < -3.0)
                        }
                
                logger.info(
                    "Rating trends analyzed",
                    region_id=region_id,
                    total_players=trend_analysis["total_players"],
                    avg_change=trend_analysis["avg_rating_change"]
                )
                
                return trend_analysis
        
        return asyncio.run(_analyze_trends())
        
    except Exception as exc:
        logger.error(
            "Rating trend analysis failed",
            region_id=region_id,
            exception=str(exc)
        )
        raise self.retry(exc=exc)


async def _collect_daily_metrics(session, region_id: str, date: datetime.date) -> Dict[str, Any]:
    """
    Collect daily metrics for a region.
    
    Args:
        session: Database session
        region_id: Region ID
        date: Date to collect metrics for
        
    Returns:
        Dict containing daily metrics
    """
    from src.domain.repositories.player_repository import PlayerRepository
    from src.infrastructure.repositories.match import MatchRepository
    
    player_repo = PlayerRepository(session)
    match_repo = MatchRepository(session)
    
    # Basic player metrics
    total_players = await player_repo.count_players({"region_id": region_id})
    active_players = await player_repo.count_active_players(region_id, date)
    new_registrations = await player_repo.count_new_registrations(region_id, date)
    
    # Match metrics
    total_matches = await match_repo.count_matches_on_date(region_id, date)
    
    # Rating metrics
    avg_rating = await player_repo.get_average_rating(region_id)
    rating_distribution = await player_repo.get_rating_distribution(region_id)
    
    return {
        "date": date.isoformat(),
        "region_id": region_id,
        "player_metrics": {
            "total_players": total_players,
            "active_players": active_players,
            "new_registrations": new_registrations
        },
        "match_metrics": {
            "total_matches": total_matches
        },
        "rating_metrics": {
            "average_rating": avg_rating,
            "distribution": rating_distribution
        }
    }


async def _store_daily_report(session, region_id: str, date: datetime.date, metrics: Dict[str, Any]):
    """
    Store daily report in database.
    
    Args:
        session: Database session
        region_id: Region ID
        date: Report date
        metrics: Metrics data
        
    Returns:
        Stored report entity
    """
    from src.infrastructure.database.models.analytics import DailyReport
    
    report = DailyReport(
        region_id=region_id,
        report_date=date,
        metrics_data=metrics,
        created_at=datetime.utcnow()
    )
    
    session.add(report)
    await session.commit()
    await session.refresh(report)
    
    return report