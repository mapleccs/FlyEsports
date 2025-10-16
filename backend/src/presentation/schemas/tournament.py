"""赛事相关的API Schema定义"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from src.domain.value_objects.tournament import (
    TournamentFormat,
    TournamentType,
)


# 基础Schema
class TournamentBase(BaseModel):
    """赛事基础Schema"""
    
    name: str = Field(..., min_length=1, max_length=100, description="赛事名称")
    tournament_type: TournamentType = Field(..., description="赛事类型")
    format: TournamentFormat = Field(..., description="赛制格式")
    max_participants: int = Field(..., gt=0, description="最大参赛名额")
    min_rank: Optional[str] = Field(None, max_length=20, description="最低段位限制")
    max_rank: Optional[str] = Field(None, max_length=20, description="最高段位限制")
    team_size: Optional[int] = Field(None, gt=0, description="战队人数")
    
    registration_start: datetime = Field(..., description="报名开始时间")
    registration_end: datetime = Field(..., description="报名结束时间")
    tournament_start: datetime = Field(..., description="比赛开始时间")
    tournament_end: datetime = Field(..., description="比赛结束时间")
    
    description: Optional[str] = Field(None, description="赛事描述")
    logo_url: Optional[str] = Field(None, max_length=500, description="赛事Logo URL")
    banner_url: Optional[str] = Field(None, max_length=500, description="赛事横幅URL")
    
    @validator("registration_end")
    def validate_registration_end(cls, v, values):
        if "registration_start" in values and v <= values["registration_start"]:
            raise ValueError("报名结束时间必须晚于报名开始时间")
        return v
    
    @validator("tournament_start")
    def validate_tournament_start(cls, v, values):
        if "registration_end" in values and v <= values["registration_end"]:
            raise ValueError("比赛开始时间必须晚于报名结束时间")
        return v
    
    @validator("tournament_end")
    def validate_tournament_end(cls, v, values):
        if "tournament_start" in values and v <= values["tournament_start"]:
            raise ValueError("比赛结束时间必须晚于比赛开始时间")
        return v


class TournamentCreate(TournamentBase):
    """创建赛事Schema"""
    
    region_id: int = Field(..., description="赛区ID")


class TournamentUpdate(BaseModel):
    """更新赛事Schema"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="赛事名称")
    description: Optional[str] = Field(None, description="赛事描述")
    tournament_type: Optional[TournamentType] = Field(None, description="赛事类型")
    format: Optional[TournamentFormat] = Field(None, description="赛制格式")
    max_participants: Optional[int] = Field(None, gt=0, description="最大参赛名额")
    min_rank: Optional[str] = Field(None, max_length=20, description="最低段位限制")
    max_rank: Optional[str] = Field(None, max_length=20, description="最高段位限制")
    team_size: Optional[int] = Field(None, gt=0, description="战队人数")
    registration_start: Optional[datetime] = Field(None, description="报名开始时间")
    registration_end: Optional[datetime] = Field(None, description="报名结束时间")
    tournament_start: Optional[datetime] = Field(None, description="比赛开始时间")
    tournament_end: Optional[datetime] = Field(None, description="比赛结束时间")
    logo_url: Optional[str] = Field(None, max_length=500, description="赛事Logo URL")
    banner_url: Optional[str] = Field(None, max_length=500, description="赛事横幅URL")
    status: Optional[str] = Field(None, description="赛事状态")


