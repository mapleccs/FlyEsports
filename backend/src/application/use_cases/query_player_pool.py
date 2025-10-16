"""
Query player pool use case for FlyEsports.

Handles player pool queries including filtering, searching, and pagination
with caching support for performance.
"""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
import structlog

from ..base import UseCase, UseCaseError
from ...domain.repositories.player_profile import PlayerProfileRepository
from ...domain.services.player_pool_manager import PlayerPoolManager
from ...domain.value_objects.pool_filter import PoolFilter
from ...domain.value_objects.player_pool_statistics import PlayerPoolStatistics
from ...domain.aggregates.player_profile import PlayerProfile


logger = structlog.get_logger(__name__)


class QueryPlayerPoolRequest:
    """Request object for player pool query."""

    def __init__(
        self,
        region_id: Optional[int] = None,
        pool_filter: Optional[PoolFilter] = None,
        include_statistics: bool = False,
        cache_duration_seconds: int = 300  # 5 minutes default cache
    ):
        self.region_id = region_id
        self.pool_filter = pool_filter or PoolFilter.create_default(region_id)
        self.include_statistics = include_statistics
        self.cache_duration_seconds = cache_duration_seconds


class QueryPlayerPoolResponse:
    """Response object for player pool query."""

    def __init__(
        self,
        players: List[PlayerProfile],
        total_count: int,
        page: int,
        page_size: int,
        total_pages: int,
        statistics: Optional[PlayerPoolStatistics] = None,
        query_time_ms: Optional[int] = None,
        from_cache: bool = False
    ):
        self.players = players
        self.total_count = total_count
        self.page = page
        self.page_size = page_size
        self.total_pages = total_pages
        self.statistics = statistics
        self.query_time_ms = query_time_ms
        self.from_cache = from_cache

    @property
    def has_next_page(self) -> bool:
        """Check if there are more pages available."""
        return self.page < self.total_pages

    @property
    def has_previous_page(self) -> bool:
        """Check if there are previous pages available."""
        return self.page > 1


