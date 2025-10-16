"""
Player-related Pydantic schemas for API requests and responses.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PositionEnum(str, Enum):
    """Player position enumeration."""

    TOP = "TOP"
    JUNGLE = "JUNGLE"
    MIDDLE = "MIDDLE"
    BOTTOM = "BOTTOM"
    UTILITY = "UTILITY"


class RankTierEnum(str, Enum):
    """League of Legends rank tier enumeration."""

    IRON = "IRON"
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"
    EMERALD = "EMERALD"
    DIAMOND = "DIAMOND"
    MASTER = "MASTER"
    GRANDMASTER = "GRANDMASTER"
    CHALLENGER = "CHALLENGER"


class RankDivisionEnum(str, Enum):
    """League of Legends rank division enumeration."""

    I = "I"
    II = "II"
    III = "III"
    IV = "IV"


class PlayerRegistrationRequest(BaseModel):
    """Request schema for player registration."""

    model_config = ConfigDict(str_strip_whitespace=True)

    region_id: int = Field(..., description="Region ID to register in")
    player_name: str = Field(
        ..., min_length=2, max_length=100, description="Player display name"
    )
    summoner_name: str = Field(
        ..., min_length=2, max_length=50, description="League of Legends summoner name"
    )
    position: PositionEnum = Field(..., description="Primary position")
    rank_tier: Optional[RankTierEnum] = Field(
        None, description="League of Legends rank tier"
    )
    rank_division: Optional[RankDivisionEnum] = Field(
        None, description="League of Legends rank division"
    )
    league_points: Optional[int] = Field(
        None, ge=0, le=10000, description="League points"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Player description"
    )


class PlayerProfileResponse(BaseModel):
    """Response schema for player profile."""

    model_config = ConfigDict(from_attributes=True)

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
    region_id: int
    created_at: datetime
    last_active: Optional[datetime]


class PlayerRegistrationResponse(BaseModel):
    """Response schema for player registration."""

    model_config = ConfigDict(from_attributes=True)

    profile_id: str
    player_name: str
    summoner_name: str
    position: str
    current_rating: float
    region_id: int
    created_at: datetime


class PlayerListResponse(BaseModel):
    """Response schema for player list."""

    players: List[PlayerProfileResponse]
    total: Optional[int] = None
    page: Optional[int] = None
    per_page: Optional[int] = None


class SummonerAvailabilityRequest(BaseModel):
    """Request schema for checking summoner name availability."""

    model_config = ConfigDict(str_strip_whitespace=True)

    summoner_name: str = Field(..., min_length=2, max_length=50)
    region_id: int = Field(..., description="Region ID to check in")
    exclude_profile_id: Optional[str] = Field(
        None, description="Profile ID to exclude from check"
    )


class SummonerAvailabilityResponse(BaseModel):
    """Response schema for summoner name availability check."""

    available: bool
    summoner_name: str
    region_id: int


class RegionSummaryResponse(BaseModel):
    """Response schema for region summary."""

    model_config = ConfigDict(from_attributes=True)

    region_id: int
    region_name: str
    status: str
    total_players: int
    active_players: int
    is_active: bool
    created_at: datetime


class RegionListResponse(BaseModel):
    """Response schema for region list."""

    regions: List[RegionSummaryResponse]
    total: Optional[int] = None
