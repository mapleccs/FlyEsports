"""
Region aggregate root.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from ..base import AggregateRoot, BusinessRuleViolationError
from ..value_objects.transfer_window import TransferWindow
from ..value_objects.rating_config import RatingConfig


@dataclass
class Region(AggregateRoot):
    """
    Region aggregate root representing a competitive region.
    
    A Region manages its configuration, transfer windows, seasons,
    and administrative settings for competitive play.
    """
    
    region_id: str = field(default_factory=lambda: f"region_{uuid.uuid4().hex[:8]}")
    region_name: str = ""
    region_code: str = ""
    status: str = "active"  # active, inactive, maintenance
    
    # Region configuration
    rating_config: RatingConfig = field(default_factory=RatingConfig.create_default)
    transfer_windows: List[TransferWindow] = field(default_factory=list)
    
    # Statistics
    total_players: int = 0
    active_players: int = 0
    total_teams: int = 0
    active_teams: int = 0
    
    # Season information
    current_season: str = ""
    season_start: Optional[datetime] = None
    season_end: Optional[datetime] = None
    
    # Administrators
    admin_users: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Post initialization validation and setup."""
        super().__post_init__()
        
        # Validate required fields
        if not self.region_name.strip():
            raise BusinessRuleViolationError("Region name is required")
        
        if not self.region_code.strip():
            raise BusinessRuleViolationError("Region code is required")
        
        # Validate region name length
        if len(self.region_name) > 100:
            raise BusinessRuleViolationError(
                "Region name cannot exceed 100 characters"
            )
        
        # Validate region code format
        region_code = self.region_code.upper()
        if len(region_code) < 2 or len(region_code) > 10:
            raise BusinessRuleViolationError(
                "Region code must be between 2 and 10 characters"
            )
        object.__setattr__(self, 'region_code', region_code)
        
        # Validate status
        valid_statuses = {"active", "inactive", "maintenance"}
        if self.status not in valid_statuses:
            raise BusinessRuleViolationError(
                f"Invalid region status: {self.status}. Valid statuses: {valid_statuses}"
            )
        
        # Validate statistics
        stats_fields = ['total_players', 'active_players', 'total_teams', 'active_teams']
        for field_name in stats_fields:
            value = getattr(self, field_name)
            if value < 0:
                raise BusinessRuleViolationError(f"{field_name} cannot be negative")
        
        # Validate active counts don't exceed totals
        if self.active_players > self.total_players:
            raise BusinessRuleViolationError(
                "Active players cannot exceed total players"
            )
        
        if self.active_teams > self.total_teams:
            raise BusinessRuleViolationError(
                "Active teams cannot exceed total teams"
            )
        
        # Validate season dates
        if self.season_start and self.season_end:
            if self.season_end <= self.season_start:
                raise BusinessRuleViolationError(
                    "Season end must be after season start"
                )
        
        # Validate current season
        if self.current_season and len(self.current_season) > 50:
            raise BusinessRuleViolationError(
                "Current season name cannot exceed 50 characters"
            )
        
        # Ensure at least one admin
        if not self.admin_users:
            raise BusinessRuleViolationError("Region must have at least one administrator")
    
    @classmethod
    def create(
        cls,
        region_name: str,
        region_code: str,
        admin_user_id: str,
        rating_config: Optional[RatingConfig] = None
    ) -> 'Region':
        """
        Create a new region.
        
        Args:
            region_name: Display name of the region
            region_code: Short code for the region (e.g., "CN", "KR", "NA")
            admin_user_id: ID of the initial administrator
            rating_config: Optional custom rating configuration
            
        Returns:
            New Region aggregate root
            
        Raises:
            BusinessRuleViolationError: If creation rules are violated
        """
        if not region_name or not region_name.strip():
            raise BusinessRuleViolationError("Region name is required")
        
        if not region_code or not region_code.strip():
            raise BusinessRuleViolationError("Region code is required")
        
        if not admin_user_id or not admin_user_id.strip():
            raise BusinessRuleViolationError("Admin user ID is required")
        
        config = rating_config if rating_config else RatingConfig.create_default()
        
        region = cls(
            region_name=region_name.strip(),
            region_code=region_code.strip().upper(),
            admin_users=[admin_user_id.strip()],
            rating_config=config
        )
        
        # Add domain event for region creation
        from ..events.region_events import RegionCreatedEvent
        event = RegionCreatedEvent(
            region_id=region.region_id,
            region_name=region_name,
            region_code=region_code,
            admin_user_id=admin_user_id,
            timestamp=region.created_at
        )
        region.add_domain_event(event)
        
        return region
    
    def open_transfer_window(
        self,
        window_name: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None
    ) -> None:
        """
        Open a new transfer window.
        
        Args:
            window_name: Name of the transfer window
            start_time: When the window opens
            end_time: When the window closes
            description: Optional description
            
        Raises:
            BusinessRuleViolationError: If window creation fails
        """
        if self.status != "active":
            raise BusinessRuleViolationError(
                f"Cannot open transfer window for inactive region (status: {self.status})"
            )
        
        # Create new transfer window
        transfer_window = TransferWindow.create(
            window_name=window_name,
            start_time=start_time,
            end_time=end_time,
            description=description
        )
        
        # Close any existing active transfer windows
        updated_windows = []
        for window in self.transfer_windows:
            if window.is_active:
                updated_windows.append(window.close())
            else:
                updated_windows.append(window)
        
        # Add new window
        updated_windows.append(transfer_window)
        object.__setattr__(self, 'transfer_windows', updated_windows)
        object.__setattr__(self, 'updated_at', datetime.utcnow())
        
        # Add domain event for transfer window opening
        from ..events.region_events import TransferWindowOpenedEvent
        event = TransferWindowOpenedEvent(
            region_id=self.region_id,
            window_name=window_name,
            start_time=start_time,
            end_time=end_time,
            timestamp=self.updated_at
        )
        self.add_domain_event(event)
    
    def close_current_transfer_window(self) -> None:
        """
        Close the currently active transfer window.
        
        Raises:
            BusinessRuleViolationError: If no active window exists
        """
        current_window = self.get_current_transfer_window()
        if not current_window:
            raise BusinessRuleViolationError("No active transfer window to close")
        
        # Close the current window
        updated_windows = []
        for window in self.transfer_windows:
            if window.is_active and window.is_open_now():
                updated_windows.append(window.close())
            else:
                updated_windows.append(window)
        
        object.__setattr__(self, 'transfer_windows', updated_windows)
        object.__setattr__(self, 'updated_at', datetime.utcnow())
        
        # Add domain event for transfer window closing
        from ..events.region_events import TransferWindowClosedEvent
        event = TransferWindowClosedEvent(
            region_id=self.region_id,
            window_name=current_window.window_name,
            timestamp=self.updated_at
        )
        self.add_domain_event(event)
    
    def update_rating_config(self, rating_config: RatingConfig) -> None:
        """
        Update the region's rating configuration.
        
        Args:
            rating_config: New rating configuration
        """
        if not rating_config:
            raise BusinessRuleViolationError("Rating config is required")
        
        old_config = self.rating_config
        object.__setattr__(self, 'rating_config', rating_config)
        object.__setattr__(self, 'updated_at', datetime.utcnow())
        
        # Add domain event for config update
        from ..events.region_events import RegionConfigUpdatedEvent
        event = RegionConfigUpdatedEvent(
            region_id=self.region_id,
            config_type="rating",
            old_config=old_config.to_dict(),
            new_config=rating_config.to_dict(),
            timestamp=self.updated_at
        )
        self.add_domain_event(event)
    
    def add_admin(self, user_id: str, added_by_user_id: str) -> None:
        """
        Add an administrator to the region.
        
        Args:
            user_id: ID of the user to add as admin
            added_by_user_id: ID of the user adding the admin
            
        Raises:
            BusinessRuleViolationError: If addition fails
        """
        if not user_id or not user_id.strip():
            raise BusinessRuleViolationError("User ID is required")
        
        if not added_by_user_id or not added_by_user_id.strip():
            raise BusinessRuleViolationError("Added by user ID is required")
        
        if not self.is_user_admin(added_by_user_id):
            raise BusinessRuleViolationError(
                f"User {added_by_user_id} is not authorized to add admins"
            )
        
        user_id = user_id.strip()
        if user_id in self.admin_users:
            raise BusinessRuleViolationError(f"User {user_id} is already an admin")
        
        self.admin_users.append(user_id)
        object.__setattr__(self, 'updated_at', datetime.utcnow())
        
        # Add domain event for admin addition
        from ..events.region_events import RegionAdminAddedEvent
        event = RegionAdminAddedEvent(
            region_id=self.region_id,
            admin_user_id=user_id,
            added_by_user_id=added_by_user_id,
            timestamp=self.updated_at
        )
        self.add_domain_event(event)
    
    def remove_admin(self, user_id: str, removed_by_user_id: str) -> None:
        """
        Remove an administrator from the region.
        
        Args:
            user_id: ID of the user to remove as admin
            removed_by_user_id: ID of the user removing the admin
            
        Raises:
            BusinessRuleViolationError: If removal fails
        """
        if not user_id or not user_id.strip():
            raise BusinessRuleViolationError("User ID is required")
        
        if not removed_by_user_id or not removed_by_user_id.strip():
            raise BusinessRuleViolationError("Removed by user ID is required")
        
        if not self.is_user_admin(removed_by_user_id):
            raise BusinessRuleViolationError(
                f"User {removed_by_user_id} is not authorized to remove admins"
            )
        
        user_id = user_id.strip()
        if user_id not in self.admin_users:
            raise BusinessRuleViolationError(f"User {user_id} is not an admin")
        
        if len(self.admin_users) <= 1:
            raise BusinessRuleViolationError(
                "Cannot remove the last administrator"
            )
        
        self.admin_users.remove(user_id)
        object.__setattr__(self, 'updated_at', datetime.utcnow())
        
        # Add domain event for admin removal
        from ..events.region_events import RegionAdminRemovedEvent
        event = RegionAdminRemovedEvent(
            region_id=self.region_id,
            admin_user_id=user_id,
            removed_by_user_id=removed_by_user_id,
            timestamp=self.updated_at
        )
        self.add_domain_event(event)
    
    def update_statistics(
        self,
        total_players: Optional[int] = None,
        active_players: Optional[int] = None,
        total_teams: Optional[int] = None,
        active_teams: Optional[int] = None
    ) -> None:
        """
        Update region statistics.
        
        Args:
            total_players: Total number of players
            active_players: Number of active players
            total_teams: Total number of teams
            active_teams: Number of active teams
        """
        old_stats = {
            "total_players": self.total_players,
            "active_players": self.active_players,
            "total_teams": self.total_teams,
            "active_teams": self.active_teams
        }
        
        has_changes = False
        
        if total_players is not None and total_players != self.total_players:
            if total_players < 0:
                raise BusinessRuleViolationError("Total players cannot be negative")
            object.__setattr__(self, 'total_players', total_players)
            has_changes = True
        
        if active_players is not None and active_players != self.active_players:
            if active_players < 0:
                raise BusinessRuleViolationError("Active players cannot be negative")
            if active_players > self.total_players:
                raise BusinessRuleViolationError(
                    "Active players cannot exceed total players"
                )
            object.__setattr__(self, 'active_players', active_players)
            has_changes = True
        
        if total_teams is not None and total_teams != self.total_teams:
            if total_teams < 0:
                raise BusinessRuleViolationError("Total teams cannot be negative")
            object.__setattr__(self, 'total_teams', total_teams)
            has_changes = True
        
        if active_teams is not None and active_teams != self.active_teams:
            if active_teams < 0:
                raise BusinessRuleViolationError("Active teams cannot be negative")
            if active_teams > self.total_teams:
                raise BusinessRuleViolationError(
                    "Active teams cannot exceed total teams"
                )
            object.__setattr__(self, 'active_teams', active_teams)
            has_changes = True
        
        if has_changes:
            object.__setattr__(self, 'updated_at', datetime.utcnow())
            
            # Add domain event for statistics update
            from ..events.region_events import RegionStatsUpdatedEvent
            event = RegionStatsUpdatedEvent(
                region_id=self.region_id,
                old_stats=old_stats,
                new_stats={
                    "total_players": self.total_players,
                    "active_players": self.active_players,
                    "total_teams": self.total_teams,
                    "active_teams": self.active_teams
                },
                timestamp=self.updated_at
            )
            self.add_domain_event(event)
    
    def start_season(
        self,
        season_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> None:
        """
        Start a new season.
        
        Args:
            season_name: Name of the season
            start_time: Season start time
            end_time: Season end time
        """
        if not season_name or not season_name.strip():
            raise BusinessRuleViolationError("Season name is required")
        
        if len(season_name.strip()) > 50:
            raise BusinessRuleViolationError(
                "Season name cannot exceed 50 characters"
            )
        
        if end_time <= start_time:
            raise BusinessRuleViolationError("Season end must be after start")
        
        object.__setattr__(self, 'current_season', season_name.strip())
        object.__setattr__(self, 'season_start', start_time)
        object.__setattr__(self, 'season_end', end_time)
        object.__setattr__(self, 'updated_at', datetime.utcnow())
        
        # Add domain event for season start
        from ..events.region_events import SeasonStartedEvent
        event = SeasonStartedEvent(
            region_id=self.region_id,
            season_name=season_name,
            season_start=start_time,
            season_end=end_time,
            timestamp=self.updated_at
        )
        self.add_domain_event(event)
    
    def end_current_season(self) -> None:
        """
        End the current season.
        
        Raises:
            BusinessRuleViolationError: If no active season exists
        """
        if not self.current_season:
            raise BusinessRuleViolationError("No active season to end")
        
        season_name = self.current_season
        final_stats = {
            "total_players": self.total_players,
            "active_players": self.active_players,
            "total_teams": self.total_teams,
            "active_teams": self.active_teams
        }
        
        object.__setattr__(self, 'current_season', "")
        object.__setattr__(self, 'season_start', None)
        object.__setattr__(self, 'season_end', None)
        object.__setattr__(self, 'updated_at', datetime.utcnow())
        
        # Add domain event for season end
        from ..events.region_events import SeasonEndedEvent
        event = SeasonEndedEvent(
            region_id=self.region_id,
            season_name=season_name,
            final_stats=final_stats,
            timestamp=self.updated_at
        )
        self.add_domain_event(event)
    
    def change_status(self, new_status: str, reason: str) -> None:
        """
        Change the region status.
        
        Args:
            new_status: New status ("active", "inactive", "maintenance")
            reason: Reason for status change
        """
        valid_statuses = {"active", "inactive", "maintenance"}
        if new_status not in valid_statuses:
            raise BusinessRuleViolationError(
                f"Invalid status: {new_status}. Valid statuses: {valid_statuses}"
            )
        
        if not reason or not reason.strip():
            raise BusinessRuleViolationError("Reason for status change is required")
        
        if new_status == self.status:
            return  # No change needed
        
        old_status = self.status
        object.__setattr__(self, 'status', new_status)
        object.__setattr__(self, 'updated_at', datetime.utcnow())
        
        # Add domain event for status change
        from ..events.region_events import RegionStatusChangedEvent
        event = RegionStatusChangedEvent(
            region_id=self.region_id,
            old_status=old_status,
            new_status=new_status,
            reason=reason.strip(),
            timestamp=self.updated_at
        )
        self.add_domain_event(event)
    
    def get_current_transfer_window(self) -> Optional[TransferWindow]:
        """
        Get the currently active transfer window.
        
        Returns:
            Active transfer window if one exists
        """
        current_time = datetime.utcnow()
        for window in self.transfer_windows:
            if window.is_active and window.is_open_at(current_time):
                return window
        return None
    
    def is_user_admin(self, user_id: str) -> bool:
        """
        Check if a user is an administrator of this region.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user is an admin
        """
        return user_id in self.admin_users
    
    @property
    def is_transfer_window_open(self) -> bool:
        """Check if a transfer window is currently open."""
        return self.get_current_transfer_window() is not None
    
    @property
    def is_active(self) -> bool:
        """Check if the region is active."""
        return self.status == "active"
    
    @property
    def is_in_season(self) -> bool:
        """Check if the region is currently in a season."""
        return bool(self.current_season and self.season_start and self.season_end)
    
    @property
    def player_activity_rate(self) -> float:
        """Calculate player activity rate."""
        if self.total_players == 0:
            return 0.0
        return self.active_players / self.total_players
    
    @property
    def team_activity_rate(self) -> float:
        """Calculate team activity rate."""
        if self.total_teams == 0:
            return 0.0
        return self.active_teams / self.total_teams
    
    @property
    def region_summary(self) -> Dict[str, Any]:
        """Get a summary of region information."""
        return {
            "region_id": self.region_id,
            "region_name": self.region_name,
            "region_code": self.region_code,
            "status": self.status,
            "current_season": self.current_season,
            "is_transfer_window_open": self.is_transfer_window_open,
            "total_players": self.total_players,
            "active_players": self.active_players,
            "total_teams": self.total_teams,
            "active_teams": self.active_teams,
            "player_activity_rate": round(self.player_activity_rate * 100, 1),
            "team_activity_rate": round(self.team_activity_rate * 100, 1),
            "admin_count": len(self.admin_users),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def __str__(self) -> str:
        """String representation of the region."""
        return (f"Region({self.region_name} [{self.region_code}], "
                f"status={self.status}, "
                f"players={self.active_players}/{self.total_players})")
    
    def __hash__(self) -> int:
        """Hash based on region ID."""
        return hash(self.region_id)