"""比赛API路由"""

from typing import List, Optional
from uuid import UUID
import structlog

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from src.infrastructure.database.connection import database_manager
from src.infrastructure.database.models.tournament import TournamentMatch, Tournament, TournamentRegistration
from src.infrastructure.database.models.team import Team
from src.infrastructure.database.models.player_profile import PlayerProfile
from src.presentation.schemas.tournament import MatchResponse, MatchListResponse

logger = structlog.get_logger(__name__)

router = APIRouter()


async def get_participant_name(session, participant_id: str) -> str:
    """获取参赛者名称"""
    if not participant_id:
        return "未知参赛者"

    try:
        # 尝试作为team ID查询
        if participant_id.isdigit():
            team_stmt = select(Team).where(Team.id == int(participant_id))
            team_result = await session.execute(team_stmt)
            team = team_result.scalar_one_or_none()
            if team:
                return team.name

        # 尝试作为player profile ID查询
        player_stmt = select(PlayerProfile).where(PlayerProfile.profile_id == participant_id)
        player_result = await session.execute(player_stmt)
        player = player_result.scalar_one_or_none()
        if player:
            return player.player_name or player.summoner_name or "未知选手"

        return "未知参赛者"
    except Exception as e:
        logger.warning(f"查询参赛者名称失败: {e}", participant_id=participant_id)
        return "未知参赛者"


@router.get(
    "/",
    response_model=MatchListResponse,
    summary="获取全局比赛列表",
    description="获取所有赛事的比赛列表，用于比赛大厅显示",
)
async def get_all_matches(
    status_filter: Optional[str] = Query(None, alias="status", description="状态筛选"),
    limit: int = Query(50, description="限制数量"),
    offset: int = Query(0, description="偏移量"),
):
    """获取全局比赛列表"""
    async with database_manager.get_session() as session:
        # 构建查询语句
        stmt = select(TournamentMatch).options(
            selectinload(TournamentMatch.tournament)
        ).order_by(TournamentMatch.scheduled_time.desc())

        # 添加状态筛选
        if status_filter:
            stmt = stmt.where(TournamentMatch.status_id == status_filter)

        # 添加分页
        stmt = stmt.offset(offset).limit(limit)

        result = await session.execute(stmt)
        matches = result.scalars().all()

        match_responses = []
        for match in matches:
            # 获取赛事名称
            tournament_name = "未知赛事"
            if match.tournament:
                tournament_name = match.tournament.name

            # 获取参赛者名称
            blue_side_name = "未知队伍"
            red_side_name = "未知队伍"

            # 获取参赛者名称 - 简化逻辑，直接根据ID查询
            blue_side_name = await get_participant_name(session, match.blue_side_id)
            red_side_name = await get_participant_name(session, match.red_side_id)

            # 获取状态名称
            status_name = "scheduled"  # 默认状态
            try:
                status_result = await session.execute(text(
                    "SELECT name FROM dict_match_statuses WHERE id = :status_id"
                ), {"status_id": match.status_id})
                status_row = status_result.fetchone()
                if status_row:
                    status_name = status_row[0]
            except Exception:
                pass

            match_responses.append(MatchResponse(
                id=match.id,
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
                check_ins={},  # 简化check_ins处理
                blue_side_name=blue_side_name,
                red_side_name=red_side_name,
                tournament_name=tournament_name,
            ))

        return MatchListResponse(
            matches=match_responses,
            total=len(match_responses),
        )