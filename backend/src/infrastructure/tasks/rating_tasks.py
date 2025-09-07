"""
Rating calculation tasks for FlyEsports.

This module contains asynchronous tasks for player rating calculations,
ELO updates, and confidence level adjustments.
"""

from celery import Task
from celery.exceptions import Retry
from typing import Dict, Any, List, Optional
import asyncio
import structlog
from datetime import datetime, timedelta

from .celery_app import celery_app
from src.infrastructure.database.connection import database_manager
from src.domain.repositories.player_repository import PlayerRepository
from src.domain.services.rating_calculator_service import RatingCalculatorService

logger = structlog.get_logger(__name__)


class BaseTaskWithRetry(Task):
    """
    Base task class with automatic retry configuration.
    
    Provides consistent retry behavior across all rating-related tasks.
    """
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True
    retry_backoff_max = 700
    retry_jitter = False

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure with proper logging."""
        logger.error(
            "Task failed after all retries",
            task_name=self.name,
            task_id=task_id,
            exception=str(exc),
            args=args,
            kwargs=kwargs
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry with proper logging."""
        logger.warning(
            "Task retry attempted",
            task_name=self.name,
            task_id=task_id,
            exception=str(exc),
            retry_count=self.request.retries
        )


@celery_app.task(bind=True, base=BaseTaskWithRetry, queue="high_priority")
def calculate_player_rating(
    self,
    profile_id: str,
    match_data: Dict[str, Any],
    opponent_profile_ids: List[str]
) -> Dict[str, Any]:
    """
    Calculate rating update for a single player based on match result.
    
    Args:
        profile_id: Player profile ID
        match_data: Match result and performance data
        opponent_profile_ids: List of opponent profile IDs
        
    Returns:
        Dict containing rating update information
    """
    try:
        async def _calculate() -> Dict[str, Any]:
            async with database_manager.get_session() as session:
                player_repo = PlayerRepository(session)
                rating_service = RatingCalculatorService()
                
                # Get player profile
                player_profile = await player_repo.get_by_id(profile_id)
                if not player_profile:
                    raise ValueError(f"Player profile {profile_id} not found")
                
                # Get opponent ratings
                opponent_ratings = []
                for opponent_id in opponent_profile_ids:
                    opponent = await player_repo.get_by_id(opponent_id)
                    if opponent:
                        opponent_ratings.append(opponent.rating)
                
                # Calculate new rating
                new_rating = await rating_service.calculate_elo_update(
                    player_profile.rating,
                    opponent_ratings,
                    match_data.get("result", 0.0),  # 1.0 = win, 0.0 = loss
                    match_data.get("performance", {})
                )
                
                # Update player rating
                old_rating = player_profile.rating.current_score
                player_profile.update_rating(new_rating.current_score, "match_result")
                await player_repo.save(player_profile)
                
                rating_change = new_rating.current_score - old_rating
                
                logger.info(
                    "Player rating updated",
                    profile_id=profile_id,
                    old_rating=old_rating,
                    new_rating=new_rating.current_score,
                    rating_change=rating_change,
                    match_id=match_data.get("match_id")
                )
                
                return {
                    "profile_id": profile_id,
                    "old_rating": old_rating,
                    "new_rating": new_rating.current_score,
                    "rating_change": rating_change,
                    "confidence_level": new_rating.confidence_level,
                    "total_matches": new_rating.total_matches,
                    "match_id": match_data.get("match_id"),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return asyncio.run(_calculate())
        
    except Exception as exc:
        logger.error(
            "Rating calculation failed",
            profile_id=profile_id,
            match_id=match_data.get("match_id"),
            exception=str(exc)
        )
        raise self.retry(exc=exc)


@celery_app.task(bind=True, base=BaseTaskWithRetry, queue="medium_priority")
def batch_update_player_ratings(
    self,
    region_id: str,
    match_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Batch update multiple player ratings from match results.
    
    Args:
        region_id: Region ID for the matches
        match_results: List of match result data
        
    Returns:
        Dict containing batch update summary
    """
    try:
        async def _batch_update() -> Dict[str, Any]:
            updated_profiles = []
            failed_updates = []
            
            for match_result in match_results:
                try:
                    match_id = match_result.get("match_id")
                    participants = match_result.get("participants", [])
                    
                    # Process each participant
                    for participant in participants:
                        profile_id = participant.get("profile_id")
                        if not profile_id:
                            continue
                        
                        # Get opponent profile IDs
                        opponent_ids = [
                            p.get("profile_id") 
                            for p in participants 
                            if p.get("profile_id") != profile_id and p.get("profile_id")
                        ]
                        
                        # Queue individual rating calculation
                        result = calculate_player_rating.delay(
                            profile_id=profile_id,
                            match_data={
                                "match_id": match_id,
                                "result": participant.get("match_result", 0.0),
                                "performance": participant.get("performance", {})
                            },
                            opponent_profile_ids=opponent_ids
                        )
                        
                        updated_profiles.append({
                            "profile_id": profile_id,
                            "task_id": result.id,
                            "match_id": match_id
                        })
                        
                except Exception as e:
                    failed_updates.append({
                        "match_id": match_result.get("match_id"),
                        "error": str(e)
                    })
                    logger.error(
                        "Failed to queue rating update",
                        match_id=match_result.get("match_id"),
                        exception=str(e)
                    )
            
            return {
                "region_id": region_id,
                "updated_count": len(updated_profiles),
                "failed_count": len(failed_updates),
                "updated_profiles": updated_profiles,
                "failed_updates": failed_updates,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return asyncio.run(_batch_update())
        
    except Exception as exc:
        logger.error(
            "Batch rating update failed",
            region_id=region_id,
            exception=str(exc)
        )
        raise self.retry(exc=exc)


@celery_app.task(bind=True, queue="medium_priority")
def batch_update_confidence(self) -> Dict[str, Any]:
    """
    Periodic task to update confidence levels for all active players.
    
    Returns:
        Dict containing update summary
    """
    try:
        async def _update_confidence() -> Dict[str, Any]:
            async with database_manager.get_session() as session:
                player_repo = PlayerRepository(session)
                
                # Get all active players who haven't played in the last 7 days
                inactive_threshold = datetime.utcnow() - timedelta(days=7)
                
                players = await player_repo.get_players_needing_confidence_update(
                    last_active_before=inactive_threshold
                )
                
                updated_count = 0
                for player in players:
                    # Decrease confidence for inactive players
                    current_confidence = player.rating.confidence_level
                    new_confidence = max(0.5, current_confidence * 0.95)  # 5% decay, minimum 0.5
                    
                    if new_confidence != current_confidence:
                        updated_rating = player.rating.update_confidence(new_confidence)
                        player.rating = updated_rating
                        await player_repo.save(player)
                        updated_count += 1
                
                logger.info(
                    "Confidence levels updated",
                    updated_count=updated_count,
                    total_checked=len(players)
                )
                
                return {
                    "updated_count": updated_count,
                    "total_checked": len(players),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return asyncio.run(_update_confidence())
        
    except Exception as exc:
        logger.error("Confidence update batch failed", exception=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, queue="high_priority")
def process_six_dimension_analysis(
    self,
    profile_id: str,
    match_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process detailed 6-dimension performance analysis for a player.
    
    Args:
        profile_id: Player profile ID
        match_data: Match performance data
        
    Returns:
        Dict containing analysis results
    """
    try:
        async def _analyze() -> Dict[str, Any]:
            async with database_manager.get_session() as session:
                from src.domain.services.six_dimension_analyzer import SixDimensionAnalyzer
                
                player_repo = PlayerRepository(session)
                analyzer = SixDimensionAnalyzer()
                
                # Get player profile
                player_profile = await player_repo.get_by_id(profile_id)
                if not player_profile:
                    raise ValueError(f"Player profile {profile_id} not found")
                
                # Analyze 6-dimension performance
                performance_data = match_data.get("performance", {})
                dimensions = analyzer.analyze_match_performance(
                    performance_data,
                    player_profile.position,
                    match_data.get("duration", 1800)  # Default 30 minutes
                )
                
                # Update player's 6-dimension history
                await player_repo.update_dimension_history(profile_id, dimensions)
                
                logger.info(
                    "Six dimension analysis completed",
                    profile_id=profile_id,
                    match_id=match_data.get("match_id")
                )
                
                return {
                    "profile_id": profile_id,
                    "dimensions": dimensions,
                    "match_id": match_data.get("match_id"),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return asyncio.run(_analyze())
        
    except Exception as exc:
        logger.error(
            "Six dimension analysis failed",
            profile_id=profile_id,
            match_id=match_data.get("match_id"),
            exception=str(exc)
        )
        raise self.retry(exc=exc)


@celery_app.task(bind=True, queue="medium_priority")
def recalculate_rating_from_history(
    self,
    profile_id: str,
    from_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Recalculate player rating from match history (for corrections/adjustments).
    
    Args:
        profile_id: Player profile ID
        from_date: ISO date string to recalculate from (optional)
        
    Returns:
        Dict containing recalculation results
    """
    try:
        async def _recalculate() -> Dict[str, Any]:
            async with database_manager.get_session() as session:
                player_repo = PlayerRepository(session)
                rating_service = RatingCalculatorService()
                
                # Get player profile
                player_profile = await player_repo.get_by_id(profile_id)
                if not player_profile:
                    raise ValueError(f"Player profile {profile_id} not found")
                
                # Get match history
                start_date = datetime.fromisoformat(from_date) if from_date else None
                match_history = await player_repo.get_match_history(
                    profile_id, 
                    from_date=start_date
                )
                
                old_rating = player_profile.rating.current_score
                
                # Reset to initial rating or rating at from_date
                if start_date:
                    # Find rating at start date
                    base_rating = await player_repo.get_rating_at_date(profile_id, start_date)
                else:
                    # Reset to initial rating
                    base_rating = await rating_service.calculate_initial_rating(
                        player_profile.rank_info,
                        player_profile.position,
                        player_profile.region_id
                    )
                
                current_rating = base_rating
                
                # Replay matches chronologically
                for match in match_history:
                    opponent_ratings = await player_repo.get_opponent_ratings_for_match(
                        match.match_id, profile_id
                    )
                    
                    current_rating = await rating_service.calculate_elo_update(
                        current_rating,
                        opponent_ratings,
                        match.result,
                        match.performance_data
                    )
                
                # Update player rating
                player_profile.rating = current_rating
                await player_repo.save(player_profile)
                
                rating_change = current_rating.current_score - old_rating
                
                logger.info(
                    "Rating recalculated from history",
                    profile_id=profile_id,
                    old_rating=old_rating,
                    new_rating=current_rating.current_score,
                    rating_change=rating_change,
                    matches_processed=len(match_history)
                )
                
                return {
                    "profile_id": profile_id,
                    "old_rating": old_rating,
                    "new_rating": current_rating.current_score,
                    "rating_change": rating_change,
                    "matches_processed": len(match_history),
                    "from_date": from_date,
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return asyncio.run(_recalculate())
        
    except Exception as exc:
        logger.error(
            "Rating recalculation failed",
            profile_id=profile_id,
            from_date=from_date,
            exception=str(exc)
        )
        raise self.retry(exc=exc)