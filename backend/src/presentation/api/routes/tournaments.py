"""赛事API路由"""

from typing import Dict, List, Optional
from uuid import UUID
import structlog

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from fastapi.security import HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
import random

from src.application.services.tournament_service import TournamentService
from src.domain.value_objects.tournament import (
    RegistrationSummary,
    TournamentType,
)
from src.presentation.dependencies.auth import get_current_user, get_optional_current_user
from src.domain.entities.user import User
from src.presentation.dependencies.tournament import get_tournament_service
from src.presentation.dependencies.permission import (
    verify_permission,
    get_permission_checker,
    PermissionChecker,
    RequireRegionAdmin,
)
from src.domain.value_objects.role import PermissionAction, PermissionResource
from src.presentation.schemas.tournament import (
    CheckInRequest,
    CheckInResponse,
    MatchCreate,
    MatchListResponse,
    MatchResponse,
    MatchUpdate,
    RegistrationCreate,
    RegistrationListResponse,
    RegistrationResponse,
    TeamInfo,
    PlayerInfo,
    TournamentCreate,
    TournamentListResponse,
    TournamentResponse,
    TournamentUpdate,
    TournamentStatusUpdate,
)
from src.infrastructure.database.models.tournament import TournamentRegistration
from src.infrastructure.database.models.team import Team
from src.infrastructure.database.models.player_profile import PlayerProfile
from src.infrastructure.database.models.region import Region
from src.infrastructure.database.connection import database_manager
from src.infrastructure.websocket.connection_manager import websocket_manager

router = APIRouter()
security = HTTPBearer()
logger = structlog.get_logger(__name__)


@router.get("/health")
async def tournaments_health():
    """健康检查"""
    return {"status": "Tournaments service is healthy"}


@router.post(
    "/",
    response_model=TournamentResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="创建赛事",
    description="赛区管理员创建新赛事",
)
async def create_tournament(
    tournament_data: TournamentCreate,
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """创建赛事"""
    # 检查权限：需要赛区管理员或更高级别的权限
    await checker.require_permission(
        PermissionResource.TOURNAMENT,
        PermissionAction.CREATE,
        region_id=tournament_data.region_id
    )

    try:
        tournament = await tournament_service.create_tournament(
            region_id=tournament_data.region_id,
            name=tournament_data.name,
            tournament_type=tournament_data.tournament_type,
            format=tournament_data.format,
            max_participants=tournament_data.max_participants,
            registration_start=tournament_data.registration_start,
            registration_end=tournament_data.registration_end,
            tournament_start=tournament_data.tournament_start,
            tournament_end=tournament_data.tournament_end,
            created_by=current_user.id,
            description=tournament_data.description,
            logo_url=tournament_data.logo_url,
            banner_url=tournament_data.banner_url,
            min_rank=tournament_data.min_rank,
            max_rank=tournament_data.max_rank,
            team_size=tournament_data.team_size,
        )

        registration_entries = list(tournament.registrations.values())
        registration_count = len(registration_entries)
        confirmed_count = sum(
            1 for reg in registration_entries
            if getattr(reg, 'status', None) == 'confirmed'
        )
        team_registration_count = sum(
            1 for reg in registration_entries
            if getattr(reg, 'participant_type', None) == 'team'
        )
        player_registration_count = sum(
            1 for reg in registration_entries
            if getattr(reg, 'participant_type', None) == 'player'
        )

        return TournamentResponse(
            id=tournament.id,
            region_id=tournament.region_id,
            name=tournament.name,
            tournament_type=tournament.tournament_type,
            status=tournament.status,
            format=tournament.rules.format,
            max_participants=tournament.rules.max_participants,
            min_rank=tournament.rules.min_rank,
            max_rank=tournament.rules.max_rank,
            team_size=tournament.rules.team_size,
            registration_start=tournament.schedule.registration_start,
            registration_end=tournament.schedule.registration_end,
            tournament_start=tournament.schedule.tournament_start,
            tournament_end=tournament.schedule.tournament_end,
            description=tournament.description,
            logo_url=tournament.logo_url,
            banner_url=tournament.banner_url,
            created_by=tournament.created_by,
            created_at=tournament.created_at,
            updated_at=tournament.updated_at,
            registration_count=registration_count,
            confirmed_count=confirmed_count,
            team_registration_count=team_registration_count,
            player_registration_count=player_registration_count,
        )
    except ValueError as e:
        logger.warning(
            "Tournament creation validation failed",
            user_id=current_user.id,
            region_id=tournament_data.region_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Tournament creation failed unexpectedly",
            user_id=current_user.id,
            region_id=tournament_data.region_id,
            tournament_name=tournament_data.name,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建赛事失败: {str(e)}"
        )


@router.get(
    "/",
    response_model=TournamentListResponse,
    summary="获取赛事列表",
    description="获取赛事列表，支持筛选和分页",
)
async def get_tournaments(
    region_id: Optional[int] = Query(None, description="赛区ID"),
    status: Optional[str] = Query(None, description="赛事状态"),
    tournament_type: Optional[str] = Query(None, description="赛事类型"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    tournament_service: TournamentService = Depends(get_tournament_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """获取赛事列表"""
    try:
        offset = (page - 1) * size

        # 将字符串参数转换为枚举
        status_enum = None
        tournament_type_enum = None

        if status:
            try:
                status_enum = str(status)
            except ValueError:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的赛事状态: {status}"
                )

        if tournament_type:
            try:
                tournament_type_enum = TournamentType(tournament_type)
            except ValueError:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的赛事类型: {tournament_type}"
                )

        tournaments = await tournament_service.get_region_tournaments(
            region_id=region_id,
            status=status_enum,
            tournament_type=tournament_type_enum,
            limit=size,
            offset=offset,
        )

        stats_map: Dict[str, RegistrationSummary] = {}
        if tournaments:
            raw_stats = await tournament_service.get_registration_stats(
                [UUID(str(tournament.id)) for tournament in tournaments]
            )
            stats_map = {str(tid): summary for tid, summary in raw_stats.items()}


        # 转换为响应格式
        tournament_responses = []
        for tournament in tournaments:
            # 检查当前用户是否已报名
            user_registered = False
            user_registration_status = None
            stats = stats_map.get(str(tournament.id))
            if not stats:
                stats = RegistrationSummary(total=0, confirmed=0, team=0, player=0)


            if current_user is not None:
                # 检查用户是否已报名此赛事
                # 使用简单的数据库查询获取用户报名状态
                from src.infrastructure.database.connection import database_manager
                from sqlalchemy import select
                from src.infrastructure.database.models.tournament import TournamentRegistration
                from src.infrastructure.database.models.player_profile import PlayerProfile

                async with database_manager.get_session() as session:
                    # 查找用户的PlayerProfile（如果有重复记录，取最新的）
                    player_profile_query = select(PlayerProfile).where(
                        PlayerProfile.user_id == current_user.id
                    ).order_by(PlayerProfile.created_at.desc()).limit(1)
                    player_profile_result = await session.execute(player_profile_query)
                    player_profile = player_profile_result.scalar_one_or_none()

                    if player_profile:
                        # 查找用户在此赛事的报名记录
                        registration_query = select(TournamentRegistration).where(
                            TournamentRegistration.tournament_id == tournament.id,
                            TournamentRegistration.participant_id == player_profile.profile_id
                        )
                        registration_result = await session.execute(registration_query)
                        registration = registration_result.scalar_one_or_none()

                        if registration:
                            user_registered = True
                            # 根据status_id获取状态名称
                            status_mapping = {1: 'pending', 2: 'confirmed', 3: 'rejected', 4: 'withdrawn'}
                            user_registration_status = status_mapping.get(registration.status_id, 'unknown')

            tournament_responses.append(TournamentResponse(
                id=tournament.id,
                region_id=tournament.region_id,
                name=tournament.name,
                tournament_type=tournament.tournament_type,
                status=tournament.status,
                format=tournament.rules.format,
                max_participants=tournament.rules.max_participants,
                min_rank=tournament.rules.min_rank,
                max_rank=tournament.rules.max_rank,
                team_size=tournament.rules.team_size,
                registration_start=tournament.schedule.registration_start,
                registration_end=tournament.schedule.registration_end,
                tournament_start=tournament.schedule.tournament_start,
                tournament_end=tournament.schedule.tournament_end,
                description=tournament.description,
                logo_url=tournament.logo_url,
                banner_url=tournament.banner_url,
                created_by=tournament.created_by,
                created_at=tournament.created_at,
                updated_at=tournament.updated_at,
                registration_count=stats.total,
                confirmed_count=stats.confirmed,
                team_registration_count=stats.team,
                player_registration_count=stats.player,
                user_registered=user_registered,
                user_registration_status=user_registration_status,
            ))

        return TournamentListResponse(
            tournaments=tournament_responses,
            total=len(tournament_responses),
            page=page,
            size=size,
            has_next=len(tournament_responses) == size,
        )
    except ValueError as e:
        logger.warning(
            "Invalid parameters for tournament list",
            error=str(e)
        )
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to get tournament list",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取赛事列表失败: {str(e)}"
        )


@router.get(
    "/{tournament_id}",
    response_model=TournamentResponse,
    summary="获取赛事详情",
    description="根据ID获取赛事详细信息",
)
async def get_tournament(
    tournament_id: UUID,
    tournament_service: TournamentService = Depends(get_tournament_service),
):
    """获取赛事详情"""
    tournament = await tournament_service.get_tournament(tournament_id)
    if not tournament:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="赛事不存在"
        )

    registration_entries = list(tournament.registrations.values())
    registration_count = len(registration_entries)
    confirmed_count = sum(
        1 for reg in registration_entries
        if getattr(reg, 'status', None) == 'confirmed'
    )
    team_registration_count = sum(
        1 for reg in registration_entries
        if getattr(reg, 'participant_type', None) == 'team'
    )
    player_registration_count = sum(
        1 for reg in registration_entries
        if getattr(reg, 'participant_type', None) == 'player'
    )

    return TournamentResponse(
        id=tournament.id,
        region_id=tournament.region_id,
        name=tournament.name,
        tournament_type=tournament.tournament_type,
        status=tournament.status,
        format=tournament.rules.format,
        max_participants=tournament.rules.max_participants,
        min_rank=tournament.rules.min_rank,
        max_rank=tournament.rules.max_rank,
        team_size=tournament.rules.team_size,
        registration_start=tournament.schedule.registration_start,
        registration_end=tournament.schedule.registration_end,
        tournament_start=tournament.schedule.tournament_start,
        tournament_end=tournament.schedule.tournament_end,
        description=tournament.description,
        logo_url=tournament.logo_url,
        banner_url=tournament.banner_url,
        created_by=tournament.created_by,
        created_at=tournament.created_at,
        updated_at=tournament.updated_at,
        registration_count=registration_count,
        confirmed_count=confirmed_count,
        team_registration_count=team_registration_count,
        player_registration_count=player_registration_count,
    )


