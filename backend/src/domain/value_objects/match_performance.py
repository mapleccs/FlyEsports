"""
Match performance value object for player rating calculation.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from ..base import ValueObject, BusinessRuleViolationError


@dataclass(frozen=True)
class MatchPerformance(ValueObject):
    """
    Match performance value object representing a player's performance in a single match.

    Contains all the raw data needed for rating calculation including basic stats,
    objective control, vision, and team fight metrics.
    """

    # 基础标识信息
    player_profile_id: str
    match_id: str
    position: str  # 位置：TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY
    match_duration: int  # 比赛时长(秒)

    # 基础KDA数据
    kills: int
    deaths: int
    assists: int

    # 伤害数据
    damage_dealt: int
    damage_taken: int

    # 经济数据
    gold_earned: int
    cs_score: int  # 补兵数

    # 视野数据
    vision_score: int
    wards_placed: int
    wards_cleared: int

    # 目标控制数据
    dragon_kills: int
    baron_kills: int
    tower_kills: int
    objective_damage: int

    # 团战数据
    teamfight_participation: float  # 团战参与率 (0.0-1.0)
    teamfight_damage_share: float   # 团战伤害占比 (0.0-1.0)
    teamfight_kills: int
    teamfight_deaths: int

    # 比赛结果
    match_result: str  # "win", "loss", "draw"

    # 时间信息
    played_at: datetime

    # 衍生指标（可选，会自动计算）
    dpm: Optional[float] = None      # 每分钟伤害
    gpm: Optional[float] = None      # 每分钟金币
    kda: Optional[float] = None      # KDA值
    kill_participation: Optional[float] = None  # 击杀参与率

    def __post_init__(self) -> None:
        """Validate performance data after initialization."""

        # 验证基础数据
        if self.match_duration <= 0:
            raise BusinessRuleViolationError("Match duration must be positive")

        if any(stat < 0 for stat in [self.kills, self.deaths, self.assists]):
            raise BusinessRuleViolationError("KDA stats cannot be negative")

        if any(stat < 0 for stat in [self.damage_dealt, self.damage_taken]):
            raise BusinessRuleViolationError("Damage stats cannot be negative")

        if any(stat < 0 for stat in [self.gold_earned, self.cs_score]):
            raise BusinessRuleViolationError("Economic stats cannot be negative")

        if any(stat < 0 for stat in [self.vision_score, self.wards_placed, self.wards_cleared]):
            raise BusinessRuleViolationError("Vision stats cannot be negative")

        if any(stat < 0 for stat in [self.dragon_kills, self.baron_kills, self.tower_kills, self.objective_damage]):
            raise BusinessRuleViolationError("Objective stats cannot be negative")

        if any(stat < 0 for stat in [self.teamfight_kills, self.teamfight_deaths]):
            raise BusinessRuleViolationError("Teamfight stats cannot be negative")

        # 验证百分比数据范围
        if not (0.0 <= self.teamfight_participation <= 1.0):
            raise BusinessRuleViolationError("Teamfight participation must be between 0.0 and 1.0")

        if not (0.0 <= self.teamfight_damage_share <= 1.0):
            raise BusinessRuleViolationError("Teamfight damage share must be between 0.0 and 1.0")

        valid_results = {'win', 'loss', 'draw'}
        if self.match_result not in valid_results:
            raise BusinessRuleViolationError(f"Invalid match result: {self.match_result}")

        # 验证位置
        valid_positions = {'TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY'}
        if self.position not in valid_positions:
            raise BusinessRuleViolationError(f"Invalid position: {self.position}")

        # 自动计算衍生指标
        object.__setattr__(self, 'dpm', self.calculate_dpm())
        object.__setattr__(self, 'gpm', self.calculate_gpm())
        object.__setattr__(self, 'kda', self.calculate_kda())

    def calculate_dpm(self) -> float:
        """Calculate damage per minute."""
        match_minutes = self.match_duration / 60.0
        return self.damage_dealt / match_minutes if match_minutes > 0 else 0.0

    def calculate_gpm(self) -> float:
        """Calculate gold per minute."""
        match_minutes = self.match_duration / 60.0
        return self.gold_earned / match_minutes if match_minutes > 0 else 0.0

    def calculate_kda(self) -> float:
        """Calculate KDA ratio."""
        if self.deaths == 0:
            # 零死亡特殊处理：给予奖励倍数
            return (self.kills + self.assists) * 1.2
        return (self.kills + self.assists) / self.deaths

    def calculate_cspm(self) -> float:
        """Calculate CS per minute."""
        match_minutes = self.match_duration / 60.0
        return self.cs_score / match_minutes if match_minutes > 0 else 0.0

    def calculate_vision_per_minute(self) -> float:
        """Calculate vision score per minute."""
        match_minutes = self.match_duration / 60.0
        return self.vision_score / match_minutes if match_minutes > 0 else 0.0

    def calculate_wards_placed_per_minute(self) -> float:
        """Calculate wards placed per minute."""
        match_minutes = self.match_duration / 60.0
        return self.wards_placed / match_minutes if match_minutes > 0 else 0.0

    def calculate_damage_efficiency(self) -> float:
        """Calculate damage efficiency (damage dealt / damage taken)."""
        if self.damage_taken == 0:
            return float('inf') if self.damage_dealt > 0 else 0.0
        return self.damage_dealt / self.damage_taken

    def calculate_gold_per_cs(self) -> float:
        """Calculate gold efficiency per CS."""
        if self.cs_score == 0:
            return 0.0
        return self.gold_earned / self.cs_score

    def get_teamfight_kd_ratio(self) -> float:
        """Calculate KD ratio in team fights."""
        if self.teamfight_deaths == 0:
            return float(self.teamfight_kills) if self.teamfight_kills > 0 else 0.0
        return self.teamfight_kills / self.teamfight_deaths

    @property
    def is_excellent_performance(self) -> bool:
        """Check if this is considered an excellent performance."""
        return (
            self.kda >= 3.0 and
            self.match_result >= 0.5 and
            self.teamfight_participation >= 0.7
        )

    @property
    def is_poor_performance(self) -> bool:
        """Check if this is considered a poor performance."""
        return (
            self.kda <= 1.0 and
            self.match_result <= 0.5 and
            self.teamfight_participation <= 0.5
        )

    def __str__(self) -> str:
        """String representation of the performance."""
        return (
            f"Performance({self.player_profile_id}, "
            f"KDA={self.kda:.2f}, "
            f"DPM={self.dpm:.0f}, "
            f"GPM={self.gpm:.0f}, "
            f"Result={'W' if self.match_result == 1.0 else 'L' if self.match_result == 0.0 else 'D'})"
        )