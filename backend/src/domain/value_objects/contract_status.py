"""
Contract status value object for player contracts.
"""

from enum import Enum
from dataclasses import dataclass
from typing import ClassVar, Dict

from ..base import ValueObject


class ContractStatusType(Enum):
    """Enumeration of player contract statuses."""

    FREE = "FREE"  # 自由选手
    LOCKED = "LOCKED"  # 已签约
    PENDING = "PENDING"  # 待处理状态


@dataclass(frozen=True)
class ContractStatus(ValueObject):
    """
    Contract status value object with business rules.
    """

    type: ContractStatusType

    # Display name mappings
    DISPLAY_NAMES: ClassVar[Dict[ContractStatusType, str]] = {
        ContractStatusType.FREE: "自由选手",
        ContractStatusType.LOCKED: "已签约",
        ContractStatusType.PENDING: "待处理",
    }

    @classmethod
    def create_free(cls) -> "ContractStatus":
        """Create FREE contract status."""
        return cls(type=ContractStatusType.FREE)

    @classmethod
    def create_locked(cls) -> "ContractStatus":
        """Create LOCKED contract status."""
        return cls(type=ContractStatusType.LOCKED)

    @classmethod
    def create_pending(cls) -> "ContractStatus":
        """Create PENDING contract status."""
        return cls(type=ContractStatusType.PENDING)

    @classmethod
    def from_string(cls, status_str: str) -> "ContractStatus":
        """
        Create ContractStatus from string.

        Args:
            status_str: Status string (case-insensitive)

        Returns:
            ContractStatus value object

        Raises:
            ValueError: If status string is invalid
        """
        try:
            status_type = ContractStatusType(status_str.upper())
            return cls(type=status_type)
        except ValueError as e:
            valid_statuses = [s.value for s in ContractStatusType]
            raise ValueError(
                f"Invalid contract status: {status_str}. Valid statuses: {valid_statuses}"
            ) from e

    @property
    def value(self) -> str:
        """Get the contract status value."""
        return self.type.value

    @property
    def display_name(self) -> str:
        """Get the display name for the contract status."""
        return self.DISPLAY_NAMES[self.type]

    @property
    def is_available_for_signing(self) -> bool:
        """Check if the player is available for signing."""
        return self.type == ContractStatusType.FREE

    @property
    def is_active(self) -> bool:
        """Check if the player is in an active status."""
        return self.type in [ContractStatusType.FREE, ContractStatusType.LOCKED]

    @property
    def is_locked(self) -> bool:
        """Check if the player is locked (signed to a team)."""
        return self.type == ContractStatusType.LOCKED

    @property
    def is_pending(self) -> bool:
        """Check if the player is in pending status."""
        return self.type == ContractStatusType.PENDING

    def can_transition_to(self, new_status: "ContractStatus") -> bool:
        """
        Check if transition to new status is allowed.

        Args:
            new_status: The target contract status

        Returns:
            True if transition is allowed
        """
        # Define allowed transitions
        allowed_transitions = {
            ContractStatusType.FREE: [
                ContractStatusType.LOCKED,
                ContractStatusType.PENDING,
            ],
            ContractStatusType.LOCKED: [
                ContractStatusType.FREE,
                ContractStatusType.PENDING,
            ],
            ContractStatusType.PENDING: [
                ContractStatusType.FREE,
                ContractStatusType.LOCKED,
            ],
        }

        return new_status.type in allowed_transitions.get(self.type, [])

    def __str__(self) -> str:
        """String representation of the contract status."""
        return self.value

    def __hash__(self) -> int:
        """Hash based on the contract status type."""
        return hash(self.type)

    def __eq__(self, other: object) -> bool:
        """Equality check based on contract status type."""
        if not isinstance(other, ContractStatus):
            return False
        return self.type == other.type
