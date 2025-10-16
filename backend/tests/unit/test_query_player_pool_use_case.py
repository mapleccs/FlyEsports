"""
Unit tests for query player pool use case.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.application.use_cases.query_player_pool import (
    QueryPlayerPoolUseCase,
    QueryPlayerPoolRequest,
    QueryPlayerPoolResponse
)
from src.domain.value_objects.pool_filter import PoolFilter
from src.domain.value_objects.player_pool_statistics import PlayerPoolStatistics
from src.domain.aggregates.player_profile import PlayerProfile
from src.domain.value_objects.rating import Rating


class TestQueryPlayerPoolUseCase:
    """Test suite for query player pool use case."""

    def setup_method(self):
        """Setup test instances."""
        self.player_repository = AsyncMock()
        self.pool_manager = AsyncMock()
        self.cache_service = AsyncMock()

        self.use_case = QueryPlayerPoolUseCase(
            player_repository=self.player_repository,
            pool_manager=self.pool_manager,
            cache_service=self.cache_service
        )

    def create_sample_player_profile(
        self,
        profile_id: str = "player-123",
        rating_score: float = 1600.0,
        position: str = "MIDDLE",
        **kwargs
    ) -> PlayerProfile:
        """Create sample player profile for testing."""
        rating = Rating(
            current_score=rating_score,
            confidence_level=0.75,
            six_dimensions={"kda": 65.0, "damage": 70.0, "economy": 60.0,
                           "vision": 55.0, "objective": 75.0, "teamfight": 68.0},
            matches_played=50,
            last_updated=datetime.utcnow(),
            is_locked=False
        )

        # This is a simplified mock - in real implementation would use proper constructor
        player = Mock(spec=PlayerProfile)
        player.id = profile_id
        player.rating = rating
        player.primary_position = position
        player.total_matches = 50
        player.total_wins = 30
        return player

    @pytest.mark.asyncio
    async def test_execute_basic_query_no_cache(self):
        """Test basic query execution without cache."""
        # Setup
        pool_filter = PoolFilter.create_default()
        request = QueryPlayerPoolRequest(
            region_id=1,
            pool_filter=pool_filter,
            include_statistics=False
        )

        # Mock data
        sample_players = [
            self.create_sample_player_profile("player-1", 1800.0),
            self.create_sample_player_profile("player-2", 1600.0),
            self.create_sample_player_profile("player-3", 1400.0)
        ]

        # Mock repository responses
        self.player_repository.find_by_region.return_value = sample_players
        self.pool_manager.filter_and_rank_players.return_value = (sample_players, 3)
        self.cache_service.get.return_value = None  # No cache hit

        # Execute
        response = await self.use_case.execute(request)

        # Verify
        assert isinstance(response, QueryPlayerPoolResponse)
        assert len(response.players) == 3
        assert response.total_count == 3
        assert response.page == 1
        assert response.page_size == 20
        assert response.total_pages == 1
        assert response.statistics is None
        assert response.query_time_ms is not None
        assert response.from_cache is False

        # Verify repository calls
        self.player_repository.find_by_region.assert_called_once_with(region_id=1)
        self.pool_manager.filter_and_rank_players.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_query_with_statistics(self):
        """Test query execution with statistics included."""
        # Setup
        pool_filter = PoolFilter.create_default()
        request = QueryPlayerPoolRequest(
            region_id=1,
            pool_filter=pool_filter,
            include_statistics=True
        )

        sample_players = [self.create_sample_player_profile("player-1")]
        sample_statistics = PlayerPoolStatistics.create_empty(region_id=1)

        # Mock responses
        self.player_repository.find_by_region.return_value = sample_players
        self.pool_manager.filter_and_rank_players.return_value = (sample_players, 1)
        self.pool_manager.calculate_pool_statistics.return_value = sample_statistics
        self.cache_service.get.return_value = None

        # Execute
        response = await self.use_case.execute(request)

        # Verify
        assert response.statistics is not None
        assert isinstance(response.statistics, PlayerPoolStatistics)

        # Verify statistics calculation was called
        self.pool_manager.calculate_pool_statistics.assert_called_once_with(
            players=sample_players,
            region_id=1
        )

    @pytest.mark.asyncio
    async def test_execute_query_global_region(self):
        """Test query execution for global region (no region filter)."""
        # Setup
        pool_filter = PoolFilter.create_default()
        request = QueryPlayerPoolRequest(
            region_id=None,  # Global query
            pool_filter=pool_filter,
            include_statistics=True
        )

        sample_players = [self.create_sample_player_profile("player-1")]

        # Mock responses
        self.player_repository.find_all.return_value = sample_players
        self.pool_manager.filter_and_rank_players.return_value = (sample_players, 1)
        self.pool_manager.calculate_pool_statistics.return_value = PlayerPoolStatistics.create_empty(0)
        self.cache_service.get.return_value = None

        # Execute
        response = await self.use_case.execute(request)

        # Verify global query behavior
        self.player_repository.find_all.assert_called_once()
        self.player_repository.find_by_region.assert_not_called()

        # Statistics should be calculated with region_id=0 for global
        self.pool_manager.calculate_pool_statistics.assert_called_once_with(
            players=sample_players,
            region_id=0
        )

    @pytest.mark.asyncio
    async def test_execute_query_with_cache_hit(self):
        """Test query execution with cache hit."""
        # Setup
        pool_filter = PoolFilter.create_default()
        request = QueryPlayerPoolRequest(
            region_id=1,
            pool_filter=pool_filter
        )

        # Mock cached response
        cached_response = QueryPlayerPoolResponse(
            players=[],
            total_count=0,
            page=1,
            page_size=20,
            total_pages=1,
            from_cache=True
        )
        self.cache_service.get.return_value = "cached_data"  # Simulate cache hit

        # In real implementation, this would deserialize cached data
        # For test, we'll mock the cache retrieval to return None to skip caching logic
        self.use_case._get_from_cache = AsyncMock(return_value=cached_response)

        # Execute
        response = await self.use_case.execute(request)

        # Verify cache was used
        assert response.from_cache is True

        # Repository should not be called when cache hits
        self.player_repository.find_by_region.assert_not_called()
        self.pool_manager.filter_and_rank_players.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_query_pagination(self):
        """Test query execution with pagination."""
        # Setup for page 2 with custom page size
        pool_filter = PoolFilter(page=2, page_size=10)
        request = QueryPlayerPoolRequest(
            region_id=1,
            pool_filter=pool_filter
        )

        # Mock 25 total players, should return page 2 (players 11-20)
        sample_players = [
            self.create_sample_player_profile(f"player-{i}")
            for i in range(11, 21)  # Page 2 players
        ]

        self.player_repository.find_by_region.return_value = sample_players
        self.pool_manager.filter_and_rank_players.return_value = (sample_players, 25)
        self.cache_service.get.return_value = None

        # Execute
        response = await self.use_case.execute(request)

        # Verify pagination
        assert response.page == 2
        assert response.page_size == 10
        assert response.total_count == 25
        assert response.total_pages == 3  # ceil(25/10) = 3
        assert response.has_previous_page is True
        assert response.has_next_page is True

    @pytest.mark.asyncio
    async def test_execute_query_custom_filter(self):
        """Test query execution with custom filter parameters."""
        # Setup with complex filter
        pool_filter = PoolFilter(
            position="JUNGLE",
            min_rating=1500.0,
            max_rating=2000.0,
            min_confidence=0.7,
            dimension_filters={"objective": 70.0},
            sort_by="confidence",
            sort_order="desc"
        )

        request = QueryPlayerPoolRequest(
            region_id=2,
            pool_filter=pool_filter
        )

        sample_players = [self.create_sample_player_profile("player-1")]

        self.player_repository.find_by_region.return_value = sample_players
        self.pool_manager.filter_and_rank_players.return_value = (sample_players, 1)
        self.cache_service.get.return_value = None

        # Execute
        response = await self.use_case.execute(request)

        # Verify filter was passed correctly
        self.pool_manager.filter_and_rank_players.assert_called_once_with(
            players=sample_players,
            pool_filter=pool_filter
        )

    @pytest.mark.asyncio
    async def test_execute_query_no_results(self):
        """Test query execution with no matching results."""
        # Setup
        pool_filter = PoolFilter.create_default()
        request = QueryPlayerPoolRequest(
            region_id=1,
            pool_filter=pool_filter
        )

        # Mock empty results
        self.player_repository.find_by_region.return_value = []
        self.pool_manager.filter_and_rank_players.return_value = ([], 0)
        self.cache_service.get.return_value = None

        # Execute
        response = await self.use_case.execute(request)

        # Verify empty results handling
        assert len(response.players) == 0
        assert response.total_count == 0
        assert response.total_pages == 1  # At least 1 page even with no results
        assert response.has_next_page is False
        assert response.has_previous_page is False

    @pytest.mark.asyncio
    async def test_execute_query_without_cache_service(self):
        """Test query execution without cache service."""
        # Setup use case without cache
        use_case_no_cache = QueryPlayerPoolUseCase(
            player_repository=self.player_repository,
            pool_manager=self.pool_manager,
            cache_service=None
        )

        pool_filter = PoolFilter.create_default()
        request = QueryPlayerPoolRequest(region_id=1, pool_filter=pool_filter)

        sample_players = [self.create_sample_player_profile("player-1")]
        self.player_repository.find_by_region.return_value = sample_players
        self.pool_manager.filter_and_rank_players.return_value = (sample_players, 1)

        # Execute
        response = await use_case_no_cache.execute(request)

        # Should work without cache
        assert len(response.players) == 1
        assert response.from_cache is False

    @pytest.mark.asyncio
    async def test_execute_query_repository_error(self):
        """Test query execution with repository error."""
        # Setup
        pool_filter = PoolFilter.create_default()
        request = QueryPlayerPoolRequest(region_id=1, pool_filter=pool_filter)

        # Mock repository error
        self.player_repository.find_by_region.side_effect = Exception("Database error")
        self.cache_service.get.return_value = None

        # Execute and verify exception
        with pytest.raises(Exception, match="Failed to query player pool"):
            await self.use_case.execute(request)

    @pytest.mark.asyncio
    async def test_execute_query_pool_manager_error(self):
        """Test query execution with pool manager error."""
        # Setup
        pool_filter = PoolFilter.create_default()
        request = QueryPlayerPoolRequest(region_id=1, pool_filter=pool_filter)

        sample_players = [self.create_sample_player_profile("player-1")]
        self.player_repository.find_by_region.return_value = sample_players
        self.pool_manager.filter_and_rank_players.side_effect = Exception("Filter error")
        self.cache_service.get.return_value = None

        # Execute and verify exception
        with pytest.raises(Exception, match="Failed to query player pool"):
            await self.use_case.execute(request)

    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        """Test cache key generation consistency."""
        # Same filter should generate same cache key
        pool_filter1 = PoolFilter(region_id=1, position="TOP", min_rating=1500.0)
        pool_filter2 = PoolFilter(region_id=1, position="TOP", min_rating=1500.0)

        request1 = QueryPlayerPoolRequest(region_id=1, pool_filter=pool_filter1)
        request2 = QueryPlayerPoolRequest(region_id=1, pool_filter=pool_filter2)

        key1 = self.use_case._generate_cache_key(request1)
        key2 = self.use_case._generate_cache_key(request2)

        assert key1 == key2

        # Different filters should generate different keys
        pool_filter3 = PoolFilter(region_id=1, position="MIDDLE", min_rating=1500.0)
        request3 = QueryPlayerPoolRequest(region_id=1, pool_filter=pool_filter3)
        key3 = self.use_case._generate_cache_key(request3)

        assert key1 != key3

    @pytest.mark.asyncio
    async def test_response_properties(self):
        """Test response object properties."""
        # Setup for testing pagination properties
        pool_filter = PoolFilter(page=3, page_size=15)
        request = QueryPlayerPoolRequest(region_id=1, pool_filter=pool_filter)

        sample_players = [self.create_sample_player_profile(f"player-{i}") for i in range(5)]
        self.player_repository.find_by_region.return_value = sample_players
        self.pool_manager.filter_and_rank_players.return_value = (sample_players, 50)
        self.cache_service.get.return_value = None

        # Execute
        response = await self.use_case.execute(request)

        # Test pagination properties
        assert response.total_pages == 4  # ceil(50/15) = 4
        assert response.has_previous_page is True  # Page 3 has previous
        assert response.has_next_page is True      # Page 3 has next (total 4 pages)

        # Test first page
        pool_filter_first = PoolFilter(page=1, page_size=15)
        request_first = QueryPlayerPoolRequest(region_id=1, pool_filter=pool_filter_first)
        response_first = await self.use_case.execute(request_first)
        assert response_first.has_previous_page is False

        # Test last page
        pool_filter_last = PoolFilter(page=4, page_size=15)
        request_last = QueryPlayerPoolRequest(region_id=1, pool_filter=pool_filter_last)
        response_last = await self.use_case.execute(request_last)
        assert response_last.has_next_page is False