@router.put(
    "/{tournament_id}",
    response_model=TournamentResponse,
    summary="更新赛事",
    description="管理员更新赛事信息",
)
async def update_tournament(
    tournament_id: UUID,
    tournament_data: TournamentUpdate,
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """更新赛事"""
    # 获取现有赛事
    tournament = await tournament_service.get_tournament(tournament_id)
    if not tournament:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="赛事不存在"
        )

    # 检查权限：需要赛区管理员或更高级别的权限
    await checker.require_permission(
        PermissionResource.TOURNAMENT,
        PermissionAction.UPDATE,
        region_id=tournament.region_id
    )

    try:
        # 只更新非None的字段
        updates = {}
        if tournament_data.name is not None:
            updates['name'] = tournament_data.name
        if tournament_data.description is not None:
            updates['description'] = tournament_data.description
        if tournament_data.tournament_type is not None:
            updates['tournament_type'] = tournament_data.tournament_type
        if tournament_data.format is not None:
            updates['format'] = tournament_data.format
        if tournament_data.max_participants is not None:
            updates['max_participants'] = tournament_data.max_participants
        if tournament_data.registration_start is not None:
            updates['registration_start'] = tournament_data.registration_start
        if tournament_data.registration_end is not None:
            updates['registration_end'] = tournament_data.registration_end
        if tournament_data.tournament_start is not None:
            updates['tournament_start'] = tournament_data.tournament_start
        if tournament_data.tournament_end is not None:
            updates['tournament_end'] = tournament_data.tournament_end
        if tournament_data.logo_url is not None:
            updates['logo_url'] = tournament_data.logo_url
        if tournament_data.banner_url is not None:
            updates['banner_url'] = tournament_data.banner_url
        if tournament_data.min_rank is not None:
            updates['min_rank'] = tournament_data.min_rank
        if tournament_data.max_rank is not None:
            updates['max_rank'] = tournament_data.max_rank
        if tournament_data.team_size is not None:
            updates['team_size'] = tournament_data.team_size
        if tournament_data.status is not None:
            updates['status'] = tournament_data.status

        updated_tournament = await tournament_service.update_tournament(
            tournament_id=tournament_id,
            updates=updates
        )

        registration_entries = list(updated_tournament.registrations.values())
        registration_count = len(registration_entries)
        confirmed_count = sum(
            1 for reg in registration_entries
            if getattr(reg, 'status', None) == 'confirmed'
        )
        team_registration_count = sum(
            1 for reg in registration_entries
            if getattr(reg, 'participant_type', None) == 'team'
        )
        player_registration_count = sum(
            1 for reg in registration_entries
            if getattr(reg, 'participant_type', None) == 'player'
        )

        return TournamentResponse(
            id=updated_tournament.id,
            region_id=updated_tournament.region_id,
            name=updated_tournament.name,
            tournament_type=updated_tournament.tournament_type,
            status=updated_tournament.status,
            format=updated_tournament.rules.format,
            max_participants=updated_tournament.rules.max_participants,
            min_rank=updated_tournament.rules.min_rank,
            max_rank=updated_tournament.rules.max_rank,
            team_size=updated_tournament.rules.team_size,
            registration_start=updated_tournament.schedule.registration_start,
            registration_end=updated_tournament.schedule.registration_end,
            tournament_start=updated_tournament.schedule.tournament_start,
            tournament_end=updated_tournament.schedule.tournament_end,
            description=updated_tournament.description,
            logo_url=updated_tournament.logo_url,
            banner_url=updated_tournament.banner_url,
            created_by=updated_tournament.created_by,
            created_at=updated_tournament.created_at,
            updated_at=updated_tournament.updated_at,
            registration_count=registration_count,
            confirmed_count=confirmed_count,
            team_registration_count=team_registration_count,
            player_registration_count=player_registration_count,
        )
    except ValueError as e:
        logger.warning(
            "Tournament update validation failed",
            user_id=current_user.id,
            tournament_id=str(tournament_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Tournament update failed unexpectedly",
            user_id=current_user.id,
            tournament_id=str(tournament_id),
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新赛事失败: {str(e)}"
        )


@router.delete(
    "/{tournament_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="删除赛事",
    description="管理员删除赛事",
)
async def delete_tournament(
    tournament_id: UUID,
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """删除赛事"""
    # 获取现有赛事
    tournament = await tournament_service.get_tournament(tournament_id)
    if not tournament:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="赛事不存在"
        )

    # 检查权限：需要赛区管理员或更高级别的权限
    await checker.require_permission(
        PermissionResource.TOURNAMENT,
        PermissionAction.DELETE,
        region_id=tournament.region_id
    )

    try:
        await tournament_service.delete_tournament(tournament_id)
        logger.info(
            "Tournament deleted successfully",
            user_id=current_user.id,
            tournament_id=str(tournament_id),
            tournament_name=tournament.name
        )
    except ValueError as e:
        logger.warning(
            "Tournament deletion validation failed",
            user_id=current_user.id,
            tournament_id=str(tournament_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Tournament deletion failed unexpectedly",
            user_id=current_user.id,
            tournament_id=str(tournament_id),
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除赛事失败: {str(e)}"
        )


@router.patch(
    "/{tournament_id}/status",
    response_model=TournamentResponse,
    summary="更新赛事状态",
    description="管理员更新赛事状态",
)
async def update_tournament_status(
    tournament_id: UUID,
    status_update: TournamentStatusUpdate,
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """更新赛事状态"""
    # 获取现有赛事
    tournament = await tournament_service.get_tournament(tournament_id)
    if not tournament:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="赛事不存在"
        )

    # 检查权限：需要赛区管理员或更高级别的权限
    await checker.require_permission(
        PermissionResource.TOURNAMENT,
        PermissionAction.UPDATE,
        region_id=tournament.region_id
    )

    try:
        updated_tournament = await tournament_service.update_tournament_status(
            tournament_id=tournament_id,
            new_status=status_update.status
        )

        logger.info(
            "Tournament status updated",
            user_id=current_user.id,
            tournament_id=str(tournament_id),
            old_status=tournament.status,
            new_status=status_update.status
        )

        registration_entries = list(updated_tournament.registrations.values())
        registration_count = len(registration_entries)
        confirmed_count = sum(
            1 for reg in registration_entries
            if getattr(reg, 'status', None) == 'confirmed'
        )
        team_registration_count = sum(
            1 for reg in registration_entries
            if getattr(reg, 'participant_type', None) == 'team'
        )
        player_registration_count = sum(
            1 for reg in registration_entries
            if getattr(reg, 'participant_type', None) == 'player'
        )

        return TournamentResponse(
            id=updated_tournament.id,
            region_id=updated_tournament.region_id,
            name=updated_tournament.name,
            tournament_type=updated_tournament.tournament_type,
            status=updated_tournament.status,
            format=updated_tournament.rules.format,
            max_participants=updated_tournament.rules.max_participants,
            min_rank=updated_tournament.rules.min_rank,
            max_rank=updated_tournament.rules.max_rank,
            team_size=updated_tournament.rules.team_size,
            registration_start=updated_tournament.schedule.registration_start,
            registration_end=updated_tournament.schedule.registration_end,
            tournament_start=updated_tournament.schedule.tournament_start,
            tournament_end=updated_tournament.schedule.tournament_end,
            description=updated_tournament.description,
            logo_url=updated_tournament.logo_url,
            banner_url=updated_tournament.banner_url,
            created_by=updated_tournament.created_by,
            created_at=updated_tournament.created_at,
            updated_at=updated_tournament.updated_at,
            registration_count=registration_count,
            confirmed_count=confirmed_count,
            team_registration_count=team_registration_count,
            player_registration_count=player_registration_count,
        )
    except ValueError as e:
        logger.warning(
            "Tournament status update validation failed",
            user_id=current_user.id,
            tournament_id=str(tournament_id),
            target_status=status_update.status,
            error=str(e)
        )
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Tournament status update failed unexpectedly",
            user_id=current_user.id,
            tournament_id=str(tournament_id),
            target_status=status_update.status,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新赛事状态失败: {str(e)}"
        )


@router.post(
    "/{tournament_id}/register",
    response_model=RegistrationResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="报名参赛",
    description="玩家报名参加赛事",
)
async def register_for_tournament(
    tournament_id: UUID,
    registration_data: RegistrationCreate,
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """报名参赛"""
    # 获取赛事信息以检查权限
    tournament = await tournament_service.get_tournament(tournament_id)
    if not tournament:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="赛事不存在"
        )

    # 检查基础权限：需要能够读取赛事信息
    await checker.require_permission(
        PermissionResource.TOURNAMENT,
        PermissionAction.READ,
        region_id=tournament.region_id
    )

    # 业务逻辑验证：检查赛事类型与参赛者类型匹配
    if tournament.tournament_type == "team_based" and registration_data.participant_type != "team":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="战队赛只能以战队身份参加，个人无法报名"
        )

    if tournament.tournament_type == "solo_based" and registration_data.participant_type != "player":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="个人赛只能以选手身份参加，战队无法报名"
        )

    try:
        registration = await tournament_service.register_for_tournament(
            tournament_id=tournament_id,
            participant_id=registration_data.participant_id,
            participant_type=registration_data.participant_type,
            registered_by=current_user.id,
        )

        return RegistrationResponse(
            id=registration.registration_id,
            tournament_id=registration.tournament_id,
            participant_id=registration.participant_id,
            participant_type=registration.participant_type,
            status=registration.status,
            registered_by=registration.registered_by,
            registered_at=registration.registered_at,
            is_admin_registered=registration.is_admin_registered,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # 处理重复注册和其他数据库完整性错误
        error_msg = str(e)
        if "duplicate key value violates unique constraint" in error_msg:
            if "tournament_registrations_tournament_id_participant_id_key" in error_msg:
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail="您已经报名了这个赛事，无法重复报名"
                )

        # 其他未知错误
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="报名失败，请稍后重试"
        )


