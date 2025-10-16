"""
ELO rating calculation service for FlyEsports.

Based on the traditional ELO rating system with adaptations for team-based esports,
particularly League of Legends 5v5 matches.
"""

import math
from typing import List, Optional, Tuple
from datetime import datetime

from ..base import DomainService
from ..value_objects.match_performance import MatchPerformance


class ELOCalculator(DomainService):
    """
    ELO rating calculation service.

    Implements the traditional ELO rating system with modifications for:
    - Team-based competitions (5v5)
    - Dynamic K-factor based on player experience and confidence
    - Position-aware adjustments
    """

    def __init__(self):
        """Initialize ELO calculator with default parameters."""
        self.base_k_factor = 32
        self.rating_scale = 400  # Standard ELO scale parameter
        self.min_rating = 0.0
        self.max_rating = 5000.0

    def calculate_elo_change(
        self,
        player_rating: float,
        opponent_ratings: List[float],
        match_result: float,
        k_factor: Optional[float] = None,
        team_ratings: Optional[List[float]] = None,
        opponent_team_ratings: Optional[List[float]] = None
    ) -> float:
        """
        Calculate ELO rating change for a player.

        Args:
            player_rating: Current player rating
            opponent_ratings: List of opponent player ratings
            match_result: Match result (1.0=win, 0.0=loss, 0.5=draw)
            k_factor: Custom K-factor (optional)
            team_ratings: Player's team ratings for team balance calculation
            opponent_team_ratings: Opponent team ratings for team balance calculation

        Returns:
            Rating change value (can be positive or negative)
        """
        if not opponent_ratings:
            return 0.0

        # Use provided K-factor or default
        if k_factor is None:
            k_factor = self.base_k_factor

        # Calculate expected score
        if team_ratings and opponent_team_ratings:
            # Use team-based expectation for more accurate results
            expected_score = self._calculate_team_expected_score(
                team_ratings, opponent_team_ratings, player_rating
            )
        else:
            # Fall back to individual player expectation
            expected_score = self._calculate_individual_expected_score(
                player_rating, opponent_ratings
            )

        # ELO change formula: K * (actual_result - expected_result)
        rating_change = k_factor * (match_result - expected_score)

        # Ensure the new rating stays within bounds
        new_rating = player_rating + rating_change
        if new_rating < self.min_rating:
            rating_change = self.min_rating - player_rating
        elif new_rating > self.max_rating:
            rating_change = self.max_rating - player_rating

        return rating_change

    def _calculate_individual_expected_score(
        self,
        player_rating: float,
        opponent_ratings: List[float]
    ) -> float:
        """
        Calculate expected score against individual opponents.

        Uses the standard ELO expectation formula:
        E = 1 / (1 + 10^((R_opponent - R_player) / scale))

        For multiple opponents, uses average opponent rating.
        """
        if not opponent_ratings:
            return 0.5

        # Calculate average opponent rating
        avg_opponent_rating = sum(opponent_ratings) / len(opponent_ratings)

        # Rating difference
        rating_diff = avg_opponent_rating - player_rating

        # ELO expectation formula
        expected = 1.0 / (1.0 + math.pow(10, rating_diff / self.rating_scale))

        # Ensure expectation is within valid bounds
        return max(0.01, min(0.99, expected))

    def _calculate_team_expected_score(
        self,
        team_ratings: List[float],
        opponent_team_ratings: List[float],
        player_rating: float
    ) -> float:
        """
        Calculate expected score considering full team composition.

        This method considers:
        - Team average rating strength
        - Team balance (rating variance)
        - Individual player position within their team
        """
        if not team_ratings or not opponent_team_ratings:
            return 0.5

        # Team average ratings
        team_avg = sum(team_ratings) / len(team_ratings)
        opponent_avg = sum(opponent_team_ratings) / len(opponent_team_ratings)

        # Base expectation from team averages
        rating_diff = opponent_avg - team_avg
        base_expected = 1.0 / (1.0 + math.pow(10, rating_diff / self.rating_scale))

        # Team balance factor
        team_variance = self._calculate_variance(team_ratings)
        opponent_variance = self._calculate_variance(opponent_team_ratings)

        # More balanced teams (lower variance) get slight advantage
        balance_factor = 1.0 + (opponent_variance - team_variance) / 10000.0
        balance_factor = max(0.95, min(1.05, balance_factor))  # Limit to ±5%

        # Individual player position within team
        player_strength_in_team = self._calculate_player_team_position(
            player_rating, team_ratings
        )

        # Adjust expectation based on player's relative strength within team
        individual_factor = 0.9 + (player_strength_in_team * 0.2)  # 0.9 to 1.1 range
        individual_factor = max(0.9, min(1.1, individual_factor))

        # Combine factors
        adjusted_expected = base_expected * balance_factor * individual_factor

        return max(0.01, min(0.99, adjusted_expected))

    def _calculate_variance(self, ratings: List[float]) -> float:
        """Calculate variance of a list of ratings."""
        if len(ratings) <= 1:
            return 0.0

        mean = sum(ratings) / len(ratings)
        variance = sum((r - mean) ** 2 for r in ratings) / len(ratings)
        return variance

    def _calculate_player_team_position(
        self,
        player_rating: float,
        team_ratings: List[float]
    ) -> float:
        """
        Calculate player's relative position within their team.

        Returns:
            Value between 0.0 (weakest) and 1.0 (strongest) in team
        """
        if not team_ratings or len(team_ratings) <= 1:
            return 0.5

        # Sort team ratings to find player's position
        sorted_ratings = sorted(team_ratings)

        # Find where player rating would fit in sorted list
        position = 0
        for rating in sorted_ratings:
            if player_rating > rating:
                position += 1

        # Convert to 0.0-1.0 scale
        return position / (len(sorted_ratings) - 1) if len(sorted_ratings) > 1 else 0.5

    def calculate_rating_uncertainty(
        self,
        current_rating: float,
        recent_performances: List[MatchPerformance],
        confidence_level: float
    ) -> float:
        """
        Calculate rating uncertainty based on recent performance variance.

        Args:
            current_rating: Current player rating
            recent_performances: List of recent match performances
            confidence_level: Current confidence level (0.5-0.95)

        Returns:
            Rating uncertainty value (higher = more uncertain)
        """
        if not recent_performances or len(recent_performances) < 3:
            return 100.0  # High uncertainty for insufficient data

        # Calculate performance variance
        performance_results = [perf.match_result for perf in recent_performances]
        mean_result = sum(performance_results) / len(performance_results)
        variance = sum((r - mean_result) ** 2 for r in performance_results) / len(performance_results)

        # Base uncertainty from performance variance
        performance_uncertainty = variance * 200  # Scale to rating points

        # Adjust by confidence level
        confidence_factor = (1.0 - confidence_level) * 100  # Higher when less confident

        # Combine factors
        total_uncertainty = performance_uncertainty + confidence_factor

        return min(200.0, max(10.0, total_uncertainty))

    def predict_match_outcome(
        self,
        team1_ratings: List[float],
        team2_ratings: List[float]
    ) -> Tuple[float, float]:
        """
        Predict match outcome probabilities for two teams.

        Args:
            team1_ratings: Team 1 player ratings
            team2_ratings: Team 2 player ratings

        Returns:
            Tuple of (team1_win_probability, team2_win_probability)
        """
        if not team1_ratings or not team2_ratings:
            return 0.5, 0.5

        # Calculate team average ratings
        team1_avg = sum(team1_ratings) / len(team1_ratings)
        team2_avg = sum(team2_ratings) / len(team2_ratings)

        # Use ELO expectation formula
        rating_diff = team2_avg - team1_avg
        team1_win_prob = 1.0 / (1.0 + math.pow(10, rating_diff / self.rating_scale))
        team2_win_prob = 1.0 - team1_win_prob

        return team1_win_prob, team2_win_prob


