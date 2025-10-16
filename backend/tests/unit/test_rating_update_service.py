"""
Unit tests for rating update service.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from src.domain.services.rating_update_service import RatingUpdateService
from src.domain.value_objects.match_performance import MatchPerformance
from src.domain.value_objects.rating import Rating


class TestRatingUpdateService:
    """Test suite for rating update service."""

    def setup_method(self):
        """Setup test instances."""
        # Mock all dependencies
        self.elo_calculator = Mock()
        self.dimension_analyzer = AsyncMock()
        self.confidence_manager = Mock()

        self.service = RatingUpdateService(
            elo_calculator=self.elo_calculator,
            dimension_analyzer=self.dimension_analyzer,
            confidence_manager=self.confidence_manager
        )

    def create_sample_performance(self, **overrides):
        """Create sample match performance for testing."""
        defaults = {
            "player_profile_id": "player-123",
            "match_id": "match-456",
            "position": "MIDDLE",
            "match_duration": 1800,
            "kills": 8,
            "deaths": 3,
            "assists": 12,
            "damage_dealt": 25000,
            "damage_taken": 15000,
            "gold_earned": 12000,
            "cs_score": 180,
            "vision_score": 25,
            "wards_placed": 8,
            "wards_cleared": 5,
            "dragon_kills": 2,
            "baron_kills": 1,
            "tower_kills": 3,
            "objective_damage": 8000,
            "teamfight_participation": 0.8,
            "teamfight_damage_share": 0.25,
            "teamfight_kills": 4,
            "teamfight_deaths": 1,
            "match_result": "win",
            "played_at": datetime.utcnow()
        }
        defaults.update(overrides)
        return MatchPerformance(**defaults)

    def create_sample_rating(self, **overrides):
        """Create sample rating for testing."""
        defaults = {
            "current_score": 1500.0,
            "locked_score": None,
            "confidence_level": 0.7,
            "total_matches": 25,
            "six_dimensions": {
                "kda": 65.0, "damage": 70.0, "economy": 60.0,
                "vision": 55.0, "objective": 75.0, "teamfight": 68.0
            }
        }
        defaults.update(overrides)
        return Rating(**defaults)

    @pytest.mark.asyncio
    async def test_update_single_rating_basic(self):
        """Test basic single rating update."""
        # Setup
        performance = self.create_sample_performance()
        current_rating = self.create_sample_rating()

        # Mock dependencies
        self.elo_calculator.calculate_elo_change.return_value = 25.0
        self.dimension_analyzer.analyze_performance.return_value = {
            "kda": 70.0, "damage": 75.0, "economy": 65.0,
            "vision": 60.0, "objective": 80.0, "teamfight": 73.0
        }
        self.confidence_manager.calculate_confidence_level.return_value = 0.75

        # Execute
        updated_rating, details = await self.service.update_single_rating(
            player_performance=performance,
            current_rating=current_rating,
            opponent_ratings=[1400.0, 1500.0, 1600.0, 1450.0, 1550.0]
        )

        # Verify
        assert isinstance(updated_rating, Rating)
        assert updated_rating.current_score == 1525.0  # 1500 + 25
        assert updated_rating.confidence_level == 0.75
        assert updated_rating.total_matches == 26  # 25 + 1
        assert "success" in details
        assert details["success"] is True
        assert "elo_change" in details

        # Verify dependency calls
        self.elo_calculator.calculate_elo_change.assert_called_once()
        self.dimension_analyzer.analyze_performance.assert_called_once_with(performance)
        self.confidence_manager.calculate_confidence_level.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_single_rating_with_locked_score(self):
        """Test rating update when rating is locked."""
        # Setup - locked rating
        performance = self.create_sample_performance()
        locked_rating = self.create_sample_rating(
            current_score=1800.0,
            locked_score=1700.0  # Rating is locked
        )

        # Mock dependencies
        self.elo_calculator.calculate_elo_change.return_value = 30.0
        self.dimension_analyzer.analyze_performance.return_value = {
            "kda": 75.0, "damage": 80.0, "economy": 70.0,
            "vision": 65.0, "objective": 85.0, "teamfight": 78.0
        }
        self.confidence_manager.calculate_confidence_level.return_value = 0.8

        # Execute
        updated_rating, details = await self.service.update_single_rating(
            player_performance=performance,
            current_rating=locked_rating,
            opponent_ratings=[1600.0, 1650.0, 1700.0, 1550.0, 1750.0]
        )

        # Verify - should update locked score instead of current
        assert updated_rating.current_score == 1800.0  # Unchanged
        assert updated_rating.locked_score == 1730.0   # 1700 + 30 (locked score updated)

    @pytest.mark.asyncio
    async def test_batch_update_ratings_basic(self):
        """Test batch rating updates."""
        # Setup
        performances = [
            self.create_sample_performance(player_profile_id="player-1"),
            self.create_sample_performance(player_profile_id="player-2"),
            self.create_sample_performance(player_profile_id="player-3")
        ]

        current_ratings = {
            "player-1": self.create_sample_rating(current_score=1600.0),
            "player-2": self.create_sample_rating(current_score=1500.0),
            "player-3": self.create_sample_rating(current_score=1400.0)
        }

        # Mock team performances
        team1_performances = performances[:2]  # First 2 players
        team2_performances = performances[2:]  # Last player

        # Mock dependencies for each player
        self.elo_calculator.calculate_elo_change.side_effect = [20.0, 15.0, -25.0]
        self.dimension_analyzer.analyze_performance.side_effect = [
            {"kda": 70.0, "damage": 75.0, "economy": 65.0, "vision": 60.0, "objective": 80.0, "teamfight": 73.0},
            {"kda": 65.0, "damage": 70.0, "economy": 60.0, "vision": 55.0, "objective": 75.0, "teamfight": 68.0},
            {"kda": 55.0, "damage": 60.0, "economy": 50.0, "vision": 45.0, "objective": 65.0, "teamfight": 58.0}
        ]
        self.confidence_manager.calculate_confidence_level.side_effect = [0.75, 0.72, 0.68]

        # Execute
        results = await self.service.batch_update_ratings(
            match_performances=performances,
            current_ratings=current_ratings,
            team1_performances=team1_performances,
            team2_performances=team2_performances
        )

        # Verify
        assert len(results) == 3
        assert all(player_id in results for player_id in ["player-1", "player-2", "player-3"])

        # Check individual results
        player1_rating, player1_details = results["player-1"]
        assert player1_rating.current_score == 1620.0  # 1600 + 20
        assert player1_details["success"] is True

        player2_rating, player2_details = results["player-2"]
        assert player2_rating.current_score == 1515.0  # 1500 + 15
        assert player2_details["success"] is True

        player3_rating, player3_details = results["player-3"]
        assert player3_rating.current_score == 1375.0  # 1400 - 25
        assert player3_details["success"] is True

    @pytest.mark.asyncio
    async def test_batch_update_with_calculation_error(self):
        """Test batch update handling calculation errors."""
        # Setup
        performances = [
            self.create_sample_performance(player_profile_id="player-1"),
            self.create_sample_performance(player_profile_id="player-2")
        ]

        current_ratings = {
            "player-1": self.create_sample_rating(current_score=1600.0),
            "player-2": self.create_sample_rating(current_score=1500.0)
        }

        team1_performances = performances[:1]
        team2_performances = performances[1:]

        # Mock successful calculation for player-1, error for player-2
        self.elo_calculator.calculate_elo_change.side_effect = [25.0, Exception("ELO calculation failed")]
        self.dimension_analyzer.analyze_performance.side_effect = [
            {"kda": 70.0, "damage": 75.0, "economy": 65.0, "vision": 60.0, "objective": 80.0, "teamfight": 73.0},
            Exception("Dimension analysis failed")
        ]

        # Execute
        results = await self.service.batch_update_ratings(
            match_performances=performances,
            current_ratings=current_ratings,
            team1_performances=team1_performances,
            team2_performances=team2_performances
        )

        # Verify
        assert len(results) == 2

        # Player 1 should succeed
        player1_rating, player1_details = results["player-1"]
        assert player1_details["success"] is True
        assert player1_rating.current_score == 1625.0  # 1600 + 25

        # Player 2 should fail
        player2_rating, player2_details = results["player-2"]
        assert player2_details["success"] is False
        assert "error" in player2_details
        assert player2_rating is None

    @pytest.mark.asyncio
    async def test_dimension_update_integration(self):
        """Test that dimension scores are properly integrated into rating."""
        # Setup
        performance = self.create_sample_performance()
        current_rating = self.create_sample_rating(
            six_dimensions={
                "kda": 60.0, "damage": 65.0, "economy": 55.0,
                "vision": 50.0, "objective": 70.0, "teamfight": 63.0
            }
        )

        # Mock improved dimension scores
        improved_dimensions = {
            "kda": 75.0, "damage": 80.0, "economy": 70.0,
            "vision": 65.0, "objective": 85.0, "teamfight": 78.0
        }

        self.elo_calculator.calculate_elo_change.return_value = 20.0
        self.dimension_analyzer.analyze_performance.return_value = improved_dimensions
        self.confidence_manager.calculate_confidence_level.return_value = 0.78

        # Execute
        updated_rating, details = await self.service.update_single_rating(
            player_performance=performance,
            current_rating=current_rating,
            opponent_ratings=[1500.0, 1500.0, 1500.0, 1500.0, 1500.0]
        )

        # Verify dimension update
        assert updated_rating.six_dimensions == improved_dimensions
        assert all(
            updated_rating.six_dimensions[dim] >= current_rating.six_dimensions[dim]
            for dim in improved_dimensions.keys()
        )

    @pytest.mark.asyncio
    async def test_confidence_level_update(self):
        """Test confidence level updates based on performance consistency."""
        # Setup
        performance = self.create_sample_performance()
        current_rating = self.create_sample_rating(confidence_level=0.7)

        # Mock calculations
        self.elo_calculator.calculate_elo_change.return_value = 15.0
        self.dimension_analyzer.analyze_performance.return_value = {
            "kda": 65.0, "damage": 70.0, "economy": 60.0,
            "vision": 55.0, "objective": 75.0, "teamfight": 68.0
        }

        # Test confidence increase
        self.confidence_manager.calculate_confidence_level.return_value = 0.75

        # Execute
        updated_rating, _ = await self.service.update_single_rating(
            player_performance=performance,
            current_rating=current_rating,
            opponent_ratings=[1400.0, 1500.0, 1600.0, 1450.0, 1550.0]
        )

        # Verify confidence increased
        assert updated_rating.confidence_level == 0.75
        assert updated_rating.confidence_level > current_rating.confidence_level

    @pytest.mark.asyncio
    async def test_match_count_increment(self):
        """Test that match count is properly incremented."""
        # Setup
        performance = self.create_sample_performance()
        current_rating = self.create_sample_rating(total_matches=49)

        # Mock calculations
        self.elo_calculator.calculate_elo_change.return_value = 10.0
        self.dimension_analyzer.analyze_performance.return_value = {
            "kda": 65.0, "damage": 70.0, "economy": 60.0,
            "vision": 55.0, "objective": 75.0, "teamfight": 68.0
        }
        self.confidence_manager.calculate_confidence_level.return_value = 0.7

        # Execute
        updated_rating, details = await self.service.update_single_rating(
            player_performance=performance,
            current_rating=current_rating,
            opponent_ratings=[1500.0] * 5
        )

        # Verify match count increment
        assert updated_rating.total_matches == 50  # 49 + 1
        assert "matches_played" in details
        assert details["matches_played"] == 50

    @pytest.mark.asyncio
    async def test_rating_bounds_enforcement(self):
        """Test that rating stays within valid bounds."""
        # Test upper bound
        high_performance = self.create_sample_performance()
        high_rating = self.create_sample_rating(current_score=4980.0)  # Near max

        # Mock large ELO gain
        self.elo_calculator.calculate_elo_change.return_value = 50.0
        self.dimension_analyzer.analyze_performance.return_value = {
            "kda": 90.0, "damage": 95.0, "economy": 85.0,
            "vision": 80.0, "objective": 95.0, "teamfight": 92.0
        }
        self.confidence_manager.calculate_confidence_level.return_value = 0.9

        # Execute
        updated_rating, _ = await self.service.update_single_rating(
            player_performance=high_performance,
            current_rating=high_rating,
            opponent_ratings=[2000.0] * 5  # Much lower opponents
        )

        # Verify rating doesn't exceed maximum
        assert updated_rating.current_score <= Rating.MAX_RATING
        assert updated_rating.current_score == min(5030.0, Rating.MAX_RATING)

        # Test lower bound
        low_performance = self.create_sample_performance(match_result="loss")
        low_rating = self.create_sample_rating(current_score=50.0)  # Near min

        # Mock large ELO loss
        self.elo_calculator.calculate_elo_change.return_value = -100.0
        self.dimension_analyzer.analyze_performance.return_value = {
            "kda": 20.0, "damage": 25.0, "economy": 15.0,
            "vision": 10.0, "objective": 30.0, "teamfight": 22.0
        }
        self.confidence_manager.calculate_confidence_level.return_value = 0.55

        # Execute
        updated_rating2, _ = await self.service.update_single_rating(
            player_performance=low_performance,
            current_rating=low_rating,
            opponent_ratings=[2000.0] * 5  # Much higher opponents
        )

        # Verify rating doesn't go below minimum
        assert updated_rating2.current_score >= Rating.MIN_RATING
        assert updated_rating2.current_score == max(-50.0, Rating.MIN_RATING)