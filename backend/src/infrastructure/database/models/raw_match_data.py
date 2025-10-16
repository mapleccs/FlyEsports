"""
原始比赛数据数据库模型
存储来自LOL客户端的完整比赛数据，支持与BP房间系统关联
"""
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Float,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from src.infrastructure.database.models.base import BaseModel


class RawMatchData(BaseModel):
    """
    原始比赛数据表
    存储每局比赛的完整原始data.json数据
    """

    __tablename__ = "raw_match_data"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)

    # LOL游戏数据标识
    game_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)

    # 系统内部关联
    bp_room_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("bp_rooms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tournament_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tournaments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    match_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    match_game_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("match_games.id", ondelete="SET NULL"), nullable=True
    )

    # 基础比赛信息
    game_mode: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    game_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    game_length: Mapped[int] = mapped_column(Integer, nullable=False)  # 秒
    queue_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_ranked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='false')

    # 比赛结果
    winning_team_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 100 or 200
    is_surrender: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='false')
    is_early_surrender: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='false')

    # 比赛时间
    end_of_game_timestamp: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    played_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # 完整的原始JSON数据存储
    raw_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # 解析状态
    is_parsed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='false', index=True)
    parsing_errors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 数据质量控制
    data_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 客户端版本
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='true', index=True)
    validation_errors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 关系映射
    bp_room: Mapped[Optional["BPRoom"]] = relationship(
        "BPRoom", foreign_keys=[bp_room_id], back_populates="raw_match_data"
    )
    tournament: Mapped[Optional["Tournament"]] = relationship(
        "Tournament", foreign_keys=[tournament_id]
    )
    match_game: Mapped[Optional["MatchGame"]] = relationship(
        "MatchGame", foreign_keys=[match_game_id]
    )

    # 选手表现数据
    player_performances: Mapped[list["RawPlayerPerformance"]] = relationship(
        "RawPlayerPerformance", back_populates="raw_match_data", cascade="all, delete-orphan"
    )

    # 解析任务
    parsing_jobs: Mapped[list["RawDataParsingJob"]] = relationship(
        "RawDataParsingJob", back_populates="raw_match_data", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<RawMatchData(id={self.id}, game_id={self.game_id}, bp_room_id='{self.bp_room_id}')>"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "game_id": self.game_id,
            "bp_room_id": self.bp_room_id,
            "tournament_id": str(self.tournament_id) if self.tournament_id else None,
            "match_id": self.match_id,
            "match_game_id": self.match_game_id,
            "game_mode": self.game_mode,
            "game_type": self.game_type,
            "game_length": self.game_length,
            "queue_type": self.queue_type,
            "is_ranked": self.is_ranked,
            "winning_team_id": self.winning_team_id,
            "is_surrender": self.is_surrender,
            "is_early_surrender": self.is_early_surrender,
            "played_at": self.played_at.isoformat() if self.played_at else None,
            "is_parsed": self.is_parsed,
            "is_valid": self.is_valid,
            "data_version": self.data_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def duration_minutes(self) -> float:
        """获取比赛时长（分钟）"""
        return self.game_length / 60.0 if self.game_length else 0.0

    @property
    def player_count(self) -> int:
        """获取参与选手数量"""
        return len(self.player_performances)

    def get_team_performances(self, team_id: int) -> list["RawPlayerPerformance"]:
        """获取指定队伍的选手表现"""
        return [perf for perf in self.player_performances if perf.team_id == team_id]


class RawPlayerPerformance(BaseModel):
    """
    原始选手表现数据表
    存储每个选手在比赛中的详细表现数据
    """

    __tablename__ = "raw_player_performance"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    raw_match_data_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("raw_match_data.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_profile_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("player_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # 选手识别信息
    puuid: Mapped[Optional[str]] = mapped_column(String(78), nullable=True, index=True)
    summoner_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    summoner_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    riot_id_game_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    riot_id_tag_line: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    current_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 比赛基础信息
    team_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 100 or 200
    champion_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    champion_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    detected_team_position: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    selected_position: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # 胜负记录
    wins: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    losses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    leaves: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 是否离开/挂机
    leaver: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='false')
    was_afk: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='false')

    # ========== 核心战斗数据 ==========
    kills: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    deaths: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    assists: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    largest_killing_spree: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    largest_multi_kill: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    largest_critical_strike: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ========== 经济数据 ==========
    gold_earned: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    minions_killed: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    neutral_minions_killed: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    neutral_minions_killed_enemy_jungle: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    neutral_minions_killed_your_jungle: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ========== 伤害数据 ==========
    total_damage_dealt: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    total_damage_dealt_to_champions: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    total_damage_taken: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    total_damage_self_mitigated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    magic_damage_dealt_to_champions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    physical_damage_dealt_to_champions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    true_damage_dealt_to_champions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    magic_damage_taken: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    physical_damage_taken: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    true_damage_taken: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ========== 建筑和目标伤害 ==========
    total_damage_dealt_to_buildings: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_damage_dealt_to_turrets: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_damage_dealt_to_objectives: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    turrets_killed: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    barracks_killed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ========== 视野数据 ==========
    vision_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    wards_placed: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    wards_killed: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    vision_wards_bought_in_game: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sight_wards_bought_in_game: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ========== 控制和治疗 ==========
    total_time_crowd_control_dealt: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    time_ccing_others: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_heal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_heal_on_teammates: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_damage_shielded_on_teammates: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ========== 时间相关 ==========
    total_time_spent_dead: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ========== 技能使用 ==========
    spell1_casts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    spell2_casts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    spell1_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    spell2_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ========== 目标控制相关 ==========
    team_objective: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    objective_damage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ========== 符文和天赋 ==========
    perk_primary_style: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    perk_sub_style: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    perk0: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    perk1: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    perk2: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    perk3: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    perk4: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    perk5: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ========== 装备信息 (JSON存储) ==========
    items: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    skin_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # ========== 衍生计算字段 ==========
    kda_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    damage_per_minute: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gold_per_minute: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cs_per_minute: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vision_per_minute: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    kill_participation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    damage_efficiency: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ========== 比赛结果 ==========
    win: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    lose: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # ========== 关联状态 ==========
    is_linked_to_profile: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='false', index=True)
    linking_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    manual_verification: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default='false')

    # 关系映射
    raw_match_data: Mapped["RawMatchData"] = relationship(
        "RawMatchData", back_populates="player_performances"
    )
    player_profile: Mapped[Optional["PlayerProfile"]] = relationship(
        "PlayerProfile", foreign_keys=[player_profile_id]
    )

    # 约束
    __table_args__ = (
        UniqueConstraint('raw_match_data_id', 'puuid', name='uq_raw_player_performance_match_puuid'),
    )

    def __repr__(self) -> str:
        return f"<RawPlayerPerformance(id={self.id}, match_id={self.raw_match_data_id}, puuid='{self.puuid}', champion_id={self.champion_id})>"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "raw_match_data_id": self.raw_match_data_id,
            "player_profile_id": self.player_profile_id,
            "puuid": self.puuid,
            "summoner_name": self.summoner_name,
            "riot_id_game_name": self.riot_id_game_name,
            "riot_id_tag_line": self.riot_id_tag_line,
            "team_id": self.team_id,
            "champion_id": self.champion_id,
            "champion_name": self.champion_name,
            "detected_team_position": self.detected_team_position,
            "kills": self.kills,
            "deaths": self.deaths,
            "assists": self.assists,
            "gold_earned": self.gold_earned,
            "minions_killed": self.minions_killed,
            "total_damage_dealt_to_champions": self.total_damage_dealt_to_champions,
            "vision_score": self.vision_score,
            "kda_ratio": self.kda_ratio,
            "damage_per_minute": self.damage_per_minute,
            "gold_per_minute": self.gold_per_minute,
            "win": self.win,
            "is_linked_to_profile": self.is_linked_to_profile,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def calculate_derived_stats(self, match_duration_seconds: int):
        """计算衍生统计数据"""
        if match_duration_seconds > 0:
            duration_minutes = match_duration_seconds / 60.0

            # 计算KDA
            self.kda_ratio = (self.kills + self.assists) / max(self.deaths, 1)

            # 计算每分钟数据
            self.damage_per_minute = self.total_damage_dealt_to_champions / duration_minutes
            self.gold_per_minute = self.gold_earned / duration_minutes
            self.cs_per_minute = (self.minions_killed + self.neutral_minions_killed) / duration_minutes
            self.vision_per_minute = self.vision_score / duration_minutes

            # 计算伤害效率
            if self.total_damage_taken > 0:
                self.damage_efficiency = self.total_damage_dealt_to_champions / self.total_damage_taken
            else:
                self.damage_efficiency = float('inf') if self.total_damage_dealt_to_champions > 0 else 0

    @property
    def position_display(self) -> str:
        """获取位置显示名称"""
        position_map = {
            "TOP": "上单",
            "JUNGLE": "打野",
            "MIDDLE": "中单",
            "BOTTOM": "下路",
            "UTILITY": "辅助"
        }
        return position_map.get(self.detected_team_position, self.detected_team_position or "未知")


class RawDataParsingJob(BaseModel):
    """
    数据解析任务表
    支持异步处理原始比赛数据
    """

    __tablename__ = "raw_data_parsing_jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    raw_match_data_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("raw_match_data.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 任务信息
    job_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # parse, link_players, calculate_ratings
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)    # pending, processing, completed, failed
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default='5', index=True)

    # 执行参数
    job_params: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # 执行信息
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, server_default='3')

    # 处理结果
    result_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # 关系映射
    raw_match_data: Mapped["RawMatchData"] = relationship(
        "RawMatchData", back_populates="parsing_jobs"
    )

    def __repr__(self) -> str:
        return f"<RawDataParsingJob(id={self.id}, type='{self.job_type}', status='{self.status}')>"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "raw_match_data_id": self.raw_match_data_id,
            "job_type": self.job_type,
            "status": self.status,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def is_running(self) -> bool:
        """检查任务是否正在运行"""
        return self.status == "processing"

    @property
    def can_retry(self) -> bool:
        """检查任务是否可以重试"""
        return self.status == "failed" and self.retry_count < self.max_retries

    @property
    def duration(self) -> Optional[float]:
        """获取任务执行时长（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None