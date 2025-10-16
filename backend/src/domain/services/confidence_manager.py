"""
Confidence level management for player ratings in FlyEsports.

The confidence system tracks how reliable a player's rating is based on:
- Number of matches played
- Consistency of recent performance
- Quality of opponents faced
- Recency of activity
"""

import math
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from ..base import DomainService
from ..value_objects.match_performance import MatchPerformance


class ConfidenceManager(DomainService):
    """
    Manages confidence levels for player ratings.

    Confidence levels range from 0.5 (minimum) to 0.95 (maximum) and represent
    how reliable we consider a player's rating to be.
    """

    def __init__(self):
        """Initialize confidence manager with default parameters."""
        self.initial_confidence = 0.5   # Starting confidence for new players
        self.max_confidence = 0.95      # Maximum achievable confidence
        self.min_confidence = 0.5       # Minimum confidence level
        self.base_growth_rate = 0.01    # Base confidence growth per match

    async def calculate_confidence_level(
        self,
        current_confidence: float,
        match_performance: MatchPerformance,
        recent_performances: List[MatchPerformance],
        total_matches: int,
        opponent_average_rating: Optional[float] = None
    ) -> float:
        """
        Calculate updated confidence level after a match.

        Args:
            current_confidence: Current confidence level
            match_performance: Latest match performance
            recent_performances: Recent match performances (up to last 20)
            total_matches: Total matches played by the player
            opponent_average_rating: Average rating of opponents (optional)

        Returns:
            Updated confidence level (0.5-0.95)
        """
        # 1. Base confidence growth
        base_growth = self._calculate_base_growth(total_matches)

        # 2. Consistency factor based on recent performance
        consistency_factor = await self._calculate_consistency_factor(
            match_performance, recent_performances
        )

        # 3. Match quality factor
        quality_factor = self._calculate_match_quality_factor(
            match_performance, opponent_average_rating
        )

        # 4. Activity recency factor
        activity_factor = await self._calculate_activity_factor(recent_performances)

        # 5. Performance level factor
        performance_factor = self._calculate_performance_factor(match_performance)

        # Calculate total confidence change
        confidence_change = (
            base_growth *
            consistency_factor *
            quality_factor *
            activity_factor *
            performance_factor
        )

        # Apply change and ensure bounds
        new_confidence = current_confidence + confidence_change
        return max(self.min_confidence, min(self.max_confidence, new_confidence))

    def _calculate_base_growth(self, total_matches: int) -> float:
        """
        Calculate base confidence growth based on total matches.

        Growth rate decreases as player accumulates more matches.
        """
        if total_matches < 5:
            return self.base_growth_rate * 3.0      # Fast initial growth
        elif total_matches < 15:
            return self.base_growth_rate * 2.0      # Moderate growth
        elif total_matches < 50:
            return self.base_growth_rate * 1.5      # Standard growth
        elif total_matches < 100:
            return self.base_growth_rate * 1.0      # Slower growth
        else:
            return self.base_growth_rate * 0.5      # Minimal growth for veterans

    async def _calculate_consistency_factor(
        self,
        current_performance: MatchPerformance,
        recent_performances: List[MatchPerformance]
    ) -> float:
        """
        Calculate consistency factor based on performance variance.

        More consistent performance leads to higher confidence growth.
        """
        if len(recent_performances) < 3:
            return 1.0  # Insufficient data for consistency analysis

        # Calculate performance metrics variance
        metrics = [
            'kda', 'dpm', 'gpm', 'teamfight_participation'
        ]

        consistency_scores = []

        for metric in metrics:
            if not hasattr(current_performance, metric):
                continue

            # Get metric values from recent performances
            recent_values = []
            for perf in recent_performances:
                if hasattr(perf, metric):
                    value = getattr(perf, metric)
                    if value is not None:
                        recent_values.append(value)

            if len(recent_values) < 3:
                continue

            # Calculate coefficient of variation (std/mean)
            mean_value = sum(recent_values) / len(recent_values)
            if mean_value == 0:
                continue

            variance = sum((x - mean_value) ** 2 for x in recent_values) / len(recent_values)
            std_dev = math.sqrt(variance)
            cv = std_dev / mean_value if mean_value > 0 else 0

            # Convert CV to consistency score (lower CV = higher consistency)
            consistency_score = max(0.5, 1.0 - cv)
            consistency_scores.append(consistency_score)

        if not consistency_scores:
            return 1.0

        # Average consistency across all metrics
        average_consistency = sum(consistency_scores) / len(consistency_scores)

        # Convert to multiplier (0.8 to 1.3 range)
        return 0.8 + (average_consistency * 0.5)

    def _calculate_match_quality_factor(
        self,
        match_performance: MatchPerformance,
        opponent_average_rating: Optional[float] = None
    ) -> float:
        """
        Calculate match quality factor.

        Higher quality matches (proper duration, competitive opponents)
        provide more confidence value.
        """
        quality_factor = 1.0

        # Duration factor
        duration_minutes = match_performance.match_duration / 60.0
        if duration_minutes < 15:
            quality_factor *= 0.7   # Short games provide less information
        elif duration_minutes > 50:
            quality_factor *= 0.85  # Very long games may have unusual circumstances
        else:
            quality_factor *= 1.0   # Normal duration games

        # Match type factor (would need additional data in MatchPerformance)
        # For now, assume all matches are of equal type importance

        # Opponent strength factor (if available)
        if opponent_average_rating is not None:
            # Playing against similarly skilled opponents provides more value
            # This would require the current player's rating for comparison
            # For now, assume neutral impact
            quality_factor *= 1.0

        return max(0.6, min(1.4, quality_factor))

    async def _calculate_activity_factor(
        self,
        recent_performances: List[MatchPerformance]
    ) -> float:
        """
        Calculate activity recency factor.

        Regular activity maintains confidence growth, while inactivity reduces it.
        """
        if not recent_performances:
            return 0.8  # Penalty for no recent activity

        # Check time since last match
        most_recent = max(recent_performances, key=lambda p: p.played_at)
        time_since_last = datetime.utcnow() - most_recent.played_at
        days_since_last = time_since_last.total_seconds() / 86400

        # Calculate activity factor based on recency
        if days_since_last <= 1:
            return 1.2      # Very recent activity bonus
        elif days_since_last <= 7:
            return 1.0      # Recent activity (normal)
        elif days_since_last <= 14:
            return 0.9      # Somewhat inactive
        elif days_since_last <= 30:
            return 0.8      # Inactive
        else:
            return 0.6      # Very inactive

    def _calculate_performance_factor(
        self,
        match_performance: MatchPerformance
    ) -> float:
        """
        Calculate performance level factor.

        Exceptional or poor performances may indicate rating instability,
        while consistent performance builds confidence.
        """
        # This is a simplified version - in a full implementation,
        # you'd compare against the player's expected performance level

        kda = match_performance.kda or 0.0

        if kda >= 5.0 or kda <= 0.5:
            # Extreme performances suggest possible rating mismatch
            return 0.9
        elif kda >= 3.0 or kda <= 1.0:
            # Strong but not extreme performance
            return 1.0
        else:
            # Normal performance range builds confidence
            return 1.1

    async def bulk_update_confidence_levels(
        self,
        player_data: Dict[str, Dict],
        performance_history: Dict[str, List[MatchPerformance]]
    ) -> Dict[str, float]:
        """
        Bulk update confidence levels for multiple players.

        Args:
            player_data: Dictionary with player info (current_confidence, total_matches, etc.)
            performance_history: Dictionary with recent performances per player

        Returns:
            Dictionary with updated confidence levels per player
        """
        updated_confidence = {}

        for player_id, data in player_data.items():
            performances = performance_history.get(player_id, [])

            if not performances:
                # No recent performances - apply decay
                current_confidence = data.get('current_confidence', self.initial_confidence)
                decayed_confidence = await self._apply_inactivity_decay(
                    current_confidence, data.get('days_since_last_match', 0)
                )
                updated_confidence[player_id] = decayed_confidence
                continue

            # Get latest performance and recent history
            latest_performance = performances[0]  # Assume sorted by recency
            recent_performances = performances[1:21]  # Up to 20 recent performances
            total_matches = data.get('total_matches', len(performances))
            current_confidence = data.get('current_confidence', self.initial_confidence)

            # Calculate new confidence
            new_confidence = await self.calculate_confidence_level(
                current_confidence=current_confidence,
                match_performance=latest_performance,
                recent_performances=recent_performances,
                total_matches=total_matches,
                opponent_average_rating=data.get('opponent_average_rating')
            )

            updated_confidence[player_id] = new_confidence

        return updated_confidence

    async def _apply_inactivity_decay(
        self,
        current_confidence: float,
        days_since_last_match: int
    ) -> float:
        """
        Apply confidence decay for inactive players.

        Confidence gradually decreases when players are inactive,
        as their rating becomes less reliable over time.
        """
        if days_since_last_match <= 7:
            return current_confidence  # No decay for recent activity

        # Calculate decay based on inactivity period
        if days_since_last_match <= 30:
            decay_rate = 0.001  # Minimal decay
        elif days_since_last_match <= 90:
            decay_rate = 0.003  # Moderate decay
        else:
            decay_rate = 0.005  # Significant decay

        # Apply exponential decay
        decay_amount = current_confidence * decay_rate * (days_since_last_match / 7)
        new_confidence = current_confidence - decay_amount

        return max(self.min_confidence, new_confidence)

    def get_confidence_category(self, confidence_level: float) -> str:
        """
        Get human-readable confidence category.

        Args:
            confidence_level: Confidence level (0.5-0.95)

        Returns:
            Confidence category string
        """
        if confidence_level >= 0.9:
            return "VERY_HIGH"
        elif confidence_level >= 0.8:
            return "HIGH"
        elif confidence_level >= 0.7:
            return "MEDIUM"
        elif confidence_level >= 0.6:
            return "LOW"
        else:
            return "VERY_LOW"

    def should_display_rating(
        self,
        confidence_level: float,
        total_matches: int,
        min_matches_threshold: int = 5
    ) -> bool:
        """
        Determine if a player's rating should be displayed publicly.

        Args:
            confidence_level: Current confidence level
            total_matches: Total matches played
            min_matches_threshold: Minimum matches required

        Returns:
            True if rating should be displayed
        """
        return (
            total_matches >= min_matches_threshold and
            confidence_level >= 0.6
        )

    def calculate_rating_uncertainty(
        self,
        confidence_level: float,
        base_rating: float
    ) -> tuple:
        """
        Calculate rating display range based on confidence.

        Args:
            confidence_level: Current confidence level
            base_rating: Base rating value

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        # Higher confidence = smaller uncertainty range
        uncertainty_factor = (1.0 - confidence_level) * 200  # Max 100 points uncertainty

        lower_bound = max(0, base_rating - uncertainty_factor)
        upper_bound = min(5000, base_rating + uncertainty_factor)

        return lower_bound, upper_bound