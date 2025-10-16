"""
PlayerProfile repository interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..aggregates.player_profile import PlayerProfile


class PlayerProfileRepository(ABC):
    """
    Repository interface for PlayerProfile aggregate root.

    Defines the contract for PlayerProfile data access operations.
    """

    @abstractmethod
    async def save(self, player_profile: PlayerProfile) -> PlayerProfile:
        """
        Save or update a player profile.

        Args:
            player_profile: PlayerProfile to save

        Returns:
            Saved PlayerProfile
        """
        pass

    @abstractmethod
    async def find_by_id(self, profile_id: str) -> Optional[PlayerProfile]:
        """
        Find player profile by ID.

        Args:
            profile_id: Profile ID to search for

        Returns:
            PlayerProfile if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_user_id(self, user_id: str) -> List[PlayerProfile]:
        """
        Find all player profiles for a user.

        Args:
            user_id: User ID to search for

        Returns:
            List of PlayerProfiles for the user
        """
        pass

    @abstractmethod
    async def find_by_user_and_region(
        self, user_id: str, region_id: str
    ) -> Optional[PlayerProfile]:
        """
        Find player profile by user and region.

        Args:
            user_id: User ID
            region_id: Region ID

        Returns:
            PlayerProfile if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_summoner_name(
        self, summoner_name: str, region_id: str
    ) -> Optional[PlayerProfile]:
        """
        Find player profile by summoner name within a region.

        Args:
            summoner_name: Summoner name to search for
            region_id: Region ID to search within

        Returns:
            PlayerProfile if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_region(
        self, region_id: str, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[PlayerProfile]:
        """
        Find player profiles by region.

        Args:
            region_id: Region ID to search for
            limit: Optional limit for results
            offset: Optional offset for pagination

        Returns:
            List of PlayerProfiles in the region
        """
        pass

    @abstractmethod
    async def find_free_players(
        self, region_id: str, position: Optional[str] = None
    ) -> List[PlayerProfile]:
        """
        Find free (uncontracted) players in a region.

        Args:
            region_id: Region ID to search for
            position: Optional position filter

        Returns:
            List of free PlayerProfiles
        """
        pass

    @abstractmethod
    async def find_by_team(self, team_id: str) -> List[PlayerProfile]:
        """
        Find player profiles by team.

        Args:
            team_id: Team ID to search for

        Returns:
            List of PlayerProfiles in the team
        """
        pass

    @abstractmethod
    async def count_by_region(self, region_id: str) -> int:
        """
        Count player profiles in a region.

        Args:
            region_id: Region ID to count for

        Returns:
            Number of player profiles in the region
        """
        pass

    @abstractmethod
    async def exists_summoner_in_region(
        self,
        summoner_name: str,
        region_id: str,
        exclude_profile_id: Optional[str] = None,
    ) -> bool:
        """
        Check if summoner name exists in region.

        Args:
            summoner_name: Summoner name to check
            region_id: Region ID to check within
            exclude_profile_id: Optional profile ID to exclude from check

        Returns:
            True if summoner name exists, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, player_profile: PlayerProfile) -> None:
        """
        Delete a player profile.

        Args:
            player_profile: PlayerProfile to delete
        """
        pass
