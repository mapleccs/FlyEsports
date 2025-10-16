"""
Public registration API routes.
"""

from fastapi import APIRouter, HTTPException, status
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/health")
async def registration_health():
    """Registration service health check"""
    return {"status": "Registration service is healthy"}


@router.get("/regions")
async def get_regions_for_registration(active_only: bool = False):
    """
    Get all regions for player registration - public endpoint.

    This endpoint provides access to regions without authentication,
    specifically for use during player registration.

    Args:
        active_only: If True, only returns active regions
    """
    try:
        from src.infrastructure.database.connection import database_manager
        from sqlalchemy import select, text
        
        async with database_manager.get_session() as session:
            # Query regions with player count statistics
            if active_only:
                query = text("""
                    SELECT 
                        r.id, 
                        r.name, 
                        r.description, 
                        r.is_active, 
                        r.created_at, 
                        r.updated_at,
                        COUNT(DISTINCT pp.id) AS total_players,
                        COUNT(DISTINCT CASE WHEN cs.code = 'FREE' THEN pp.id END) AS active_players
                    FROM regions r
                    LEFT JOIN player_profiles pp ON pp.region_id = r.id
                    LEFT JOIN dict_contract_statuses cs ON pp.contract_status_id = cs.id
                    WHERE r.is_active = true
                    GROUP BY r.id, r.name, r.description, r.is_active, r.created_at, r.updated_at
                    ORDER BY r.name
                """)
            else:
                query = text("""
                    SELECT 
                        r.id, 
                        r.name, 
                        r.description, 
                        r.is_active, 
                        r.created_at, 
                        r.updated_at,
                        COUNT(DISTINCT pp.id) AS total_players,
                        COUNT(DISTINCT CASE WHEN cs.code = 'FREE' THEN pp.id END) AS active_players
                    FROM regions r
                    LEFT JOIN player_profiles pp ON pp.region_id = r.id
                    LEFT JOIN dict_contract_statuses cs ON pp.contract_status_id = cs.id
                    GROUP BY r.id, r.name, r.description, r.is_active, r.created_at, r.updated_at
                    ORDER BY r.name
                """)
            
            result = await session.execute(query)
            regions_data = result.fetchall()
            
            regions = []
            for row in regions_data:
                regions.append({
                    "region_id": row[0],  # 返回数字类型，与前端类型定义一致
                    "region_name": row[1],
                    "status": "active" if row[3] else "inactive",
                    "total_players": row[6] if row[6] else 0,  # 使用实际统计数据
                    "active_players": row[7] if row[7] else 0,  # 使用实际统计数据
                    "is_active": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                })

            return {
                "regions": regions,
                "total": len(regions)
            }

    except Exception as e:
        logger.error(
            "Failed to get regions for registration",
            active_only=active_only,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="获取赛区列表失败，请稍后重试"
        )