@router.get(
    "/{tournament_id}/registrations",
    response_model=RegistrationListResponse,
    summary="获取报名列表",
    description="获取赛事的报名列表",
)
async def get_tournament_registrations(

    tournament_id: UUID,

    status_filter: Optional[str] = Query(None, alias="status", description="状态筛选"),

):

    """获取报名列表"""

    async with database_manager.get_session() as session:

        stmt = (

            select(TournamentRegistration)

            .options(selectinload(TournamentRegistration.status))

            .where(TournamentRegistration.tournament_id == tournament_id)

            .order_by(TournamentRegistration.registered_at.asc())

        )



        result = await session.execute(stmt)

        registrations = result.scalars().all()



        status_mapping = {

            1: "pending",

            2: "confirmed",

            3: "rejected",

            4: "withdrawn",

        }



        normalized_filter = status_filter.lower() if status_filter else None

        registration_responses = []



        for reg in registrations:

            if reg.status and getattr(reg.status, "code", None):

                status_code = reg.status.code.lower()

            else:

                status_code = status_mapping.get(reg.status_id, "pending")



            if normalized_filter and status_code != normalized_filter:

                continue



            team_info = None

            player_info = None



            # 根据参赛者类型查询详细信息

            if reg.participant_type == "team":

                try:

                    team_id = int(reg.participant_id)

                    team_stmt = select(Team).options(

                        selectinload(Team.region)

                    ).where(Team.id == team_id)

                    team_result = await session.execute(team_stmt)

                    team = team_result.scalar_one_or_none()



                    if team:

                        team_size_result = await session.execute(text(

                            "SELECT COUNT(*) FROM team_members WHERE team_id = :team_id AND is_active = true"

                        ), {"team_id": team.id})

                        current_size = team_size_result.scalar() or 0



                        team_info = TeamInfo(

                            id=str(team.id),

                            name=team.name,

                            logo_url=team.logo_url,

                            current_size=current_size,

                            region={"id": team.region.id, "name": team.region.name} if team.region else None

                        )

                    else:

                        team_info = TeamInfo(

                            id=reg.participant_id,

                            name=f"战队 {reg.participant_id[:8]}",

                            logo_url=None,

                            current_size=None,

                            region=None

                        )

                except ValueError:

                    team_info = TeamInfo(

                        id=reg.participant_id,

                        name=f"战队 {reg.participant_id[:8]}",

                        logo_url=None,

                        current_size=None,

                        region=None

                    )



            elif reg.participant_type == "player":

                player_stmt = select(PlayerProfile).options(

                    selectinload(PlayerProfile.region)

                ).where(PlayerProfile.profile_id == reg.participant_id)

                player_result = await session.execute(player_stmt)

                player = player_result.scalar_one_or_none()



                if player:

                    current_rank = None

                    if player.rank_tier:

                        if player.rank_division:

                            current_rank = f"{player.rank_tier} {player.rank_division}"

                        else:

                            current_rank = player.rank_tier



                    player_info = PlayerInfo(

                        id=str(player.profile_id),

                        username=player.summoner_name or "",

                        player_name=player.player_name,

                        current_rank=current_rank,

                        region={"id": player.region.id, "name": player.region.name} if player.region else None

                    )



            registration_responses.append(

                RegistrationResponse(

                    id=reg.id,

                    tournament_id=reg.tournament_id,

                    participant_id=reg.participant_id,

                    participant_type=reg.participant_type,

                    status=status_code,

                    registered_by=reg.registered_by,

                    registered_at=reg.registered_at,

                    is_admin_registered=reg.is_admin_registered,

                    team=team_info,

                    player=player_info,

                )

            )



    return RegistrationListResponse(

        registrations=registration_responses,

        total=len(registration_responses),

    )





