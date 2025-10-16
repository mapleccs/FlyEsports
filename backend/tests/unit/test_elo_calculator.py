"""
Unit tests for ELO calculator service.
"""

import pytest
from datetime import datetime, timedelta

from src.domain.services.elo_calculator import ELOCalculator
from src.domain.value_objects.rating import Rating


class TestEloCalculator:
    """Test suite for ELO calculator."""

    def setup_method(self):
        """Setup test instance."""
        self.calculator = ELOCalculator()

    def test_calculate_k_factor_new_player(self):
        """Test K-factor calculation for new player."""
        # New player with low confidence and few matches
        rating = Rating(
            current_score=1200.0,
            locked_score=None,
            confidence_level=0.5,
            total_matches=5,
            six_dimensions={"kda": 50.0, "damage": 50.0, "economy": 50.0,
                           "vision": 50.0, "objective": 50.0, "teamfight": 50.0}
        )

        k_factor = self.calculator.calculate_k_factor(rating, matches_played=5)

        # New player should have high K-factor (around 50-60)
        assert 45.0 <= k_factor <= 65.0

    def test_calculate_k_factor_experienced_player(self):
        """Test K-factor calculation for experienced player."""
        # Experienced player with high confidence
        rating = Rating(
            current_score=2000.0,
            locked_score=None,
            confidence_level=0.85,
            total_matches=100,
            six_dimensions={"kda": 70.0, "damage": 75.0, "economy": 65.0,
                           "vision": 60.0, "objective": 80.0, "teamfight": 70.0}
        )

        k_factor = self.calculator.calculate_k_factor(rating, matches_played=100)

        # Experienced player should have lower K-factor (around 20-30)
        assert 15.0 <= k_factor <= 35.0

    def test_calculate_k_factor_master_player(self):
        """Test K-factor calculation for master-tier player."""
        # Master tier player (2500+ rating)
        rating = Rating(
            current_score=2600.0,
            locked_score=None,
            confidence_level=0.90,
            total_matches=200,
            six_dimensions={"kda": 85.0, "damage": 90.0, "economy": 80.0,
                           "vision": 75.0, "objective": 85.0, "teamfight": 88.0}
        )

        k_factor = self.calculator.calculate_k_factor(rating, matches_played=200)

        # Master player should have very low K-factor (10-20)
        assert 8.0 <= k_factor <= 22.0

    def test_calculate_expected_score_equal_teams(self):
        """Test expected score calculation for equal teams."""
        # Equal team ratings should result in ~0.5 expected score
        player_rating = 1500.0
        opponent_ratings = [1500.0, 1500.0, 1500.0, 1500.0, 1500.0]

        expected = self.calculator.calculate_expected_score(player_rating, opponent_ratings)

        # Should be very close to 0.5 for equal teams
        assert 0.48 <= expected <= 0.52

    def test_calculate_expected_score_stronger_player(self):
        """Test expected score for stronger player vs weaker opponents."""
        player_rating = 2000.0
        opponent_ratings = [1500.0, 1600.0, 1400.0, 1550.0, 1450.0]

        expected = self.calculator.calculate_expected_score(player_rating, opponent_ratings)

        # Stronger player should have higher expected score
        assert expected > 0.7

    def test_calculate_expected_score_weaker_player(self):
        """Test expected score for weaker player vs stronger opponents."""
        player_rating = 1200.0
        opponent_ratings = [1800.0, 1900.0, 1750.0, 1850.0, 1700.0]

        expected = self.calculator.calculate_expected_score(player_rating, opponent_ratings)

        # Weaker player should have lower expected score
        assert expected < 0.3

    def test_calculate_elo_change_win_expected(self):
        """Test ELO change when winning an expected match."""
        player_rating = 1800.0
        opponent_ratings = [1400.0, 1500.0, 1300.0, 1450.0, 1350.0]
        match_result = 1.0  # Win
        k_factor = 30.0

        elo_change = self.calculator.calculate_elo_change(
            player_rating, opponent_ratings, match_result, k_factor
        )

        # Should gain points but not too many (expected win)
        assert 2.0 <= elo_change <= 15.0

    def test_calculate_elo_change_win_upset(self):
        """Test ELO change when winning an upset match."""
        player_rating = 1300.0
        opponent_ratings = [1800.0, 1900.0, 1750.0, 1850.0, 1700.0]
        match_result = 1.0  # Win
        k_factor = 40.0

        elo_change = self.calculator.calculate_elo_change(
            player_rating, opponent_ratings, match_result, k_factor
        )

        # Should gain many points (upset win)
        assert elo_change >= 25.0

    def test_calculate_elo_change_loss_expected(self):
        """Test ELO change when losing an expected loss."""
        player_rating = 1300.0
        opponent_ratings = [1800.0, 1900.0, 1750.0, 1850.0, 1700.0]
        match_result = 0.0  # Loss
        k_factor = 40.0

        elo_change = self.calculator.calculate_elo_change(
            player_rating, opponent_ratings, match_result, k_factor
        )

        # Should lose few points (expected loss)
        assert -15.0 <= elo_change <= -2.0

    def test_calculate_elo_change_loss_upset(self):
        """Test ELO change when losing an upset match."""
        player_rating = 1900.0
        opponent_ratings = [1300.0, 1400.0, 1250.0, 1350.0, 1200.0]
        match_result = 0.0  # Loss
        k_factor = 25.0

        elo_change = self.calculator.calculate_elo_change(
            player_rating, opponent_ratings, match_result, k_factor
        )

        # Should lose many points (upset loss)
        assert elo_change <= -20.0

    def test_calculate_elo_change_draw(self):
        """Test ELO change for a draw."""
        player_rating = 1600.0
        opponent_ratings = [1600.0, 1600.0, 1600.0, 1600.0, 1600.0]
        match_result = 0.5  # Draw
        k_factor = 30.0

        elo_change = self.calculator.calculate_elo_change(
            player_rating, opponent_ratings, match_result, k_factor
        )

        # Should have minimal change for expected draw
        assert -2.0 <= elo_change <= 2.0

    def test_rating_boundaries(self):
        """Test that ratings don't go below minimum or above maximum."""
        # Test minimum rating boundary
        player_rating = 500.0  # Very low rating
        opponent_ratings = [2000.0, 2100.0, 1900.0, 2050.0, 1950.0]
        match_result = 0.0  # Loss
        k_factor = 50.0

        elo_change = self.calculator.calculate_elo_change(
            player_rating, opponent_ratings, match_result, k_factor
        )

        # Even with large loss, should not result in negative final rating
        final_rating = player_rating + elo_change
        assert final_rating >= 200.0

        # Test maximum rating boundary
        player_rating = 4000.0  # Very high rating
        opponent_ratings = [1000.0, 1100.0, 900.0, 1050.0, 950.0]
        match_result = 1.0  # Win
        k_factor = 10.0

        elo_change = self.calculator.calculate_elo_change(
            player_rating, opponent_ratings, match_result, k_factor
        )

        # Should gain minimal points at high rating
        assert 0.0 <= elo_change <= 5.0

    def test_team_balance_consideration(self):
        """Test that team balance affects expected score calculation."""
        # Test with balanced teams
        player_rating = 1600.0
        balanced_opponents = [1600.0, 1600.0, 1600.0, 1600.0, 1600.0]

        expected_balanced = self.calculator.calculate_expected_score(
            player_rating, balanced_opponents
        )

        # Test with unbalanced teams (mix of high and low rated opponents)
        unbalanced_opponents = [2000.0, 1200.0, 2100.0, 1100.0, 1900.0]

        expected_unbalanced = self.calculator.calculate_expected_score(
            player_rating, unbalanced_opponents
        )

        # Both should be around 0.5 if average is same, but unbalanced might vary slightly
        assert 0.4 <= expected_balanced <= 0.6
        assert 0.3 <= expected_unbalanced <= 0.7

    def test_invalid_match_result(self):
        """Test handling of invalid match result values."""
        player_rating = 1500.0
        opponent_ratings = [1500.0, 1500.0, 1500.0, 1500.0, 1500.0]
        k_factor = 30.0

        # Test invalid match results
        invalid_results = [-0.5, 1.5, 2.0, -1.0]

        for invalid_result in invalid_results:
            with pytest.raises(ValueError):
                self.calculator.calculate_elo_change(
                    player_rating, opponent_ratings, invalid_result, k_factor
                )

    def test_empty_opponent_list(self):
        """Test handling of empty opponent ratings list."""
        player_rating = 1500.0
        opponent_ratings = []
        match_result = 1.0
        k_factor = 30.0

        with pytest.raises(ValueError):
            self.calculator.calculate_elo_change(
                player_rating, opponent_ratings, match_result, k_factor
            )

    def test_negative_ratings(self):
        """Test handling of negative ratings."""
        # Negative player rating should raise error
        with pytest.raises(ValueError):
            self.calculator.calculate_elo_change(
                -100.0, [1500.0], 1.0, 30.0
            )

        # Negative opponent rating should raise error
        with pytest.raises(ValueError):
            self.calculator.calculate_elo_change(
                1500.0, [1500.0, -200.0], 1.0, 30.0
            )