class QueryPlayerPoolUseCase(UseCase):
    """
    Use case for querying player pools with filtering and pagination.

    Provides efficient querying of player pools with support for:
    - Complex filtering criteria
    - Sorting and pagination
    - Statistics calculation
    - Response caching
    """

    def __init__(
        self,
        player_repository: PlayerProfileRepository,
        pool_manager: PlayerPoolManager,
        cache_service: Optional[Any] = None  # Redis cache service
    ):
        self.player_repository = player_repository
        self.pool_manager = pool_manager
        self.cache_service = cache_service

    async def execute(self, request: QueryPlayerPoolRequest) -> QueryPlayerPoolResponse:
        """
        Execute player pool query.

        Args:
            request: Query request parameters

        Returns:
            QueryPlayerPoolResponse with filtered players and metadata

        Raises:
            UseCaseError: If query execution fails
        """
        start_time = datetime.utcnow()

        try:
            logger.info(
                "Executing player pool query",
                region_id=request.region_id,
                filter=str(request.pool_filter),
                include_statistics=request.include_statistics
            )

            # Try to get from cache first
            if self.cache_service:
                cached_response = await self._get_from_cache(request)
                if cached_response:
                    logger.info("Player pool query served from cache")
                    return cached_response

            # Execute the actual query
            response = await self._execute_query(request)

            # Calculate query time
            end_time = datetime.utcnow()
            query_time_ms = int((end_time - start_time).total_seconds() * 1000)
            response.query_time_ms = query_time_ms

            # Cache the response
            if self.cache_service:
                await self._cache_response(request, response)

            logger.info(
                "Player pool query completed",
                total_count=response.total_count,
                page=response.page,
                query_time_ms=query_time_ms
            )

            return response

        except Exception as e:
            logger.error(
                "Player pool query failed",
                error=str(e),
                region_id=request.region_id
            )
            raise UseCaseError(f"Failed to query player pool: {str(e)}") from e

    async def _execute_query(self, request: QueryPlayerPoolRequest) -> QueryPlayerPoolResponse:
        """Execute the actual player pool query."""

        # Get all players from the repository with basic filters
        base_players = await self.player_repository.find_by_region(
            region_id=request.region_id
        ) if request.region_id else await self.player_repository.find_all()

        # Apply advanced filtering and sorting
        filtered_players, total_count = await self.pool_manager.filter_and_rank_players(
            players=base_players,
            pool_filter=request.pool_filter
        )

        # Calculate pagination metadata
        total_pages = max(1, (total_count + request.pool_filter.page_size - 1) // request.pool_filter.page_size)

        # Get statistics if requested
        statistics = None
        if request.include_statistics:
            statistics = await self.pool_manager.calculate_pool_statistics(
                players=base_players,
                region_id=request.region_id or 0
            )

        return QueryPlayerPoolResponse(
            players=filtered_players,
            total_count=total_count,
            page=request.pool_filter.page,
            page_size=request.pool_filter.page_size,
            total_pages=total_pages,
            statistics=statistics
        )

    async def _get_from_cache(self, request: QueryPlayerPoolRequest) -> Optional[QueryPlayerPoolResponse]:
        """Try to get response from cache."""
        if not self.cache_service:
            return None

        try:
            cache_key = self._generate_cache_key(request)
            cached_data = await self.cache_service.get(cache_key)

            if cached_data:
                # Deserialize and return cached response
                # This would need proper serialization/deserialization
                # For now, return None to force fresh query
                pass

        except Exception as e:
            logger.warning("Cache retrieval failed", error=str(e))

        return None

    async def _cache_response(self, request: QueryPlayerPoolRequest, response: QueryPlayerPoolResponse):
        """Cache the response for future queries."""
        if not self.cache_service:
            return

        try:
            cache_key = self._generate_cache_key(request)

            # Mark response as cached
            response.from_cache = False  # Original response

            # Cache with TTL
            await self.cache_service.setex(
                cache_key,
                request.cache_duration_seconds,
                self._serialize_response(response)
            )

        except Exception as e:
            logger.warning("Cache storage failed", error=str(e))

    def _generate_cache_key(self, request: QueryPlayerPoolRequest) -> str:
        """Generate cache key for the request."""
        filter_hash = hash(str(request.pool_filter))
        return f"player_pool:{request.region_id}:{filter_hash}:{request.include_statistics}"

    def _serialize_response(self, response: QueryPlayerPoolResponse) -> str:
        """Serialize response for caching."""
        # This would implement proper serialization
        # For now, return empty string
        return ""


class GetPlayerPoolStatisticsUseCase(UseCase):
    """Use case for getting player pool statistics."""

    def __init__(
        self,
        player_repository: PlayerProfileRepository,
        pool_manager: PlayerPoolManager
    ):
        self.player_repository = player_repository
        self.pool_manager = pool_manager

    async def execute(self, region_id: Optional[int] = None) -> PlayerPoolStatistics:
        """
        Get comprehensive statistics for a player pool.

        Args:
            region_id: Region ID (None for global statistics)

        Returns:
            PlayerPoolStatistics object

        Raises:
            UseCaseError: If statistics calculation fails
        """
        try:
            logger.info("Calculating player pool statistics", region_id=region_id)

            # Get all players in the region/globally
            if region_id:
                players = await self.player_repository.find_by_region(region_id)
            else:
                players = await self.player_repository.find_all()

            # Calculate statistics
            statistics = await self.pool_manager.calculate_pool_statistics(
                players=players,
                region_id=region_id or 0
            )

            logger.info(
                "Player pool statistics calculated",
                region_id=region_id,
                total_players=statistics.total_players,
                active_players=statistics.active_players
            )

            return statistics

        except Exception as e:
            logger.error(
                "Failed to calculate pool statistics",
                region_id=region_id,
                error=str(e)
            )
            raise UseCaseError(f"Failed to calculate pool statistics: {str(e)}") from e


class RecommendPlayersUseCase(UseCase):
    """Use case for recommending players based on team needs."""

    def __init__(
        self,
        player_repository: PlayerProfileRepository,
        pool_manager: PlayerPoolManager
    ):
        self.player_repository = player_repository
        self.pool_manager = pool_manager

    async def execute(
        self,
        team_needs: Dict[str, Any],
        region_id: Optional[int] = None,
        max_recommendations: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get player recommendations based on team needs.

        Args:
            team_needs: Dictionary describing team requirements
            region_id: Region to search in (None for all regions)
            max_recommendations: Maximum number of recommendations

        Returns:
            List of player recommendations

        Raises:
            UseCaseError: If recommendation fails
        """
        try:
            logger.info(
                "Generating player recommendations",
                team_needs=team_needs,
                region_id=region_id,
                max_recommendations=max_recommendations
            )

            # Get available players
            if region_id:
                available_players = await self.player_repository.find_by_region(region_id)
            else:
                available_players = await self.player_repository.find_all()

            # Filter to only free agents if not specified otherwise
            if team_needs.get('contract_status') != 'all':
                available_players = [
                    p for p in available_players
                    if p.contract_status.is_free_agent()
                ]

            # Get recommendations
            recommendations = await self.pool_manager.recommend_players(
                team_needs=team_needs,
                available_players=available_players,
                max_recommendations=max_recommendations
            )

            logger.info(
                "Player recommendations generated",
                recommendation_count=len(recommendations),
                region_id=region_id
            )

            return recommendations

        except Exception as e:
            logger.error(
                "Failed to generate player recommendations",
                team_needs=team_needs,
                region_id=region_id,
                error=str(e)
            )
            raise UseCaseError(f"Failed to generate recommendations: {str(e)}") from e


class ComparePlayersUseCase(UseCase):
    """Use case for comparing multiple players."""

    def __init__(self, player_repository: PlayerProfileRepository):
        self.player_repository = player_repository

    async def execute(self, player_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple players across various metrics.

        Args:
            player_ids: List of player profile IDs to compare

        Returns:
            Comparison data and analysis

        Raises:
            UseCaseError: If comparison fails
        """
        try:
            logger.info("Comparing players", player_ids=player_ids)

            if len(player_ids) < 2:
                raise UseCaseError("At least 2 players are required for comparison")

            if len(player_ids) > 5:
                raise UseCaseError("Cannot compare more than 5 players at once")

            # Get player profiles
            players = []
            for player_id in player_ids:
                player = await self.player_repository.find_by_id(player_id)
                if not player:
                    raise UseCaseError(f"Player not found: {player_id}")
                players.append(player)

            # Generate comparison data
            comparison_data = {
                'players': players,
                'comparison': await self._generate_comparison_data(players),
                'generated_at': datetime.utcnow().isoformat()
            }

            logger.info("Player comparison completed", player_count=len(players))

            return comparison_data

        except Exception as e:
            logger.error(
                "Failed to compare players",
                player_ids=player_ids,
                error=str(e)
            )
            raise UseCaseError(f"Failed to compare players: {str(e)}") from e

    async def _generate_comparison_data(self, players: List[PlayerProfile]) -> Dict[str, Any]:
        """Generate detailed comparison data for players."""

        comparison = {
            'basic_stats': {},
            'ratings': {},
            'dimensions': {},
            'experience': {},
            'strengths_weaknesses': {}
        }

        # Basic stats comparison
        comparison['basic_stats'] = {
            'total_matches': [p.total_matches for p in players],
            'win_rate': [
                (p.total_wins / p.total_matches * 100) if p.total_matches > 0 else 0
                for p in players
            ]
        }

        # Ratings comparison
        comparison['ratings'] = {
            'current_rating': [p.rating.current_score if p.rating else 0 for p in players],
            'confidence_level': [p.rating.confidence_level if p.rating else 0.5 for p in players],
            'is_locked': [p.rating.is_locked if p.rating else False for p in players]
        }

        # Dimensions comparison
        dimension_names = ['kda', 'damage', 'economy', 'vision', 'objective', 'teamfight']
        for dimension in dimension_names:
            comparison['dimensions'][dimension] = [
                p.rating.six_dimensions.get(dimension, 50.0) if p.rating else 50.0
                for p in players
            ]

        # Find strengths and weaknesses for each player
        for i, player in enumerate(players):
            if player.rating:
                strengths = []
                weaknesses = []

                for dim, score in player.rating.six_dimensions.items():
                    if score >= 75:
                        strengths.append(dim)
                    elif score <= 40:
                        weaknesses.append(dim)

                comparison['strengths_weaknesses'][f'player_{i}'] = {
                    'strengths': strengths,
                    'weaknesses': weaknesses
                }

        return comparison