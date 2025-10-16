"""
Player rating update service for FlyEsports.

Orchestrates the rating calculation process by combining:
- ELO rating calculations
- Six-dimensional performance analysis
- Confidence level management
- Rating history tracking
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime

from ..base import DomainService
from ..value_objects.match_performance import MatchPerformance
from ..value_objects.rating import Rating
from .elo_calculator import ELOCalculator, DynamicKFactorCalculator
from .six_dimension_analyzer import SixDimensionAnalyzer
from .confidence_manager import ConfidenceManager


class RatingUpdateService(DomainService):
    """
    Service for updating player ratings after matches.

    This service combines multiple rating algorithms and factors to produce
    accurate, fair, and dynamic rating updates.
    """

    def __init__(self):
        """Initialize rating update service with component calculators."""
        self.elo_calculator = ELOCalculator()
        self.k_factor_calculator = DynamicKFactorCalculator()
        self.six_dimension_analyzer = SixDimensionAnalyzer()
        self.confidence_manager = ConfidenceManager()

        # Rating adjustment parameters
        self.max_rating_change_per_match = 100.0  # Maximum rating change per match
        self.performance_adjustment_weight = 0.3   # Weight of performance vs ELO adjustment

    async def update_player_rating(
        self,
        current_rating: Rating,
        match_performance: MatchPerformance,
        opponent_performances: List[MatchPerformance],
        team_performances: Optional[List[MatchPerformance]] = None,
        historical_performances: Optional[List[MatchPerformance]] = None
    ) -> Tuple[Rating, Dict[str, any]]:
        """
        Update a player's rating based on match performance.

        Args:
            current_rating: Current player rating
            match_performance: Player's performance in the match
            opponent_performances: Opponent performances for ELO calculation
            team_performances: Teammate performances (optional)
            historical_performances: Recent performance history (optional)

        Returns:
            Tuple of (new_rating, calculation_details)
        """
        calculation_details = {
            'timestamp': datetime.utcnow(),
            'match_id': match_performance.match_id,
            'player_id': match_performance.player_profile_id,
            'position': match_performance.position,
            'match_result': match_performance.match_result
        }

        try:
            # 1. Calculate ELO rating change
            elo_change, elo_details = await self._calculate_elo_change(
                current_rating, match_performance, opponent_performances, team_performances
            )
            calculation_details['elo_change'] = elo_change
            calculation_details['elo_details'] = elo_details

            # 2. Analyze six-dimensional performance
            dimension_scores = await self.six_dimension_analyzer.analyze_performance(
                match_performance, match_performance.player_profile_id
            )
            calculation_details['dimension_scores'] = dimension_scores

            # 3. Calculate performance-based adjustment
            performance_adjustment = await self._calculate_performance_adjustment(
                dimension_scores, current_rating.six_dimensions, match_performance.position
            )
            calculation_details['performance_adjustment'] = performance_adjustment

            # 4. Combine ELO and performance adjustments
            total_rating_change = self._combine_rating_adjustments(
                elo_change, performance_adjustment
            )
            calculation_details['total_rating_change'] = total_rating_change

            # 5. Apply rating change with bounds checking
            new_score = self._apply_rating_change(
                current_rating.current_score, total_rating_change
            )
            calculation_details['new_score'] = new_score

            # 6. Update confidence level
            new_confidence = await self._update_confidence_level(
                current_rating, match_performance, historical_performances or []
            )
            calculation_details['new_confidence'] = new_confidence

            # 7. Create new rating object
            new_rating = Rating(
                current_score=new_score,
                locked_score=current_rating.locked_score,  # Preserve locked status
                confidence_level=new_confidence,
                total_matches=current_rating.total_matches + 1,
                six_dimensions=dimension_scores
            )

            calculation_details['success'] = True
            return new_rating, calculation_details

        except Exception as e:
            calculation_details['error'] = str(e)
            calculation_details['success'] = False
            # Return unchanged rating on error
            return current_rating, calculation_details

    async def _calculate_elo_change(
        self,
        current_rating: Rating,
        match_performance: MatchPerformance,
        opponent_performances: List[MatchPerformance],
        team_performances: Optional[List[MatchPerformance]] = None
    ) -> Tuple[float, Dict[str, any]]:
        """Calculate ELO rating change with dynamic K-factor."""

        details = {}

        # Get opponent ratings
        opponent_ratings = [
            perf.player_profile_id  # Would need to get actual ratings from repository
            for perf in opponent_performances
        ]

        # For now, simulate opponent ratings (in real implementation, fetch from repository)
        simulated_opponent_ratings = [current_rating.current_score + i * 50 for i in range(-2, 3)]
        details['opponent_ratings'] = simulated_opponent_ratings

        # Calculate dynamic K-factor
        k_factor = self.k_factor_calculator.calculate_k_factor(
            current_rating=current_rating.current_score,
            confidence_level=current_rating.confidence_level,
            total_matches=current_rating.total_matches,
            recent_performance_variance=0.1  # Would calculate from historical data
        )
        details['k_factor'] = k_factor

        # Get team ratings if available
        team_ratings = None
        opponent_team_ratings = None

        if team_performances and opponent_performances:
            # Simulate team ratings (in real implementation, fetch from repository)
            team_ratings = [current_rating.current_score + i * 30 for i in range(-2, 3)]
            opponent_team_ratings = simulated_opponent_ratings
            details['team_ratings'] = team_ratings
            details['opponent_team_ratings'] = opponent_team_ratings

        # Calculate ELO change
        elo_change = self.elo_calculator.calculate_elo_change(
            player_rating=current_rating.current_score,
            opponent_ratings=simulated_opponent_ratings,
            match_result=match_performance.match_result,
            k_factor=k_factor,
            team_ratings=team_ratings,
            opponent_team_ratings=opponent_team_ratings
        )

        return elo_change, details

    async def _calculate_performance_adjustment(
        self,
        current_dimensions: Dict[str, float],
        historical_dimensions: Dict[str, float],
        position: str
    ) -> float:
        """
        Calculate rating adjustment based on performance dimensions.

        Compares current performance dimensions against historical averages
        and applies position-specific weights.
        """
        # Position-specific dimension weights for rating impact
        position_weights = {
            'TOP': {
                'kda': 0.25, 'damage': 0.20, 'economy': 0.15,
                'vision': 0.10, 'objective': 0.20, 'teamfight': 0.10
            },
            'JUNGLE': {
                'kda': 0.20, 'damage': 0.15, 'economy': 0.15,
                'vision': 0.25, 'objective': 0.25, 'teamfight': 0.00
            },
            'MIDDLE': {
                'kda': 0.20, 'damage': 0.25, 'economy': 0.15,
                'vision': 0.10, 'objective': 0.15, 'teamfight': 0.15
            },
            'BOTTOM': {
                'kda': 0.15, 'damage': 0.30, 'economy': 0.20,
                'vision': 0.05, 'objective': 0.15, 'teamfight': 0.15
            },
            'UTILITY': {
                'kda': 0.10, 'damage': 0.05, 'economy': 0.10,
                'vision': 0.30, 'objective': 0.20, 'teamfight': 0.25
            }
        }

        weights = position_weights.get(position, position_weights['MIDDLE'])
        total_adjustment = 0.0

        for dimension, current_score in current_dimensions.items():
            historical_score = historical_dimensions.get(dimension, 50.0)  # Default to 50
            weight = weights.get(dimension, 0.0)

            # Calculate dimension difference (positive = improvement, negative = decline)
            dimension_diff = current_score - historical_score

            # Apply weight and convert to rating adjustment
            # Scale factor: 1 point difference in dimension = 0.5 rating points
            weighted_adjustment = dimension_diff * weight * 0.5
            total_adjustment += weighted_adjustment

        # Limit performance adjustment to reasonable bounds
        return max(-20.0, min(20.0, total_adjustment))

    def _combine_rating_adjustments(
        self,
        elo_change: float,
        performance_adjustment: float
    ) -> float:
        """
        Combine ELO change and performance adjustment.

        ELO provides the base rating change, while performance adjustment
        provides fine-tuning based on detailed performance analysis.
        """
        # Weight the adjustments
        elo_weight = 1.0 - self.performance_adjustment_weight
        performance_weight = self.performance_adjustment_weight

        combined_change = (
            elo_change * elo_weight +
            performance_adjustment * performance_weight
        )

        # Limit total change to maximum per match
        return max(
            -self.max_rating_change_per_match,
            min(self.max_rating_change_per_match, combined_change)
        )

    def _apply_rating_change(
        self,
        current_score: float,
        rating_change: float
    ) -> float:
        """
        Apply rating change while respecting rating bounds.
        """
        new_score = current_score + rating_change

        # Ensure new score is within valid bounds
        return max(
            Rating.MIN_RATING,
            min(Rating.MAX_RATING, new_score)
        )

    async def _update_confidence_level(
        self,
        current_rating: Rating,
        match_performance: MatchPerformance,
        historical_performances: List[MatchPerformance]
    ) -> float:
        """Update confidence level based on match performance."""

        return await self.confidence_manager.calculate_confidence_level(
            current_confidence=current_rating.confidence_level,
            match_performance=match_performance,
            recent_performances=historical_performances[-20:],  # Last 20 matches
            total_matches=current_rating.total_matches + 1
        )

    async def batch_update_ratings(
        self,
        match_performances: List[MatchPerformance],
        current_ratings: Dict[str, Rating],
        team1_performances: List[MatchPerformance],
        team2_performances: List[MatchPerformance]
    ) -> Dict[str, Tuple[Rating, Dict[str, any]]]:
        """
        Batch update ratings for all players in a match.

        Args:
            match_performances: All player performances in the match
            current_ratings: Current ratings for all players
            team1_performances: Team 1 player performances
            team2_performances: Team 2 player performances

        Returns:
            Dictionary mapping player IDs to (new_rating, details) tuples
        """
        results = {}

        for performance in match_performances:
            player_id = performance.player_profile_id
            current_rating = current_ratings.get(player_id)

            if current_rating is None:
                # Create initial rating for new player
                current_rating = Rating.create_initial(1200.0)  # Default starting rating

            # Determine teammates and opponents
            if performance in team1_performances:
                team_performances = [p for p in team1_performances if p.player_profile_id != player_id]
                opponent_performances = team2_performances
            else:
                team_performances = [p for p in team2_performances if p.player_profile_id != player_id]
                opponent_performances = team1_performances

            # Update rating
            new_rating, details = await self.update_player_rating(
                current_rating=current_rating,
                match_performance=performance,
                opponent_performances=opponent_performances,
                team_performances=team_performances
            )

            results[player_id] = (new_rating, details)

        return results

    def calculate_rating_volatility(
        self,
        recent_changes: List[float],
        confidence_level: float
    ) -> float:
        """
        Calculate rating volatility based on recent rating changes.

        Args:
            recent_changes: List of recent rating changes
            confidence_level: Current confidence level

        Returns:
            Volatility score (0.0 = stable, 1.0 = highly volatile)
        """
        if not recent_changes or len(recent_changes) < 3:
            return 0.5  # Default moderate volatility for insufficient data

        # Calculate standard deviation of recent changes
        mean_change = sum(recent_changes) / len(recent_changes)
        variance = sum((change - mean_change) ** 2 for change in recent_changes) / len(recent_changes)
        std_deviation = variance ** 0.5

        # Normalize to 0-1 scale (assuming max std dev of 50 rating points)
        normalized_volatility = min(1.0, std_deviation / 50.0)

        # Adjust by confidence level (lower confidence = higher perceived volatility)
        confidence_adjustment = (1.0 - confidence_level) * 0.3

        return min(1.0, normalized_volatility + confidence_adjustment)