class TournamentResponse(TournamentBase):
    """赛事响应Schema"""
    
    id: UUID = Field(..., description="赛事ID")
    region_id: int = Field(..., description="赛区ID")
    status: str = Field(..., description="赛事状态")
    created_by: int = Field(..., description="创建者ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 统计信息
    registration_count: Optional[int] = Field(None, description="报名人数")
    confirmed_count: Optional[int] = Field(None, description="确认人数")
    team_registration_count: Optional[int] = Field(None, description="参赛队伍数量")
    player_registration_count: Optional[int] = Field(None, description="参赛选手数量")

    # 用户相关信息
    user_registered: Optional[bool] = Field(None, description="当前用户是否已报名")
    user_registration_status: Optional[str] = Field(None, description="当前用户报名状态")

    class Config:
        from_attributes = True


class TournamentListResponse(BaseModel):
    """赛事列表响应Schema"""
    
    tournaments: List[TournamentResponse]
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    has_next: bool = Field(..., description="是否有下一页")


# 报名相关Schema
class RegistrationCreate(BaseModel):
    """创建报名Schema"""

    participant_id: str = Field(..., description="参赛者ID")
    participant_type: str = Field(..., pattern="^(team|player)$", description="参赛者类型")


class AdminRegistrationCreate(RegistrationCreate):
    """管理员创建报名Schema"""
    pass


class TeamInfo(BaseModel):
    """战队信息Schema"""
    id: str = Field(..., description="战队ID")
    name: str = Field(..., description="战队名称")
    logo_url: Optional[str] = Field(None, description="战队Logo")
    current_size: Optional[int] = Field(None, description="当前队伍人数")
    region: Optional[Dict] = Field(None, description="赛区信息")

class PlayerInfo(BaseModel):
    """选手信息Schema"""
    id: str = Field(..., description="选手ID")
    username: str = Field(..., description="用户名")
    player_name: Optional[str] = Field(None, description="选手名")
    current_rank: Optional[str] = Field(None, description="当前段位")
    region: Optional[Dict] = Field(None, description="赛区信息")

class RegistrationResponse(BaseModel):
    """报名响应Schema"""

    id: UUID = Field(..., description="报名ID")
    tournament_id: UUID = Field(..., description="赛事ID")
    participant_id: str = Field(..., description="参赛者ID")
    participant_type: str = Field(..., description="参赛者类型")
    status: str = Field(..., description="报名状态")
    registered_by: int = Field(..., description="报名人ID")
    registered_at: datetime = Field(..., description="报名时间")
    is_admin_registered: bool = Field(..., description="是否管理员报名")

    # 扩展信息（可选）
    participant_name: Optional[str] = Field(None, description="参赛者名称")
    team: Optional[TeamInfo] = Field(None, description="战队详细信息")
    player: Optional[PlayerInfo] = Field(None, description="选手详细信息")

    class Config:
        from_attributes = True


class RegistrationListResponse(BaseModel):
    """报名列表响应Schema"""
    
    registrations: List[RegistrationResponse]
    total: int = Field(..., description="总数")


class RegistrationStatusUpdate(BaseModel):
    """报名状态更新Schema"""

    status: str = Field(..., description="新状态")


class TournamentStatusUpdate(BaseModel):
    """赛事状态更新Schema"""

    status: str = Field(..., description="新状态")


# 比赛相关Schema
class MatchCreate(BaseModel):
    """创建比赛Schema"""
    
    tournament_id: UUID = Field(..., description="赛事ID")
    blue_side_id: UUID = Field(..., description="蓝方ID")
    red_side_id: UUID = Field(..., description="红方ID")
    round_number: int = Field(1, ge=1, description="轮次")
    scheduled_time: Optional[datetime] = Field(None, description="预定时间")


class MatchResponse(BaseModel):
    """比赛响应Schema"""

    id: UUID = Field(..., description="比赛ID")
    tournament_id: UUID = Field(..., description="赛事ID")
    round_number: int = Field(..., description="轮次")
    blue_side_id: str = Field(..., description="蓝方参赛者ID")
    red_side_id: str = Field(..., description="红方参赛者ID")
    status: str = Field(..., description="比赛状态")
    room_id: Optional[UUID] = Field(None, description="房间ID")
    scheduled_time: datetime = Field(..., description="预定时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="结束时间")
    winner_id: Optional[str] = Field(None, description="胜者ID")
    
    # 签到信息
    check_ins: Dict[str, str] = Field(default_factory=dict, description="签到状态")
    
    # 扩展信息（可选）
    blue_side_name: Optional[str] = Field(None, description="蓝方名称")
    red_side_name: Optional[str] = Field(None, description="红方名称")
    tournament_name: Optional[str] = Field(None, description="赛事名称")
    
    class Config:
        from_attributes = True


class MatchListResponse(BaseModel):
    """比赛列表响应Schema"""
    
    matches: List[MatchResponse]
    total: int = Field(..., description="总数")


class MatchStatusUpdate(BaseModel):
    """比赛状态更新Schema"""

    status: str = Field(..., description="新状态")


class MatchUpdate(BaseModel):
    """比赛信息更新Schema"""

    blue_side_id: Optional[str] = Field(None, description="蓝方参赛者ID")
    red_side_id: Optional[str] = Field(None, description="红方参赛者ID")
    scheduled_time: Optional[datetime] = Field(None, description="预定时间")
    round_number: Optional[int] = Field(None, ge=1, description="轮次")

    @validator("blue_side_id")
    def validate_blue_side_id(cls, v):
        if v is not None and not v.strip():
            raise ValueError("蓝方参赛者ID不能为空")
        return v

    @validator("red_side_id")
    def validate_red_side_id(cls, v):
        if v is not None and not v.strip():
            raise ValueError("红方参赛者ID不能为空")
        return v


class MatchResult(BaseModel):
    """比赛结果Schema"""
    
    winner_id: UUID = Field(..., description="胜者ID")


# 签到相关Schema
class CheckInRequest(BaseModel):
    """签到请求Schema"""

    participant_id: str = Field(..., description="参赛者ID")


class CheckInResponse(BaseModel):
    """签到响应Schema"""

    participant_id: str = Field(..., description="参赛者ID")
    status: str = Field(..., description="签到状态")
    checked_in_at: Optional[datetime] = Field(None, description="签到时间")
    
    # 扩展信息
    participant_name: Optional[str] = Field(None, description="参赛者名称")
    
    class Config:
        from_attributes = True


# 查询参数Schema
class TournamentQuery(BaseModel):
    """赛事查询参数"""
    
    region_id: Optional[int] = Field(None, description="赛区ID")
    status: Optional[str] = Field(None, description="赛事状态")
    tournament_type: Optional[TournamentType] = Field(None, description="赛事类型")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页大小")


class MatchQuery(BaseModel):
    """比赛查询参数"""
    
    tournament_id: Optional[UUID] = Field(None, description="赛事ID")
    round_number: Optional[int] = Field(None, ge=1, description="轮次")
    status: Optional[str] = Field(None, description="比赛状态")
    participant_id: Optional[str] = Field(None, description="参赛者ID")


class RegistrationQuery(BaseModel):
    """报名查询参数"""
    
    tournament_id: Optional[UUID] = Field(None, description="赛事ID")
    status: Optional[str] = Field(None, description="报名状态")
    participant_type: Optional[str] = Field(None, pattern="^(team|player)$", description="参赛者类型")


# 统计相关Schema
class TournamentStats(BaseModel):
    """赛事统计Schema"""
    
    total_tournaments: int = Field(..., description="总赛事数")
    active_tournaments: int = Field(..., description="活跃赛事数")
    total_registrations: int = Field(..., description="总报名数")
    upcoming_matches: int = Field(..., description="即将开始的比赛数")


# WebSocket相关Schema
class WebSocketMessage(BaseModel):
    """WebSocket消息Schema"""
    
    type: str = Field(..., description="消息类型")
    data: dict = Field(..., description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")


class CheckInStatusMessage(WebSocketMessage):
    """签到状态消息Schema"""

    type: str = Field("check_in_status", description="消息类型")
    data: CheckInResponse = Field(..., description="签到数据")


# 错误响应Schema
class ErrorResponse(BaseModel):
    """错误响应Schema"""
    
    detail: str = Field(..., description="错误详情")
    code: Optional[str] = Field(None, description="错误代码")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")
