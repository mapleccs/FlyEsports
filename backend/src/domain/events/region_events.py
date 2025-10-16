"""
Region domain events.
"""

from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime

from .base import DomainEvent


@dataclass
class RegionCreatedEvent(DomainEvent):
    """
    Event published when a new region is created.
    """

    region_id: str = ""
    region_name: str = ""
    region_code: str = ""
    admin_user_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.region_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "region.created"


@dataclass
class TransferWindowOpenedEvent(DomainEvent):
    """
    Event published when a transfer window is opened.
    """

    region_id: str = ""
    window_name: str = ""
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime = field(default_factory=datetime.utcnow)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.region_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "region.transfer_window_opened"

    @property
    def window_duration_days(self) -> int:
        """Get the duration of the transfer window in days."""
        return (self.end_time - self.start_time).days


@dataclass
class TransferWindowClosedEvent(DomainEvent):
    """
    Event published when a transfer window is closed.
    """

    region_id: str = ""
    window_name: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.region_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "region.transfer_window_closed"


@dataclass
class RegionConfigUpdatedEvent(DomainEvent):
    """
    Event published when region configuration is updated.
    """

    region_id: str = ""
    config_type: str = ""  # "rating", "general", "transfer"
    old_config: Dict[str, Any] = field(default_factory=dict)
    new_config: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.region_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "region.config_updated"


@dataclass
class RegionStatsUpdatedEvent(DomainEvent):
    """
    Event published when region statistics are updated.
    """

    region_id: str = ""
    old_stats: Dict[str, int] = field(default_factory=dict)
    new_stats: Dict[str, int] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Initialize event after creation."""
        super().__post_init__()
        # Set aggregate_id from region_id
        self.aggregate_id = self.region_id
        self.aggregate_type = "Region"

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "region.stats_updated"


@dataclass
class RegionAdminAddedEvent(DomainEvent):
    """
    Event published when an admin is added to a region.
    """

    region_id: str = ""
    admin_user_id: str = ""
    added_by_user_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.region_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "region.admin_added"


@dataclass
class RegionAdminRemovedEvent(DomainEvent):
    """
    Event published when an admin is removed from a region.
    """

    region_id: str = ""
    admin_user_id: str = ""
    removed_by_user_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.region_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "region.admin_removed"


@dataclass
class RegionStatusChangedEvent(DomainEvent):
    """
    Event published when a region's status changes.
    """

    region_id: str = ""
    old_status: str = ""
    new_status: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.region_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "region.status_changed"


@dataclass
class SeasonStartedEvent(DomainEvent):
    """
    Event published when a new season starts in a region.
    """

    region_id: str = ""
    season_name: str = ""
    season_start: datetime = field(default_factory=datetime.utcnow)
    season_end: datetime = field(default_factory=datetime.utcnow)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.region_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "region.season_started"

    @property
    def season_duration_days(self) -> int:
        """Get the duration of the season in days."""
        return (self.season_end - self.season_start).days


@dataclass
class SeasonEndedEvent(DomainEvent):
    """
    Event published when a season ends in a region.
    """

    region_id: str = ""
    season_name: str = ""
    final_stats: Dict[str, int] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def aggregate_id(self) -> str:
        """Get the aggregate ID for this event."""
        return self.region_id

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return "region.season_ended"
