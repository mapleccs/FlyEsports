"""
Base domain event classes.
"""

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
import uuid


@dataclass
class DomainEvent(ABC):
    """
    Base class for all domain events.
    
    Domain events represent significant business occurrences that other
    bounded contexts or aggregates may need to respond to.
    """
    
    event_id: str = None
    occurred_at: datetime = None
    aggregate_id: str = ""
    aggregate_type: str = ""
    event_version: int = 1
    
    def __post_init__(self):
        """Initialize default values after dataclass initialization."""
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())
        if self.occurred_at is None:
            self.occurred_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the event to a dictionary representation.
        
        Returns:
            Dict containing event metadata and data
        """
        return {
            "event_id": self.event_id,
            "event_type": self.__class__.__name__,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "occurred_at": self.occurred_at.isoformat(),
            "event_version": self.event_version,
            "data": self._get_event_data()
        }
    
    def _get_event_data(self) -> Dict[str, Any]:
        """
        Get event-specific data.
        
        Returns:
            Dict containing event data (excluding metadata)
        """
        excluded_fields = {
            "event_id", "occurred_at", "aggregate_id", 
            "aggregate_type", "event_version"
        }
        return {
            k: v for k, v in self.__dict__.items() 
            if k not in excluded_fields
        }
    
    @property
    def event_type(self) -> str:
        """Get the event type name."""
        return self.__class__.__name__
    
    def __str__(self) -> str:
        """String representation of the event."""
        return f"{self.event_type}(id={self.event_id}, aggregate={self.aggregate_type}:{self.aggregate_id})"