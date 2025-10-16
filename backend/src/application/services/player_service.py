"""
Player application service.
"""

from typing import List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from src.domain.repositories.player_profile import PlayerProfileRepository
from src.domain.repositories.region import RegionRepository
from src.domain.repositories.user import UserRepository
from src.application.use_cases.player_registration import (
    PlayerRegistrationUseCase,
    PlayerRegistrationCommand,
    PlayerRegistrationResult,
)
from src.domain.base import BusinessRuleViolationError


@dataclass
class PlayerProfileSummary:
    """
    Summary of a player profile.
    """

    profile_id: str
    player_name: str
    summoner_name: str
    position: str
    current_rating: float
    effective_rating: float
    rank_display: str
    contract_status: str
    current_team_id: Optional[str]
    total_matches: int
    win_rate: float
    region_id: str
    created_at: datetime
    last_active: Optional[datetime]


@dataclass
class RegionSummary:
    """
    Summary of a region.
    """

    region_id: str
    region_name: str
    status: str
    total_players: int
    active_players: int
    is_active: bool
    created_at: datetime


class PlayerService:
    """
    Application service for player-related operations.
    """

    def __init__(
        self,
        player_profile_repository: PlayerProfileRepository,
        region_repository: RegionRepository,
        user_repository: UserRepository,
    ):
        """
        Initialize the service with repositories.

        Args:
            player_profile_repository: PlayerProfile repository
            region_repository: Region repository
            user_repository: User repository
        """
        self.player_profile_repository = player_profile_repository
        self.region_repository = region_repository
        self.user_repository = user_repository
        self.registration_use_case = PlayerRegistrationUseCase(
            player_profile_repository=player_profile_repository,
            region_repository=region_repository,
            user_repository=user_repository,
        )

    async def register_player_to_region(
        self,
        user_id: str,
        region_id: str,
        player_name: str,
        summoner_name: str,
        position: str,
        rank_tier: Optional[str] = None,
        rank_division: Optional[str] = None,
        league_points: Optional[int] = None,
        description: Optional[str] = None,
    ) -> PlayerRegistrationResult:
        """
        Register a player to a region.

        Args:
            user_id: User ID
            region_id: Region ID
            player_name: Display name for the player
            summoner_name: League of Legends summoner name
            position: Player position
            rank_tier: Optional rank tier
            rank_division: Optional rank division
            league_points: Optional league points
            description: Optional player description

        Returns:
            Player registration result

        Raises:
            BusinessRuleViolationError: If registration violates business rules
        """
        command = PlayerRegistrationCommand(
            user_id=user_id,
            region_id=region_id,
            player_name=player_name,
            summoner_name=summoner_name,
            position=position,
            rank_tier=rank_tier,
            rank_division=rank_division,
            league_points=league_points,
            description=description,
        )

        return await self.registration_use_case.execute(command)

    async def get_player_profile(
        self, profile_id: str
    ) -> Optional[PlayerProfileSummary]:
        """
        Get player profile by ID.

        Args:
            profile_id: Profile ID

        Returns:
            Player profile summary if found
        """
        profile = await self.player_profile_repository.find_by_id(profile_id)
        if not profile:
            return None

        return self._profile_to_summary(profile)

    async def get_user_profiles(self, user_id: str) -> List[PlayerProfileSummary]:
        """
        Get all player profiles for a user.

        Args:
            user_id: User ID

        Returns:
            List of player profile summaries
        """
        profiles = await self.player_profile_repository.find_by_user_id(user_id)
        return [self._profile_to_summary(profile) for profile in profiles]

    async def get_region_players(
        self, region_id: str, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[PlayerProfileSummary]:
        """
        Get players in a region.

        Args:
            region_id: Region ID
            limit: Optional result limit
            offset: Optional result offset

        Returns:
            List of player profile summaries
        """
        profiles = await self.player_profile_repository.find_by_region(
            region_id, limit, offset
        )
        return [self._profile_to_summary(profile) for profile in profiles]

    async def get_free_players(
        self, region_id: str, position: Optional[str] = None
    ) -> List[PlayerProfileSummary]:
        """
        Get free (uncontracted) players in a region.

        Args:
            region_id: Region ID
            position: Optional position filter

        Returns:
            List of free player profile summaries
        """
        profiles = await self.player_profile_repository.find_free_players(
            region_id, position
        )
        return [self._profile_to_summary(profile) for profile in profiles]

    async def check_summoner_availability(
        self,
        summoner_name: str,
        region_id: str,
        exclude_profile_id: Optional[str] = None,
    ) -> bool:
        """
        Check if summoner name is available in a region.

        Args:
            summoner_name: Summoner name to check
            region_id: Region ID
            exclude_profile_id: Optional profile ID to exclude

        Returns:
            True if summoner name is available, False otherwise
        """
        exists = await self.player_profile_repository.exists_summoner_in_region(
            summoner_name, region_id, exclude_profile_id
        )
        return not exists

    async def get_all_regions(self) -> List[RegionSummary]:
        """
        Get all regions.

        Returns:
            List of region summaries
        """
        regions = await self.region_repository.find_all()
        return [self._region_to_summary(region) for region in regions]

    async def get_active_regions(self) -> List[RegionSummary]:
        """
        Get all active regions.

        Returns:
            List of active region summaries
        """
        regions = await self.region_repository.find_all_active()
        return [self._region_to_summary(region) for region in regions]

    async def get_region_by_id(self, region_id: str) -> Optional[RegionSummary]:
        """
        Get region by ID.

        Args:
            region_id: Region ID

        Returns:
            Region summary if found
        """
        region = await self.region_repository.find_by_id(region_id)
        return self._region_to_summary(region) if region else None

    def _profile_to_summary(self, profile: Any) -> PlayerProfileSummary:
        """
        Convert player profile domain object to summary.

        Args:
            profile: PlayerProfile domain object

        Returns:
            PlayerProfileSummary
        """
        rank_display = "Unranked"
        if profile.rank_info and not profile.rank_info.is_unranked:
            if profile.rank_info.tier.name in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
                rank_display = (
                    f"{profile.rank_info.tier.value} "
                    f"{profile.rank_info.league_points} LP"
                )
            else:
                rank_display = (
                    f"{profile.rank_info.tier.value} {profile.rank_info.division.value}"
                )

        return PlayerProfileSummary(
            profile_id=profile.profile_id,
            player_name=profile.player_name,
            summoner_name=profile.summoner_name,
            position=profile.position.display_name,
            current_rating=profile.rating.current_score if profile.rating else 0.0,
            effective_rating=profile.current_market_value,
            rank_display=rank_display,
            contract_status=profile.contract_status.display_name,
            current_team_id=profile.current_team_id,
            total_matches=profile.total_matches,
            win_rate=profile.win_rate * 100,
            region_id=profile.region_id,
            created_at=profile.created_at,
            last_active=profile.last_active,
        )

    def _region_to_summary(self, region: Any) -> RegionSummary:
        """
        Convert region domain object to summary.

        Args:
            region: Region domain object

        Returns:
            RegionSummary
        """
        return RegionSummary(
            region_id=region.region_id,
            region_name=region.region_name,
            status=region.status,
            total_players=region.total_players,
            active_players=region.active_players,
            is_active=region.is_active,
            created_at=region.created_at,
        )