@router.post("/admin/fix-participant-ids")
async def fix_participant_ids_temp():
    """临时修复participant_id数据的接口"""

    async with database_manager.get_session() as session:
        # 获取所有团队类型的报名记录
        registrations_result = await session.execute(text("""
            SELECT tr.id, tr.participant_id, tr.participant_type, t.region_id
            FROM tournament_registrations tr
            JOIN tournaments t ON tr.tournament_id = t.id
            WHERE tr.participant_type = 'team'
        """))
        registrations = registrations_result.all()

        # 获取所有团队
        teams_result = await session.execute(text("SELECT id, region_id FROM teams"))
        teams = teams_result.all()
        teams_by_region = {}
        for team in teams:
            region_id = team[1]
            if region_id not in teams_by_region:
                teams_by_region[region_id] = []
            teams_by_region[region_id].append(team[0])

        # 获取所有团队ID用于分配
        all_team_ids = [team[0] for team in teams]
        used_team_ids = set()

        fixed_count = 0
        for reg in registrations:
            reg_id = reg[0]
            current_participant_id = reg[1]
            tournament_id = None

            # 从原始查询结果中获取tournament_id（第4个元素包含tournament信息）
            # 重新查询tournament_id
            tournament_result = await session.execute(text(
                "SELECT tournament_id FROM tournament_registrations WHERE id = :reg_id"
            ), {"reg_id": reg_id})
            tournament_id = tournament_result.scalar()

            # 检查当前participant_id是否是有效的团队ID
            try:
                team_id = int(current_participant_id)
                check_result = await session.execute(text(
                    "SELECT COUNT(*) FROM teams WHERE id = :team_id"
                ), {"team_id": team_id})
                if check_result.scalar() > 0:
                    continue  # 如果已经是有效ID，跳过
            except ValueError:
                pass  # 不是整数，需要修复

            # 选择一个尚未在该赛事中使用的团队ID
            new_participant_id = None
            for team_id in all_team_ids:
                # 检查这个团队ID是否已经在该赛事中被使用
                check_used = await session.execute(text("""
                    SELECT COUNT(*) FROM tournament_registrations
                    WHERE tournament_id = :tournament_id AND participant_id = :team_id
                """), {"tournament_id": tournament_id, "team_id": str(team_id)})

                if check_used.scalar() == 0:  # 如果没有被使用
                    new_participant_id = str(team_id)
                    break

            if new_participant_id:
                # 更新数据库
                await session.execute(text(
                    "UPDATE tournament_registrations SET participant_id = :new_id WHERE id = :reg_id"
                ), {"new_id": new_participant_id, "reg_id": reg_id})
                fixed_count += 1

        await session.commit()

        return {
            "message": f"成功修复了 {fixed_count} 条记录",
            "fixed_count": fixed_count,
            "total_registrations": len(registrations)
        }



