"""
Team domain events.
"""

from dataclasses import dataclass, field
from typing import List
from datetime import datetime

from .base import DomainEvent


@dataclass
class TeamCreatedEvent(DomainEvent):
    """
    Event published when a new team is created.
    """

    team_id: str = ""
    team_name: str = ""
    team_tag: str = ""
    region_id: str = ""
    owner_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.team_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "team.created"


@dataclass
class PlayerAddedToTeamEvent(DomainEvent):
    """
    Event published when a player is added to a team roster.
    """

    team_id: str = ""
    profile_id: str = ""
    position: str = ""
    signing_cost: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.team_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "team.player_added"


@dataclass
class PlayerRemovedFromTeamEvent(DomainEvent):
    """
    Event published when a player is removed from a team roster.
    """

    team_id: str = ""
    profile_id: str = ""
    position: str = ""
    reason: str = ""
    cost_reduction: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.team_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "team.player_removed"


@dataclass
class TeamDisbandedEvent(DomainEvent):
    """
    Event published when a team is disbanded.
    """

    team_id: str = ""
    reason: str = ""
    final_roster: List[str] = field(default_factory=list)  # List of profile_ids
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.team_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "team.disbanded"


@dataclass
class TeamInfoUpdatedEvent(DomainEvent):
    """
    Event published when team information is updated.
    """

    team_id: str = ""
    old_data: dict = field(default_factory=dict)
    new_data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.team_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "team.info_updated"


@dataclass
class TeamMatchResultEvent(DomainEvent):
    """
    Event published when a team match result is recorded.
    """

    team_id: str = ""
    match_id: str = ""
    result: str = ""  # "win", "loss", "draw"
    opponent_team_id: str = ""
    total_matches: int = 0
    total_wins: int = 0
    total_losses: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.team_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "team.match_result"
