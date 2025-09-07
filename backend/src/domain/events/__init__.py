"""
Domain events for FlyEsports.

This package contains all domain events that represent significant
business occurrences in the system.
"""

from .base import DomainEvent
from . import user_events
from . import player_events
from . import team_events
from . import region_events

__all__ = [
    "DomainEvent",
    "user_events",
    "player_events",
    "team_events",
    "region_events",
]