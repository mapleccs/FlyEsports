"""
Player registration use case.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from src.domain.aggregates.player_profile import PlayerProfile
from src.domain.repositories.player_profile import PlayerProfileRepository
from src.domain.repositories.region import RegionRepository
from src.domain.repositories.user import UserRepository
from src.domain.value_objects.position import Position
from src.domain.value_objects.rating import Rating
from src.domain.value_objects.rank_info import RankInfo, RankTier, RankDivision
from src.domain.base import BusinessRuleViolationError


@dataclass
class PlayerRegistrationCommand:
    """
    Command for player registration.
    """

    user_id: str
    region_id: str
    player_name: str
    summoner_name: str
    position: str
    rank_tier: Optional[str] = None
    rank_division: Optional[str] = None
    league_points: Optional[int] = None
    description: Optional[str] = None


@dataclass
class PlayerRegistrationResult:
    """
    Result of player registration.
    """

    profile_id: str
    player_name: str
    summoner_name: str
    position: str
    current_rating: float
    region_id: str
    created_at: datetime


class PlayerRegistrationUseCase:
    """
    Use case for registering a player to a region.
    """

    def __init__(
        self,
        player_profile_repository: PlayerProfileRepository,
        region_repository: RegionRepository,
        user_repository: UserRepository,
    ):
        """
        Initialize the use case with repositories.

        Args:
            player_profile_repository: PlayerProfile repository
            region_repository: Region repository
            user_repository: User repository
        """
        self.player_profile_repository = player_profile_repository
        self.region_repository = region_repository
        self.user_repository = user_repository

    async def execute(
        self, command: PlayerRegistrationCommand
    ) -> PlayerRegistrationResult:
        """
        Execute player registration.

        Args:
            command: Player registration command

        Returns:
            Player registration result

        Raises:
            BusinessRuleViolationError: If registration violates business rules
        """
        # Validate user exists
        user = await self.user_repository.find_by_id(int(command.user_id))
        if not user:
            raise BusinessRuleViolationError(f"User not found: {command.user_id}")

        if not user.is_active:
            raise BusinessRuleViolationError("User account is inactive")

        # Validate region exists
        region = await self.region_repository.find_by_id(command.region_id)
        if not region:
            raise BusinessRuleViolationError(f"Region not found: {command.region_id}")

        if not region.is_active:
            raise BusinessRuleViolationError("Region is not active")

        # Check if user already has a profile in this region
        existing_profile = await self.player_profile_repository.find_by_user_and_region(
            command.user_id, command.region_id
        )
        if existing_profile:
            raise BusinessRuleViolationError(
                "User already has a player profile in this region"
            )

        # Check if summoner name is already taken in this region
        summoner_exists = (
            await self.player_profile_repository.exists_summoner_in_region(
                command.summoner_name, command.region_id
            )
        )
        if summoner_exists:
            raise BusinessRuleViolationError(
                f"Summoner name '{command.summoner_name}' is already taken in this region"
            )

        # Create position value object
        try:
            position = Position.from_string(command.position)
        except BusinessRuleViolationError as e:
            raise BusinessRuleViolationError(f"Invalid position: {e}")

        # Create rank info if provided
        rank_info = None
        if command.rank_tier and command.rank_division:
            try:
                tier = RankTier(command.rank_tier.upper())
                division = RankDivision(command.rank_division.upper())
                rank_info = RankInfo.create(
                    tier=tier,
                    division=division,
                    league_points=command.league_points or 0,
                )
            except (ValueError, BusinessRuleViolationError) as e:
                raise BusinessRuleViolationError(f"Invalid rank information: {e}")

        # If no rank provided, create unranked
        if rank_info is None:
            rank_info = RankInfo.create_unranked()

        # Calculate initial rating based on rank
        initial_rating_score = self._calculate_initial_rating(rank_info)
        initial_rating = Rating.create_initial(initial_rating_score)

        # Create player profile
        player_profile = PlayerProfile.create(
            user_id=command.user_id,
            region_id=command.region_id,
            player_name=command.player_name,
            summoner_name=command.summoner_name,
            position=position,
            rank_info=rank_info,
            initial_rating=initial_rating,
        )

        # Set optional description
        if command.description:
            player_profile.update_profile(description=command.description)

        # Save player profile
        saved_profile = await self.player_profile_repository.save(player_profile)

        # Update region statistics
        region.update_statistics(
            total_players=region.total_players + 1,
            active_players=region.active_players + 1,
        )
        await self.region_repository.save(region)

        return PlayerRegistrationResult(
            profile_id=saved_profile.profile_id,
            player_name=saved_profile.player_name,
            summoner_name=saved_profile.summoner_name,
            position=saved_profile.position.value,
            current_rating=saved_profile.rating.current_score,
            region_id=saved_profile.region_id,
            created_at=saved_profile.created_at,
        )

    def _calculate_initial_rating(self, rank_info: RankInfo) -> float:
        """
        Calculate initial rating based on League of Legends rank.

        Args:
            rank_info: Player's rank information

        Returns:
            Initial rating score (ELO system, ~1200 base)
        """
        if not rank_info or rank_info.is_unranked:
            return 1200.0  # Default for unranked (standard ELO starting point)

        # Base ratings for each tier (ELO system)
        base_ratings = {
            RankTier.IRON: 600.0,
            RankTier.BRONZE: 800.0,
            RankTier.SILVER: 1000.0,
            RankTier.GOLD: 1200.0,
            RankTier.PLATINUM: 1450.0,
            RankTier.EMERALD: 1700.0,
            RankTier.DIAMOND: 1950.0,
            RankTier.MASTER: 2200.0,
            RankTier.GRANDMASTER: 2500.0,
            RankTier.CHALLENGER: 2800.0,
        }

        base_rating = base_ratings.get(rank_info.tier, 1200.0)

        # Adjust for division (higher divisions get bonus points)
        division_bonus = 0.0
        if rank_info.tier not in [
            RankTier.MASTER,
            RankTier.GRANDMASTER,
            RankTier.CHALLENGER,
        ]:
            # These tiers don't have divisions
            division_values = {
                RankDivision.IV: 0.0,
                RankDivision.III: 50.0,
                RankDivision.II: 100.0,
                RankDivision.TIER_I: 150.0,
            }
            division_bonus = division_values.get(rank_info.division, 0.0)

        # Adjust for LP (small bonus based on LP, max 50 points)
        lp_bonus = (
            min(rank_info.league_points * 0.5, 50.0) if rank_info.league_points else 0.0
        )

        # Calculate final rating
        final_rating = base_rating + division_bonus + lp_bonus
        return min(5000.0, max(0.0, final_rating))
