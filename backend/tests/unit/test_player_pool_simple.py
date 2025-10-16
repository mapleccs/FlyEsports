"""
Simple unit tests for player pool functionality.
"""

import pytest
from datetime import datetime

from src.domain.services.elo_calculator import ELOCalculator
from src.domain.value_objects.rating import Rating
from src.domain.value_objects.match_performance import MatchPerformance
from src.domain.value_objects.pool_filter import PoolFilter, SortBy, SortOrder


class TestPlayerPoolSimple:
    """Simple test suite for player pool core functionality."""

    def test_rating_creation(self):
        """Test basic rating creation."""
        rating = Rating(
            current_score=1500.0,
            locked_score=None,
            confidence_level=0.7,
            total_matches=25,
            six_dimensions={
                "kda": 65.0,
                "damage": 70.0,
                "economy": 60.0,
                "vision": 55.0,
                "objective": 75.0,
                "teamfight": 68.0
            }
        )

        assert rating.current_score == 1500.0
        assert rating.confidence_level == 0.7
        assert rating.total_matches == 25
        assert len(rating.six_dimensions) == 6

    def test_match_performance_creation(self):
        """Test basic match performance creation."""
        performance = MatchPerformance(
            player_profile_id="test-player",
            match_id="test-match",
            position="MIDDLE",
            match_duration=1800,
            kills=8,
            deaths=3,
            assists=12,
            damage_dealt=25000,
            damage_taken=15000,
            gold_earned=12000,
            cs_score=180,
            vision_score=25,
            wards_placed=8,
            wards_cleared=5,
            dragon_kills=2,
            baron_kills=1,
            tower_kills=3,
            objective_damage=8000,
            teamfight_participation=0.8,
            teamfight_damage_share=0.25,
            teamfight_kills=4,
            teamfight_deaths=1,
            match_result="win",
            played_at=datetime.utcnow()
        )

        assert performance.player_profile_id == "test-player"
        assert performance.kills == 8
        assert performance.deaths == 3
        assert performance.assists == 12
        assert performance.kda is not None  # Should be auto-calculated

    def test_pool_filter_creation(self):
        """Test pool filter creation."""
        pool_filter = PoolFilter.create_default(region_id=1)

        assert pool_filter.region_id == 1
        assert pool_filter.page == 1
        assert pool_filter.page_size == 20
        assert pool_filter.sort_by == SortBy.RATING
        assert pool_filter.sort_order == SortOrder.DESC

    def test_pool_filter_with_parameters(self):
        """Test pool filter with custom parameters."""
        pool_filter = PoolFilter(
            region_id=2,
            position="JUNGLE",
            min_rating=1500.0,
            max_rating=2000.0,
            page=2,
            page_size=25
        )

        assert pool_filter.region_id == 2
        assert pool_filter.position == "JUNGLE"
        assert pool_filter.min_rating == 1500.0
        assert pool_filter.max_rating == 2000.0
        assert pool_filter.has_rating_filter is True

    def test_elo_calculator_instantiation(self):
        """Test ELO calculator can be instantiated."""
        calculator = ELOCalculator()
        assert calculator is not None

    def test_rating_validation_bounds(self):
        """Test rating validation for score bounds."""
        # Valid rating should work
        rating = Rating(
            current_score=1500.0,
            locked_score=None,
            confidence_level=0.7,
            total_matches=10,
            six_dimensions={
                "kda": 50.0, "damage": 50.0, "economy": 50.0,
                "vision": 50.0, "objective": 50.0, "teamfight": 50.0
            }
        )
        assert rating.current_score == 1500.0

        # Invalid rating (too high) should raise error
        with pytest.raises(Exception):  # Should raise BusinessRuleViolationError
            Rating(
                current_score=6000.0,  # Above max
                locked_score=None,
                confidence_level=0.7,
                total_matches=10,
                six_dimensions={
                    "kda": 50.0, "damage": 50.0, "economy": 50.0,
                    "vision": 50.0, "objective": 50.0, "teamfight": 50.0
                }
            )

    def test_match_performance_kda_calculation(self):
        """Test KDA calculation in match performance."""
        # Normal KDA calculation
        performance = MatchPerformance(
            player_profile_id="test",
            match_id="test",
            position="MIDDLE",
            match_duration=1800,
            kills=10,
            deaths=5,
            assists=15,
            damage_dealt=20000,
            damage_taken=10000,
            gold_earned=12000,
            cs_score=150,
            vision_score=20,
            wards_placed=5,
            wards_cleared=3,
            dragon_kills=1,
            baron_kills=0,
            tower_kills=2,
            objective_damage=5000,
            teamfight_participation=0.7,
            teamfight_damage_share=0.2,
            teamfight_kills=6,
            teamfight_deaths=2,
            match_result="win",
            played_at=datetime.utcnow()
        )

        # KDA = (kills + assists) / deaths = (10 + 15) / 5 = 5.0
        assert performance.kda == 5.0

        # Perfect KDA (0 deaths)
        perfect_performance = MatchPerformance(
            player_profile_id="test",
            match_id="test",
            position="MIDDLE",
            match_duration=1800,
            kills=15,
            deaths=0,
            assists=20,
            damage_dealt=30000,
            damage_taken=8000,
            gold_earned=15000,
            cs_score=200,
            vision_score=30,
            wards_placed=8,
            wards_cleared=5,
            dragon_kills=2,
            baron_kills=1,
            tower_kills=4,
            objective_damage=8000,
            teamfight_participation=0.9,
            teamfight_damage_share=0.3,
            teamfight_kills=10,
            teamfight_deaths=0,
            match_result="win",
            played_at=datetime.utcnow()
        )

        # Perfect KDA should be high (with bonus for 0 deaths)
        assert perfect_performance.kda > 30.0

    def test_pool_filter_offset_calculation(self):
        """Test pool filter offset calculation for pagination."""
        # Page 1, size 20: offset = 0
        filter1 = PoolFilter(page=1, page_size=20)
        assert filter1.offset == 0

        # Page 3, size 15: offset = 30
        filter2 = PoolFilter(page=3, page_size=15)
        assert filter2.offset == 30

        # Page 5, size 10: offset = 40
        filter3 = PoolFilter(page=5, page_size=10)
        assert filter3.offset == 40