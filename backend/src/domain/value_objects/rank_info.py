"""
Rank info value object for League of Legends ranks.
"""

from enum import Enum
from dataclasses import dataclass
from typing import ClassVar, Dict, Optional

from ..base import ValueObject, BusinessRuleViolationError


class RankTier(Enum):
    """League of Legends rank tiers."""

    IRON = "IRON"
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"
    EMERALD = "EMERALD"
    DIAMOND = "DIAMOND"
    MASTER = "MASTER"
    GRANDMASTER = "GRANDMASTER"
    CHALLENGER = "CHALLENGER"


class RankDivision(Enum):
    """League of Legends rank divisions."""

    IV = "IV"
    III = "III"
    II = "II"
    TIER_I = "I"


@dataclass(frozen=True)
class RankInfo(ValueObject):
    """
    Rank info value object representing a player's League of Legends rank.
    """

    tier: RankTier
    division: Optional[RankDivision]
    league_points: int

    # Display name mappings
    TIER_DISPLAY_NAMES: ClassVar[Dict[RankTier, str]] = {
        RankTier.IRON: "黑铁",
        RankTier.BRONZE: "青铜",
        RankTier.SILVER: "白银",
        RankTier.GOLD: "黄金",
        RankTier.PLATINUM: "白金",
        RankTier.EMERALD: "翡翠",
        RankTier.DIAMOND: "钻石",
        RankTier.MASTER: "大师",
        RankTier.GRANDMASTER: "宗师",
        RankTier.CHALLENGER: "王者",
    }

    DIVISION_DISPLAY_NAMES: ClassVar[Dict[RankDivision, str]] = {
        RankDivision.IV: "4",
        RankDivision.III: "3",
        RankDivision.II: "2",
        RankDivision.TIER_I: "1",
    }

    # Rank values for comparison (higher is better)
    TIER_VALUES: ClassVar[Dict[RankTier, int]] = {
        RankTier.IRON: 1000,
        RankTier.BRONZE: 2000,
        RankTier.SILVER: 3000,
        RankTier.GOLD: 4000,
        RankTier.PLATINUM: 5000,
        RankTier.EMERALD: 6000,
        RankTier.DIAMOND: 7000,
        RankTier.MASTER: 8000,
        RankTier.GRANDMASTER: 9000,
        RankTier.CHALLENGER: 10000,
    }

    DIVISION_VALUES: ClassVar[Dict[RankDivision, int]] = {
        RankDivision.IV: 0,
        RankDivision.III: 100,
        RankDivision.II: 200,
        RankDivision.TIER_I: 300,
    }

    def __post_init__(self) -> None:
        """Validate rank info after initialization."""
        # Validate league points
        if self.league_points < 0:
            raise BusinessRuleViolationError(
                f"League points cannot be negative, got {self.league_points}"
            )

        if self.league_points > 100 and self.division is not None:
            raise BusinessRuleViolationError(
                f"League points cannot exceed 100 for divisioned ranks, got {self.league_points}"
            )

        # Validate division requirements
        high_tier_ranks = {RankTier.MASTER, RankTier.GRANDMASTER, RankTier.CHALLENGER}
        if self.tier in high_tier_ranks and self.division is not None:
            raise BusinessRuleViolationError(
                f"Tier {self.tier.value} should not have divisions"
            )

        low_tier_ranks = {
            RankTier.IRON,
            RankTier.BRONZE,
            RankTier.SILVER,
            RankTier.GOLD,
            RankTier.PLATINUM,
            RankTier.EMERALD,
            RankTier.DIAMOND,
        }
        if self.tier in low_tier_ranks and self.division is None:
            raise BusinessRuleViolationError(
                f"Tier {self.tier.value} must have a division"
            )

    @classmethod
    def create(
        cls, tier: RankTier, division: Optional[RankDivision], league_points: int
    ) -> "RankInfo":
        """
        Create rank info with validation.

        Args:
            tier: Rank tier
            division: Rank division (None for Master+)
            league_points: League points

        Returns:
            RankInfo instance

        Raises:
            BusinessRuleViolationError: If rank combination is invalid
        """
        return cls(tier=tier, division=division, league_points=league_points)

    @classmethod
    def create_unranked(cls) -> "RankInfo":
        """Create unranked rank info."""
        return cls(tier=RankTier.IRON, division=RankDivision.IV, league_points=0)

    @classmethod
    def from_riot_api(
        cls, tier: str, rank: Optional[str], league_points: int
    ) -> "RankInfo":
        """
        Create RankInfo from Riot API data.

        Args:
            tier: Tier string from Riot API
            rank: Rank string from Riot API (e.g., 'IV', 'III', etc.)
            league_points: League points from Riot API

        Returns:
            RankInfo value object

        Raises:
            BusinessRuleViolationError: If data is invalid
        """
        try:
            tier_enum = RankTier(tier.upper())
        except ValueError:
            raise BusinessRuleViolationError(f"Invalid tier: {tier}")

        division_enum = None
        if rank:
            try:
                division_enum = RankDivision(rank.upper())
            except ValueError:
                raise BusinessRuleViolationError(f"Invalid division: {rank}")

        return cls(tier=tier_enum, division=division_enum, league_points=league_points)

    @property
    def display_name(self) -> str:
        """Get the display name for the rank."""
        tier_name = self.TIER_DISPLAY_NAMES[self.tier]
        if self.division:
            division_name = self.DIVISION_DISPLAY_NAMES[self.division]
            return f"{tier_name} {division_name}"
        return tier_name

    @property
    def tier_display_name(self) -> str:
        """Get the tier display name."""
        return self.TIER_DISPLAY_NAMES[self.tier]

    @property
    def division_display_name(self) -> Optional[str]:
        """Get the division display name."""
        if self.division:
            return self.DIVISION_DISPLAY_NAMES[self.division]
        return None

    @property
    def numeric_value(self) -> int:
        """Get numeric value for comparison (higher is better)."""
        tier_value = self.TIER_VALUES[self.tier]
        division_value = self.DIVISION_VALUES.get(self.division, 0)
        return tier_value + division_value + self.league_points

    @property
    def is_high_tier(self) -> bool:
        """Check if this is a high tier rank (Master+)."""
        return self.tier in {RankTier.MASTER, RankTier.GRANDMASTER, RankTier.CHALLENGER}

    @property
    def is_unranked(self) -> bool:
        """Check if this is unranked."""
        return (
            self.tier == RankTier.IRON
            and self.division == RankDivision.IV
            and self.league_points == 0
        )

    def __str__(self) -> str:
        """String representation of the rank."""
        return self.display_name

    def __hash__(self) -> int:
        """Hash based on tier, division, and league points."""
        return hash((self.tier, self.division, self.league_points))

    def __lt__(self, other: "RankInfo") -> bool:
        """Less than comparison for ranking."""
        if not isinstance(other, RankInfo):
            return NotImplemented
        return self.numeric_value < other.numeric_value

    def __le__(self, other: "RankInfo") -> bool:
        """Less than or equal comparison."""
        if not isinstance(other, RankInfo):
            return NotImplemented
        return self.numeric_value <= other.numeric_value

    def __gt__(self, other: "RankInfo") -> bool:
        """Greater than comparison."""
        if not isinstance(other, RankInfo):
            return NotImplemented
        return self.numeric_value > other.numeric_value

    def __ge__(self, other: "RankInfo") -> bool:
        """Greater than or equal comparison."""
        if not isinstance(other, RankInfo):
            return NotImplemented
        return self.numeric_value >= other.numeric_value
