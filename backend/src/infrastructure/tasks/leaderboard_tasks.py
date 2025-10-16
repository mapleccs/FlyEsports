"""
Leaderboard management tasks for FlyEsports.

This module contains asynchronous tasks for leaderboard updates,
cache management, and ranking calculations.
"""

from celery import Task
from typing import Dict, Any, List, Optional
import asyncio
import structlog
from datetime import datetime, timedelta

from .celery_app import celery_app
from src.infrastructure.database.connection import database_manager
from src.infrastructure.cache.redis_client import redis_manager
# from src.domain.repositories.player_repository import PlayerRepository  # TODO: Create this module
# from src.domain.services.leaderboard_service import LeaderboardService  # TODO: Create this module

logger = structlog.get_logger(__name__)


class BaseLeaderboardTask(Task):
    """
    Base task class for leaderboard operations.

    Provides common functionality and error handling for leaderboard tasks.
    """

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 2, "countdown": 30}
    retry_backoff = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure with proper logging."""
        logger.error(
            "Leaderboard task failed",
            task_name=self.name,
            task_id=task_id,
            exception=str(exc),
            args=args,
            kwargs=kwargs,
        )


@celery_app.task(bind=True, base=BaseLeaderboardTask, queue="medium_priority")
def update_region_leaderboard(
    self,
    region_id: str,
    positions: Optional[List[str]] = None,
    force_rebuild: bool = False,
) -> Dict[str, Any]:
    """
    Update leaderboard for a specific region.

    Args:
        region_id: Region ID to update
        positions: Specific positions to update (optional, updates all if None)
        force_rebuild: Force complete rebuild instead of incremental update

    Returns:
        Dict containing update summary
    """
    try:

        async def _update_leaderboard() -> Dict[str, Any]:
            async with database_manager.get_session() as session:
                player_repo = PlayerRepository(session)
                cache_client = redis_manager.get_client()
                leaderboard_service = LeaderboardService(player_repo, cache_client)

                positions_to_update = positions or [
                    "TOP",
                    "JUNGLE",
                    "MIDDLE",
                    "BOTTOM",
                    "UTILITY",
                    None,
                ]
                updated_positions = []

                for position in positions_to_update:
                    try:
                        if force_rebuild:
                            # Clear existing cache
                            await leaderboard_service.invalidate_region_leaderboard_cache(
                                region_id, position
                            )

                        # Update leaderboard (this will rebuild cache if needed)
                        leaderboard = await leaderboard_service.get_region_leaderboard(
                            region_id=region_id,
                            position=position,
                            page=1,
                            page_size=100,  # Pre-cache first 100 entries
                        )

                        # Pre-cache additional pages
                        for page in range(2, 6):  # Cache first 5 pages
                            await leaderboard_service.get_region_leaderboard(
                                region_id=region_id,
                                position=position,
                                page=page,
                                page_size=50,
                            )

                        updated_positions.append(
                            {
                                "position": position or "ALL",
                                "total_players": leaderboard["pagination"][
                                    "total_count"
                                ],
                                "updated_at": datetime.utcnow().isoformat(),
                            }
                        )

                        logger.info(
                            "Leaderboard updated",
                            region_id=region_id,
                            position=position,
                            total_players=leaderboard["pagination"]["total_count"],
                        )

                    except Exception as e:
                        logger.error(
                            "Failed to update position leaderboard",
                            region_id=region_id,
                            position=position,
                            exception=str(e),
                        )

                return {
                    "region_id": region_id,
                    "updated_positions": updated_positions,
                    "force_rebuild": force_rebuild,
                    "timestamp": datetime.utcnow().isoformat(),
                }

        return asyncio.run(_update_leaderboard())

    except Exception as exc:
        logger.error(
            "Region leaderboard update failed", region_id=region_id, exception=str(exc)
        )
        raise self.retry(exc=exc)


@celery_app.task(bind=True, base=BaseLeaderboardTask, queue="medium_priority")
def rebuild_region_leaderboard(
    self, region_id: str, position: Optional[str] = None
) -> Dict[str, Any]:
    """
    Completely rebuild leaderboard for a region/position.

    Args:
        region_id: Region ID to rebuild
        position: Specific position to rebuild (optional)

    Returns:
        Dict containing rebuild summary
    """
    return update_region_leaderboard.apply_async(
        args=[region_id],
        kwargs={"positions": [position] if position else None, "force_rebuild": True},
    ).get()


@celery_app.task(bind=True, queue="low_priority")
def update_active_leaderboards(self) -> Dict[str, Any]:
    """
    Periodic task to update all active region leaderboards.

    Returns:
        Dict containing update summary for all regions
    """
    try:

        async def _update_all() -> Dict[str, Any]:
            async with database_manager.get_session() as session:
                from src.infrastructure.repositories.region import RegionRepository

                region_repo = RegionRepository(session)

                # Get all active regions
                active_regions = await region_repo.get_active_regions()

                updated_regions = []
                failed_regions = []

                for region in active_regions:
                    try:
                        # Queue leaderboard update for this region
                        result = update_region_leaderboard.delay(region.id)

                        updated_regions.append(
                            {
                                "region_id": region.id,
                                "region_name": region.name,
                                "task_id": result.id,
                            }
                        )

                    except Exception as e:
                        failed_regions.append(
                            {
                                "region_id": region.id,
                                "region_name": region.name,
                                "error": str(e),
                            }
                        )
                        logger.error(
                            "Failed to queue leaderboard update",
                            region_id=region.id,
                            exception=str(e),
                        )

                logger.info(
                    "Active leaderboards update queued",
                    updated_count=len(updated_regions),
                    failed_count=len(failed_regions),
                )

                return {
                    "updated_regions": updated_regions,
                    "failed_regions": failed_regions,
                    "updated_count": len(updated_regions),
                    "failed_count": len(failed_regions),
                    "timestamp": datetime.utcnow().isoformat(),
                }

        return asyncio.run(_update_all())

    except Exception as exc:
        logger.error("Active leaderboards update failed", exception=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, base=BaseLeaderboardTask, queue="medium_priority")
def update_player_ranking_position(
    self, profile_id: str, old_rating: float, new_rating: float
) -> Dict[str, Any]:
    """
    Update leaderboard cache when a player's rating changes significantly.

    Args:
        profile_id: Player profile ID
        old_rating: Previous rating
        new_rating: New rating

    Returns:
        Dict containing update summary
    """
    try:

        async def _update_position() -> Dict[str, Any]:
            async with database_manager.get_session() as session:
                player_repo = PlayerRepository(session)
                cache_client = redis_manager.get_client()
                leaderboard_service = LeaderboardService(player_repo, cache_client)

                # Get player profile
                player = await player_repo.get_by_id(profile_id)
                if not player:
                    raise ValueError(f"Player profile {profile_id} not found")

                region_id = player.region_id
                position = player.position
                rating_change = abs(new_rating - old_rating)

                # If rating change is significant, update leaderboard
                if rating_change > 5.0:  # Threshold for significant change
                    await leaderboard_service.update_player_ranking(
                        profile_id, old_rating, new_rating
                    )

                    # Schedule leaderboard rebuild if change is very significant
                    if rating_change > 15.0:
                        rebuild_region_leaderboard.delay(region_id, position)

                logger.info(
                    "Player ranking position updated",
                    profile_id=profile_id,
                    region_id=region_id,
                    position=position,
                    rating_change=rating_change,
                )

                return {
                    "profile_id": profile_id,
                    "region_id": region_id,
                    "position": position,
                    "old_rating": old_rating,
                    "new_rating": new_rating,
                    "rating_change": rating_change,
                    "significant_change": rating_change > 5.0,
                    "rebuild_scheduled": rating_change > 15.0,
                    "timestamp": datetime.utcnow().isoformat(),
                }

        return asyncio.run(_update_position())

    except Exception as exc:
        logger.error(
            "Player ranking position update failed",
            profile_id=profile_id,
            old_rating=old_rating,
            new_rating=new_rating,
            exception=str(exc),
        )
        raise self.retry(exc=exc)


@celery_app.task(bind=True, base=BaseLeaderboardTask, queue="low_priority")
def create_daily_leaderboard_snapshot(
    self, region_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create daily snapshot of leaderboards for historical tracking.

    Args:
        region_id: Specific region ID (optional, creates for all if None)

    Returns:
        Dict containing snapshot creation summary
    """
    try:

        async def _create_snapshots() -> Dict[str, Any]:
            async with database_manager.get_session() as session:
                from src.infrastructure.repositories.region import RegionRepository

                player_repo = PlayerRepository(session)
                region_repo = RegionRepository(session)
                cache_client = redis_manager.get_client()
                leaderboard_service = LeaderboardService(player_repo, cache_client)

                # Get regions to snapshot
                if region_id:
                    regions = [await region_repo.get_by_id(region_id)]
                else:
                    regions = await region_repo.get_active_regions()

                created_snapshots = []

                for region in regions:
                    if not region:
                        continue

                    try:
                        snapshot = (
                            await leaderboard_service.create_leaderboard_snapshot(
                                region.id, "daily"
                            )
                        )

                        created_snapshots.append(
                            {
                                "region_id": region.id,
                                "region_name": region.name,
                                "snapshot_id": snapshot.id,
                                "total_players": len(snapshot.entries),
                                "avg_rating": snapshot.metadata.get("avg_rating"),
                                "created_at": snapshot.snapshot_date.isoformat(),
                            }
                        )

                        logger.info(
                            "Daily leaderboard snapshot created",
                            region_id=region.id,
                            total_players=len(snapshot.entries),
                        )

                    except Exception as e:
                        logger.error(
                            "Failed to create snapshot",
                            region_id=region.id,
                            exception=str(e),
                        )

                return {
                    "created_snapshots": created_snapshots,
                    "snapshot_count": len(created_snapshots),
                    "target_region_id": region_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }

        return asyncio.run(_create_snapshots())

    except Exception as exc:
        logger.error(
            "Daily leaderboard snapshot creation failed",
            region_id=region_id,
            exception=str(exc),
        )
        raise self.retry(exc=exc)


