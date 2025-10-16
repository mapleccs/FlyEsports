"""
Team aggregate root.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime
import uuid

from ..base import AggregateRoot, BusinessRuleViolationError
from ..value_objects.position import Position
from ..entities.roster_slot import RosterSlot


@dataclass
class Team(AggregateRoot):
    """
    Team aggregate root representing a competitive team.

    A Team manages its roster, tracks performance statistics,
    and maintains team information within a specific region.
    """

    team_id: str = field(default_factory=lambda: f"team_{uuid.uuid4().hex[:12]}")
    team_name: str = ""
    team_tag: str = ""
    region_id: str = ""
    owner_id: str = ""
    description: Optional[str] = None
    logo_url: Optional[str] = None
    status: str = "active"  # active, disbanded

    # Roster management
    roster: Dict[Position, Optional[RosterSlot]] = field(default_factory=dict)

    # Statistics
    total_cost: float = 0.0
    total_matches: int = 0
    total_wins: int = 0
    total_losses: int = 0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Post initialization validation and setup."""

        # Initialize empty roster if not provided
        if not self.roster:
            all_positions = Position.all_positions()
            object.__setattr__(self, "roster", {pos: None for pos in all_positions})

        # Validate required fields
        if not self.region_id.strip():
            raise BusinessRuleViolationError("Region ID is required")

        if not self.owner_id.strip():
            raise BusinessRuleViolationError("Owner ID is required")

        # Validate team name
        if self.team_name and len(self.team_name) > 100:
            raise BusinessRuleViolationError("Team name cannot exceed 100 characters")

        # Validate team tag
        if self.team_tag and (len(self.team_tag) < 2 or len(self.team_tag) > 10):
            raise BusinessRuleViolationError(
                "Team tag must be between 2 and 10 characters"
            )

        # Validate description
        if self.description and len(self.description) > 1000:
            raise BusinessRuleViolationError(
                "Description cannot exceed 1000 characters"
            )

        # Validate status
        valid_statuses = {"active", "disbanded"}
        if self.status not in valid_statuses:
            raise BusinessRuleViolationError(
                f"Invalid team status: {self.status}. Valid statuses: {valid_statuses}"
            )

        # Validate statistics
        if self.total_cost < 0:
            raise BusinessRuleViolationError("Total cost cannot be negative")

        if self.total_matches < 0:
            raise BusinessRuleViolationError("Total matches cannot be negative")

        if self.total_wins < 0:
            raise BusinessRuleViolationError("Total wins cannot be negative")

        if self.total_losses < 0:
            raise BusinessRuleViolationError("Total losses cannot be negative")

        if self.total_wins + self.total_losses > self.total_matches:
            raise BusinessRuleViolationError(
                "Wins + losses cannot exceed total matches"
            )

    @classmethod
    def create(
        cls,
        team_name: str,
        team_tag: str,
        region_id: str,
        owner_id: str,
        description: Optional[str] = None,
    ) -> "Team":
        """
        Create a new team.

        Args:
            team_name: Team's display name
            team_tag: Team's short tag/abbreviation
            region_id: ID of the region this team belongs to
            owner_id: ID of the team owner
            description: Optional team description

        Returns:
            New Team aggregate root

        Raises:
            BusinessRuleViolationError: If creation rules are violated
        """
        if not team_name or not team_name.strip():
            raise BusinessRuleViolationError("Team name is required")

        if not team_tag or not team_tag.strip():
            raise BusinessRuleViolationError("Team tag is required")

        if not region_id or not region_id.strip():
            raise BusinessRuleViolationError("Region ID is required")

        if not owner_id or not owner_id.strip():
            raise BusinessRuleViolationError("Owner ID is required")

        team_name = team_name.strip()
        team_tag = team_tag.strip().upper()

        team = cls(
            team_name=team_name,
            team_tag=team_tag,
            region_id=region_id.strip(),
            owner_id=owner_id.strip(),
            description=description.strip() if description else None,
        )

        # Add domain event for team creation
        from ..events.team_events import TeamCreatedEvent

        event = TeamCreatedEvent(
            team_id=team.team_id,
            team_name=team_name,
            team_tag=team_tag,
            region_id=region_id,
            owner_id=owner_id,
            timestamp=team.created_at,
        )
        team.add_domain_event(event)

        return team

    def add_player(
        self, profile_id: str, player_name: str, position: Position, signing_cost: float
    ) -> None:
        """
        Add a player to the team roster.

        Args:
            profile_id: Player profile ID
            player_name: Player's display name
            position: Position to fill
            signing_cost: Cost to sign this player

        Raises:
            BusinessRuleViolationError: If addition rules are violated
        """
        if self.status != "active":
            raise BusinessRuleViolationError(
                f"Cannot add players to inactive team (status: {self.status})"
            )

        if not profile_id or not profile_id.strip():
            raise BusinessRuleViolationError("Profile ID is required")

        if not player_name or not player_name.strip():
            raise BusinessRuleViolationError("Player name is required")

        if not position:
            raise BusinessRuleViolationError("Position is required")

        if signing_cost < 0:
            raise BusinessRuleViolationError("Signing cost cannot be negative")

        if self.roster[position] is not None:
            raise BusinessRuleViolationError(
                f"Position {position.value} is already occupied by "
                f"{self.roster[position].player_name}"
            )

        # Create roster slot
        roster_slot = RosterSlot.create(
            profile_id=profile_id.strip(),
            player_name=player_name.strip(),
            position=position,
            signing_cost=signing_cost,
        )

        # Update roster and costs
        self.roster[position] = roster_slot
        object.__setattr__(self, "total_cost", self.total_cost + signing_cost)
        object.__setattr__(self, "updated_at", datetime.utcnow())

        # Add domain event for player addition
        from ..events.team_events import PlayerAddedToTeamEvent

        event = PlayerAddedToTeamEvent(
            team_id=self.team_id,
            profile_id=profile_id,
            position=position.value,
            signing_cost=signing_cost,
            timestamp=self.updated_at,
        )
        self.add_domain_event(event)

    def remove_player(self, position: Position, reason: str = "released") -> None:
        """
        Remove a player from the team roster.

        Args:
            position: Position to remove player from
            reason: Reason for removal

        Raises:
            BusinessRuleViolationError: If removal rules are violated
        """
        if not position:
            raise BusinessRuleViolationError("Position is required")

        if not reason or not reason.strip():
            raise BusinessRuleViolationError("Reason is required")

        if self.roster[position] is None:
            raise BusinessRuleViolationError(f"No player in position {position.value}")

        removed_slot = self.roster[position]

        # Mark slot as released and remove from roster
        removed_slot.release()
        self.roster[position] = None

        # Update costs and timestamp
        object.__setattr__(
            self, "total_cost", self.total_cost - removed_slot.signing_cost
        )
        object.__setattr__(self, "updated_at", datetime.utcnow())

        # Add domain event for player removal
        from ..events.team_events import PlayerRemovedFromTeamEvent

        event = PlayerRemovedFromTeamEvent(
            team_id=self.team_id,
            profile_id=removed_slot.profile_id,
            position=position.value,
            reason=reason.strip(),
            cost_reduction=removed_slot.signing_cost,
            timestamp=self.updated_at,
        )
        self.add_domain_event(event)

    def update_team_info(
        self,
        team_name: Optional[str] = None,
        team_tag: Optional[str] = None,
        description: Optional[str] = None,
        logo_url: Optional[str] = None,
    ) -> None:
        """
        Update team information.

        Args:
            team_name: New team name
            team_tag: New team tag
            description: New description
            logo_url: New logo URL
        """
        old_data = {
            "team_name": self.team_name,
            "team_tag": self.team_tag,
            "description": self.description,
            "logo_url": self.logo_url,
        }

        has_changes = False

        if team_name is not None and team_name != self.team_name:
            if not team_name.strip():
                raise BusinessRuleViolationError("Team name cannot be empty")
            if len(team_name.strip()) > 100:
                raise BusinessRuleViolationError(
                    "Team name cannot exceed 100 characters"
                )
            object.__setattr__(self, "team_name", team_name.strip())
            has_changes = True

        if team_tag is not None and team_tag != self.team_tag:
            if not team_tag.strip():
                raise BusinessRuleViolationError("Team tag cannot be empty")
            tag = team_tag.strip().upper()
            if len(tag) < 2 or len(tag) > 10:
                raise BusinessRuleViolationError(
                    "Team tag must be between 2 and 10 characters"
                )
            object.__setattr__(self, "team_tag", tag)
            has_changes = True

        if description is not None and description != self.description:
            if description and len(description.strip()) > 1000:
                raise BusinessRuleViolationError(
                    "Description cannot exceed 1000 characters"
                )
            object.__setattr__(
                self, "description", description.strip() if description else None
            )
            has_changes = True

        if logo_url is not None and logo_url != self.logo_url:
            object.__setattr__(self, "logo_url", logo_url)
            has_changes = True

        if has_changes:
            object.__setattr__(self, "updated_at", datetime.utcnow())

            # Add domain event for team info update
            from ..events.team_events import TeamInfoUpdatedEvent

            event = TeamInfoUpdatedEvent(
                team_id=self.team_id,
                old_data=old_data,
                new_data={
                    "team_name": self.team_name,
                    "team_tag": self.team_tag,
                    "description": self.description,
                    "logo_url": self.logo_url,
                },
                timestamp=self.updated_at,
            )
            self.add_domain_event(event)

    def record_match_result(
        self, match_id: str, result: str, opponent_team_id: Optional[str] = None
    ) -> None:
        """
        Record a match result for the team.

        Args:
            match_id: Unique match identifier
            result: Match result ("win", "loss", "draw")
            opponent_team_id: Optional opponent team ID

        Raises:
            BusinessRuleViolationError: If result is invalid
        """
        valid_results = {"win", "loss", "draw"}
        if result not in valid_results:
            raise BusinessRuleViolationError(
                f"Invalid match result: {result}. Valid results: {valid_results}"
            )

        if not match_id or not match_id.strip():
            raise BusinessRuleViolationError("Match ID is required")

        # Update match statistics
        object.__setattr__(self, "total_matches", self.total_matches + 1)

        if result == "win":
            object.__setattr__(self, "total_wins", self.total_wins + 1)
        elif result == "loss":
            object.__setattr__(self, "total_losses", self.total_losses + 1)

        object.__setattr__(self, "updated_at", datetime.utcnow())

        # Add domain event for match result
        from ..events.team_events import TeamMatchResultEvent

        event = TeamMatchResultEvent(
            team_id=self.team_id,
            match_id=match_id.strip(),
            result=result,
            opponent_team_id=opponent_team_id or "",
            total_matches=self.total_matches,
            total_wins=self.total_wins,
            total_losses=self.total_losses,
            timestamp=self.updated_at,
        )
        self.add_domain_event(event)

    def disband(self, reason: str = "voluntary") -> None:
        """
        Disband the team.

        Args:
            reason: Reason for disbanding

        Raises:
            BusinessRuleViolationError: If team cannot be disbanded
        """
        if self.status != "active":
            raise BusinessRuleViolationError(
                f"Cannot disband inactive team (status: {self.status})"
            )

        if not reason or not reason.strip():
            raise BusinessRuleViolationError("Disbanding reason is required")

        # Get final roster before disbanding
        final_roster = [
            slot.profile_id
            for slot in self.roster.values()
            if slot is not None and slot.is_active
        ]

        # Release all active players
        for position, slot in self.roster.items():
            if slot is not None and slot.is_active:
                slot.release()

        # Update team status
        object.__setattr__(self, "status", "disbanded")
        object.__setattr__(self, "updated_at", datetime.utcnow())

        # Add domain event for team disbanding
        from ..events.team_events import TeamDisbandedEvent

        event = TeamDisbandedEvent(
            team_id=self.team_id,
            reason=reason.strip(),
            final_roster=final_roster,
            timestamp=self.updated_at,
        )
        self.add_domain_event(event)

    @property
    def player_count(self) -> int:
        """Get the number of active players in the roster."""
        return sum(
            1 for slot in self.roster.values() if slot is not None and slot.is_active
        )

    @property
    def is_full_roster(self) -> bool:
        """Check if the team has a full roster (5 players)."""
        return self.player_count == 5

    @property
    def win_rate(self) -> float:
        """Calculate win rate."""
        if self.total_matches == 0:
            return 0.0
        return self.total_wins / self.total_matches

    @property
    def is_active(self) -> bool:
        """Check if the team is active."""
        return self.status == "active"

    @property
    def is_disbanded(self) -> bool:
        """Check if the team is disbanded."""
        return self.status == "disbanded"

    @property
    def active_players(self) -> List[RosterSlot]:
        """Get list of active players."""
        return [
            slot for slot in self.roster.values() if slot is not None and slot.is_active
        ]

    @property
    def roster_summary(self) -> Dict[str, Optional[dict]]:
        """Get a summary of the current roster."""
        return {
            position.value: slot.slot_summary if slot else None
            for position, slot in self.roster.items()
        }

    @property
    def team_summary(self) -> dict:
        """Get a summary of team information."""
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "team_tag": self.team_tag,
            "region_id": self.region_id,
            "owner_id": self.owner_id,
            "status": self.status,
            "player_count": self.player_count,
            "is_full_roster": self.is_full_roster,
            "total_cost": self.total_cost,
            "total_matches": self.total_matches,
            "win_rate": round(self.win_rate * 100, 1),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def get_player_in_position(self, position: Position) -> Optional[RosterSlot]:
        """
        Get the player in a specific position.

        Args:
            position: Position to check

        Returns:
            RosterSlot if occupied, None otherwise
        """
        return self.roster.get(position)

    def has_player(self, profile_id: str) -> bool:
        """
        Check if a player is on the team.

        Args:
            profile_id: Player profile ID to check

        Returns:
            True if player is on the team
        """
        return any(
            slot and slot.is_active and slot.profile_id == profile_id
            for slot in self.roster.values()
        )

    def __str__(self) -> str:
        """String representation of the team."""
        return (
            f"Team({self.team_name} [{self.team_tag}], "
            f"players={self.player_count}/5, "
            f"status={self.status})"
        )

    def __hash__(self) -> int:
        """Hash based on team ID."""
        return hash(self.team_id)
