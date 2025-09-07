"""
Base classes for domain models.

This module provides the foundational classes for implementing
Domain-Driven Design patterns in FlyEsports.
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Any, Dict, Optional
from uuid import uuid4


class DomainEvent(ABC):
    """
    Base class for all domain events.
    
    Domain events represent significant business occurrences that other
    parts of the system may need to respond to.
    """
    
    def __init__(self):
        self.event_id: str = str(uuid4())
        self.occurred_at: datetime = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary representation."""
        return {
            "event_id": self.event_id,
            "event_type": self.__class__.__name__,
            "occurred_at": self.occurred_at.isoformat(),
            "data": self._get_event_data()
        }
    
    def _get_event_data(self) -> Dict[str, Any]:
        """Get event-specific data. Override in subclasses."""
        return {}


@dataclass
class Entity(ABC):
    """
    Base class for all entities.
    
    Entities have a unique identity that runs through time and different states.
    """
    
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __eq__(self, other: object) -> bool:
        """Entities are equal if they have the same ID."""
        if not isinstance(other, Entity):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Entities are hashed by their ID."""
        return hash(self.id)
    
    def update_timestamp(self) -> None:
        """Update the entity's last updated timestamp."""
        self.updated_at = datetime.utcnow()


class ValueObject(ABC):
    """
    Base class for value objects.
    
    Value objects are immutable and defined by their attributes rather than identity.
    They should be implemented as frozen dataclasses.
    """
    pass


@dataclass
class AggregateRoot(Entity):
    """
    Base class for aggregate roots.
    
    Aggregate roots are the only objects that can be referenced from outside
    the aggregate. They ensure consistency boundaries and manage domain events.
    """
    
    _domain_events: List[DomainEvent] = field(default_factory=list, init=False)
    _version: int = field(default=0, init=False)
    
    def add_domain_event(self, event: DomainEvent) -> None:
        """Add a domain event to be published."""
        self._domain_events.append(event)
    
    def clear_domain_events(self) -> None:
        """Clear all domain events after they have been published."""
        self._domain_events.clear()
    
    def get_domain_events(self) -> List[DomainEvent]:
        """Get all unpublished domain events."""
        return self._domain_events.copy()
    
    def increment_version(self) -> None:
        """Increment the aggregate version for optimistic concurrency control."""
        self._version += 1
        self.update_timestamp()
    
    @property
    def version(self) -> int:
        """Get the current aggregate version."""
        return self._version


class DomainException(Exception):
    """
    Base class for all domain-specific exceptions.
    
    Domain exceptions represent business rule violations or invalid states.
    """
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__


class BusinessRuleViolationError(DomainException):
    """
    Exception raised when a business rule is violated.
    """
    pass


class InvalidOperationError(DomainException):
    """
    Exception raised when an operation is not valid in the current state.
    """
    pass


class ResourceNotFoundError(DomainException):
    """
    Exception raised when a required resource is not found.
    """
    pass


class ConcurrencyError(DomainException):
    """
    Exception raised when a concurrency conflict occurs.
    """
    pass