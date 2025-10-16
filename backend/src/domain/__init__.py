"""
Domain layer of FlyEsports.

This package contains the core business logic and domain models,
following Domain-Driven Design (DDD) principles.

Structure:
- aggregates: Aggregate roots that ensure business invariants
- entities: Domain entities with identity
- value_objects: Immutable value objects
- events: Domain events for communication between aggregates
- services: Domain services for complex business logic
- repositories: Repository interfaces for data access
- exceptions: Domain-specific exceptions
"""

# Import core domain components
from .base import (
    AggregateRoot,
    Entity,
    ValueObject,
    DomainEvent,
    BusinessRuleViolationError,
)
from .aggregates import User, PlayerProfile, Team, Region
from .value_objects import (
    Email,
    Position,
    ContractStatus,
    Rating,
    UserPreferences,
    RankInfo,
    TransferWindow,
    RatingConfig,
)
from .entities import MatchRecord, RosterSlot
from .events import user_events, player_events, team_events, region_events

__all__ = [
    # Base classes
    "AggregateRoot",
    "Entity",
    "ValueObject",
    "DomainEvent",
    "BusinessRuleViolationError",
    # Aggregates
    "User",
    "PlayerProfile",
    "Team",
    "Region",
    # Entities
    "MatchRecord",
    "RosterSlot",
    # Value objects
    "Email",
    "Position",
    "ContractStatus",
    "Rating",
    "UserPreferences",
    "RankInfo",
    "TransferWindow",
    "RatingConfig",
    # Events modules
    "user_events",
    "player_events",
    "team_events",
    "region_events",
]