@router.get(
    "/{tournament_id}/matches",
    response_model=MatchListResponse,
    summary="获取比赛列表",
    description="获取赛事的比赛列表",
)
async def get_tournament_matches(
    tournament_id: UUID,
    round_number: Optional[int] = Query(None, description="轮次筛选"),
    status_filter: Optional[str] = Query(None, alias="status", description="状态筛选"),
    tournament_service: TournamentService = Depends(get_tournament_service),
):
    """获取比赛列表"""
    matches = await tournament_service.get_tournament_matches(
        tournament_id=tournament_id,
        round_number=round_number,
        status=status_filter.value if status_filter else None,
    )

    match_responses = []
    async with database_manager.get_session() as session:
        for match in matches:
            # 获取参赛者名称
            blue_side_name = await tournament_service.get_participant_name(match.blue_side_id)
            red_side_name = await tournament_service.get_participant_name(match.red_side_id)

            # 获取状态名称
            status_name = match.status  # 默认状态
            try:
                status_result = await session.execute(text(
                    "SELECT name FROM dict_match_statuses WHERE code = :status_code"
                ), {"status_code": match.status})
                status_row = status_result.fetchone()
                if status_row:
                    status_name = status_row[0]
            except Exception:
                pass

            match_responses.append(MatchResponse(
                id=match.match_id,
                tournament_id=match.tournament_id,
                round_number=match.round_number,
                blue_side_id=match.blue_side_id,
                red_side_id=match.red_side_id,
                status=status_name,
                room_id=match.room_id,
                scheduled_time=match.scheduled_time,
                started_at=match.started_at,
                completed_at=match.completed_at,
                winner_id=match.winner_id,
                check_ins={str(k): v for k, v in match.check_ins.items()},
                blue_side_name=blue_side_name,
                red_side_name=red_side_name,
            ))

    return MatchListResponse(
        matches=match_responses,
        total=len(match_responses),
    )


@router.get(
    "/matches/{match_id}",
    response_model=MatchResponse,
    summary="获取比赛详情",
    description="获取比赛详细信息",
)
async def get_match(
    match_id: UUID,
    tournament_service: TournamentService = Depends(get_tournament_service),
):
    """获取比赛详情"""
    match = await tournament_service.get_match(match_id)
    if not match:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="比赛不存在"
        )

    # 获取参赛者名称
    blue_side_name = await tournament_service.get_participant_name(match.blue_side_id)
    red_side_name = await tournament_service.get_participant_name(match.red_side_id)

    return MatchResponse(
        id=match.match_id,
        tournament_id=match.tournament_id,
        round_number=match.round_number,
        blue_side_id=match.blue_side_id,
        red_side_id=match.red_side_id,
        status=match.status,
        room_id=match.room_id,
        scheduled_time=match.scheduled_time,
        started_at=match.started_at,
        completed_at=match.completed_at,
        winner_id=match.winner_id,
        check_ins={str(k): v for k, v in match.check_ins.items()},
        blue_side_name=blue_side_name,
        red_side_name=red_side_name,
    )


@router.post(
    "/matches/{match_id}/checkin",
    response_model=CheckInResponse,
    summary="参赛者签到",
    description="参赛者在比赛房间进行签到",
)
async def check_in_participant(
    match_id: UUID,
    check_in_data: CheckInRequest,
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """参赛者签到"""
    try:
        # 获取比赛信息
        match = await tournament_service.get_match(match_id)
        if not match:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="比赛不存在"
            )

        # 获取赛事信息以检查权限
        tournament = await tournament_service.get_tournament(match.tournament_id)
        if not tournament:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="赛事不存在"
            )

        # 检查基础权限：需要能够读取赛事信息
        await checker.require_permission(
            PermissionResource.TOURNAMENT,
            PermissionAction.READ,
            region_id=tournament.region_id
        )

        # 执行签到
        updated_match = await tournament_service.check_in_participant(
            match_id=match_id,
            participant_id=check_in_data.participant_id,
        )

        # 获取签到状态
        check_in_status = updated_match.check_ins.get(check_in_data.participant_id)

        # 创建响应
        response = CheckInResponse(
            participant_id=check_in_data.participant_id,
            status=check_in_status,
            checked_in_at=updated_match.started_at if check_in_status and check_in_status == "checked_in" else None,
        )

        # 实时广播签到状态更新
        if match.room_id:
            broadcast_message = {
                "type": "check_in_update",
                "data": {
                    "match_id": str(match_id),
                    "participant_id": str(check_in_data.participant_id),
                    "status": check_in_status if check_in_status else "not_checked_in",
                    "all_checked_in": updated_match.all_checked_in(),
                    "checked_in_at": response.checked_in_at.isoformat() if response.checked_in_at else None,
                    "timestamp": "now"  # TODO: 使用实际时间戳
                }
            }
            await websocket_manager.send_room_message(broadcast_message, match.room_id)

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/matches/{match_id}/open-checkin",
    response_model=MatchResponse,
    summary="开启签到",
    description="管理员开启比赛签到（生成房间）",
)
async def open_match_checkin(
    match_id: UUID,
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """开启比赛签到"""
    try:
        # 获取比赛信息
        match = await tournament_service.get_match(match_id)
        if not match:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="比赛不存在"
            )

        # 获取赛事信息以检查权限
        tournament = await tournament_service.get_tournament(match.tournament_id)
        if not tournament:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="赛事不存在"
            )

        # 检查管理权限：需要能够管理赛事
        await checker.require_permission(
            PermissionResource.TOURNAMENT,
            PermissionAction.MANAGE,
            region_id=tournament.region_id
        )

        # 获取参赛者列表（这里简化处理，实际应根据比赛类型获取具体参赛者）
        participants = [match.blue_side_id, match.red_side_id]

        # 开启签到
        updated_match = await tournament_service.open_match_check_in(
            match_id=match_id,
            participants=participants,
        )

        # 实时广播签到开启消息
        if updated_match.room_id:
            broadcast_message = {
                "type": "check_in_opened",
                "data": {
                    "match_id": str(match_id),
                    "room_id": str(updated_match.room_id),
                    "status": updated_match.status,
                    "participants": [str(p) for p in participants],
                    "timestamp": "now"
                }
            }
            await websocket_manager.send_room_message(broadcast_message, updated_match.room_id)

        return MatchResponse(
            id=updated_match.match_id,
            tournament_id=updated_match.tournament_id,
            round_number=updated_match.round_number,
            blue_side_id=updated_match.blue_side_id,
            red_side_id=updated_match.red_side_id,
            status=updated_match.status,
            room_id=updated_match.room_id,
            scheduled_time=updated_match.scheduled_time,
            started_at=updated_match.started_at,
            completed_at=updated_match.completed_at,
            winner_id=updated_match.winner_id,
            check_ins={str(k): v for k, v in updated_match.check_ins.items()},
        )

    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/matches/{match_id}/start",
    response_model=MatchResponse,
    summary="开始比赛",
    description="管理员开始比赛（所有人签到完成后）",
)
async def start_match(
    match_id: UUID,
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """开始比赛"""
    try:
        # 获取比赛信息
        match = await tournament_service.get_match(match_id)
        if not match:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="比赛不存在"
            )

        # 获取赛事信息以检查权限
        tournament = await tournament_service.get_tournament(match.tournament_id)
        if not tournament:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="赛事不存在"
            )

        # 检查管理权限
        await checker.require_permission(
            PermissionResource.TOURNAMENT,
            PermissionAction.MANAGE,
            region_id=tournament.region_id
        )

        # 开始比赛
        updated_match = await tournament_service.start_match(match_id)

        # 实时广播比赛开始消息
        if updated_match.room_id:
            broadcast_message = {
                "type": "match_started",
                "data": {
                    "match_id": str(match_id),
                    "status": updated_match.status,
                    "started_at": updated_match.started_at.isoformat() if updated_match.started_at else None,
                    "timestamp": "now"
                }
            }
            await websocket_manager.send_room_message(broadcast_message, updated_match.room_id)

        return MatchResponse(
            id=updated_match.match_id,
            tournament_id=updated_match.tournament_id,
            round_number=updated_match.round_number,
            blue_side_id=updated_match.blue_side_id,
            red_side_id=updated_match.red_side_id,
            status=updated_match.status,
            room_id=updated_match.room_id,
            scheduled_time=updated_match.scheduled_time,
            started_at=updated_match.started_at,
            completed_at=updated_match.completed_at,
            winner_id=updated_match.winner_id,
            check_ins={str(k): v for k, v in updated_match.check_ins.items()},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to start match",
            match_id=str(match_id),
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="开始比赛失败"
        )


