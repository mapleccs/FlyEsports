"""
Players API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
import structlog

from src.presentation.schemas.player import (
    PlayerRegistrationRequest,
    PlayerRegistrationResponse,
    PlayerProfileResponse,
    PlayerListResponse,
    SummonerAvailabilityRequest,
    SummonerAvailabilityResponse,
)


def _extract_region_id(region_id_str: str) -> int:
    """
    Extract numeric region ID from string format.
    
    Args:
        region_id_str: Region ID in format 'region_1' or '1'
        
    Returns:
        Numeric region ID
    """
    try:
        if isinstance(region_id_str, int):
            return region_id_str
        if isinstance(region_id_str, str):
            if region_id_str.startswith("region_"):
                return int(region_id_str.split("_")[1])
            else:
                return int(region_id_str)
        return int(region_id_str)
    except (ValueError, IndexError, TypeError):
        return 1  # Default fallback
from src.presentation.schemas.auth import MessageResponse, ErrorResponse
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.permission import (
    RequirePlayerRead,
    verify_permission,
)
from src.domain.value_objects.role import PermissionAction, PermissionResource
from src.application.services.player_service import PlayerService
from src.domain.entities.user import User
from src.domain.base import BusinessRuleViolationError
from src.presentation.dependencies.player import get_player_service


router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post(
    "/register",
    response_model=PlayerRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_player(
    request: PlayerRegistrationRequest,
    current_user: User = Depends(get_current_active_user),
    player_service: PlayerService = Depends(get_player_service),
    _: None = Depends(
        verify_permission(PermissionResource.PLAYER, PermissionAction.CREATE)
    ),
):
    """
    Register current user as a player in a region.

    Creates a new player profile for the authenticated user in the specified region.
    """
    try:
        logger.info(
            "Player registration attempt",
            user_id=str(current_user.id),
            region_id=str(request.region_id),
            player_name=request.player_name,
            summoner_name=request.summoner_name,
            position=request.position.value,
        )

        result = await player_service.register_player_to_region(
            user_id=str(current_user.id),
            region_id=str(request.region_id),
            player_name=request.player_name,
            summoner_name=request.summoner_name,
            position=request.position.value,
            rank_tier=request.rank_tier.value if request.rank_tier else None,
            rank_division=request.rank_division.value
            if request.rank_division
            else None,
            league_points=request.league_points,
            description=request.description,
        )

        logger.info(
            "Player registration successful",
            user_id=str(current_user.id),
            profile_id=result.profile_id,
            player_name=result.player_name,
        )

        return PlayerRegistrationResponse(
            profile_id=result.profile_id,
            player_name=result.player_name,
            summoner_name=result.summoner_name,
            position=result.position,
            current_rating=result.current_rating,
            region_id=result.region_id,
            created_at=result.created_at,
        )

    except BusinessRuleViolationError as e:
        logger.warning(
            "Player registration failed due to business rule violation",
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        import traceback
        full_traceback = traceback.format_exc()
        print(f"FULL ERROR: {str(e)}")
        print(f"FULL TRACEBACK: {full_traceback}")
        logger.error(
            "Player registration failed with unexpected error",
            user_id=str(current_user.id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="选手注册失败，请稍后重试"
        )


@router.get("/me", response_model=List[PlayerProfileResponse])
async def get_my_player_profiles(
    current_user: User = Depends(get_current_active_user),
    player_service: PlayerService = Depends(get_player_service),
):
    """
    Get all player profiles for the current user.

    Returns a list of all player profiles associated with the authenticated user.
    """
    try:
        profiles = await player_service.get_user_profiles(current_user.id)

        return [
            PlayerProfileResponse(
                profile_id=profile.profile_id,
                player_name=profile.player_name,
                summoner_name=profile.summoner_name,
                position=profile.position,
                current_rating=profile.current_rating,
                effective_rating=profile.effective_rating,
                rank_display=profile.rank_display,
                contract_status=profile.contract_status,
                current_team_id=profile.current_team_id,
                total_matches=profile.total_matches,
                win_rate=profile.win_rate,
                region_id=_extract_region_id(profile.region_id),
                created_at=profile.created_at,
                last_active=profile.last_active,
            )
            for profile in profiles
        ]

    except Exception as e:
        logger.error(
            "Failed to get user player profiles",
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取选手档案失败，请稍后重试"
        )


@router.get("/{profile_id}", response_model=PlayerProfileResponse)
async def get_player_profile(
    profile_id: str,
    player_service: PlayerService = Depends(get_player_service),
    _: None = Depends(RequirePlayerRead),
):
    """
    Get a specific player profile by ID.

    Returns detailed information about a player profile.
    """
    try:
        profile = await player_service.get_player_profile(profile_id)

        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="选手档案未找到")

        return PlayerProfileResponse(
            profile_id=profile.profile_id,
            player_name=profile.player_name,
            summoner_name=profile.summoner_name,
            position=profile.position,
            current_rating=profile.current_rating,
            effective_rating=profile.effective_rating,
            rank_display=profile.rank_display,
            contract_status=profile.contract_status,
            current_team_id=profile.current_team_id,
            total_matches=profile.total_matches,
            win_rate=profile.win_rate,
            region_id=profile.region_id,
            created_at=profile.created_at,
            last_active=profile.last_active,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get player profile",
            profile_id=profile_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取选手档案失败，请稍后重试"
        )


@router.get("/region/{region_id}", response_model=PlayerListResponse)
async def get_region_players(
    region_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    position: Optional[str] = Query(None, description="Filter by position"),
    free_only: bool = Query(False, description="Show only free players"),
    player_service: PlayerService = Depends(get_player_service),
):
    """
    Get players in a specific region.

    Returns a paginated list of players in the specified region.
    """
    try:
        offset = (page - 1) * per_page

        if free_only:
            profiles = await player_service.get_free_players(region_id, position)
            # For free players, we don't implement pagination yet, so slice the results
            paginated_profiles = profiles[offset : offset + per_page]
            total = len(profiles)
        else:
            profiles = await player_service.get_region_players(
                region_id=region_id, limit=per_page, offset=offset
            )
            paginated_profiles = profiles
            # TODO: Implement total count for non-free players
            total = None

        return PlayerListResponse(
            players=[
                PlayerProfileResponse(
                    profile_id=profile.profile_id,
                    player_name=profile.player_name,
                    summoner_name=profile.summoner_name,
                    position=profile.position,
                    current_rating=profile.current_rating,
                    effective_rating=profile.effective_rating,
                    rank_display=profile.rank_display,
                    contract_status=profile.contract_status,
                    current_team_id=profile.current_team_id,
                    total_matches=profile.total_matches,
                    win_rate=profile.win_rate,
                    region_id=_extract_region_id(profile.region_id),
                    created_at=profile.created_at,
                    last_active=profile.last_active,
                )
                for profile in paginated_profiles
            ],
            total=total,
            page=page,
            per_page=per_page,
        )

    except Exception as e:
        logger.error(
            "Failed to get region players",
            region_id=region_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取赛区选手列表失败，请稍后重试"
        )


@router.post("/check-summoner", response_model=SummonerAvailabilityResponse)
async def check_summoner_availability(
    request: SummonerAvailabilityRequest,
    player_service: PlayerService = Depends(get_player_service),
):
    """
    Check if a summoner name is available in a region.

    Returns whether the summoner name is available for registration.
    """
    try:
        available = await player_service.check_summoner_availability(
            summoner_name=request.summoner_name,
            region_id=str(request.region_id),
            exclude_profile_id=request.exclude_profile_id,
        )

        return SummonerAvailabilityResponse(
            available=available,
            summoner_name=request.summoner_name,
            region_id=str(request.region_id),
        )

    except Exception as e:
        logger.error(
            "Failed to check summoner availability",
            summoner_name=request.summoner_name,
            region_id=str(request.region_id),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="检查召唤师名称可用性失败，请稍后重试",
        )
