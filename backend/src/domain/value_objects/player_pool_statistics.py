"""
Player pool statistics value object for FlyEsports.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

from ..base import ValueObject


@dataclass(frozen=True)
class PlayerPoolStatistics(ValueObject):
    """
    Statistics about a player pool in a region.

    Contains aggregated information about players, ratings distribution,
    activity levels, and other pool-wide metrics.
    """

    # Basic counts
    total_players: int
    active_players: int  # Active within last 30 days
    free_agents: int
    contracted_players: int

    # Position distribution
    position_distribution: Dict[str, int]  # {'TOP': 50, 'JUNGLE': 45, ...}

    # Rating distribution
    average_rating: float
    median_rating: float
    rating_std_deviation: float
    min_rating: float
    max_rating: float

    # Rating tier distribution
    rating_tiers: Dict[str, int]  # {'Bronze': 100, 'Silver': 150, ...}

    # Confidence distribution
    average_confidence: float
    high_confidence_players: int  # Confidence >= 0.8
    low_confidence_players: int   # Confidence < 0.6

    # Activity metrics
    matches_last_week: int
    matches_last_month: int
    most_active_position: str
    least_active_position: str

    # Top performers
    highest_rated_players: List[Dict[str, any]]  # Top 10 players
    most_improved_players: List[Dict[str, any]]  # Biggest rating gains

    # Dimension averages by position
    dimension_averages: Dict[str, Dict[str, float]]  # {'TOP': {'kda': 65.2, ...}, ...}

    # Pool growth metrics
    new_players_last_week: int
    new_players_last_month: int
    retention_rate_30d: float  # Percentage of players still active after 30 days

    # Generation timestamp
    generated_at: datetime

    def __post_init__(self) -> None:
        """Validate statistics data."""
        # Basic validation
        if self.total_players < 0:
            raise ValueError("total_players cannot be negative")

        if self.active_players < 0 or self.active_players > self.total_players:
            raise ValueError("active_players must be between 0 and total_players")

        if self.free_agents < 0 or self.contracted_players < 0:
            raise ValueError("contract counts cannot be negative")

        if self.free_agents + self.contracted_players > self.total_players:
            raise ValueError("contract counts cannot exceed total players")

        # Rating validation
        if self.min_rating < 0 or self.max_rating > 5000:
            raise ValueError("ratings must be within valid range (0-5000)")

        if self.min_rating > self.max_rating:
            raise ValueError("min_rating cannot be greater than max_rating")

        # Confidence validation
        if not (0.5 <= self.average_confidence <= 0.95):
            raise ValueError("average_confidence must be between 0.5 and 0.95")

    @classmethod
    def create_empty(cls, region_id: int) -> "PlayerPoolStatistics":
        """Create empty statistics for a region with no players."""
        return cls(
            total_players=0,
            active_players=0,
            free_agents=0,
            contracted_players=0,
            position_distribution={},
            average_rating=0.0,
            median_rating=0.0,
            rating_std_deviation=0.0,
            min_rating=0.0,
            max_rating=0.0,
            rating_tiers={},
            average_confidence=0.5,
            high_confidence_players=0,
            low_confidence_players=0,
            matches_last_week=0,
            matches_last_month=0,
            most_active_position="",
            least_active_position="",
            highest_rated_players=[],
            most_improved_players=[],
            dimension_averages={},
            new_players_last_week=0,
            new_players_last_month=0,
            retention_rate_30d=0.0,
            generated_at=datetime.utcnow()
        )

    def get_rating_tier(self, rating: float) -> str:
        """
        Get rating tier name for a given rating.

        Args:
            rating: Player rating

        Returns:
            Tier name (e.g., 'Bronze', 'Silver', etc.)
        """
        if rating >= 3000:
            return "Challenger"
        elif rating >= 2500:
            return "Master"
        elif rating >= 2000:
            return "Diamond"
        elif rating >= 1500:
            return "Platinum"
        elif rating >= 1200:
            return "Gold"
        elif rating >= 900:
            return "Silver"
        else:
            return "Bronze"

    def get_position_percentage(self, position: str) -> float:
        """
        Get percentage of players in a specific position.

        Args:
            position: Position name

        Returns:
            Percentage (0.0-100.0)
        """
        if self.total_players == 0:
            return 0.0

        position_count = self.position_distribution.get(position, 0)
        return (position_count / self.total_players) * 100.0

    def get_activity_rate(self) -> float:
        """
        Get overall activity rate (active players / total players).

        Returns:
            Activity rate as percentage (0.0-100.0)
        """
        if self.total_players == 0:
            return 0.0

        return (self.active_players / self.total_players) * 100.0

    def get_free_agent_rate(self) -> float:
        """
        Get free agent rate (free agents / total players).

        Returns:
            Free agent rate as percentage (0.0-100.0)
        """
        if self.total_players == 0:
            return 0.0

        return (self.free_agents / self.total_players) * 100.0

    def is_healthy_pool(self) -> bool:
        """
        Determine if the player pool is considered healthy.

        A healthy pool has:
        - Sufficient player count
        - Good activity rate
        - Reasonable rating distribution
        - Active player growth

        Returns:
            True if pool is considered healthy
        """
        return (
            self.total_players >= 50 and              # Minimum pool size
            self.get_activity_rate() >= 60.0 and      # Good activity rate
            self.average_confidence >= 0.65 and       # Reasonable confidence
            self.new_players_last_month > 0 and       # Growth
            self.retention_rate_30d >= 50.0            # Good retention
        )

    def get_growth_trend(self) -> str:
        """
        Get pool growth trend description.

        Returns:
            Growth trend description ('Growing', 'Stable', 'Declining')
        """
        if self.new_players_last_month >= 10 and self.retention_rate_30d >= 70.0:
            return "Growing"
        elif self.new_players_last_month >= 3 and self.retention_rate_30d >= 50.0:
            return "Stable"
        else:
            return "Declining"

    def get_competitive_balance(self) -> float:
        """
        Calculate competitive balance score.

        Lower standard deviation and good tier distribution indicates
        better competitive balance.

        Returns:
            Balance score (0.0-1.0, higher is better)
        """
        if self.total_players == 0:
            return 0.0

        # Normalized rating standard deviation (lower is better)
        max_std_dev = 800.0  # Reasonable maximum
        std_dev_score = max(0.0, 1.0 - (self.rating_std_deviation / max_std_dev))

        # Tier distribution evenness (more even is better)
        if not self.rating_tiers:
            tier_evenness = 0.0
        else:
            tier_counts = list(self.rating_tiers.values())
            if len(tier_counts) <= 1:
                tier_evenness = 0.5
            else:
                # Calculate coefficient of variation for tiers
                mean_count = sum(tier_counts) / len(tier_counts)
                if mean_count == 0:
                    tier_evenness = 0.0
                else:
                    tier_variance = sum((count - mean_count) ** 2 for count in tier_counts) / len(tier_counts)
                    tier_std = tier_variance ** 0.5
                    tier_cv = tier_std / mean_count
                    tier_evenness = max(0.0, 1.0 - tier_cv)

        # Combine scores
        return (std_dev_score * 0.6) + (tier_evenness * 0.4)

    def get_summary_stats(self) -> Dict[str, any]:
        """
        Get summary statistics for display.

        Returns:
            Dictionary with key statistics
        """
        return {
            "total_players": self.total_players,
            "active_rate": round(self.get_activity_rate(), 1),
            "free_agent_rate": round(self.get_free_agent_rate(), 1),
            "average_rating": round(self.average_rating, 1),
            "rating_spread": round(self.max_rating - self.min_rating, 1),
            "average_confidence": round(self.average_confidence, 2),
            "pool_health": "Healthy" if self.is_healthy_pool() else "Needs Attention",
            "growth_trend": self.get_growth_trend(),
            "competitive_balance": round(self.get_competitive_balance(), 2),
            "most_active_position": self.most_active_position,
            "generated_at": self.generated_at.isoformat()
        }

    def __str__(self) -> str:
        """String representation of pool statistics."""
        return (
            f"PoolStats(players={self.total_players}, "
            f"active={self.get_activity_rate():.1f}%, "
            f"avg_rating={self.average_rating:.0f}, "
            f"health={'✓' if self.is_healthy_pool() else '✗'})"
        )