@router.post(
    "/matches/{match_id}/force-checkin-all",
    response_model=MatchResponse,
    summary="强制全员签到",
    description="管理员强制所有参赛者签到",
)
async def force_checkin_all_participants(
    match_id: UUID,
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """管理员强制全员签到"""
    try:
        # 获取比赛信息
        match = await tournament_service.get_match(match_id)
        if not match:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="比赛不存在"
            )

        # 获取赛事信息以检查权限
        tournament = await tournament_service.get_tournament(match.tournament_id)
        if not tournament:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="赛事不存在"
            )

        # 检查管理权限
        await checker.require_permission(
            PermissionResource.TOURNAMENT,
            PermissionAction.MANAGE,
            region_id=tournament.region_id
        )

        # 强制全员签到
        updated_match = await tournament_service.force_checkin_all_participants(match_id)

        # 实时广播强制签到消息
        if updated_match.room_id:
            broadcast_message = {
                "type": "force_checkin_completed",
                "data": {
                    "match_id": str(match_id),
                    "status": updated_match.status,
                    "check_ins": {str(k): v for k, v in updated_match.check_ins.items()},
                    "timestamp": "now"
                }
            }
            await websocket_manager.send_room_message(broadcast_message, updated_match.room_id)

        # 获取参赛者名称
        blue_side_name = await tournament_service.get_participant_name(updated_match.blue_side_id)
        red_side_name = await tournament_service.get_participant_name(updated_match.red_side_id)

        return MatchResponse(
            id=updated_match.match_id,
            tournament_id=updated_match.tournament_id,
            round_number=updated_match.round_number,
            blue_side_id=updated_match.blue_side_id,
            red_side_id=updated_match.red_side_id,
            status=updated_match.status,
            room_id=updated_match.room_id,
            scheduled_time=updated_match.scheduled_time,
            started_at=updated_match.started_at,
            completed_at=updated_match.completed_at,
            winner_id=updated_match.winner_id,
            check_ins={str(k): v for k, v in updated_match.check_ins.items()},
            blue_side_name=blue_side_name,
            red_side_name=red_side_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to force checkin all participants",
            match_id=str(match_id),
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="强制签到失败"
        )


@router.post(
    "/{tournament_id}/generate-bracket",
    response_model=MatchListResponse,
    summary="生成赛程",
    description="管理员为赛事生成对阵表",
)
async def generate_tournament_bracket(
    tournament_id: UUID,
    auto_assign_byes: bool = Query(True, description="是否自动分配轮空"),
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """生成赛事对阵表"""
    try:
        # 获取赛事信息以检查权限
        tournament = await tournament_service.get_tournament(tournament_id)
        if not tournament:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="赛事不存在"
            )

        # 检查管理权限：需要能够管理赛事
        await checker.require_permission(
            PermissionResource.TOURNAMENT,
            PermissionAction.MANAGE,
            region_id=tournament.region_id
        )

        # 生成对阵表
        matches = await tournament_service.generate_bracket(
            tournament_id=tournament_id,
            auto_assign_byes=auto_assign_byes,
        )

        # 转换为响应格式
        match_responses = [
            MatchResponse(
                id=match.match_id,
                tournament_id=match.tournament_id,
                round_number=match.round_number,
                match_number=getattr(match, 'match_number', None),
                blue_side_id=match.blue_side_id,
                red_side_id=match.red_side_id,
                status=match.status,
                room_id=match.room_id,
                scheduled_time=match.scheduled_time,
                started_at=match.started_at,
                completed_at=match.completed_at,
                winner_id=match.winner_id,
                check_ins={str(k): v for k, v in match.check_ins.items()},
            )
            for match in matches
        ]

        logger.info(
            "Tournament bracket generated successfully",
            tournament_id=str(tournament_id),
            matches_count=len(matches),
            user_id=current_user.id
        )

        return MatchListResponse(
            matches=match_responses,
            total=len(match_responses),
        )

    except ValueError as e:
        logger.warning(
            "Failed to generate tournament bracket",
            tournament_id=str(tournament_id),
            error=str(e),
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Unexpected error generating tournament bracket",
            tournament_id=str(tournament_id),
            error=str(e),
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成对阵表失败，请稍后重试"
        )


