"""
Domain aggregates module.

This module contains all aggregate root classes that serve as consistency boundaries
within the FlyEsports domain model.
"""

from .user import User
from .player_profile import PlayerProfile
from .team import Team
from .region import Region

__all__ = [
    "User",
    "PlayerProfile",
    "Team",
    "Region",
]