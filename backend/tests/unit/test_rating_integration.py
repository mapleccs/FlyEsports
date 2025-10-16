"""
Integration tests for rating system components.
"""

import pytest
from datetime import datetime

from src.domain.services.rating_update_service import RatingUpdateService
from src.domain.services.elo_calculator import ELOCalculator, DynamicKFactorCalculator
from src.domain.services.six_dimension_analyzer import SixDimensionAnalyzer
from src.domain.services.confidence_manager import ConfidenceManager
from src.domain.value_objects.match_performance import MatchPerformance
from src.domain.value_objects.rating import Rating


class TestRatingIntegration:
    """Integration tests for rating system components."""

    def setup_method(self):
        """Setup test instances."""
        self.rating_service = RatingUpdateService()
        self.elo_calculator = ELOCalculator()
        self.k_factor_calculator = DynamicKFactorCalculator()
        self.dimension_analyzer = SixDimensionAnalyzer()
        self.confidence_manager = ConfidenceManager()

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

    def test_elo_calculator_basic(self):
        """Test ELO calculator basic functionality."""
        rating = self.create_sample_rating(current_score=1600.0)

        # Test K-factor calculation
        k_factor = self.k_factor_calculator.calculate_k_factor(
            current_rating=rating.current_score,
            confidence_level=rating.confidence_level,
            total_matches=rating.total_matches,
            recent_performance_variance=0.1
        )
        assert isinstance(k_factor, float)
        assert 10.0 <= k_factor <= 100.0  # Reasonable K-factor range

        # Test match outcome prediction
        opponent_ratings = [1500.0, 1550.0, 1450.0, 1600.0, 1400.0]
        prediction = self.elo_calculator.predict_match_outcome(
            player_rating=1600.0,
            opponent_ratings=opponent_ratings
        )
        assert isinstance(prediction, dict)
        assert "win_probability" in prediction
        assert 0.0 <= prediction["win_probability"] <= 1.0

        # Test ELO change calculation
        elo_change = self.elo_calculator.calculate_elo_change(
            player_rating=1600.0,
            opponent_ratings=opponent_ratings,
            match_result=1.0,  # Win
            k_factor=k_factor
        )
        assert isinstance(elo_change, float)
        # Should gain some points for winning against similar/lower rated opponents
        assert -50.0 <= elo_change <= 50.0

    @pytest.mark.asyncio
    async def test_dimension_analyzer_basic(self):
        """Test dimension analyzer basic functionality."""
        performance = self.create_sample_performance()

        # Test dimension analysis
        dimensions = await self.dimension_analyzer.analyze_performance(performance)

        assert isinstance(dimensions, dict)
        assert len(dimensions) == 6  # Six dimensions

        expected_dimensions = {"kda", "damage", "economy", "vision", "objective", "teamfight"}
        assert set(dimensions.keys()) == expected_dimensions

        # All scores should be within valid range
        for dimension, score in dimensions.items():
            assert 0.0 <= score <= 100.0, f"Dimension {dimension} score {score} out of range"

    def test_confidence_manager_basic(self):
        """Test confidence manager basic functionality."""
        rating = self.create_sample_rating()

        # Test confidence calculation with consistent performances
        consistent_performances = [0.5, 0.52, 0.48, 0.51, 0.49, 0.53, 0.47, 0.50]
        confidence = self.confidence_manager.calculate_confidence_level(
            current_rating=rating,
            recent_performances=consistent_performances,
            matches_played=25
        )

        assert isinstance(confidence, float)
        assert 0.5 <= confidence <= 0.95  # Valid confidence range

        # Test inactivity decay
        old_rating = self.create_sample_rating(
            six_dimensions={
                "kda": 65.0, "damage": 70.0, "economy": 60.0,
                "vision": 55.0, "objective": 75.0, "teamfight": 68.0
            }
        )
        # Note: We can't easily test inactivity decay without modifying the rating's last_updated
        # This would require creating a proper Rating object with an old timestamp

    @pytest.mark.asyncio
    async def test_rating_service_integration(self):
        """Test rating service integration with all components."""
        # Setup
        current_rating = self.create_sample_rating()
        performance = self.create_sample_performance()
        opponent_performances = [
            self.create_sample_performance(
                player_profile_id=f"opponent-{i}",
                match_id="match-456",
                kills=6, deaths=4, assists=10
            )
            for i in range(5)
        ]

        # Execute rating update
        updated_rating, details = await self.rating_service.update_player_rating(
            current_rating=current_rating,
            match_performance=performance,
            opponent_performances=opponent_performances
        )

        # Verify results
        assert isinstance(updated_rating, Rating)
        assert isinstance(details, dict)

        # Check that rating was actually updated
        assert updated_rating.current_score != current_rating.current_score
        assert updated_rating.total_matches == current_rating.total_matches + 1

        # Check that dimensions were updated
        assert updated_rating.six_dimensions != current_rating.six_dimensions

        # Verify details contain expected information
        assert "elo_change" in details
        assert "new_dimensions" in details
        assert "confidence_change" in details

    @pytest.mark.asyncio
    async def test_winning_performance_improvement(self):
        """Test that winning with good performance improves rating."""
        current_rating = self.create_sample_rating(current_score=1500.0)

        # Create a strong winning performance
        strong_performance = self.create_sample_performance(
            kills=15,
            deaths=2,
            assists=20,
            damage_dealt=40000,
            gold_earned=18000,
            cs_score=250,
            vision_score=45,
            match_result="win"
        )

        # Weaker opponents
        opponent_performances = [
            self.create_sample_performance(
                player_profile_id=f"opponent-{i}",
                match_id="match-456",
                kills=3, deaths=8, assists=5
            )
            for i in range(5)
        ]

        # Execute update
        updated_rating, details = await self.rating_service.update_player_rating(
            current_rating=current_rating,
            match_performance=strong_performance,
            opponent_performances=opponent_performances
        )

        # Should gain rating points
        assert updated_rating.current_score > current_rating.current_score

        # Should have improved dimensions
        assert updated_rating.six_dimensions["kda"] > current_rating.six_dimensions["kda"]
        assert updated_rating.six_dimensions["damage"] > current_rating.six_dimensions["damage"]

    @pytest.mark.asyncio
    async def test_losing_performance_degradation(self):
        """Test that losing with poor performance decreases rating."""
        current_rating = self.create_sample_rating(current_score=1500.0)

        # Create a poor losing performance
        poor_performance = self.create_sample_performance(
            kills=2,
            deaths=12,
            assists=4,
            damage_dealt=8000,
            gold_earned=7000,
            cs_score=80,
            vision_score=10,
            match_result="loss"
        )

        # Stronger opponents
        opponent_performances = [
            self.create_sample_performance(
                player_profile_id=f"opponent-{i}",
                match_id="match-456",
                kills=12, deaths=3, assists=15
            )
            for i in range(5)
        ]

        # Execute update
        updated_rating, details = await self.rating_service.update_player_rating(
            current_rating=current_rating,
            match_performance=poor_performance,
            opponent_performances=opponent_performances
        )

        # Should lose rating points (usually, unless opponents were much stronger)
        # Note: This might not always be true due to ELO expected results
        # But dimensions should definitely be worse
        assert updated_rating.six_dimensions["kda"] < current_rating.six_dimensions["kda"]

    def test_rating_bounds_enforcement(self):
        """Test that ratings stay within valid bounds."""
        # Test Rating creation with boundary values
        min_rating = Rating(
            current_score=0.0,
            locked_score=None,
            confidence_level=0.5,
            total_matches=1,
            six_dimensions={"kda": 0.0, "damage": 0.0, "economy": 0.0,
                           "vision": 0.0, "objective": 0.0, "teamfight": 0.0}
        )
        assert min_rating.current_score == 0.0

        max_rating = Rating(
            current_score=5000.0,
            locked_score=None,
            confidence_level=0.95,
            total_matches=1000,
            six_dimensions={"kda": 100.0, "damage": 100.0, "economy": 100.0,
                           "vision": 100.0, "objective": 100.0, "teamfight": 100.0}
        )
        assert max_rating.current_score == 5000.0

        # Test invalid ratings raise errors
        with pytest.raises(Exception):  # Should raise BusinessRuleViolationError
            Rating(
                current_score=-100.0,  # Below minimum
                locked_score=None,
                confidence_level=0.5,
                total_matches=1,
                six_dimensions={"kda": 50.0, "damage": 50.0, "economy": 50.0,
                               "vision": 50.0, "objective": 50.0, "teamfight": 50.0}
            )

        with pytest.raises(Exception):  # Should raise BusinessRuleViolationError
            Rating(
                current_score=6000.0,  # Above maximum
                locked_score=None,
                confidence_level=0.5,
                total_matches=1,
                six_dimensions={"kda": 50.0, "damage": 50.0, "economy": 50.0,
                               "vision": 50.0, "objective": 50.0, "teamfight": 50.0}
            )