"""
Domain entities module.

This module contains domain entities that have identity but are not aggregate roots.
"""

from .match_record import MatchRecord
from .roster_slot import RosterSlot

__all__ = [
    "MatchRecord",
    "RosterSlot",
]
