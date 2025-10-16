"""
User domain events.
"""

from dataclasses import dataclass, field
from typing import Any, Dict
from datetime import datetime

from .base import DomainEvent


@dataclass
class UserCreatedEvent(DomainEvent):
    """
    Event published when a new user is created.
    """

    user_id: str = ""
    username: str = ""
    email: str = ""
    display_name: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.user_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "user.created"


@dataclass
class UserUpdatedEvent(DomainEvent):
    """
    Event published when user profile is updated.
    """

    user_id: str = ""
    old_data: Dict[str, Any] = field(default_factory=dict)
    new_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.user_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "user.updated"


@dataclass
class UserSuspendedEvent(DomainEvent):
    """
    Event published when a user account is suspended.
    """

    user_id: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.user_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "user.suspended"


@dataclass
class UserActivatedEvent(DomainEvent):
    """
    Event published when a user account is activated (unsuspended).
    """

    user_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.user_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "user.activated"


@dataclass
class UserDeletedEvent(DomainEvent):
    """
    Event published when a user account is deleted (soft delete).
    """

    user_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.user_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "user.deleted"
