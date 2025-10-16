"""
Region repository interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..aggregates.region import Region


class RegionRepository(ABC):
    """
    Repository interface for Region aggregate root.

    Defines the contract for Region data access operations.
    """

    @abstractmethod
    async def save(self, region: Region) -> Region:
        """
        Save or update a region.

        Args:
            region: Region to save

        Returns:
            Saved Region
        """
        pass

    @abstractmethod
    async def find_by_id(self, region_id: str) -> Optional[Region]:
        """
        Find region by ID.

        Args:
            region_id: Region ID to search for

        Returns:
            Region if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_code(self, region_code: str) -> Optional[Region]:
        """
        Find region by code.

        Args:
            region_code: Region code to search for

        Returns:
            Region if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_name(self, region_name: str) -> Optional[Region]:
        """
        Find region by name.

        Args:
            region_name: Region name to search for

        Returns:
            Region if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_all_active(self) -> List[Region]:
        """
        Find all active regions.

        Returns:
            List of active Regions
        """
        pass

    @abstractmethod
    async def find_all(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[Region]:
        """
        Find all regions.

        Args:
            limit: Optional limit for results
            offset: Optional offset for pagination

        Returns:
            List of Regions
        """
        pass

    @abstractmethod
    async def find_administered_by(self, admin_user_id: str) -> List[Region]:
        """
        Find regions administered by a user.

        Args:
            admin_user_id: Admin user ID

        Returns:
            List of Regions administered by the user
        """
        pass

    @abstractmethod
    async def exists_name(
        self, region_name: str, exclude_region_id: Optional[str] = None
    ) -> bool:
        """
        Check if region name exists.

        Args:
            region_name: Region name to check
            exclude_region_id: Optional region ID to exclude from check

        Returns:
            True if region name exists, False otherwise
        """
        pass

    @abstractmethod
    async def exists_code(
        self, region_code: str, exclude_region_id: Optional[str] = None
    ) -> bool:
        """
        Check if region code exists.

        Args:
            region_code: Region code to check
            exclude_region_id: Optional region ID to exclude from check

        Returns:
            True if region code exists, False otherwise
        """
        pass

    @abstractmethod
    async def count_all(self) -> int:
        """
        Count all regions.

        Returns:
            Total number of regions
        """
        pass

    @abstractmethod
    async def delete(self, region: Region) -> None:
        """
        Delete a region.

        Args:
            region: Region to delete
        """
        pass