@router.post(
    "/matches/{match_id}/advance-winner",
    response_model=MatchResponse,
    summary="推进获胜者",
    description="管理员将比赛获胜者推进到下一轮",
)
async def advance_winner_to_next_round(
    match_id: UUID,
    winner_id: UUID = Query(..., description="获胜者ID"),
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """推进获胜者到下一轮"""
    try:
        # 获取比赛信息
        match = await tournament_service.get_match(match_id)
        if not match:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="比赛不存在"
            )

        # 获取赛事信息以检查权限
        tournament = await tournament_service.get_tournament(match.tournament_id)
        if not tournament:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="赛事不存在"
            )

        # 检查管理权限
        await checker.require_permission(
            PermissionResource.TOURNAMENT,
            PermissionAction.MANAGE,
            region_id=tournament.region_id
        )

        # 先完成当前比赛
        completed_match = await tournament_service.complete_match(
            match_id=match_id,
            winner_id=winner_id,
        )

        # 推进获胜者到下一轮
        next_match = await tournament_service.advance_winner_to_next_round(
            completed_match_id=match_id,
            winner_id=winner_id,
        )

        # 返回下一轮比赛信息（如果存在）
        if next_match:
            return MatchResponse(
                id=next_match.match_id,
                tournament_id=next_match.tournament_id,
                round_number=next_match.round_number,
                match_number=getattr(next_match, 'match_number', None),
                blue_side_id=next_match.blue_side_id,
                red_side_id=next_match.red_side_id,
                status=next_match.status,
                room_id=next_match.room_id,
                scheduled_time=next_match.scheduled_time,
                started_at=next_match.started_at,
                completed_at=next_match.completed_at,
                winner_id=next_match.winner_id,
                check_ins={str(k): v for k, v in next_match.check_ins.items()},
            )
        else:
            # 如果没有下一轮比赛，返回已完成的比赛信息
            return MatchResponse(
                id=completed_match.match_id,
                tournament_id=completed_match.tournament_id,
                round_number=completed_match.round_number,
                match_number=getattr(completed_match, 'match_number', None),
                blue_side_id=completed_match.blue_side_id,
                red_side_id=completed_match.red_side_id,
                status=completed_match.status,
                room_id=completed_match.room_id,
                scheduled_time=completed_match.scheduled_time,
                started_at=completed_match.started_at,
                completed_at=completed_match.completed_at,
                winner_id=completed_match.winner_id,
                check_ins={str(k): v for k, v in completed_match.check_ins.items()},
            )

    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to advance winner to next round",
            match_id=str(match_id),
            winner_id=str(winner_id),
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="推进获胜者失败"
        )


@router.put(
    "/{tournament_id}/matches/{match_id}",
    response_model=MatchResponse,
    summary="更新比赛信息",
    description="管理员更新比赛的参赛者、时间等信息",
)
async def update_match(
    tournament_id: UUID,
    match_id: UUID,
    match_data: MatchUpdate,
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """更新比赛信息"""
    try:
        # 检查赛事是否存在
        tournament = await tournament_service.get_tournament(tournament_id)
        if not tournament:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="赛事不存在"
            )

        # 检查权限
        await checker.require_permission(
            PermissionResource.TOURNAMENT,
            PermissionAction.MANAGE,
            region_id=tournament.region_id
        )

        # 获取当前比赛信息
        match = await tournament_service.get_match(match_id)
        if not match:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="比赛不存在"
            )

        if str(match.tournament_id) != str(tournament_id):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="比赛不属于该赛事"
            )

        # 确保比赛未开始，只能修改未开始的比赛
        if match.status not in ['scheduled', 'waiting_for_checkin']:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="只能修改未开始的比赛"
            )

        # 更新比赛信息
        updated_match = await tournament_service.update_match(
            match_id=match_id,
            blue_side_id=match_data.blue_side_id,
            red_side_id=match_data.red_side_id,
            scheduled_time=match_data.scheduled_time,
            round_number=match_data.round_number,
        )

        # 获取参赛者名称
        blue_side_name = await tournament_service.get_participant_name(updated_match.blue_side_id) if updated_match.blue_side_id else None
        red_side_name = await tournament_service.get_participant_name(updated_match.red_side_id) if updated_match.red_side_id else None

        logger.info(
            "Match updated successfully",
            tournament_id=str(tournament_id),
            match_id=str(match_id),
            user_id=current_user.id,
            changes={
                "blue_side_id": match_data.blue_side_id,
                "red_side_id": match_data.red_side_id,
                "scheduled_time": match_data.scheduled_time.isoformat() if match_data.scheduled_time else None,
                "round_number": match_data.round_number,
            }
        )

        return MatchResponse(
            id=updated_match.match_id,
            tournament_id=updated_match.tournament_id,
            round_number=updated_match.round_number,
            blue_side_id=updated_match.blue_side_id,
            red_side_id=updated_match.red_side_id,
            status=updated_match.status,
            room_id=updated_match.room_id,
            scheduled_time=updated_match.scheduled_time,
            started_at=updated_match.started_at,
            completed_at=updated_match.completed_at,
            winner_id=updated_match.winner_id,
            check_ins={str(k): v for k, v in updated_match.check_ins.items()},
            blue_side_name=blue_side_name,
            red_side_name=red_side_name,
            tournament_name=tournament.name,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            "Match update validation failed",
            tournament_id=str(tournament_id),
            match_id=str(match_id),
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Match update failed unexpectedly",
            tournament_id=str(tournament_id),
            match_id=str(match_id),
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新比赛失败: {str(e)}"
        )


@router.patch(
    "/{tournament_id}/registrations/{registration_id}/confirm",
    response_model=RegistrationResponse,
    summary="确认报名",
    description="管理员确认参赛者报名",
)
async def confirm_registration(
    tournament_id: UUID,
    registration_id: UUID,
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """确认报名"""
    try:
        # 获取赛事信息以检查权限
        tournament = await tournament_service.get_tournament(tournament_id)
        if not tournament:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="赛事不存在"
            )

        # 检查管理权限：需要能够管理赛事
        await checker.require_permission(
            PermissionResource.TOURNAMENT,
            PermissionAction.MANAGE,
            region_id=tournament.region_id
        )

        # 确认报名
        updated_registration = await tournament_service.confirm_registration(
            tournament_id=tournament_id,
            registration_id=registration_id
        )

        logger.info(
            "Registration confirmed successfully",
            tournament_id=str(tournament_id),
            registration_id=str(registration_id),
            user_id=current_user.id
        )

        return RegistrationResponse(
            id=updated_registration.registration_id,
            tournament_id=updated_registration.tournament_id,
            participant_id=updated_registration.participant_id,
            participant_type=updated_registration.participant_type,
            status=updated_registration.status,
            registered_by=updated_registration.registered_by,
            registered_at=updated_registration.registered_at,
            is_admin_registered=updated_registration.is_admin_registered,
        )

    except ValueError as e:
        logger.warning(
            "Registration confirmation validation failed",
            tournament_id=str(tournament_id),
            registration_id=str(registration_id),
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Registration confirmation failed unexpectedly",
            tournament_id=str(tournament_id),
            registration_id=str(registration_id),
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"确认报名失败: {str(e)}"
        )


