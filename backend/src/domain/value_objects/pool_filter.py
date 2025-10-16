"""
Player pool filter value object for querying and filtering players.
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

from ..base import ValueObject, BusinessRuleViolationError


class SortBy(Enum):
    """Available sorting options for player pool."""
    RATING = "rating"
    CONFIDENCE = "confidence"
    MATCHES = "total_matches"
    RECENT_ACTIVITY = "last_active"
    PLAYER_NAME = "player_name"
    KDA_DIMENSION = "kda_dimension"
    DAMAGE_DIMENSION = "damage_dimension"
    ECONOMY_DIMENSION = "economy_dimension"
    VISION_DIMENSION = "vision_dimension"
    OBJECTIVE_DIMENSION = "objective_dimension"
    TEAMFIGHT_DIMENSION = "teamfight_dimension"


class SortOrder(Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class ContractStatus(Enum):
    """Contract status filter options."""
    FREE_AGENT = "free_agent"
    CONTRACTED = "contracted"
    LOCKED = "locked"
    ALL = "all"


@dataclass(frozen=True)
class PoolFilter(ValueObject):
    """
    Filter criteria for querying player pool.

    Used to specify search and filtering conditions when retrieving
    players from the pool.
    """

    # Basic filters
    region_id: Optional[int] = None
    position: Optional[str] = None
    contract_status: ContractStatus = ContractStatus.ALL

    # Rating filters
    min_rating: Optional[float] = None
    max_rating: Optional[float] = None
    min_confidence: Optional[float] = None

    # Experience filters
    min_matches: Optional[int] = None
    max_matches: Optional[int] = None

    # Dimension filters (for advanced filtering)
    min_kda_dimension: Optional[float] = None
    min_damage_dimension: Optional[float] = None
    min_economy_dimension: Optional[float] = None
    min_vision_dimension: Optional[float] = None
    min_objective_dimension: Optional[float] = None
    min_teamfight_dimension: Optional[float] = None

    # Search filters
    player_name_search: Optional[str] = None
    summoner_name_search: Optional[str] = None

    # Activity filters
    active_within_days: Optional[int] = None

    # Sorting and pagination
    sort_by: SortBy = SortBy.RATING
    sort_order: SortOrder = SortOrder.DESC
    page: int = 1
    page_size: int = 20

    # Additional filters
    exclude_player_ids: Optional[List[str]] = None
    include_only_player_ids: Optional[List[str]] = None

    def __post_init__(self) -> None:
        """Validate filter parameters."""

        # Validate rating filters
        if self.min_rating is not None:
            if self.min_rating < 0 or self.min_rating > 5000:
                raise BusinessRuleViolationError("min_rating must be between 0 and 5000")

        if self.max_rating is not None:
            if self.max_rating < 0 or self.max_rating > 5000:
                raise BusinessRuleViolationError("max_rating must be between 0 and 5000")

        if self.min_rating is not None and self.max_rating is not None:
            if self.min_rating > self.max_rating:
                raise BusinessRuleViolationError("min_rating cannot be greater than max_rating")

        # Validate confidence filters
        if self.min_confidence is not None:
            if self.min_confidence < 0.5 or self.min_confidence > 0.95:
                raise BusinessRuleViolationError("min_confidence must be between 0.5 and 0.95")

        # Validate match count filters
        if self.min_matches is not None:
            if self.min_matches < 0:
                raise BusinessRuleViolationError("min_matches cannot be negative")

        if self.max_matches is not None:
            if self.max_matches < 0:
                raise BusinessRuleViolationError("max_matches cannot be negative")

        if self.min_matches is not None and self.max_matches is not None:
            if self.min_matches > self.max_matches:
                raise BusinessRuleViolationError("min_matches cannot be greater than max_matches")

        # Validate dimension filters
        dimension_filters = [
            self.min_kda_dimension, self.min_damage_dimension, self.min_economy_dimension,
            self.min_vision_dimension, self.min_objective_dimension, self.min_teamfight_dimension
        ]

        for dimension_filter in dimension_filters:
            if dimension_filter is not None:
                if dimension_filter < 0 or dimension_filter > 100:
                    raise BusinessRuleViolationError("Dimension filters must be between 0 and 100")

        # Validate position
        if self.position is not None:
            valid_positions = {'TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY'}
            if self.position not in valid_positions:
                raise BusinessRuleViolationError(f"Invalid position: {self.position}")

        # Validate activity filter
        if self.active_within_days is not None:
            if self.active_within_days < 1:
                raise BusinessRuleViolationError("active_within_days must be at least 1")

        # Validate pagination
        if self.page < 1:
            raise BusinessRuleViolationError("page must be at least 1")

        if self.page_size < 1 or self.page_size > 100:
            raise BusinessRuleViolationError("page_size must be between 1 and 100")

        # Validate search strings
        if self.player_name_search is not None:
            if len(self.player_name_search.strip()) < 2:
                raise BusinessRuleViolationError("player_name_search must be at least 2 characters")

        if self.summoner_name_search is not None:
            if len(self.summoner_name_search.strip()) < 2:
                raise BusinessRuleViolationError("summoner_name_search must be at least 2 characters")

    @classmethod
    def create_default(cls, region_id: Optional[int] = None) -> "PoolFilter":
        """Create a default filter for basic pool browsing."""
        return cls(
            region_id=region_id,
            contract_status=ContractStatus.ALL,
            sort_by=SortBy.RATING,
            sort_order=SortOrder.DESC,
            page=1,
            page_size=20
        )

    @classmethod
    def create_free_agents_filter(cls, region_id: Optional[int] = None) -> "PoolFilter":
        """Create a filter for finding free agents."""
        return cls(
            region_id=region_id,
            contract_status=ContractStatus.FREE_AGENT,
            min_confidence=0.6,  # Only show players with reasonable confidence
            min_matches=5,       # Only show players with some experience
            sort_by=SortBy.RATING,
            sort_order=SortOrder.DESC,
            page=1,
            page_size=20
        )

    @classmethod
    def create_top_players_filter(cls, region_id: Optional[int] = None) -> "PoolFilter":
        """Create a filter for finding top players."""
        return cls(
            region_id=region_id,
            min_rating=2000.0,   # High rating threshold
            min_confidence=0.75, # High confidence requirement
            min_matches=20,      # Experienced players only
            sort_by=SortBy.RATING,
            sort_order=SortOrder.DESC,
            page=1,
            page_size=10
        )

    @classmethod
    def create_position_filter(
        cls,
        position: str,
        region_id: Optional[int] = None,
        contract_status: ContractStatus = ContractStatus.ALL
    ) -> "PoolFilter":
        """Create a filter for a specific position."""
        return cls(
            region_id=region_id,
            position=position,
            contract_status=contract_status,
            sort_by=SortBy.RATING,
            sort_order=SortOrder.DESC,
            page=1,
            page_size=20
        )

    def with_page(self, page: int, page_size: Optional[int] = None) -> "PoolFilter":
        """Create a new filter with different pagination."""
        return PoolFilter(
            region_id=self.region_id,
            position=self.position,
            contract_status=self.contract_status,
            min_rating=self.min_rating,
            max_rating=self.max_rating,
            min_confidence=self.min_confidence,
            min_matches=self.min_matches,
            max_matches=self.max_matches,
            min_kda_dimension=self.min_kda_dimension,
            min_damage_dimension=self.min_damage_dimension,
            min_economy_dimension=self.min_economy_dimension,
            min_vision_dimension=self.min_vision_dimension,
            min_objective_dimension=self.min_objective_dimension,
            min_teamfight_dimension=self.min_teamfight_dimension,
            player_name_search=self.player_name_search,
            summoner_name_search=self.summoner_name_search,
            active_within_days=self.active_within_days,
            sort_by=self.sort_by,
            sort_order=self.sort_order,
            page=page,
            page_size=page_size or self.page_size,
            exclude_player_ids=self.exclude_player_ids,
            include_only_player_ids=self.include_only_player_ids
        )

    def with_sorting(self, sort_by: SortBy, sort_order: SortOrder) -> "PoolFilter":
        """Create a new filter with different sorting."""
        return PoolFilter(
            region_id=self.region_id,
            position=self.position,
            contract_status=self.contract_status,
            min_rating=self.min_rating,
            max_rating=self.max_rating,
            min_confidence=self.min_confidence,
            min_matches=self.min_matches,
            max_matches=self.max_matches,
            min_kda_dimension=self.min_kda_dimension,
            min_damage_dimension=self.min_damage_dimension,
            min_economy_dimension=self.min_economy_dimension,
            min_vision_dimension=self.min_vision_dimension,
            min_objective_dimension=self.min_objective_dimension,
            min_teamfight_dimension=self.min_teamfight_dimension,
            player_name_search=self.player_name_search,
            summoner_name_search=self.summoner_name_search,
            active_within_days=self.active_within_days,
            sort_by=sort_by,
            sort_order=sort_order,
            page=self.page,
            page_size=self.page_size,
            exclude_player_ids=self.exclude_player_ids,
            include_only_player_ids=self.include_only_player_ids
        )

    @property
    def offset(self) -> int:
        """Calculate database offset for pagination."""
        return (self.page - 1) * self.page_size

    @property
    def has_rating_filter(self) -> bool:
        """Check if any rating filters are applied."""
        return (
            self.min_rating is not None or
            self.max_rating is not None or
            self.min_confidence is not None
        )

    @property
    def has_dimension_filters(self) -> bool:
        """Check if any dimension filters are applied."""
        return any([
            self.min_kda_dimension, self.min_damage_dimension, self.min_economy_dimension,
            self.min_vision_dimension, self.min_objective_dimension, self.min_teamfight_dimension
        ])

    @property
    def has_search_filters(self) -> bool:
        """Check if any search filters are applied."""
        return (
            self.player_name_search is not None or
            self.summoner_name_search is not None
        )

    def __str__(self) -> str:
        """String representation of the filter."""
        parts = []

        if self.region_id:
            parts.append(f"region={self.region_id}")

        if self.position:
            parts.append(f"pos={self.position}")

        if self.contract_status != ContractStatus.ALL:
            parts.append(f"contract={self.contract_status.value}")

        if self.min_rating:
            parts.append(f"min_rating={self.min_rating}")

        if self.player_name_search:
            parts.append(f"search='{self.player_name_search}'")

        parts.append(f"sort={self.sort_by.value}({self.sort_order.value})")
        parts.append(f"page={self.page}/{self.page_size}")

        return f"PoolFilter({', '.join(parts)})"