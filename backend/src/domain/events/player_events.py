"""
Player domain events.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from .base import DomainEvent


@dataclass
class PlayerRegisteredEvent(DomainEvent):
    """
    Event published when a new player profile is registered.
    """
    
    profile_id: str = ""
    user_id: str = ""
    region_id: str = ""
    player_name: str = ""
    position: str = ""
    initial_rating: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.profile_id
    
    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "player.registered"


@dataclass
class PlayerRatingUpdatedEvent(DomainEvent):
    """
    Event published when a player's rating is updated.
    """
    
    profile_id: str = ""
    old_rating: float = 0.0
    new_rating: float = 0.0
    reason: str = ""
    match_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.profile_id
    
    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "player.rating_updated"
    
    @property
    def rating_change(self) -> float:
        """Get the rating change amount."""
        return self.new_rating - self.old_rating


@dataclass
class PlayerSignedEvent(DomainEvent):
    """
    Event published when a player is signed to a team.
    """
    
    profile_id: str = ""
    team_id: str = ""
    locked_rating: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.profile_id
    
    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "player.signed"


@dataclass
class PlayerReleasedEvent(DomainEvent):
    """
    Event published when a player is released from a team.
    """
    
    profile_id: str = ""
    old_team_id: str = ""
    reason: str = ""
    new_rating: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.profile_id
    
    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "player.released"


@dataclass
class PlayerMatchCompletedEvent(DomainEvent):
    """
    Event published when a player completes a match.
    """
    
    profile_id: str = ""
    match_id: str = ""
    result: str = ""
    rating_before: float = 0.0
    rating_after: float = 0.0
    kda: str = ""
    champion_name: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.profile_id
    
    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "player.match_completed"
    
    @property
    def rating_change(self) -> float:
        """Get the rating change from this match."""
        return self.rating_after - self.rating_before


@dataclass
class PlayerRankUpdatedEvent(DomainEvent):
    """
    Event published when a player's League of Legends rank is updated.
    """
    
    profile_id: str = ""
    old_rank: str = ""
    new_rank: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.profile_id
    
    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "player.rank_updated"