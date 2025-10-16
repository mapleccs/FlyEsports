"""
Roster slot entity for team composition management.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import uuid

from ..base import Entity, BusinessRuleViolationError
from ..value_objects.position import Position


@dataclass
class RosterSlot(Entity):
    """
    Roster slot entity representing a player's position within a team.

    This entity tracks a player's membership in a team, including their
    position, signing cost, and tenure information.
    """

    slot_id: str = ""
    profile_id: str = ""
    player_name: str = ""
    position: Optional[Position] = None
    signing_cost: float = 0.0
    joined_at: datetime = field(default_factory=datetime.utcnow)
    left_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Post initialization validation."""

        # Validate required fields
        if not self.profile_id.strip():
            raise BusinessRuleViolationError("Profile ID is required")

        if not self.player_name.strip():
            raise BusinessRuleViolationError("Player name is required")

        if not self.position:
            raise BusinessRuleViolationError("Position is required")

        # Validate signing cost
        if self.signing_cost < 0:
            raise BusinessRuleViolationError(
                f"Signing cost cannot be negative, got {self.signing_cost}"
            )

        # Validate player name length
        if len(self.player_name) > 100:
            raise BusinessRuleViolationError("Player name cannot exceed 100 characters")

        # Validate dates
        if self.left_at and self.left_at < self.joined_at:
            raise BusinessRuleViolationError("Left date cannot be before joined date")

    @classmethod
    def create(
        cls,
        profile_id: str,
        player_name: str,
        position: Position,
        signing_cost: float,
        joined_at: Optional[datetime] = None,
    ) -> "RosterSlot":
        """
        Create a new roster slot.

        Args:
            profile_id: Player profile ID
            player_name: Player's display name
            position: Position in the team
            signing_cost: Cost to sign this player
            joined_at: When the player joined (defaults to now)

        Returns:
            New RosterSlot entity

        Raises:
            BusinessRuleViolationError: If creation rules are violated
        """
        if not profile_id or not profile_id.strip():
            raise BusinessRuleViolationError("Profile ID is required")

        if not player_name or not player_name.strip():
            raise BusinessRuleViolationError("Player name is required")

        if not position:
            raise BusinessRuleViolationError("Position is required")

        if signing_cost < 0:
            raise BusinessRuleViolationError("Signing cost cannot be negative")

        slot_id = f"slot_{uuid.uuid4().hex[:12]}"
        join_time = joined_at if joined_at else datetime.utcnow()

        return cls(
            slot_id=slot_id,
            profile_id=profile_id.strip(),
            player_name=player_name.strip(),
            position=position,
            signing_cost=signing_cost,
            joined_at=join_time,
        )

    def release(self, left_at: Optional[datetime] = None) -> None:
        """
        Mark the roster slot as released.

        Args:
            left_at: When the player left (defaults to now)
        """
        if self.is_active:
            release_time = left_at if left_at else datetime.utcnow()
            object.__setattr__(self, "left_at", release_time)

    def update_player_info(self, player_name: str) -> None:
        """
        Update player information.

        Args:
            player_name: New player name

        Raises:
            BusinessRuleViolationError: If name is invalid
        """
        if not player_name or not player_name.strip():
            raise BusinessRuleViolationError("Player name is required")

        if len(player_name.strip()) > 100:
            raise BusinessRuleViolationError("Player name cannot exceed 100 characters")

        object.__setattr__(self, "player_name", player_name.strip())

    @property
    def is_active(self) -> bool:
        """Check if the player is currently active in this slot."""
        return self.left_at is None

    @property
    def is_released(self) -> bool:
        """Check if the player has been released from this slot."""
        return self.left_at is not None

    @property
    def tenure_days(self) -> int:
        """Get the number of days the player has been/was in the team."""
        end_time = self.left_at if self.left_at else datetime.utcnow()
        tenure = end_time - self.joined_at
        return tenure.days

    @property
    def position_display_name(self) -> str:
        """Get the display name for the position."""
        return self.position.display_name

    @property
    def slot_summary(self) -> dict:
        """Get a summary of the roster slot."""
        return {
            "slot_id": self.slot_id,
            "profile_id": self.profile_id,
            "player_name": self.player_name,
            "position": self.position.value,
            "position_display": self.position.display_name,
            "signing_cost": self.signing_cost,
            "joined_at": self.joined_at,
            "left_at": self.left_at,
            "is_active": self.is_active,
            "tenure_days": self.tenure_days,
        }

    def __str__(self) -> str:
        """String representation of the roster slot."""
        status = "active" if self.is_active else "released"
        return (
            f"RosterSlot({self.player_name}, "
            f"{self.position.value}, "
            f"cost={self.signing_cost}, "
            f"status={status})"
        )

    def __hash__(self) -> int:
        """Hash based on slot ID."""
        return hash(self.slot_id)