@router.post(
    "/{tournament_id}/registrations/confirm-batch",
    response_model=Dict,
    summary="批量确认报名",
    description="管理员批量确认多个参赛者报名",
)
async def confirm_registrations_batch(
    tournament_id: UUID,
    request_body: Dict[str, List[UUID]],
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """批量确认报名"""
    try:
        registration_ids = request_body.get('registration_ids', [])
        if not registration_ids:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="registration_ids不能为空"
            )

        # 获取赛事信息以检查权限
        tournament = await tournament_service.get_tournament(tournament_id)
        if not tournament:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="赛事不存在"
            )

        # 检查管理权限
        await checker.require_permission(
            PermissionResource.TOURNAMENT,
            PermissionAction.MANAGE,
            region_id=tournament.region_id
        )

        # 批量确认报名
        result = await tournament_service.confirm_registrations_batch(
            tournament_id=tournament_id,
            registration_ids=registration_ids
        )

        logger.info(
            "Batch registration confirmation completed",
            tournament_id=str(tournament_id),
            confirmed_count=result['confirmed_count'],
            failed_count=result['failed_count'],
            user_id=current_user.id
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Batch registration confirmation failed unexpectedly",
            tournament_id=str(tournament_id),
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量确认报名失败: {str(e)}"
        )


@router.patch(
    "/{tournament_id}/registrations/{registration_id}/reject",
    response_model=RegistrationResponse,
    summary="拒绝报名",
    description="管理员拒绝参赛者报名",
)
async def reject_registration(
    tournament_id: UUID,
    registration_id: UUID,
    request_body: Optional[Dict[str, str]] = None,
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """拒绝报名"""
    try:
        reason = request_body.get('reason') if request_body else None

        # 获取赛事信息以检查权限
        tournament = await tournament_service.get_tournament(tournament_id)
        if not tournament:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="赛事不存在"
            )

        # 检查管理权限
        await checker.require_permission(
            PermissionResource.TOURNAMENT,
            PermissionAction.MANAGE,
            region_id=tournament.region_id
        )

        # 拒绝报名
        updated_registration = await tournament_service.reject_registration(
            tournament_id=tournament_id,
            registration_id=registration_id,
            reason=reason
        )

        logger.info(
            "Registration rejected successfully",
            tournament_id=str(tournament_id),
            registration_id=str(registration_id),
            reason=reason,
            user_id=current_user.id
        )

        return RegistrationResponse(
            id=updated_registration.registration_id,
            tournament_id=updated_registration.tournament_id,
            participant_id=updated_registration.participant_id,
            participant_type=updated_registration.participant_type,
            status=updated_registration.status,
            registered_by=updated_registration.registered_by,
            registered_at=updated_registration.registered_at,
            is_admin_registered=updated_registration.is_admin_registered,
        )

    except ValueError as e:
        logger.warning(
            "Registration rejection validation failed",
            tournament_id=str(tournament_id),
            registration_id=str(registration_id),
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Registration rejection failed unexpectedly",
            tournament_id=str(tournament_id),
            registration_id=str(registration_id),
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"拒绝报名失败: {str(e)}"
        )


@router.post(
    "/{tournament_id}/matches",
    response_model=MatchResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="创建新比赛",
    description="管理员为赛事创建新的比赛房间",
)
async def create_match(
    tournament_id: UUID,
    match_data: MatchCreate,
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """创建新比赛"""
    try:
        # 检查赛事是否存在
        tournament = await tournament_service.get_tournament(tournament_id)
        if not tournament:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="赛事不存在"
            )

        # 确保match_data中的tournament_id与路径参数一致
        if str(match_data.tournament_id) != str(tournament_id):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="比赛的赛事ID与路径参数不匹配"
            )

        # 检查权限
        await checker.require_permission(
            PermissionResource.TOURNAMENT,
            PermissionAction.MANAGE,
            region_id=tournament.region_id
        )

        # 创建比赛
        new_match = await tournament_service.create_match(
            tournament_id=tournament_id,
            blue_side_id=match_data.blue_side_id,
            red_side_id=match_data.red_side_id,
            round_number=match_data.round_number,
            scheduled_time=match_data.scheduled_time,
        )

        # 获取参赛者名称
        blue_side_name = await tournament_service.get_participant_name(str(match_data.blue_side_id))
        red_side_name = await tournament_service.get_participant_name(str(match_data.red_side_id))

        logger.info(
            "Match created successfully",
            tournament_id=str(tournament_id),
            match_id=str(new_match.match_id),
            user_id=current_user.id,
            blue_side_id=str(match_data.blue_side_id),
            red_side_id=str(match_data.red_side_id),
            round_number=match_data.round_number,
        )

        return MatchResponse(
            id=new_match.match_id,
            tournament_id=new_match.tournament_id,
            round_number=new_match.round_number,
            blue_side_id=new_match.blue_side_id,
            red_side_id=new_match.red_side_id,
            status=new_match.status,
            room_id=new_match.room_id,
            scheduled_time=new_match.scheduled_time,
            started_at=new_match.started_at,
            completed_at=new_match.completed_at,
            winner_id=new_match.winner_id,
            check_ins={str(k): v for k, v in new_match.check_ins.items()},
            blue_side_name=blue_side_name,
            red_side_name=red_side_name,
            tournament_name=tournament.name,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            "Match creation validation failed",
            tournament_id=str(tournament_id),
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Match creation failed unexpectedly",
            tournament_id=str(tournament_id),
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建比赛失败: {str(e)}"
        )


@router.delete(
    "/{tournament_id}/matches/{match_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="删除比赛",
    description="管理员删除指定的比赛",
)
async def delete_match(
    tournament_id: UUID,
    match_id: UUID,
    current_user: User = Depends(get_current_user),
    tournament_service: TournamentService = Depends(get_tournament_service),
    checker: PermissionChecker = Depends(get_permission_checker),
):
    """删除比赛"""
    try:
        # 获取赛事信息以检查权限
        tournament = await tournament_service.get_tournament(tournament_id)
        if not tournament:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="赛事不存在"
            )

        # 检查管理权限
        await checker.require_permission(
            PermissionResource.TOURNAMENT,
            PermissionAction.UPDATE,
            region_id=tournament.region_id
        )

        # 获取比赛信息
        match = await tournament_service.get_match(match_id)
        if not match:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="比赛不存在"
            )

        # 验证比赛属于指定赛事
        if str(match.tournament_id) != str(tournament_id):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="比赛不属于指定赛事"
            )

        # 检查比赛状态 - 只能删除未开始的比赛
        if match.status not in ['scheduled', 'waiting_for_checkin']:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="只能删除未开始的比赛"
            )

        # 删除比赛
        success = await tournament_service.delete_match(match_id)
        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除比赛失败"
            )

        logger.info(
            "Match deleted successfully",
            tournament_id=str(tournament_id),
            match_id=str(match_id),
            user_id=current_user.id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Match deletion failed unexpectedly",
            tournament_id=str(tournament_id),
            match_id=str(match_id),
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除比赛失败: {str(e)}"
        )


