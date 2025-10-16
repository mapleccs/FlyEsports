"""
Regions API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import structlog

from src.presentation.schemas.player import RegionSummaryResponse, RegionListResponse
from src.application.services.player_service import PlayerService
from src.presentation.dependencies.player import get_player_service
from src.presentation.dependencies.permission import verify_permission
from src.domain.value_objects.role import PermissionAction, PermissionResource


router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/health")
async def regions_health():
    """Regions service health check"""
    return {"status": "Regions service is healthy"}


@router.get("/public", response_model=RegionListResponse)
async def get_regions_public(active_only: bool = False):
    """
    Get all regions - public endpoint for registration.

    This endpoint provides access to regions without authentication,
    specifically for use during player registration and public viewing.

    Args:
        active_only: If True, only returns active regions
    """
    try:
        from src.infrastructure.database.connection import database_manager
        from src.infrastructure.repositories.region import SQLAlchemyRegionRepository
        
        async with database_manager.get_session() as session:
            region_repository = SQLAlchemyRegionRepository(session)
            
            if active_only:
                regions = await region_repository.find_all_active()
            else:
                regions = await region_repository.find_all()

            return RegionListResponse(
                regions=[
                    RegionSummaryResponse(
                        region_id=region.region_id,
                        region_name=region.region_name,
                        status=region.status,
                        total_players=region.total_players,
                        active_players=region.active_players,
                        is_active=region.is_active,
                        created_at=region.created_at,
                    )
                    for region in regions
                ],
                total=len(regions),
            )

    except Exception as e:
        logger.error(
            "Failed to get regions (public)",
            active_only=active_only,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取赛区列表失败，请稍后重试"
        )


@router.get("/", response_model=RegionListResponse)
@router.get("", response_model=RegionListResponse)  # 支持不带斜杠的路径
async def get_regions(
    active_only: bool = False,
    player_service: PlayerService = Depends(get_player_service),
    _: None = Depends(
        verify_permission(PermissionResource.REGION, PermissionAction.READ)
    ),
):
    """
    Get all regions.

    Returns a list of all regions in the system. Can be filtered to show only active regions.

    Args:
        active_only: If True, only returns active regions
    """
    try:
        if active_only:
            regions = await player_service.get_active_regions()
        else:
            regions = await player_service.get_all_regions()

        return RegionListResponse(
            regions=[
                RegionSummaryResponse(
                    region_id=region.region_id,
                    region_name=region.region_name,
                    status=region.status,
                    total_players=region.total_players,
                    active_players=region.active_players,
                    is_active=region.is_active,
                    created_at=region.created_at,
                )
                for region in regions
            ],
            total=len(regions),
        )

    except Exception as e:
        logger.error(
            "Failed to get regions",
            active_only=active_only,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取赛区列表失败，请稍后重试"
        )


@router.get("/{region_id}", response_model=RegionSummaryResponse)
async def get_region(
    region_id: str,
    player_service: PlayerService = Depends(get_player_service),
    _: None = Depends(
        verify_permission(PermissionResource.REGION, PermissionAction.READ)
    ),
):
    """
    Get a specific region by ID.

    Returns detailed information about a region.
    """
    try:
        region = await player_service.get_region_by_id(region_id)

        if not region:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="赛区未找到")

        return RegionSummaryResponse(
            region_id=region.region_id,
            region_name=region.region_name,
            status=region.status,
            total_players=region.total_players,
            active_players=region.active_players,
            is_active=region.is_active,
            created_at=region.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get region",
            region_id=region_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取赛区信息失败，请稍后重试"
        )
