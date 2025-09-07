"""
Transfer window value object for managing player transfers.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from ..base import ValueObject, BusinessRuleViolationError


@dataclass(frozen=True)
class TransferWindow(ValueObject):
    """
    Transfer window value object representing a period when player transfers are allowed.
    
    Manages the timing and status of transfer periods within a region.
    """
    
    window_name: str
    start_time: datetime
    end_time: datetime
    is_active: bool = True
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate transfer window after initialization."""
        # Validate window name
        if not self.window_name or not self.window_name.strip():
            raise BusinessRuleViolationError("Window name is required")
        
        if len(self.window_name.strip()) > 100:
            raise BusinessRuleViolationError(
                "Window name cannot exceed 100 characters"
            )
        
        # Validate time range
        if self.end_time <= self.start_time:
            raise BusinessRuleViolationError(
                "End time must be after start time"
            )
        
        # Validate minimum duration (at least 1 day)
        duration = self.end_time - self.start_time
        if duration.total_seconds() < 86400:  # 24 hours
            raise BusinessRuleViolationError(
                "Transfer window must be at least 1 day long"
            )
        
        # Validate maximum duration (no more than 90 days)
        if duration.days > 90:
            raise BusinessRuleViolationError(
                "Transfer window cannot exceed 90 days"
            )
        
        # Validate description length
        if self.description and len(self.description) > 500:
            raise BusinessRuleViolationError(
                "Description cannot exceed 500 characters"
            )
    
    @classmethod
    def create(
        cls,
        window_name: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None
    ) -> 'TransferWindow':
        """
        Create a new transfer window.
        
        Args:
            window_name: Name of the transfer window
            start_time: When the window opens
            end_time: When the window closes
            description: Optional description
            
        Returns:
            TransferWindow value object
            
        Raises:
            BusinessRuleViolationError: If creation rules are violated
        """
        if not window_name or not window_name.strip():
            raise BusinessRuleViolationError("Window name is required")
        
        if not start_time:
            raise BusinessRuleViolationError("Start time is required")
        
        if not end_time:
            raise BusinessRuleViolationError("End time is required")
        
        return cls(
            window_name=window_name.strip(),
            start_time=start_time,
            end_time=end_time,
            is_active=True,
            description=description.strip() if description else None
        )
    
    @classmethod
    def create_seasonal(
        cls,
        season: str,
        start_time: datetime,
        duration_days: int = 14,
        description: Optional[str] = None
    ) -> 'TransferWindow':
        """
        Create a seasonal transfer window.
        
        Args:
            season: Season identifier (e.g., "2024-Spring", "2024-Summer")
            start_time: When the window opens
            duration_days: Duration in days (default 14)
            description: Optional description
            
        Returns:
            TransferWindow value object
        """
        if not season or not season.strip():
            raise BusinessRuleViolationError("Season is required")
        
        if duration_days < 1 or duration_days > 90:
            raise BusinessRuleViolationError(
                "Duration must be between 1 and 90 days"
            )
        
        from datetime import timedelta
        end_time = start_time + timedelta(days=duration_days)
        window_name = f"{season.strip()}-转会窗口"
        
        return cls(
            window_name=window_name,
            start_time=start_time,
            end_time=end_time,
            is_active=True,
            description=description.strip() if description else f"{season}赛季转会窗口"
        )
    
    def close(self) -> 'TransferWindow':
        """
        Create a new TransferWindow with closed status.
        
        Returns:
            New TransferWindow with is_active=False
        """
        return TransferWindow(
            window_name=self.window_name,
            start_time=self.start_time,
            end_time=self.end_time,
            is_active=False,
            description=self.description
        )
    
    def is_open_at(self, check_time: datetime) -> bool:
        """
        Check if the transfer window is open at a specific time.
        
        Args:
            check_time: Time to check
            
        Returns:
            True if window is open and active at the given time
        """
        return (self.is_active and 
                self.start_time <= check_time <= self.end_time)
    
    def is_open_now(self) -> bool:
        """
        Check if the transfer window is currently open.
        
        Returns:
            True if window is open right now
        """
        return self.is_open_at(datetime.utcnow())
    
    def days_remaining(self, from_time: Optional[datetime] = None) -> int:
        """
        Calculate days remaining in the transfer window.
        
        Args:
            from_time: Reference time (defaults to now)
            
        Returns:
            Number of days remaining (0 if window is closed or past)
        """
        reference_time = from_time if from_time else datetime.utcnow()
        
        if not self.is_active or reference_time >= self.end_time:
            return 0
        
        if reference_time < self.start_time:
            # Window hasn't started yet
            return (self.end_time - self.start_time).days
        
        # Window is active
        remaining = self.end_time - reference_time
        return max(0, remaining.days)
    
    def duration_days(self) -> int:
        """
        Get the total duration of the transfer window in days.
        
        Returns:
            Duration in days
        """
        return (self.end_time - self.start_time).days
    
    @property
    def status(self) -> str:
        """Get the current status of the transfer window."""
        if not self.is_active:
            return "closed"
        
        now = datetime.utcnow()
        if now < self.start_time:
            return "scheduled"
        elif now > self.end_time:
            return "expired"
        else:
            return "open"
    
    @property
    def display_name(self) -> str:
        """Get display name with status."""
        return f"{self.window_name} ({self.status})"
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "window_name": self.window_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "is_active": self.is_active,
            "description": self.description,
            "status": self.status,
            "duration_days": self.duration_days(),
            "days_remaining": self.days_remaining()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TransferWindow':
        """Create TransferWindow from dictionary."""
        return cls(
            window_name=data["window_name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            is_active=data.get("is_active", True),
            description=data.get("description")
        )
    
    def __str__(self) -> str:
        """String representation of the transfer window."""
        return f"TransferWindow({self.window_name}, {self.status})"
    
    def __hash__(self) -> int:
        """Hash based on all transfer window components."""
        return hash((
            self.window_name,
            self.start_time,
            self.end_time,
            self.is_active,
            self.description
        ))