class DynamicKFactorCalculator(DomainService):
    """
    Dynamic K-factor calculator for adaptive ELO rating changes.

    Adjusts K-factor based on various factors:
    - Player experience (total matches)
    - Confidence level
    - Current rating level
    - Recent performance stability
    """

    def __init__(self):
        """Initialize with default K-factor parameters."""
        self.base_k = 32
        self.min_k = 16
        self.max_k = 64

    def calculate_k_factor(
        self,
        current_rating: float,
        confidence_level: float,
        total_matches: int,
        recent_performance_variance: float = 0.0,
        rating_level_factor: bool = True
    ) -> float:
        """
        Calculate dynamic K-factor for a player.

        Args:
            current_rating: Current player rating
            confidence_level: Confidence level (0.5-0.95)
            total_matches: Total number of matches played
            recent_performance_variance: Variance in recent performance
            rating_level_factor: Whether to apply rating level adjustments

        Returns:
            Calculated K-factor value
        """
        k_factor = self.base_k

        # 1. Experience-based adjustment
        experience_multiplier = self._get_experience_multiplier(total_matches)
        k_factor *= experience_multiplier

        # 2. Confidence-based adjustment
        confidence_multiplier = self._get_confidence_multiplier(confidence_level)
        k_factor *= confidence_multiplier

        # 3. Rating level adjustment
        if rating_level_factor:
            rating_multiplier = self._get_rating_multiplier(current_rating)
            k_factor *= rating_multiplier

        # 4. Performance stability adjustment
        if recent_performance_variance > 0:
            stability_multiplier = self._get_stability_multiplier(recent_performance_variance)
            k_factor *= stability_multiplier

        # Ensure K-factor is within bounds
        return max(self.min_k, min(self.max_k, k_factor))

    def _get_experience_multiplier(self, total_matches: int) -> float:
        """Calculate K-factor multiplier based on player experience."""
        if total_matches < 10:
            return 2.0      # New players: large rating swings
        elif total_matches < 25:
            return 1.6      # Learning phase: significant changes
        elif total_matches < 50:
            return 1.3      # Growth phase: moderate changes
        elif total_matches < 100:
            return 1.1      # Stabilizing phase: smaller changes
        else:
            return 1.0      # Experienced: minimal changes

    def _get_confidence_multiplier(self, confidence_level: float) -> float:
        """Calculate K-factor multiplier based on confidence level."""
        # Lower confidence = higher K-factor (more uncertainty)
        return 1.0 + (1.0 - confidence_level) * 0.8

    def _get_rating_multiplier(self, current_rating: float) -> float:
        """Calculate K-factor multiplier based on rating level."""
        if current_rating <= 800:
            return 1.4      # Low ratings: easier to climb
        elif current_rating >= 3500:
            return 0.7      # High ratings: harder to change
        else:
            # Gradual transition in middle ratings
            normalized = (current_rating - 800) / (3500 - 800)
            return 1.4 - (normalized * 0.7)  # Linear interpolation

    def _get_stability_multiplier(self, performance_variance: float) -> float:
        """Calculate K-factor multiplier based on performance stability."""
        # Higher variance = higher K-factor (inconsistent performance)
        if performance_variance > 0.3:     # Very inconsistent
            return 1.3
        elif performance_variance > 0.2:   # Somewhat inconsistent
            return 1.15
        elif performance_variance > 0.1:   # Slightly inconsistent
            return 1.05
        else:                              # Very consistent
            return 1.0