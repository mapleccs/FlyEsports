"""
Player pool management service for FlyEsports.

Handles player pool operations including querying, filtering, statistics
calculation, and pool management.
"""

import math
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta, timezone

from ..base import DomainService
from ..aggregates.player_profile import PlayerProfile
from ..value_objects.pool_filter import PoolFilter, SortBy, SortOrder, ContractStatus
from ..value_objects.player_pool_statistics import PlayerPoolStatistics
from ..value_objects.rating import Rating


class PlayerPoolManager(DomainService):
    """
    Domain service for managing player pools.

    Provides high-level operations for player pool management including
    filtering, ranking, statistics, and recommendations.
    """

    def __init__(self):
        """Initialize player pool manager."""
        self.default_page_size = 20
        self.max_page_size = 100

    async def filter_and_rank_players(
        self,
        players: List[PlayerProfile],
        pool_filter: PoolFilter
    ) -> Tuple[List[PlayerProfile], int]:
        """
        Filter and rank players based on criteria.

        Args:
            players: List of player profiles to filter
            pool_filter: Filter criteria

        Returns:
            Tuple of (filtered_players, total_count)
        """
        # Apply filters
        filtered_players = await self._apply_filters(players, pool_filter)
        total_count = len(filtered_players)

        # Apply sorting
        sorted_players = await self._apply_sorting(filtered_players, pool_filter)

        # Apply pagination
        paginated_players = self._apply_pagination(sorted_players, pool_filter)

        return paginated_players, total_count

    async def _apply_filters(
        self,
        players: List[PlayerProfile],
        pool_filter: PoolFilter
    ) -> List[PlayerProfile]:
        """Apply all filters to the player list."""
        filtered_players = players.copy()

        # Region filter
        if pool_filter.region_id is not None:
            filtered_players = [
                p for p in filtered_players
                if p.region_id == str(pool_filter.region_id)
            ]

        # Position filter
        if pool_filter.position is not None:
            filtered_players = [
                p for p in filtered_players
                if p.position and p.position.value == pool_filter.position
            ]

        # Contract status filter
        if pool_filter.contract_status != ContractStatus.ALL:
            filtered_players = await self._filter_by_contract_status(
                filtered_players, pool_filter.contract_status
            )

        # Rating filters
        if pool_filter.min_rating is not None:
            filtered_players = [
                p for p in filtered_players
                if p.rating and p.rating.current_score >= pool_filter.min_rating
            ]

        if pool_filter.max_rating is not None:
            filtered_players = [
                p for p in filtered_players
                if p.rating and p.rating.current_score <= pool_filter.max_rating
            ]

        # Confidence filter
        if pool_filter.min_confidence is not None:
            filtered_players = [
                p for p in filtered_players
                if p.rating and p.rating.confidence_level >= pool_filter.min_confidence
            ]

        # Experience filters
        if pool_filter.min_matches is not None:
            filtered_players = [
                p for p in filtered_players
                if p.total_matches >= pool_filter.min_matches
            ]

        if pool_filter.max_matches is not None:
            filtered_players = [
                p for p in filtered_players
                if p.total_matches <= pool_filter.max_matches
            ]

        # Dimension filters
        filtered_players = await self._apply_dimension_filters(filtered_players, pool_filter)

        # Search filters
        filtered_players = await self._apply_search_filters(filtered_players, pool_filter)

        # Activity filters
        if pool_filter.active_within_days is not None:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=pool_filter.active_within_days)
            filtered_players = [
                p for p in filtered_players
                if p.last_active and p.last_active >= cutoff_date
            ]

        # Include/exclude specific players
        if pool_filter.exclude_player_ids:
            filtered_players = [
                p for p in filtered_players
                if p.profile_id not in pool_filter.exclude_player_ids
            ]

        if pool_filter.include_only_player_ids:
            filtered_players = [
                p for p in filtered_players
                if p.profile_id in pool_filter.include_only_player_ids
            ]

        return filtered_players

    async def _filter_by_contract_status(
        self,
        players: List[PlayerProfile],
        contract_status: ContractStatus
    ) -> List[PlayerProfile]:
        """Filter players by contract status."""
        if contract_status == ContractStatus.FREE_AGENT:
            return [
                p for p in players
                if p.contract_status.is_free_agent()
            ]
        elif contract_status == ContractStatus.CONTRACTED:
            return [
                p for p in players
                if not p.contract_status.is_free_agent() and not p.is_rating_locked()
            ]
        elif contract_status == ContractStatus.LOCKED:
            return [
                p for p in players
                if p.is_rating_locked()
            ]
        else:  # ContractStatus.ALL
            return players

    async def _apply_dimension_filters(
        self,
        players: List[PlayerProfile],
        pool_filter: PoolFilter
    ) -> List[PlayerProfile]:
        """Apply dimension-based filters."""
        filtered_players = players.copy()

        dimension_filters = [
            (pool_filter.min_kda_dimension, 'kda'),
            (pool_filter.min_damage_dimension, 'damage'),
            (pool_filter.min_economy_dimension, 'economy'),
            (pool_filter.min_vision_dimension, 'vision'),
            (pool_filter.min_objective_dimension, 'objective'),
            (pool_filter.min_teamfight_dimension, 'teamfight')
        ]

        for min_value, dimension in dimension_filters:
            if min_value is not None:
                filtered_players = [
                    p for p in filtered_players
                    if (p.rating and
                        p.rating.six_dimensions.get(dimension, 0) >= min_value)
                ]

        return filtered_players

    async def _apply_search_filters(
        self,
        players: List[PlayerProfile],
        pool_filter: PoolFilter
    ) -> List[PlayerProfile]:
        """Apply search-based filters."""
        filtered_players = players.copy()

        # Player name search
        if pool_filter.player_name_search:
            search_term = pool_filter.player_name_search.lower().strip()
            filtered_players = [
                p for p in filtered_players
                if search_term in p.player_name.lower()
            ]

        # Summoner name search
        if pool_filter.summoner_name_search:
            search_term = pool_filter.summoner_name_search.lower().strip()
            filtered_players = [
                p for p in filtered_players
                if search_term in p.summoner_name.lower()
            ]

        return filtered_players

    async def _apply_sorting(
        self,
        players: List[PlayerProfile],
        pool_filter: PoolFilter
    ) -> List[PlayerProfile]:
        """Apply sorting to the player list."""
        reverse_order = pool_filter.sort_order == SortOrder.DESC

        if pool_filter.sort_by == SortBy.RATING:
            return sorted(
                players,
                key=lambda p: p.rating.current_score if p.rating else 0,
                reverse=reverse_order
            )
        elif pool_filter.sort_by == SortBy.CONFIDENCE:
            return sorted(
                players,
                key=lambda p: p.rating.confidence_level if p.rating else 0,
                reverse=reverse_order
            )
        elif pool_filter.sort_by == SortBy.MATCHES:
            return sorted(
                players,
                key=lambda p: p.total_matches,
                reverse=reverse_order
            )
        elif pool_filter.sort_by == SortBy.RECENT_ACTIVITY:
            return sorted(
                players,
                key=lambda p: p.last_active or datetime.min.replace(tzinfo=timezone.utc),
                reverse=reverse_order
            )
        elif pool_filter.sort_by == SortBy.PLAYER_NAME:
            return sorted(
                players,
                key=lambda p: p.player_name.lower(),
                reverse=reverse_order
            )
        # Dimension sorting
        elif pool_filter.sort_by in [
            SortBy.KDA_DIMENSION, SortBy.DAMAGE_DIMENSION, SortBy.ECONOMY_DIMENSION,
            SortBy.VISION_DIMENSION, SortBy.OBJECTIVE_DIMENSION, SortBy.TEAMFIGHT_DIMENSION
        ]:
            dimension_map = {
                SortBy.KDA_DIMENSION: 'kda',
                SortBy.DAMAGE_DIMENSION: 'damage',
                SortBy.ECONOMY_DIMENSION: 'economy',
                SortBy.VISION_DIMENSION: 'vision',
                SortBy.OBJECTIVE_DIMENSION: 'objective',
                SortBy.TEAMFIGHT_DIMENSION: 'teamfight'
            }
            dimension = dimension_map[pool_filter.sort_by]
            return sorted(
                players,
                key=lambda p: (p.rating.six_dimensions.get(dimension, 0)
                              if p.rating else 0),
                reverse=reverse_order
            )
        else:
            # Default to rating sorting
            return sorted(
                players,
                key=lambda p: p.rating.current_score if p.rating else 0,
                reverse=True
            )

    def _apply_pagination(
        self,
        players: List[PlayerProfile],
        pool_filter: PoolFilter
    ) -> List[PlayerProfile]:
        """Apply pagination to the player list."""
        start_index = pool_filter.offset
        end_index = start_index + pool_filter.page_size

        return players[start_index:end_index]

    async def calculate_pool_statistics(
        self,
        players: List[PlayerProfile],
        region_id: int
    ) -> PlayerPoolStatistics:
        """
        Calculate comprehensive statistics for a player pool.

        Args:
            players: All players in the pool
            region_id: Region identifier

        Returns:
            PlayerPoolStatistics object
        """
        if not players:
            return PlayerPoolStatistics.create_empty(region_id)

        # Basic counts
        total_players = len(players)
        active_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        active_players = sum(
            1 for p in players
            if p.last_active and p.last_active >= active_cutoff
        )

        free_agents = sum(1 for p in players if p.contract_status.is_available_for_signing)
        contracted_players = total_players - free_agents

        # Position distribution
        position_distribution = {}
        for player in players:
            position = player.position.value if player.position else 'Unknown'
            position_distribution[position] = position_distribution.get(position, 0) + 1

        # Rating statistics
        ratings = [p.rating.current_score for p in players if p.rating]
        if ratings:
            average_rating = sum(ratings) / len(ratings)
            sorted_ratings = sorted(ratings)
            median_rating = sorted_ratings[len(sorted_ratings) // 2]
            min_rating = min(ratings)
            max_rating = max(ratings)

            # Calculate standard deviation
            rating_variance = sum((r - average_rating) ** 2 for r in ratings) / len(ratings)
            rating_std_deviation = math.sqrt(rating_variance)
        else:
            average_rating = median_rating = min_rating = max_rating = 0.0
            rating_std_deviation = 0.0

        # Rating tier distribution
        rating_tiers = {}
        for player in players:
            if player.rating:
                tier = PlayerPoolStatistics.create_empty(region_id).get_rating_tier(
                    player.rating.current_score
                )
                rating_tiers[tier] = rating_tiers.get(tier, 0) + 1

        # Confidence statistics
        confidences = [p.rating.confidence_level for p in players if p.rating]
        if confidences:
            average_confidence = sum(confidences) / len(confidences)
            high_confidence_players = sum(1 for c in confidences if c >= 0.8)
            low_confidence_players = sum(1 for c in confidences if c < 0.6)
        else:
            average_confidence = 0.5
            high_confidence_players = low_confidence_players = 0

        # Activity metrics (simplified - would need match data)
        matches_last_week = matches_last_month = 0
        most_active_position = max(position_distribution.keys(),
                                  key=lambda k: position_distribution[k]) if position_distribution else ""
        least_active_position = min(position_distribution.keys(),
                                   key=lambda k: position_distribution[k]) if position_distribution else ""

        # Top performers (top 10 by rating)
        top_players = sorted(
            players,
            key=lambda p: p.rating.current_score if p.rating else 0,
            reverse=True
        )[:10]

        highest_rated_players = [
            {
                'profile_id': p.profile_id,
                'player_name': p.player_name,
                'rating': p.rating.current_score if p.rating else 0,
                'position': p.position.value if p.position else 'Unknown'
            }
            for p in top_players
        ]

        # Most improved (simplified - would need historical data)
        most_improved_players = []

        # Dimension averages by position
        dimension_averages = {}
        for position, count in position_distribution.items():
            if count == 0:
                continue

            position_players = [p for p in players
                              if p.position and p.position.value == position and p.rating]

            if position_players:
                dimensions = {}
                for dim in ['kda', 'damage', 'economy', 'vision', 'objective', 'teamfight']:
                    values = [p.rating.six_dimensions.get(dim, 50.0) for p in position_players]
                    dimensions[dim] = sum(values) / len(values)
                dimension_averages[position] = dimensions

        # Growth metrics (simplified)
        new_players_last_week = new_players_last_month = 0
        retention_rate_30d = 75.0  # Default assumption

        return PlayerPoolStatistics(
            total_players=total_players,
            active_players=active_players,
            free_agents=free_agents,
            contracted_players=contracted_players,
            position_distribution=position_distribution,
            average_rating=average_rating,
            median_rating=median_rating,
            rating_std_deviation=rating_std_deviation,
            min_rating=min_rating,
            max_rating=max_rating,
            rating_tiers=rating_tiers,
            average_confidence=average_confidence,
            high_confidence_players=high_confidence_players,
            low_confidence_players=low_confidence_players,
            matches_last_week=matches_last_week,
            matches_last_month=matches_last_month,
            most_active_position=most_active_position,
            least_active_position=least_active_position,
            highest_rated_players=highest_rated_players,
            most_improved_players=most_improved_players,
            dimension_averages=dimension_averages,
            new_players_last_week=new_players_last_week,
            new_players_last_month=new_players_last_month,
            retention_rate_30d=retention_rate_30d,
            generated_at=datetime.utcnow()
        )

    async def recommend_players(
        self,
        team_needs: Dict[str, Any],
        available_players: List[PlayerProfile],
        max_recommendations: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recommend players based on team needs.

        Args:
            team_needs: Dictionary describing team requirements
            available_players: List of available players
            max_recommendations: Maximum number of recommendations

        Returns:
            List of player recommendations with scores
        """
        recommendations = []

        for player in available_players:
            # Skip if player doesn't meet basic requirements
            if not self._meets_basic_requirements(player, team_needs):
                continue

            # Calculate recommendation score
            score = await self._calculate_recommendation_score(player, team_needs)

            recommendations.append({
                'player': player,
                'score': score,
                'reasons': await self._get_recommendation_reasons(player, team_needs)
            })

        # Sort by score and return top recommendations
        recommendations.sort(key=lambda r: r['score'], reverse=True)
        return recommendations[:max_recommendations]

    def _meets_basic_requirements(
        self,
        player: PlayerProfile,
        team_needs: Dict[str, Any]
    ) -> bool:
        """Check if player meets basic team requirements."""
        # Position requirement
        if team_needs.get('position') and player.position:
            if player.position.value != team_needs['position']:
                return False

        # Minimum rating requirement
        min_rating = team_needs.get('min_rating', 0)
        if player.rating and player.rating.current_score < min_rating:
            return False

        # Contract status requirement
        if team_needs.get('contract_status') == 'free_agent':
            if not player.contract_status.is_free_agent():
                return False

        return True

    async def _calculate_recommendation_score(
        self,
        player: PlayerProfile,
        team_needs: Dict[str, Any]
    ) -> float:
        """Calculate recommendation score for a player."""
        score = 0.0

        # Base rating score (0-40 points)
        if player.rating:
            rating_score = min(40, player.rating.current_score / 100)
            score += rating_score

        # Confidence bonus (0-20 points)
        if player.rating:
            confidence_score = (player.rating.confidence_level - 0.5) * 40  # Scale to 0-20
            score += max(0, confidence_score)

        # Experience bonus (0-15 points)
        experience_score = min(15, player.total_matches / 10)
        score += experience_score

        # Position fit bonus (0-15 points)
        if team_needs.get('position') and player.position:
            if player.position.value == team_needs['position']:
                score += 15

        # Dimension preferences (0-10 points)
        preferred_dimensions = team_needs.get('preferred_dimensions', {})
        if player.rating and preferred_dimensions:
            dimension_score = 0
            for dimension, weight in preferred_dimensions.items():
                player_dimension = player.rating.six_dimensions.get(dimension, 50.0)
                dimension_score += (player_dimension / 100.0) * weight
            score += min(10, dimension_score)

        return min(100.0, score)  # Cap at 100

    async def _get_recommendation_reasons(
        self,
        player: PlayerProfile,
        team_needs: Dict[str, Any]
    ) -> List[str]:
        """Get reasons why this player is recommended."""
        reasons = []

        # High rating
        if player.rating and player.rating.current_score >= 2000:
            reasons.append(f"High rating ({player.rating.current_score:.0f})")

        # High confidence
        if player.rating and player.rating.confidence_level >= 0.85:
            reasons.append("High confidence rating")

        # Experience
        if player.total_matches >= 50:
            reasons.append(f"Experienced ({player.total_matches} matches)")

        # Position fit
        if team_needs.get('position') and player.position:
            if player.position.value == team_needs['position']:
                reasons.append(f"Perfect position fit ({player.position.value})")

        # Strong dimensions
        if player.rating:
            strong_dimensions = [
                dim for dim, score in player.rating.six_dimensions.items()
                if score >= 75
            ]
            if strong_dimensions:
                reasons.append(f"Strong {', '.join(strong_dimensions)}")

        # Free agent
        if player.contract_status.is_free_agent():
            reasons.append("Available free agent")

        return reasons[:5]  # Limit to top 5 reasons