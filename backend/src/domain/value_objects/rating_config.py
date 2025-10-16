"""
Rating configuration value object for region-specific rating settings.
"""

from dataclasses import dataclass
from typing import Dict, Any

from ..base import ValueObject, BusinessRuleViolationError


@dataclass(frozen=True)
class RatingConfig(ValueObject):
    """
    Rating configuration value object for region-specific rating parameters.

    Manages ELO calculation settings, confidence parameters,
    and rating constraints
    for a specific region.
    """

    # Base rating settings (ELO system)
    initial_rating: float = 1200.0
    min_rating: float = 0.0
    max_rating: float = 5000.0

    # ELO calculation parameters
    k_factor: float = 32.0
    confidence_multiplier: float = 1.5

    # Confidence system settings
    min_confidence: float = 0.5
    max_confidence: float = 0.95
    confidence_gain_per_match: float = 0.01

    # Rating adjustment settings
    placement_matches: int = 10
    rating_decay_enabled: bool = True
    decay_threshold_days: int = 30
    decay_rate_per_day: float = 0.1

    # Six dimensions weights
    dimension_weights: Dict[str, float] = None

    # Matchmaking settings
    rating_range_multiplier: float = 1.2
    max_rating_difference: float = 300.0

    def __post_init__(self) -> None:
        """Validate rating configuration after initialization."""
        # Set default dimension weights if None
        if self.dimension_weights is None:
            default_weights = {
                "kda": 0.20,
                "damage": 0.18,
                "economy": 0.16,
                "vision": 0.15,
                "objective": 0.16,
                "teamfight": 0.15,
            }
            object.__setattr__(self, "dimension_weights", default_weights)

        # Validate rating bounds
        if self.min_rating < 0:
            raise BusinessRuleViolationError(
                f"Minimum rating cannot be negative, got {self.min_rating}"
            )

        if self.max_rating <= self.min_rating:
            raise BusinessRuleViolationError(
                f"Maximum rating ({self.max_rating}) must be greater than "
                f"minimum rating ({self.min_rating})"
            )

        if not (self.min_rating <= self.initial_rating <= self.max_rating):
            raise BusinessRuleViolationError(
                f"Initial rating ({self.initial_rating}) must be between "
                f"min ({self.min_rating}) and max ({self.max_rating})"
            )

        # Validate K-factor
        if self.k_factor <= 0 or self.k_factor > 100:
            raise BusinessRuleViolationError(
                f"K-factor must be between 0 and 100, got {self.k_factor}"
            )

        # Validate confidence settings
        if self.min_confidence < 0 or self.min_confidence > 1:
            raise BusinessRuleViolationError(
                f"Minimum confidence must be between 0 and 1, "
                f"got {self.min_confidence}"
            )

        if self.max_confidence < 0 or self.max_confidence > 1:
            raise BusinessRuleViolationError(
                f"Maximum confidence must be between 0 and 1, "
                f"got {self.max_confidence}"
            )

        if self.max_confidence <= self.min_confidence:
            raise BusinessRuleViolationError(
                f"Maximum confidence ({self.max_confidence}) must be "
                f"greater than minimum confidence ({self.min_confidence})"
            )

        if self.confidence_gain_per_match <= 0 or self.confidence_gain_per_match > 0.1:
            raise BusinessRuleViolationError(
                f"Confidence gain per match must be between 0 and 0.1, "
                f"got {self.confidence_gain_per_match}"
            )

        if self.confidence_multiplier <= 0 or self.confidence_multiplier > 5:
            raise BusinessRuleViolationError(
                f"Confidence multiplier must be between 0 and 5, "
                f"got {self.confidence_multiplier}"
            )

        # Validate placement matches
        if self.placement_matches < 0 or self.placement_matches > 50:
            raise BusinessRuleViolationError(
                f"Placement matches must be between 0 and 50, "
                f"got {self.placement_matches}"
            )

        # Validate decay settings
        if self.decay_threshold_days <= 0:
            raise BusinessRuleViolationError(
                f"Decay threshold days must be positive, "
                f"got {self.decay_threshold_days}"
            )

        if self.decay_rate_per_day < 0 or self.decay_rate_per_day > 5:
            raise BusinessRuleViolationError(
                f"Decay rate per day must be between 0 and 5, "
                f"got {self.decay_rate_per_day}"
            )

        # Validate dimension weights
        if not isinstance(self.dimension_weights, dict):
            raise BusinessRuleViolationError("Dimension weights must be a dictionary")

        required_dimensions = {
            "kda",
            "damage",
            "economy",
            "vision",
            "objective",
            "teamfight",
        }
        if set(self.dimension_weights.keys()) != required_dimensions:
            raise BusinessRuleViolationError(
                f"Dimension weights must contain exactly these keys: "
                f"{required_dimensions}"
            )

        # Validate weight values
        for dim, weight in self.dimension_weights.items():
            if not isinstance(weight, (int, float)):
                raise BusinessRuleViolationError(
                    f"Weight for dimension {dim} must be numeric, "
                    f"got {type(weight)}"
                )
            if weight < 0 or weight > 1:
                raise BusinessRuleViolationError(
                    f"Weight for dimension {dim} must be between 0 and 1, "
                    f"got {weight}"
                )

        # Validate weight sum (should equal 1.0)
        weight_sum = sum(self.dimension_weights.values())
        if abs(weight_sum - 1.0) > 0.001:  # Allow small floating point errors
            raise BusinessRuleViolationError(
                f"Dimension weights must sum to 1.0, got {weight_sum}"
            )

        # Validate matchmaking settings
        if self.rating_range_multiplier <= 1.0 or self.rating_range_multiplier > 5.0:
            raise BusinessRuleViolationError(
                f"Rating range multiplier must be between 1.0 and 5.0, "
                f"got {self.rating_range_multiplier}"
            )

        if self.max_rating_difference <= 0 or self.max_rating_difference > 1000:
            raise BusinessRuleViolationError(
                f"Max rating difference must be between 0 and 1000, "
                f"got {self.max_rating_difference}"
            )

    @classmethod
    def create_default(cls) -> "RatingConfig":
        """Create default rating configuration."""
        return cls()

    @classmethod
    def create_competitive(cls) -> "RatingConfig":
        """Create competitive rating configuration with stricter settings."""
        return cls(
            initial_rating=1300.0,
            k_factor=28.0,
            confidence_multiplier=1.8,
            placement_matches=15,
            max_rating_difference=200.0,
            rating_range_multiplier=1.1,
        )

    @classmethod
    def create_casual(cls) -> "RatingConfig":
        """Create casual rating configuration with more relaxed settings."""
        return cls(
            initial_rating=1100.0,
            k_factor=40.0,
            confidence_multiplier=1.2,
            placement_matches=5,
            max_rating_difference=400.0,
            rating_range_multiplier=1.5,
            rating_decay_enabled=False,
        )

    def with_updated_k_factor(self, k_factor: float) -> "RatingConfig":
        """Create new config with updated K-factor."""
        return RatingConfig(
            initial_rating=self.initial_rating,
            min_rating=self.min_rating,
            max_rating=self.max_rating,
            k_factor=k_factor,
            confidence_multiplier=self.confidence_multiplier,
            min_confidence=self.min_confidence,
            max_confidence=self.max_confidence,
            confidence_gain_per_match=self.confidence_gain_per_match,
            placement_matches=self.placement_matches,
            rating_decay_enabled=self.rating_decay_enabled,
            decay_threshold_days=self.decay_threshold_days,
            decay_rate_per_day=self.decay_rate_per_day,
            dimension_weights=self.dimension_weights,
            rating_range_multiplier=self.rating_range_multiplier,
            max_rating_difference=self.max_rating_difference,
        )

    def with_updated_dimension_weights(
        self, dimension_weights: Dict[str, float]
    ) -> "RatingConfig":
        """Create new config with updated dimension weights."""
        return RatingConfig(
            initial_rating=self.initial_rating,
            min_rating=self.min_rating,
            max_rating=self.max_rating,
            k_factor=self.k_factor,
            confidence_multiplier=self.confidence_multiplier,
            min_confidence=self.min_confidence,
            max_confidence=self.max_confidence,
            confidence_gain_per_match=self.confidence_gain_per_match,
            placement_matches=self.placement_matches,
            rating_decay_enabled=self.rating_decay_enabled,
            decay_threshold_days=self.decay_threshold_days,
            decay_rate_per_day=self.decay_rate_per_day,
            dimension_weights=dimension_weights,
            rating_range_multiplier=self.rating_range_multiplier,
            max_rating_difference=self.max_rating_difference,
        )

    def calculate_effective_k_factor(
        self, confidence: float, matches_played: int
    ) -> float:
        """
        Calculate effective K-factor based on confidence and match count.

        Args:
            confidence: Player's confidence level
            matches_played: Number of matches played

        Returns:
            Effective K-factor for rating calculation
        """
        # Higher K-factor for low confidence (less certain ratings)
        confidence_factor = (2.0 - confidence) if confidence < 1.0 else 1.0

        # Higher K-factor for new players (fewer matches)
        if matches_played < self.placement_matches:
            placement_factor = 2.0 - (matches_played / self.placement_matches)
        else:
            placement_factor = 1.0

        return self.k_factor * confidence_factor * placement_factor

    def is_placement_period(self, matches_played: int) -> bool:
        """Check if player is still in placement period."""
        return matches_played < self.placement_matches

    def should_apply_decay(self, days_inactive: int) -> bool:
        """Check if rating decay should be applied."""
        return self.rating_decay_enabled and days_inactive > self.decay_threshold_days

    def calculate_decay_amount(self, days_inactive: int) -> float:
        """
        Calculate rating decay amount.

        Args:
            days_inactive: Number of days since last activity

        Returns:
            Amount to decay from rating
        """
        if not self.should_apply_decay(days_inactive):
            return 0.0

        excess_days = days_inactive - self.decay_threshold_days
        return excess_days * self.decay_rate_per_day

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "initial_rating": self.initial_rating,
            "min_rating": self.min_rating,
            "max_rating": self.max_rating,
            "k_factor": self.k_factor,
            "confidence_multiplier": self.confidence_multiplier,
            "min_confidence": self.min_confidence,
            "max_confidence": self.max_confidence,
            "confidence_gain_per_match": self.confidence_gain_per_match,
            "placement_matches": self.placement_matches,
            "rating_decay_enabled": self.rating_decay_enabled,
            "decay_threshold_days": self.decay_threshold_days,
            "decay_rate_per_day": self.decay_rate_per_day,
            "dimension_weights": dict(self.dimension_weights),
            "rating_range_multiplier": self.rating_range_multiplier,
            "max_rating_difference": self.max_rating_difference,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RatingConfig":
        """Create configuration from dictionary."""
        return cls(
            initial_rating=data.get("initial_rating", 1200.0),
            min_rating=data.get("min_rating", 0.0),
            max_rating=data.get("max_rating", 5000.0),
            k_factor=data.get("k_factor", 32.0),
            confidence_multiplier=data.get("confidence_multiplier", 1.5),
            min_confidence=data.get("min_confidence", 0.5),
            max_confidence=data.get("max_confidence", 0.95),
            confidence_gain_per_match=data.get("confidence_gain_per_match", 0.01),
            placement_matches=data.get("placement_matches", 10),
            rating_decay_enabled=data.get("rating_decay_enabled", True),
            decay_threshold_days=data.get("decay_threshold_days", 30),
            decay_rate_per_day=data.get("decay_rate_per_day", 0.1),
            dimension_weights=data.get("dimension_weights"),
            rating_range_multiplier=data.get("rating_range_multiplier", 1.2),
            max_rating_difference=data.get("max_rating_difference", 300.0),
        )

    def __str__(self) -> str:
        """String representation of rating configuration."""
        return (
            f"RatingConfig(initial={self.initial_rating}, "
            f"k={self.k_factor}, "
            f"placement={self.placement_matches})"
        )

    def __hash__(self) -> int:
        """Hash based on all configuration parameters."""
        return hash(
            (
                self.initial_rating,
                self.min_rating,
                self.max_rating,
                self.k_factor,
                self.confidence_multiplier,
                self.min_confidence,
                self.max_confidence,
                self.confidence_gain_per_match,
                self.placement_matches,
                self.rating_decay_enabled,
                self.decay_threshold_days,
                self.decay_rate_per_day,
                tuple(sorted(self.dimension_weights.items())),
                self.rating_range_multiplier,
                self.max_rating_difference,
            )
        )
