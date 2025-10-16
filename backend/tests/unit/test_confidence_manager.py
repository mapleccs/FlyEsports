"""
Unit tests for confidence manager service.
"""

import pytest
from datetime import datetime, timedelta

from src.domain.services.confidence_manager import ConfidenceManager
from src.domain.value_objects.rating import Rating


class TestConfidenceManager:
    """Test suite for confidence manager."""

    def setup_method(self):
        """Setup test instance."""
        self.manager = ConfidenceManager()

    def test_calculate_confidence_new_player(self):
        """Test confidence calculation for new player."""
        # New player with minimal matches
        rating = Rating(
            current_score=1200.0,
            confidence_level=0.5,
            six_dimensions={"kda": 50.0, "damage": 50.0, "economy": 50.0,
                           "vision": 50.0, "objective": 50.0, "teamfight": 50.0},
            matches_played=5,
            last_updated=datetime.utcnow(),
            is_locked=False
        )

        recent_performances = [0.6, 0.4, 0.7, 0.5, 0.8]  # Mixed results

        new_confidence = self.manager.calculate_confidence_level(
            current_rating=rating,
            recent_performances=recent_performances,
            matches_played=5
        )

        # New player should have relatively low confidence
        assert 0.5 <= new_confidence <= 0.7

    def test_calculate_confidence_experienced_consistent_player(self):
        """Test confidence calculation for experienced, consistent player."""
        rating = Rating(
            current_score=1800.0,
            confidence_level=0.75,
            six_dimensions={"kda": 70.0, "damage": 75.0, "economy": 65.0,
                           "vision": 60.0, "objective": 80.0, "teamfight": 70.0},
            matches_played=100,
            last_updated=datetime.utcnow(),
            is_locked=False
        )

        # Consistent performance around expected level
        recent_performances = [0.52, 0.48, 0.51, 0.49, 0.53, 0.47, 0.52, 0.48, 0.50, 0.51]

        new_confidence = self.manager.calculate_confidence_level(
            current_rating=rating,
            recent_performances=recent_performances,
            matches_played=100
        )

        # Experienced consistent player should have high confidence
        assert new_confidence >= 0.8

    def test_calculate_confidence_inconsistent_player(self):
        """Test confidence calculation for inconsistent player."""
        rating = Rating(
            current_score=1600.0,
            confidence_level=0.7,
            six_dimensions={"kda": 60.0, "damage": 65.0, "economy": 55.0,
                           "vision": 50.0, "objective": 70.0, "teamfight": 65.0},
            matches_played=50,
            last_updated=datetime.utcnow(),
            is_locked=False
        )

        # Very inconsistent performance
        recent_performances = [0.9, 0.1, 0.8, 0.2, 0.95, 0.05, 0.85, 0.15, 0.9, 0.1]

        new_confidence = self.manager.calculate_confidence_level(
            current_rating=rating,
            recent_performances=recent_performances,
            matches_played=50
        )

        # Inconsistent player should have lower confidence
        assert new_confidence <= 0.65

    def test_calculate_confidence_minimum_bound(self):
        """Test that confidence never goes below minimum."""
        rating = Rating(
            current_score=1000.0,
            confidence_level=0.5,
            six_dimensions={"kda": 30.0, "damage": 35.0, "economy": 25.0,
                           "vision": 40.0, "objective": 30.0, "teamfight": 35.0},
            matches_played=10,
            last_updated=datetime.utcnow(),
            is_locked=False
        )

        # Extremely poor and inconsistent performance
        recent_performances = [0.0, 0.0, 0.1, 0.0, 0.0, 0.05, 0.0, 0.0, 0.1, 0.0]

        new_confidence = self.manager.calculate_confidence_level(
            current_rating=rating,
            recent_performances=recent_performances,
            matches_played=10
        )

        # Should not go below minimum confidence
        assert new_confidence >= 0.5

    def test_calculate_confidence_maximum_bound(self):
        """Test that confidence never exceeds maximum."""
        rating = Rating(
            current_score=2500.0,
            confidence_level=0.9,
            six_dimensions={"kda": 90.0, "damage": 95.0, "economy": 85.0,
                           "vision": 80.0, "objective": 90.0, "teamfight": 95.0},
            matches_played=500,
            last_updated=datetime.utcnow(),
            is_locked=False
        )

        # Perfect consistency at high level
        recent_performances = [0.95, 0.96, 0.94, 0.97, 0.95, 0.96, 0.94, 0.95, 0.97, 0.96]

        new_confidence = self.manager.calculate_confidence_level(
            current_rating=rating,
            recent_performances=recent_performances,
            matches_played=500
        )

        # Should not exceed maximum confidence
        assert new_confidence <= 0.95

    def test_apply_inactivity_decay_no_decay(self):
        """Test no inactivity decay for recent activity."""
        rating = Rating(
            current_score=1700.0,
            confidence_level=0.8,
            six_dimensions={"kda": 65.0, "damage": 70.0, "economy": 60.0,
                           "vision": 55.0, "objective": 75.0, "teamfight": 68.0},
            matches_played=80,
            last_updated=datetime.utcnow(),  # Updated now
            is_locked=False
        )

        decayed_confidence = self.manager.apply_inactivity_decay(rating)

        # No decay for recent activity
        assert decayed_confidence == 0.8

    def test_apply_inactivity_decay_moderate(self):
        """Test moderate inactivity decay."""
        # 45 days since last update
        last_updated = datetime.utcnow() - timedelta(days=45)
        rating = Rating(
            current_score=1700.0,
            confidence_level=0.8,
            six_dimensions={"kda": 65.0, "damage": 70.0, "economy": 60.0,
                           "vision": 55.0, "objective": 75.0, "teamfight": 68.0},
            matches_played=80,
            last_updated=last_updated,
            is_locked=False
        )

        decayed_confidence = self.manager.apply_inactivity_decay(rating)

        # Should have moderate decay
        assert 0.75 <= decayed_confidence < 0.8

    def test_apply_inactivity_decay_heavy(self):
        """Test heavy inactivity decay."""
        # 120 days since last update
        last_updated = datetime.utcnow() - timedelta(days=120)
        rating = Rating(
            current_score=1900.0,
            confidence_level=0.9,
            six_dimensions={"kda": 80.0, "damage": 85.0, "economy": 75.0,
                           "vision": 70.0, "objective": 85.0, "teamfight": 82.0},
            matches_played=150,
            last_updated=last_updated,
            is_locked=False
        )

        decayed_confidence = self.manager.apply_inactivity_decay(rating)

        # Should have heavy decay
        assert 0.6 <= decayed_confidence < 0.75

    def test_apply_inactivity_decay_minimum_bound(self):
        """Test that inactivity decay respects minimum bound."""
        # 365 days since last update (very inactive)
        last_updated = datetime.utcnow() - timedelta(days=365)
        rating = Rating(
            current_score=1500.0,
            confidence_level=0.7,
            six_dimensions={"kda": 55.0, "damage": 60.0, "economy": 50.0,
                           "vision": 45.0, "objective": 65.0, "teamfight": 58.0},
            matches_played=30,
            last_updated=last_updated,
            is_locked=False
        )

        decayed_confidence = self.manager.apply_inactivity_decay(rating)

        # Should not go below minimum
        assert decayed_confidence >= 0.5

    def test_calculate_performance_variance_low(self):
        """Test calculation of low performance variance."""
        # Very consistent performances
        performances = [0.51, 0.49, 0.52, 0.48, 0.50, 0.51, 0.49, 0.52, 0.48, 0.50]

        variance = self.manager._calculate_performance_variance(performances)

        # Should have very low variance
        assert variance < 0.05

    def test_calculate_performance_variance_high(self):
        """Test calculation of high performance variance."""
        # Very inconsistent performances
        performances = [0.9, 0.1, 0.95, 0.05, 0.85, 0.15, 0.9, 0.1, 0.8, 0.2]

        variance = self.manager._calculate_performance_variance(performances)

        # Should have high variance
        assert variance > 0.3

    def test_calculate_performance_variance_empty_list(self):
        """Test handling of empty performance list."""
        performances = []

        variance = self.manager._calculate_performance_variance(performances)

        # Should return default high variance for no data
        assert variance > 0.5

    def test_calculate_performance_variance_single_value(self):
        """Test handling of single performance value."""
        performances = [0.6]

        variance = self.manager._calculate_performance_variance(performances)

        # Should return high variance for insufficient data
        assert variance > 0.4

    def test_confidence_with_locked_rating(self):
        """Test confidence handling for locked ratings."""
        locked_rating = Rating(
            current_score=1500.0,
            confidence_level=0.8,
            six_dimensions={"kda": 60.0, "damage": 65.0, "economy": 55.0,
                           "vision": 50.0, "objective": 70.0, "teamfight": 65.0},
            matches_played=50,
            last_updated=datetime.utcnow() - timedelta(days=60),
            is_locked=True  # Rating is locked
        )

        # Should still apply inactivity decay even for locked ratings
        decayed_confidence = self.manager.apply_inactivity_decay(locked_rating)

        # Confidence should decay for locked ratings too
        assert decayed_confidence < 0.8

    def test_confidence_gradual_improvement(self):
        """Test confidence improvement with gradually better performances."""
        rating = Rating(
            current_score=1400.0,
            confidence_level=0.6,
            six_dimensions={"kda": 45.0, "damage": 50.0, "economy": 40.0,
                           "vision": 35.0, "objective": 55.0, "teamfight": 48.0},
            matches_played=40,
            last_updated=datetime.utcnow(),
            is_locked=False
        )

        # Gradually improving performances
        recent_performances = [0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]

        new_confidence = self.manager.calculate_confidence_level(
            current_rating=rating,
            recent_performances=recent_performances,
            matches_played=40
        )

        # Should improve confidence with consistent improvement
        assert new_confidence > 0.6

    def test_confidence_with_varying_match_counts(self):
        """Test confidence calculation with different match counts."""
        base_rating = Rating(
            current_score=1600.0,
            confidence_level=0.7,
            six_dimensions={"kda": 60.0, "damage": 65.0, "economy": 55.0,
                           "vision": 50.0, "objective": 70.0, "teamfight": 65.0},
            matches_played=0,  # Will be overridden
            last_updated=datetime.utcnow(),
            is_locked=False
        )

        performances = [0.5, 0.6, 0.4, 0.7, 0.3, 0.8, 0.2, 0.9, 0.1, 0.85]

        # Test with very few matches
        low_matches_confidence = self.manager.calculate_confidence_level(
            current_rating=base_rating,
            recent_performances=performances[:3],
            matches_played=10
        )

        # Test with many matches
        high_matches_confidence = self.manager.calculate_confidence_level(
            current_rating=base_rating,
            recent_performances=performances,
            matches_played=200
        )

        # More matches should generally lead to higher confidence
        # (assuming same performance pattern)
        assert high_matches_confidence >= low_matches_confidence

    def test_edge_case_perfect_performances(self):
        """Test edge case with perfect performances."""
        rating = Rating(
            current_score=2000.0,
            confidence_level=0.8,
            six_dimensions={"kda": 80.0, "damage": 85.0, "economy": 75.0,
                           "vision": 70.0, "objective": 85.0, "teamfight": 82.0},
            matches_played=100,
            last_updated=datetime.utcnow(),
            is_locked=False
        )

        # All perfect performances
        perfect_performances = [1.0] * 10

        new_confidence = self.manager.calculate_confidence_level(
            current_rating=rating,
            recent_performances=perfect_performances,
            matches_played=100
        )

        # Should have very high confidence with perfect consistency
        assert new_confidence >= 0.9

    def test_edge_case_all_losses(self):
        """Test edge case with all losses."""
        rating = Rating(
            current_score=1200.0,
            confidence_level=0.65,
            six_dimensions={"kda": 40.0, "damage": 45.0, "economy": 35.0,
                           "vision": 30.0, "objective": 50.0, "teamfight": 42.0},
            matches_played=50,
            last_updated=datetime.utcnow(),
            is_locked=False
        )

        # All losses
        loss_performances = [0.0] * 10

        new_confidence = self.manager.calculate_confidence_level(
            current_rating=rating,
            recent_performances=loss_performances,
            matches_played=50
        )

        # Even with all losses, if consistent, confidence shouldn't drop too much
        # But should be lower than current
        assert new_confidence < 0.65
        assert new_confidence >= 0.5  # Minimum bound