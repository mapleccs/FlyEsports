from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from src.presentation.dependencies.permission import verify_permission
from src.domain.value_objects.role import PermissionAction, PermissionResource
from src.infrastructure.database.connection import database_manager
from src.infrastructure.database.models.team import Team
from src.infrastructure.database.models.user import User

router = APIRouter()


@router.get("/health")
async def teams_health():
    return {"status": "Teams service is healthy"}


@router.get("/")
@router.get("")  # 支持不带斜杠的路径
async def get_teams(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(12, ge=1, le=50, description="每页数量"),
    region_id: Optional[int] = Query(None, description="赛区ID筛选"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    recruitment_status: Optional[str] = Query(None, description="招募状态筛选")
):
    """
    Get teams list with pagination and filters.
    Public endpoint - no authentication required.
    """
    try:
        async with database_manager.get_session() as session:
            # 构建查询
            query = select(Team).options(
                joinedload(Team.region),
                joinedload(Team.captain)
            ).where(Team.is_active == True)
            
            # 添加筛选条件
            if region_id:
                query = query.where(Team.region_id == region_id)
            
            if keyword:
                query = query.where(
                    Team.name.ilike(f'%{keyword}%') | 
                    Team.tag.ilike(f'%{keyword}%')
                )
            
            if recruitment_status == "open":
                query = query.where(Team.is_recruiting == True)
            elif recruitment_status == "closed":
                query = query.where(Team.is_recruiting == False)
            
            # 获取总数
            count_query = select(func.count(Team.id)).where(Team.is_active == True)
            if region_id:
                count_query = count_query.where(Team.region_id == region_id)
            if keyword:
                count_query = count_query.where(
                    Team.name.ilike(f'%{keyword}%') | 
                    Team.tag.ilike(f'%{keyword}%')
                )
            if recruitment_status == "open":
                count_query = count_query.where(Team.is_recruiting == True)
            elif recruitment_status == "closed":
                count_query = count_query.where(Team.is_recruiting == False)
                
            total_result = await session.execute(count_query)
            total = total_result.scalar()
            
            # 分页
            offset = (page - 1) * limit
            query = query.offset(offset).limit(limit).order_by(Team.created_at.desc())
            
            result = await session.execute(query)
            teams_data = result.scalars().all()
            
            # 构建响应数据
            teams = []
            for team in teams_data:
                teams.append({
                    "id": team.id,
                    "name": team.name,
                    "tag": team.tag,
                    "description": team.description,
                    "logo_url": team.logo_url,
                    "region_id": team.region_id,
                    "region_name": team.region.name if team.region else None,
                    "captain_username": team.captain.username if team.captain else None,
                    "is_recruiting": team.is_recruiting,
                    "created_at": team.created_at.isoformat(),
                    "updated_at": team.updated_at.isoformat()
                })
            
            return {
                "teams": teams,
                "total": total,
                "page": page,
                "limit": limit,
                "has_next": offset + limit < total,
                "has_prev": page > 1
            }
            
    except Exception as e:
        import structlog
        logger = structlog.get_logger(__name__)
        logger.error("Failed to fetch teams", error=str(e))
        
        # 返回空结果而不是抛出异常，保证前端正常显示
        return {
            "teams": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "has_next": False,
            "has_prev": False,
            "error": "Failed to load teams"
        }


@router.post("/")
async def create_team(
    _: None = Depends(
        verify_permission(PermissionResource.TEAM, PermissionAction.CREATE)
    ),
):
    """
    Create a new team.
    Requires TEAM:CREATE permission.
    """
    return {"message": "Team creation API with permission protection"}
