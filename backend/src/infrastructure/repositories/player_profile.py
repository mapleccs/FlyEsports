"""
PlayerProfile repository implementation using SQLAlchemy.
"""

from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.repositories.player_profile import PlayerProfileRepository
from src.domain.aggregates.player_profile import PlayerProfile
from src.domain.value_objects.rating import Rating
from src.domain.value_objects.rank_info import RankInfo, RankTier, RankDivision
from src.domain.value_objects.position import Position, PositionType
from src.domain.value_objects.contract_status import ContractStatus, ContractStatusType
from src.infrastructure.database.models.player_profile import (
    PlayerProfile as PlayerProfileModel,
)
from src.infrastructure.database.models.user import User as UserModel
from src.infrastructure.database.models.region import Region as RegionModel
from src.infrastructure.database.models.team import Team as TeamModel


class SQLAlchemyPlayerProfileRepository(PlayerProfileRepository):
    """
    SQLAlchemy implementation of PlayerProfileRepository.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.

        Args:
            session: Async database session
        """
        self.session = session

    def _extract_region_db_id(self, region_id) -> int:
        """
        Extract database ID from region_id.

        Args:
            region_id: Region ID (string format like 'region_1' or '1', or integer)

        Returns:
            Database ID as integer
        """
        try:
            # If it's already an integer, return it directly
            if isinstance(region_id, int):
                return region_id
            
            # If it's a string, parse it
            if isinstance(region_id, str):
                if region_id.startswith("region_"):
                    return int(region_id.split("_")[1])
                else:
                    return int(region_id)
            
            # Try to convert whatever it is to int
            return int(region_id)
        except (ValueError, IndexError, TypeError):
            raise ValueError(f"Invalid region_id format: {region_id}")

    def _model_to_domain(self, model: PlayerProfileModel) -> PlayerProfile:
        """
        Convert database model to domain aggregate.

        Args:
            model: PlayerProfile database model

        Returns:
            PlayerProfile domain aggregate
        """
        # Convert position using position_id mapping
        position_mapping = {
            1: PositionType.TOP,
            2: PositionType.JUNGLE, 
            3: PositionType.MIDDLE,
            4: PositionType.BOTTOM,
            5: PositionType.UTILITY
        }
        position_type = position_mapping.get(model.position_id, PositionType.TOP)
        position = Position(type=position_type)

        # Convert rating - read from database fields
        six_dimensions = {
            "kda": model.kda_dimension,
            "damage": model.damage_dimension,
            "economy": model.economy_dimension,
            "vision": model.vision_dimension,
            "objective": model.objective_dimension,
            "teamfight": model.teamfight_dimension,
        }

        rating = Rating(
            current_score=model.current_rating,
            locked_score=model.locked_rating,
            confidence_level=model.confidence_level,
            total_matches=model.total_matches,
            six_dimensions=six_dimensions
        )

        # Convert rank info
        rank_info = None
        if model.rank_tier and model.rank_division:
            try:
                tier = RankTier(model.rank_tier.upper())
                division = RankDivision(model.rank_division.upper())
                rank_info = RankInfo.create(
                    tier=tier, division=division, league_points=model.league_points or 0
                )
            except (ValueError, TypeError):
                # If rank data is invalid, set to None
                rank_info = None

        # Convert contract status using contract_status_id mapping
        if model.contract_status_id == 1:  # FREE
            contract_status = ContractStatus.create_free()
        elif model.contract_status_id == 2:  # LOCKED
            contract_status = ContractStatus.create_locked()
        else:  # PENDING (contract_status_id == 3)
            contract_status = ContractStatus.create_pending()

        # Create domain aggregate
        return PlayerProfile(
            profile_id=model.profile_id,
            user_id=str(model.user_id),
            region_id=f"region_{model.region_id}",  # Convert to domain format for consistency
            player_name=model.player_name,
            summoner_name=model.summoner_name,
            position=position,
            description=model.description,
            rank_info=rank_info,
            rating=rating,
            contract_status=contract_status,
            current_team_id=str(model.current_team_id)
            if model.current_team_id
            else None,
            contract_start=model.contract_start,
            locked_rating=model.locked_rating,
            total_matches=model.total_matches,
            total_wins=model.total_wins,
            total_losses=model.total_losses,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_active=model.last_active,
        )

    def _domain_to_model(
        self, domain: PlayerProfile, model: Optional[PlayerProfileModel] = None
    ) -> PlayerProfileModel:
        """
        Convert domain aggregate to database model.

        Args:
            domain: PlayerProfile domain aggregate
            model: Optional existing model to update

        Returns:
            PlayerProfile database model
        """
        if model is None:
            model = PlayerProfileModel()

        # Basic fields
        model.profile_id = domain.profile_id
        model.user_id = int(domain.user_id)
        model.region_id = self._extract_region_db_id(domain.region_id)
        model.player_name = domain.player_name
        model.summoner_name = domain.summoner_name
        # Set position_id based on domain position value
        # For now, use hardcoded mapping - this should be improved with actual DB lookup
        position_mapping = {
            'TOP': 1, 'JUNGLE': 2, 'MIDDLE': 3, 'BOTTOM': 4, 'UTILITY': 5
        }
        model.position_id = position_mapping.get(domain.position.value, 1)
        model.description = domain.description

        # Rank info
        if domain.rank_info:
            model.rank_tier = domain.rank_info.tier.value
            model.rank_division = domain.rank_info.division.value
            model.league_points = domain.rank_info.league_points
        else:
            model.rank_tier = None
            model.rank_division = None
            model.league_points = None

        # Rating
        if domain.rating:
            model.current_rating = domain.rating.current_score
            model.peak_rating = max(model.peak_rating if hasattr(model, 'peak_rating') and model.peak_rating else 1200.0, domain.rating.current_score)
            model.locked_rating = domain.rating.locked_score
            model.confidence_level = domain.rating.confidence_level
            model.rating_updated_at = domain.updated_at

            # Save six dimensions
            model.kda_dimension = domain.rating.six_dimensions.get("kda", 50.0)
            model.damage_dimension = domain.rating.six_dimensions.get("damage", 50.0)
            model.economy_dimension = domain.rating.six_dimensions.get("economy", 50.0)
            model.vision_dimension = domain.rating.six_dimensions.get("vision", 50.0)
            model.objective_dimension = domain.rating.six_dimensions.get("objective", 50.0)
            model.teamfight_dimension = domain.rating.six_dimensions.get("teamfight", 50.0)

        # Set contract_status_id based on domain contract status
        # For now, use hardcoded mapping - this should be improved with actual DB lookup
        if domain.contract_status.is_available_for_signing:
            model.contract_status_id = 1  # FREE
        elif domain.contract_status.is_locked:
            model.contract_status_id = 2  # LOCKED
        else:
            model.contract_status_id = 3  # PENDING

        model.current_team_id = (
            int(domain.current_team_id) if domain.current_team_id else None
        )
        model.contract_start = domain.contract_start

        # Statistics
        model.total_matches = domain.total_matches
        model.total_wins = domain.total_wins
        model.total_losses = domain.total_losses

        # Timestamps
        model.created_at = domain.created_at
        model.updated_at = domain.updated_at
        model.last_active = domain.last_active

        return model

    async def save(self, player_profile: PlayerProfile) -> PlayerProfile:
        """Save or update a player profile."""
        # Find existing model if updating
        existing_query = select(PlayerProfileModel).where(
            PlayerProfileModel.profile_id == player_profile.profile_id
        )
        result = await self.session.execute(existing_query)
        existing_model = result.scalar_one_or_none()

        # Convert to model
        model = self._domain_to_model(player_profile, existing_model)

        if existing_model is None:
            self.session.add(model)

        await self.session.commit()

        # For newly created profiles, return the original domain object
        # since we have all the data we need
        if existing_model is None:
            return player_profile
        else:
            # For updates, we can return the converted model
            return self._model_to_domain(model)

    async def find_by_id(self, profile_id: str) -> Optional[PlayerProfile]:
        """Find player profile by ID."""
        query = select(PlayerProfileModel).where(
            PlayerProfileModel.profile_id == profile_id
        )
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        return self._model_to_domain(model) if model else None

    async def find_by_user_id(self, user_id: str) -> List[PlayerProfile]:
        """Find all player profiles for a user."""
        query = (
            select(PlayerProfileModel)
            .where(PlayerProfileModel.user_id == int(user_id))
            .order_by(PlayerProfileModel.created_at.desc())
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_by_user_and_region(
        self, user_id: str, region_id: str
    ) -> Optional[PlayerProfile]:
        """Find player profile by user and region."""
        query = select(PlayerProfileModel).where(
            and_(
                PlayerProfileModel.user_id == int(user_id),
                PlayerProfileModel.region_id == self._extract_region_db_id(region_id),
            )
        )
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        return self._model_to_domain(model) if model else None

    async def find_by_summoner_name(
        self, summoner_name: str, region_id: str
    ) -> Optional[PlayerProfile]:
        """Find player profile by summoner name within a region."""
        query = select(PlayerProfileModel).where(
            and_(
                PlayerProfileModel.summoner_name.ilike(summoner_name),
                PlayerProfileModel.region_id == self._extract_region_db_id(region_id),
            )
        )
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        return self._model_to_domain(model) if model else None

    async def find_by_region(
        self, region_id: str, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[PlayerProfile]:
        """Find player profiles by region."""
        query = (
            select(PlayerProfileModel)
            .where(
                PlayerProfileModel.region_id == self._extract_region_db_id(region_id)
            )
            .order_by(PlayerProfileModel.current_rating.desc())
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_all(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[PlayerProfile]:
        """Find all player profiles with optional pagination."""
        query = select(PlayerProfileModel).order_by(
            PlayerProfileModel.current_rating.desc()
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_free_players(
        self, region_id: str, position: Optional[str] = None
    ) -> List[PlayerProfile]:
        """Find free (uncontracted) players in a region."""
        conditions = [
            PlayerProfileModel.region_id == self._extract_region_db_id(region_id),
            PlayerProfileModel.contract_status.has(code='FREE'),
        ]

        if position:
            conditions.append(
                PlayerProfileModel.position.has(code=position.upper())
            )

        query = (
            select(PlayerProfileModel)
            .where(and_(*conditions))
            .order_by(PlayerProfileModel.current_rating.desc())
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_by_team(self, team_id: str) -> List[PlayerProfile]:
        """Find player profiles by team."""
        query = (
            select(PlayerProfileModel)
            .where(PlayerProfileModel.current_team_id == int(team_id))
            .order_by(PlayerProfileModel.position)
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def count_by_region(self, region_id: str) -> int:
        """Count player profiles in a region."""
        query = select(func.count(PlayerProfileModel.id)).where(
            PlayerProfileModel.region_id == int(region_id)
        )
        result = await self.session.execute(query)
        return result.scalar()

    async def exists_summoner_in_region(
        self,
        summoner_name: str,
        region_id: str,
        exclude_profile_id: Optional[str] = None,
    ) -> bool:
        """Check if summoner name exists in region."""
        conditions = [
            PlayerProfileModel.summoner_name.ilike(summoner_name),
            PlayerProfileModel.region_id == self._extract_region_db_id(region_id),
        ]

        if exclude_profile_id:
            conditions.append(PlayerProfileModel.profile_id != exclude_profile_id)

        query = select(func.count(PlayerProfileModel.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        count = result.scalar()

        return count > 0

    async def delete(self, player_profile: PlayerProfile) -> None:
        """Delete a player profile."""
        query = select(PlayerProfileModel).where(
            PlayerProfileModel.profile_id == player_profile.profile_id
        )
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            await self.session.delete(model)
            await self.session.commit()
