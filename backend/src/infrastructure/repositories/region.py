"""
Region repository implementation using SQLAlchemy.
"""

from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.repositories.region import RegionRepository
from src.domain.aggregates.region import Region
from src.domain.value_objects.rating_config import RatingConfig
from src.infrastructure.database.models.region import Region as RegionModel


class SQLAlchemyRegionRepository(RegionRepository):
    """
    SQLAlchemy implementation of RegionRepository.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.

        Args:
            session: Async database session
        """
        self.session = session

    def _model_to_domain(self, model: RegionModel) -> Region:
        """
        Convert database model to domain aggregate.

        Args:
            model: Region database model

        Returns:
            Region domain aggregate
        """
        # Create rating config (using defaults for now)
        rating_config = RatingConfig.create_default()

        return Region(
            region_id=f"region_{model.id}",  # Convert DB ID to domain format
            region_name=model.name,
            region_code=model.name.upper()[:10],  # Use region name as code for now
            status="active" if model.is_active else "inactive",
            rating_config=rating_config,
            transfer_windows=[],  # Empty for now
            total_players=0,  # Will be calculated separately
            active_players=0,  # Will be calculated separately
            total_teams=0,  # Will be calculated separately
            active_teams=0,  # Will be calculated separately
            current_season="",  # Empty for now
            season_start=None,
            season_end=None,
            admin_users=[str(model.admin_user_id)],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _domain_to_model(
        self, domain: Region, model: Optional[RegionModel] = None
    ) -> RegionModel:
        """
        Convert domain aggregate to database model.

        Args:
            domain: Region domain aggregate
            model: Optional existing model to update

        Returns:
            Region database model
        """
        if model is None:
            model = RegionModel()

        model.name = domain.region_name
        model.description = None  # For now
        model.admin_user_id = int(domain.admin_users[0]) if domain.admin_users else 1
        model.is_active = domain.status == "active"
        model.max_teams_per_season = 32  # Default
        model.allow_public_registration = True  # Default
        model.created_at = domain.created_at
        model.updated_at = domain.updated_at

        return model

    async def save(self, region: Region) -> Region:
        """Save or update a region."""
        # Extract numeric ID from region_id if it exists
        existing_model = None
        if region.region_id.startswith("region_"):
            try:
                region_db_id = int(region.region_id.split("_")[1])
                query = select(RegionModel).where(RegionModel.id == region_db_id)
                result = await self.session.execute(query)
                existing_model = result.scalar_one_or_none()
            except (ValueError, IndexError):
                pass

        # Convert to model
        model = self._domain_to_model(region, existing_model)

        if existing_model is None:
            self.session.add(model)

        await self.session.commit()
        await self.session.refresh(model)

        return self._model_to_domain(model)

    async def find_by_id(self, region_id: str) -> Optional[Region]:
        """Find region by ID."""
        try:
            if region_id.startswith("region_"):
                region_db_id = int(region_id.split("_")[1])
            else:
                region_db_id = int(region_id)

            query = select(RegionModel).where(RegionModel.id == region_db_id)
            result = await self.session.execute(query)
            model = result.scalar_one_or_none()

            return self._model_to_domain(model) if model else None
        except (ValueError, IndexError):
            # If parsing fails, try to find by name as fallback
            try:
                query = select(RegionModel).where(RegionModel.name == region_id)
                result = await self.session.execute(query)
                model = result.scalar_one_or_none()
                return self._model_to_domain(model) if model else None
            except:
                return None

    async def find_by_code(self, region_code: str) -> Optional[Region]:
        """Find region by code."""
        # Since the current model doesn't have a code field,
        # we'll use the name field for now
        return await self.find_by_name(region_code)

    async def find_by_name(self, region_name: str) -> Optional[Region]:
        """Find region by name."""
        query = select(RegionModel).where(RegionModel.name.ilike(region_name))
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        return self._model_to_domain(model) if model else None

    async def find_all_active(self) -> List[Region]:
        """Find all active regions."""
        query = (
            select(RegionModel)
            .where(RegionModel.is_active == True)
            .order_by(RegionModel.name)
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_all(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[Region]:
        """Find all regions."""
        query = select(RegionModel).order_by(RegionModel.name)

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_administered_by(self, admin_user_id: str) -> List[Region]:
        """Find regions administered by a user."""
        query = (
            select(RegionModel)
            .where(RegionModel.admin_user_id == int(admin_user_id))
            .order_by(RegionModel.name)
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def exists_name(
        self, region_name: str, exclude_region_id: Optional[str] = None
    ) -> bool:
        """Check if region name exists."""
        conditions = [RegionModel.name.ilike(region_name)]

        if exclude_region_id:
            try:
                if exclude_region_id.startswith("region_"):
                    exclude_db_id = int(exclude_region_id.split("_")[1])
                else:
                    exclude_db_id = int(exclude_region_id)
                conditions.append(RegionModel.id != exclude_db_id)
            except (ValueError, IndexError):
                pass

        query = select(func.count(RegionModel.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        count = result.scalar()

        return count > 0

    async def exists_code(
        self, region_code: str, exclude_region_id: Optional[str] = None
    ) -> bool:
        """Check if region code exists."""
        # Since we don't have a code field, use name for now
        return await self.exists_name(region_code, exclude_region_id)

    async def count_all(self) -> int:
        """Count all regions."""
        query = select(func.count(RegionModel.id))
        result = await self.session.execute(query)
        return result.scalar()

    async def delete(self, region: Region) -> None:
        """Delete a region."""
        try:
            if region.region_id.startswith("region_"):
                region_db_id = int(region.region_id.split("_")[1])
            else:
                region_db_id = int(region.region_id)

            query = select(RegionModel).where(RegionModel.id == region_db_id)
            result = await self.session.execute(query)
            model = result.scalar_one_or_none()

            if model:
                await self.session.delete(model)
                await self.session.commit()
        except (ValueError, IndexError):
            pass
