"""
PlayerProfile aggregate root.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
import uuid

from ..base import AggregateRoot, BusinessRuleViolationError
from ..value_objects.rating import Rating
from ..value_objects.rank_info import RankInfo
from ..value_objects.position import Position
from ..value_objects.contract_status import ContractStatus
from ..entities.match_record import MatchRecord


@dataclass
class PlayerProfile(AggregateRoot):
    """
    PlayerProfile aggregate root representing a player's competitive profile.
    
    A PlayerProfile contains all information related to a player's competitive
    career within a specific region, including ratings, statistics, and match history.
    """
    
    profile_id: str = field(default_factory=lambda: f"prf_{uuid.uuid4().hex[:12]}")
    user_id: str = ""
    region_id: str = ""
    player_name: str = ""
    summoner_name: str = ""
    position: Position = None
    description: Optional[str] = None
    
    # Game-related information
    rank_info: RankInfo = None
    rating: Rating = None
    contract_status: ContractStatus = field(default=ContractStatus.create_free())
    
    # Contract information
    current_team_id: Optional[str] = None
    contract_start: Optional[datetime] = None
    locked_rating: Optional[float] = None
    
    # Statistics
    total_matches: int = 0
    total_wins: int = 0
    total_losses: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_active: Optional[datetime] = None
    
    # Match records (aggregate internal entities)
    match_records: List[MatchRecord] = field(default_factory=list)
    
    def __post_init__(self):
        """Post initialization validation and setup."""
        super().__post_init__()
        
        # Validate required fields
        if not self.user_id.strip():
            raise BusinessRuleViolationError("User ID is required")
        
        if not self.region_id.strip():
            raise BusinessRuleViolationError("Region ID is required")
        
        if not self.player_name.strip():
            raise BusinessRuleViolationError("Player name is required")
        
        if not self.summoner_name.strip():
            raise BusinessRuleViolationError("Summoner name is required")
        
        # Validate player name length
        if len(self.player_name) > 100:
            raise BusinessRuleViolationError(
                "Player name cannot exceed 100 characters"
            )
        
        # Validate summoner name length
        if len(self.summoner_name) > 50:
            raise BusinessRuleViolationError(
                "Summoner name cannot exceed 50 characters"
            )
        
        # Validate description length
        if self.description and len(self.description) > 500:
            raise BusinessRuleViolationError(
                "Description cannot exceed 500 characters"
            )
        
        # Validate statistics
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
        user_id: str,
        region_id: str,
        player_name: str,
        summoner_name: str,
        position: Position,
        rank_info: RankInfo,
        initial_rating: Rating
    ) -> 'PlayerProfile':
        """
        Create a new player profile.
        
        Args:
            user_id: ID of the owning user
            region_id: ID of the region
            player_name: Display name for the player
            summoner_name: League of Legends summoner name
            position: Primary position
            rank_info: Current League of Legends rank
            initial_rating: Initial FlyEsports rating
            
        Returns:
            New PlayerProfile aggregate root
            
        Raises:
            BusinessRuleViolationError: If creation rules are violated
        """
        if not user_id or not user_id.strip():
            raise BusinessRuleViolationError("User ID is required")
        
        if not region_id or not region_id.strip():
            raise BusinessRuleViolationError("Region ID is required")
        
        if not player_name or not player_name.strip():
            raise BusinessRuleViolationError("Player name is required")
        
        if not summoner_name or not summoner_name.strip():
            raise BusinessRuleViolationError("Summoner name is required")
        
        if not position:
            raise BusinessRuleViolationError("Position is required")
        
        if not rank_info:
            raise BusinessRuleViolationError("Rank info is required")
        
        if not initial_rating:
            raise BusinessRuleViolationError("Initial rating is required")
        
        profile = cls(
            user_id=user_id.strip(),
            region_id=region_id.strip(),
            player_name=player_name.strip(),
            summoner_name=summoner_name.strip(),
            position=position,
            rank_info=rank_info,
            rating=initial_rating
        )
        
        # Add domain event for player registration
        from ..events.player_events import PlayerRegisteredEvent
        event = PlayerRegisteredEvent(
            profile_id=profile.profile_id,
            user_id=user_id,
            region_id=region_id,
            player_name=player_name,
            position=position.value,
            initial_rating=initial_rating.current_score,
            timestamp=profile.created_at
        )
        profile.add_domain_event(event)
        
        return profile
    
    def update_rating(
        self,
        new_rating: Rating,
        reason: str,
        match_id: Optional[str] = None
    ) -> None:
        """
        Update player rating.
        
        Args:
            new_rating: New rating value
            reason: Reason for rating update
            match_id: Optional match ID if update is from a match
            
        Raises:
            BusinessRuleViolationError: If update is invalid
        """
        if not reason or not reason.strip():
            raise BusinessRuleViolationError("Rating update reason is required")
        
        old_score = self.rating.current_score
        
        if self.contract_status.is_locked:
            # Locked players: update the current score but keep locked score
            if self.locked_rating is not None:
                new_rating_with_lock = new_rating.with_locked_score(self.locked_rating)
                object.__setattr__(self, 'rating', new_rating_with_lock)
        else:
            # Free players: update rating normally
            object.__setattr__(self, 'rating', new_rating)
        
        object.__setattr__(self, 'updated_at', datetime.utcnow())
        
        # Add domain event for rating update
        from ..events.player_events import PlayerRatingUpdatedEvent
        event = PlayerRatingUpdatedEvent(
            profile_id=self.profile_id,
            old_rating=old_score,
            new_rating=new_rating.current_score,
            reason=reason.strip(),
            match_id=match_id,
            timestamp=self.updated_at
        )
        self.add_domain_event(event)
    
    def sign_to_team(
        self,
        team_id: str,
        locked_rating: Optional[float] = None
    ) -> float:
        """
        Sign player to a team.
        
        Args:
            team_id: ID of the team to sign to
            locked_rating: Optional rating to lock at (defaults to current rating)
            
        Returns:
            The locked rating value
            
        Raises:
            BusinessRuleViolationError: If player cannot be signed
        """
        if not self.contract_status.is_available_for_signing:
            raise BusinessRuleViolationError(
                f"Player is not available for signing (status: {self.contract_status.value})"
            )
        
        if not team_id or not team_id.strip():
            raise BusinessRuleViolationError("Team ID is required")
        
        # Lock rating at current score if not specified
        lock_value = locked_rating if locked_rating is not None else self.rating.current_score
        
        # Update contract status and team information
        object.__setattr__(self, 'contract_status', ContractStatus.create_locked())
        object.__setattr__(self, 'current_team_id', team_id.strip())
        object.__setattr__(self, 'contract_start', datetime.utcnow())
        object.__setattr__(self, 'locked_rating', lock_value)
        object.__setattr__(self, 'updated_at', datetime.utcnow())
        
        # Update rating with locked score
        locked_rating_obj = self.rating.with_locked_score(lock_value)
        object.__setattr__(self, 'rating', locked_rating_obj)
        
        # Add domain event for player signing
        from ..events.player_events import PlayerSignedEvent
        event = PlayerSignedEvent(
            profile_id=self.profile_id,
            team_id=team_id,
            locked_rating=lock_value,
            timestamp=self.updated_at
        )
        self.add_domain_event(event)
        
        return lock_value
    
    def release_from_team(self, reason: str = "contract_ended") -> None:
        """
        Release player from team.
        
        Args:
            reason: Reason for release
            
        Raises:
            BusinessRuleViolationError: If player is not currently signed
        """
        if not self.contract_status.is_locked:
            raise BusinessRuleViolationError(
                f"Player is not currently signed (status: {self.contract_status.value})"
            )
        
        if not reason or not reason.strip():
            raise BusinessRuleViolationError("Release reason is required")
        
        old_team_id = self.current_team_id
        
        # Release from contract
        object.__setattr__(self, 'contract_status', ContractStatus.create_free())
        object.__setattr__(self, 'current_team_id', None)
        object.__setattr__(self, 'contract_start', None)
        object.__setattr__(self, 'locked_rating', None)
        object.__setattr__(self, 'updated_at', datetime.utcnow())
        
        # Unlock rating
        unlocked_rating = self.rating.with_unlocked_score()
        object.__setattr__(self, 'rating', unlocked_rating)
        
        # Add domain event for player release
        from ..events.player_events import PlayerReleasedEvent
        event = PlayerReleasedEvent(
            profile_id=self.profile_id,
            old_team_id=old_team_id,
            reason=reason.strip(),
            new_rating=self.rating.current_score,
            timestamp=self.updated_at
        )
        self.add_domain_event(event)
    
    def add_match_record(self, match_record: MatchRecord) -> None:
        """
        Add a match record to the player's history.
        
        Args:
            match_record: Match record to add
            
        Raises:
            BusinessRuleViolationError: If match record is invalid
        """
        if not match_record:
            raise BusinessRuleViolationError("Match record is required")
        
        if match_record.player_profile_id != self.profile_id:
            raise BusinessRuleViolationError(
                "Match record does not belong to this player profile"
            )
        
        # Add match record
        self.match_records.append(match_record)
        
        # Update statistics
        object.__setattr__(self, 'total_matches', self.total_matches + 1)
        
        if match_record.was_victory:
            object.__setattr__(self, 'total_wins', self.total_wins + 1)
        elif match_record.was_defeat:
            object.__setattr__(self, 'total_losses', self.total_losses + 1)
        
        # Update timestamps
        object.__setattr__(self, 'last_active', match_record.match_date)
        object.__setattr__(self, 'updated_at', datetime.utcnow())
        
        # Add domain event for match completion
        from ..events.player_events import PlayerMatchCompletedEvent
        event = PlayerMatchCompletedEvent(
            profile_id=self.profile_id,
            match_id=match_record.match_id,
            result=match_record.result,
            rating_before=match_record.rating_before,
            rating_after=match_record.rating_after,
            kda=f"{match_record.kills}/{match_record.deaths}/{match_record.assists}",
            champion_name=match_record.champion_name,
            timestamp=self.updated_at
        )
        self.add_domain_event(event)
    
    def update_rank_info(self, new_rank_info: RankInfo) -> None:
        """
        Update League of Legends rank information.
        
        Args:
            new_rank_info: New rank information
        """
        if not new_rank_info:
            raise BusinessRuleViolationError("Rank info is required")
        
        old_rank = str(self.rank_info) if self.rank_info else "Unranked"
        new_rank = str(new_rank_info)
        
        object.__setattr__(self, 'rank_info', new_rank_info)
        object.__setattr__(self, 'updated_at', datetime.utcnow())
        
        # Add domain event for rank update
        if old_rank != new_rank:
            from ..events.player_events import PlayerRankUpdatedEvent
            event = PlayerRankUpdatedEvent(
                profile_id=self.profile_id,
                old_rank=old_rank,
                new_rank=new_rank,
                timestamp=self.updated_at
            )
            self.add_domain_event(event)
    
    def update_profile(
        self,
        player_name: Optional[str] = None,
        description: Optional[str] = None
    ) -> None:
        """
        Update player profile information.
        
        Args:
            player_name: New player name
            description: New description
        """
        has_changes = False
        
        if player_name is not None and player_name != self.player_name:
            if not player_name.strip():
                raise BusinessRuleViolationError("Player name cannot be empty")
            if len(player_name.strip()) > 100:
                raise BusinessRuleViolationError(
                    "Player name cannot exceed 100 characters"
                )
            object.__setattr__(self, 'player_name', player_name.strip())
            has_changes = True
        
        if description is not None and description != self.description:
            if description and len(description.strip()) > 500:
                raise BusinessRuleViolationError(
                    "Description cannot exceed 500 characters"
                )
            object.__setattr__(
                self, 'description', 
                description.strip() if description else None
            )
            has_changes = True
        
        if has_changes:
            object.__setattr__(self, 'updated_at', datetime.utcnow())
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate."""
        if self.total_matches == 0:
            return 0.0
        return self.total_wins / self.total_matches
    
    @property
    def is_available_for_signing(self) -> bool:
        """Check if player is available for signing."""
        return self.contract_status.is_available_for_signing
    
    @property
    def current_market_value(self) -> float:
        """Get current market value (effective rating)."""
        return self.rating.effective_score if self.rating else 0.0
    
    @property
    def is_experienced(self) -> bool:
        """Check if player has enough matches to be considered experienced."""
        return self.total_matches >= 10
    
    @property
    def recent_match_records(self) -> List[MatchRecord]:
        """Get recent match records (last 10)."""
        return sorted(self.match_records, key=lambda x: x.match_date, reverse=True)[:10]
    
    @property
    def performance_summary(self) -> dict:
        """Get performance summary."""
        return {
            "player_name": self.player_name,
            "position": self.position.display_name if self.position else "Unknown",
            "rank": str(self.rank_info) if self.rank_info else "Unranked",
            "rating": round(self.rating.current_score, 1) if self.rating else 0.0,
            "effective_rating": round(self.current_market_value, 1),
            "total_matches": self.total_matches,
            "win_rate": round(self.win_rate * 100, 1),
            "contract_status": self.contract_status.display_name,
            "team_id": self.current_team_id,
            "last_active": self.last_active
        }
    
    def __str__(self) -> str:
        """String representation of the player profile."""
        return (f"PlayerProfile({self.player_name}, "
                f"{self.position.value if self.position else 'N/A'}, "
                f"rating={self.rating.current_score if self.rating else 0:.1f}, "
                f"status={self.contract_status.value})")
    
    def __hash__(self) -> int:
        """Hash based on profile ID."""
        return hash(self.profile_id)