"""
Position value object for League of Legends positions.
"""

from enum import Enum
from dataclasses import dataclass
from typing import ClassVar, Dict

from ..base import ValueObject, BusinessRuleViolationError


class PositionType(Enum):
    """Enumeration of League of Legends positions."""
    
    TOP = "TOP"
    JUNGLE = "JUNGLE"
    MIDDLE = "MIDDLE"
    BOTTOM = "BOTTOM"
    UTILITY = "UTILITY"


@dataclass(frozen=True)
class Position(ValueObject):
    """
    Position value object with display names and validation.
    """
    
    type: PositionType
    
    # Display name mappings
    DISPLAY_NAMES: ClassVar[Dict[PositionType, str]] = {
        PositionType.TOP: "上单",
        PositionType.JUNGLE: "打野",
        PositionType.MIDDLE: "中单",
        PositionType.BOTTOM: "下路",
        PositionType.UTILITY: "辅助"
    }
    
    # Position indices for ordering
    INDICES: ClassVar[Dict[PositionType, int]] = {
        PositionType.TOP: 0,
        PositionType.JUNGLE: 1,
        PositionType.MIDDLE: 2,
        PositionType.BOTTOM: 3,
        PositionType.UTILITY: 4
    }
    
    @classmethod
    def from_string(cls, position_str: str) -> 'Position':
        """
        Create Position from string.
        
        Args:
            position_str: Position string (case-insensitive)
            
        Returns:
            Position value object
            
        Raises:
            BusinessRuleViolationError: If position string is invalid
        """
        try:
            position_type = PositionType(position_str.upper())
            return cls(type=position_type)
        except ValueError:
            valid_positions = [p.value for p in PositionType]
            raise BusinessRuleViolationError(
                f"Invalid position: {position_str}. Valid positions: {valid_positions}"
            )
    
    @classmethod
    def create_top(cls) -> 'Position':
        """Create TOP position."""
        return cls(type=PositionType.TOP)
    
    @classmethod
    def create_jungle(cls) -> 'Position':
        """Create JUNGLE position."""
        return cls(type=PositionType.JUNGLE)
    
    @classmethod
    def create_middle(cls) -> 'Position':
        """Create MIDDLE position."""
        return cls(type=PositionType.MIDDLE)
    
    @classmethod
    def create_bottom(cls) -> 'Position':
        """Create BOTTOM position."""
        return cls(type=PositionType.BOTTOM)
    
    @classmethod
    def create_utility(cls) -> 'Position':
        """Create UTILITY position."""
        return cls(type=PositionType.UTILITY)
    
    @classmethod
    def all_positions(cls) -> list['Position']:
        """Get all valid positions."""
        return [cls(type=pos_type) for pos_type in PositionType]
    
    @property
    def value(self) -> str:
        """Get the position value."""
        return self.type.value
    
    @property
    def display_name(self) -> str:
        """Get the display name for the position."""
        return self.DISPLAY_NAMES[self.type]
    
    @property
    def index(self) -> int:
        """Get the position index for ordering."""
        return self.INDICES[self.type]
    
    def __str__(self) -> str:
        """String representation of the position."""
        return self.value
    
    def __lt__(self, other: 'Position') -> bool:
        """Less than comparison for ordering."""
        if not isinstance(other, Position):
            return NotImplemented
        return self.index < other.index
    
    def __hash__(self) -> int:
        """Hash based on the position type."""
        return hash(self.type)
    
    def __eq__(self, other) -> bool:
        """Equality check based on position type."""
        if not isinstance(other, Position):
            return False
        return self.type == other.type