@celery_app.task(bind=True, base=BaseLeaderboardTask, queue="low_priority")
def warm_up_leaderboard_cache(
    self, region_id: str, positions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Pre-warm leaderboard cache for better performance.

    Args:
        region_id: Region ID to warm up
        positions: Positions to warm up (optional)

    Returns:
        Dict containing warm-up summary
    """
    try:

        async def _warm_cache() -> Dict[str, Any]:
            async with database_manager.get_session() as session:
                player_repo = PlayerRepository(session)
                cache_client = redis_manager.get_client()
                leaderboard_service = LeaderboardService(player_repo, cache_client)

                positions_to_warm = positions or [
                    "TOP",
                    "JUNGLE",
                    "MIDDLE",
                    "BOTTOM",
                    "UTILITY",
                    None,
                ]
                warmed_entries = []

                for position in positions_to_warm:
                    # Warm up first 10 pages
                    for page in range(1, 11):
                        try:
                            leaderboard = (
                                await leaderboard_service.get_region_leaderboard(
                                    region_id=region_id,
                                    position=position,
                                    page=page,
                                    page_size=50,
                                )
                            )

                            warmed_entries.append(
                                {
                                    "position": position or "ALL",
                                    "page": page,
                                    "entries": len(leaderboard["entries"]),
                                }
                            )

                            # Stop if we've reached the end
                            if page >= leaderboard["pagination"]["total_pages"]:
                                break

                        except Exception as e:
                            logger.warning(
                                "Failed to warm cache page",
                                region_id=region_id,
                                position=position,
                                page=page,
                                exception=str(e),
                            )
                            break

                logger.info(
                    "Leaderboard cache warmed up",
                    region_id=region_id,
                    warmed_pages=len(warmed_entries),
                )

                return {
                    "region_id": region_id,
                    "warmed_entries": warmed_entries,
                    "total_pages_warmed": len(warmed_entries),
                    "positions": positions_to_warm,
                    "timestamp": datetime.utcnow().isoformat(),
                }

        return asyncio.run(_warm_cache())

    except Exception as exc:
        logger.error(
            "Leaderboard cache warm-up failed", region_id=region_id, exception=str(exc)
        )
        raise self.retry(exc=exc)
