"""
原始比赛数据领域实体
定义原始比赛数据的业务逻辑和状态管理
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from ..base import Entity
from ..value_objects.match_performance import MatchPerformance


@dataclass
class RawMatchDataEntity(Entity):
    """原始比赛数据领域实体"""

    id: int = 0
    game_id: int = 0
    bp_room_id: Optional[str] = None
    tournament_id: Optional[UUID] = None
    match_id: Optional[str] = None
    match_game_id: Optional[int] = None

    # 比赛基础信息
    game_mode: Optional[str] = None
    game_type: Optional[str] = None
    game_length: int = 0
    queue_type: Optional[str] = None
    is_ranked: bool = False

    # 比赛结果
    winning_team_id: Optional[int] = None
    is_surrender: bool = False
    is_early_surrender: bool = False

    # 比赛时间
    end_of_game_timestamp: Optional[int] = None
    played_at: Optional[datetime] = None

    # 原始数据
    raw_data: Dict[str, Any] = field(default_factory=dict)

    # 解析状态
    is_parsed: bool = False
    parsing_errors: Optional[str] = None
    parsed_at: Optional[datetime] = None

    # 数据质量
    data_version: Optional[str] = None
    is_valid: bool = True
    validation_errors: Optional[str] = None

    # 选手表现数据
    player_performances: List["RawPlayerPerformanceEntity"] = field(default_factory=list)

    # 解析任务
    parsing_jobs: List["RawDataParsingJobEntity"] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """初始化后处理"""
        if not self.played_at and self.end_of_game_timestamp:
            self.played_at = datetime.fromtimestamp(self.end_of_game_timestamp / 1000)

    @classmethod
    def create_from_raw_data(
        cls,
        game_id: int,
        raw_data: Dict[str, Any],
        bp_room_id: Optional[str] = None,
        tournament_id: Optional[UUID] = None
    ) -> "RawMatchDataEntity":
        """从原始数据创建实体"""

        # 提取基础信息
        game_length = raw_data.get('gameLength', 0)
        end_timestamp = raw_data.get('endOfGameTimestamp', 0)

        # 判断获胜队伍
        winning_team_id = None
        teams = raw_data.get('teams', [])
        for team in teams:
            if team.get('isWinningTeam', False):
                winning_team_id = team.get('teamId')
                break

        entity = cls(
            game_id=game_id,
            bp_room_id=bp_room_id,
            tournament_id=tournament_id,
            game_mode=raw_data.get('gameMode'),
            game_type=raw_data.get('gameType'),
            game_length=game_length,
            queue_type=raw_data.get('queueType'),
            is_ranked=raw_data.get('ranked', False),
            winning_team_id=winning_team_id,
            is_surrender=raw_data.get('gameEndedInSurrender', False),
            is_early_surrender=raw_data.get('gameEndedInEarlySurrender', False),
            end_of_game_timestamp=end_timestamp,
            raw_data=raw_data,
            is_valid=True,
        )

        # 创建选手表现数据
        entity._extract_player_performances()

        return entity

    def _extract_player_performances(self):
        """从原始数据中提取选手表现"""
        teams = self.raw_data.get('teams', [])

        for team in teams:
            team_id = team.get('teamId')
            players = team.get('players', [])

            for player_data in players:
                performance = RawPlayerPerformanceEntity.create_from_player_data(
                    player_data, team_id, self.game_length
                )
                self.player_performances.append(performance)

    def validate_data(self) -> bool:
        """验证数据完整性"""
        errors = []

        # 检查基础数据
        if not self.game_id:
            errors.append("Missing game_id")

        if not self.raw_data:
            errors.append("Missing raw_data")

        if self.game_length <= 0:
            errors.append("Invalid game_length")

        # 检查选手数据
        if len(self.player_performances) != 10:
            errors.append(f"Invalid player count: {len(self.player_performances)}")

        # 检查队伍平衡
        team_100_count = sum(1 for p in self.player_performances if p.team_id == 100)
        team_200_count = sum(1 for p in self.player_performances if p.team_id == 200)

        if team_100_count != 5 or team_200_count != 5:
            errors.append(f"Invalid team balance: {team_100_count} vs {team_200_count}")

        if errors:
            self.is_valid = False
            self.validation_errors = "; ".join(errors)
        else:
            self.is_valid = True
            self.validation_errors = None

        return self.is_valid

    def mark_as_parsed(self):
        """标记为已解析"""
        self.is_parsed = True
        self.parsed_at = datetime.utcnow()
        self.parsing_errors = None

    def mark_parsing_failed(self, error_message: str):
        """标记解析失败"""
        self.is_parsed = False
        self.parsing_errors = error_message
        self.parsed_at = None

    def get_team_performances(self, team_id: int) -> List["RawPlayerPerformanceEntity"]:
        """获取指定队伍的选手表现"""
        return [p for p in self.player_performances if p.team_id == team_id]

    def get_winner_team_performances(self) -> List["RawPlayerPerformanceEntity"]:
        """获取获胜队伍的选手表现"""
        if self.winning_team_id:
            return self.get_team_performances(self.winning_team_id)
        return []

    def get_loser_team_performances(self) -> List["RawPlayerPerformanceEntity"]:
        """获取失败队伍的选手表现"""
        if self.winning_team_id:
            loser_team_id = 200 if self.winning_team_id == 100 else 100
            return self.get_team_performances(loser_team_id)
        return []

    @property
    def duration_minutes(self) -> float:
        """获取比赛时长（分钟）"""
        return self.game_length / 60.0 if self.game_length else 0.0

    @property
    def total_kills(self) -> int:
        """获取总击杀数"""
        return sum(p.kills for p in self.player_performances)

    @property
    def match_summary(self) -> Dict[str, Any]:
        """获取比赛摘要"""
        team_100_kills = sum(p.kills for p in self.get_team_performances(100))
        team_200_kills = sum(p.kills for p in self.get_team_performances(200))

        return {
            "game_id": self.game_id,
            "duration_minutes": self.duration_minutes,
            "winning_team_id": self.winning_team_id,
            "team_scores": {
                "team_100": team_100_kills,
                "team_200": team_200_kills
            },
            "is_surrender": self.is_surrender,
            "total_kills": self.total_kills,
            "player_count": len(self.player_performances)
        }


@dataclass
class RawPlayerPerformanceEntity(Entity):
    """原始选手表现领域实体"""

    id: int = 0
    raw_match_data_id: int = 0
    player_profile_id: Optional[int] = None

    # 选手识别信息
    puuid: Optional[str] = None
    summoner_id: Optional[int] = None
    summoner_name: Optional[str] = None
    riot_id_game_name: Optional[str] = None
    riot_id_tag_line: Optional[str] = None
    current_level: Optional[int] = None

    # 比赛基础信息
    team_id: int = 0
    champion_id: int = 0
    champion_name: Optional[str] = None
    detected_team_position: Optional[str] = None
    selected_position: Optional[str] = None

    # 胜负记录
    wins: Optional[int] = None
    losses: Optional[int] = None
    leaves: Optional[int] = None

    # 状态标记
    leaver: bool = False
    was_afk: bool = False

    # 核心战斗数据
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    largest_killing_spree: Optional[int] = None
    largest_multi_kill: Optional[int] = None
    largest_critical_strike: Optional[int] = None

    # 经济数据
    gold_earned: int = 0
    minions_killed: int = 0
    neutral_minions_killed: int = 0
    neutral_minions_killed_enemy_jungle: Optional[int] = None
    neutral_minions_killed_your_jungle: Optional[int] = None

    # 伤害数据
    total_damage_dealt: int = 0
    total_damage_dealt_to_champions: int = 0
    total_damage_taken: int = 0
    total_damage_self_mitigated: Optional[int] = None
    magic_damage_dealt_to_champions: Optional[int] = None
    physical_damage_dealt_to_champions: Optional[int] = None
    true_damage_dealt_to_champions: Optional[int] = None
    magic_damage_taken: Optional[int] = None
    physical_damage_taken: Optional[int] = None
    true_damage_taken: Optional[int] = None

    # 建筑和目标伤害
    total_damage_dealt_to_buildings: Optional[int] = None
    total_damage_dealt_to_turrets: Optional[int] = None
    total_damage_dealt_to_objectives: Optional[int] = None
    turrets_killed: int = 0
    barracks_killed: Optional[int] = None

    # 视野数据
    vision_score: int = 0
    wards_placed: int = 0
    wards_killed: int = 0
    vision_wards_bought_in_game: Optional[int] = None
    sight_wards_bought_in_game: Optional[int] = None

    # 控制和治疗
    total_time_crowd_control_dealt: Optional[int] = None
    time_ccing_others: Optional[int] = None
    total_heal: Optional[int] = None
    total_heal_on_teammates: Optional[int] = None
    total_damage_shielded_on_teammates: Optional[int] = None

    # 时间相关
    total_time_spent_dead: Optional[int] = None
    level: Optional[int] = None

    # 技能使用
    spell1_casts: Optional[int] = None
    spell2_casts: Optional[int] = None
    spell1_id: Optional[int] = None
    spell2_id: Optional[int] = None

    # 目标控制
    team_objective: Optional[int] = None
    objective_damage: Optional[int] = None

    # 符文和天赋
    perk_primary_style: Optional[int] = None
    perk_sub_style: Optional[int] = None
    perk0: Optional[int] = None
    perk1: Optional[int] = None
    perk2: Optional[int] = None
    perk3: Optional[int] = None
    perk4: Optional[int] = None
    perk5: Optional[int] = None

    # 装备和皮肤信息
    items: Optional[Dict[str, Any]] = None
    skin_info: Optional[Dict[str, Any]] = None

    # 衍生统计
    kda_ratio: Optional[float] = None
    damage_per_minute: Optional[float] = None
    gold_per_minute: Optional[float] = None
    cs_per_minute: Optional[float] = None
    vision_per_minute: Optional[float] = None
    kill_participation: Optional[float] = None
    damage_efficiency: Optional[float] = None

    # 比赛结果
    win: Optional[bool] = None
    lose: Optional[bool] = None

    # 关联状态
    is_linked_to_profile: bool = False
    linking_confidence: Optional[float] = None
    manual_verification: bool = False

    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create_from_player_data(
        cls,
        player_data: Dict[str, Any],
        team_id: int,
        match_duration_seconds: int
    ) -> "RawPlayerPerformanceEntity":
        """从选手数据创建实体"""

        stats = player_data.get('stats', {})

        # 创建实体
        entity = cls(
            team_id=team_id,
            puuid=player_data.get('puuid'),
            summoner_id=player_data.get('summonerId'),
            summoner_name=player_data.get('summonerName'),
            riot_id_game_name=player_data.get('riotIdGameName'),
            riot_id_tag_line=player_data.get('riotIdTagLine'),
            current_level=player_data.get('currentLevel'),
            champion_id=player_data.get('championId', 0),
            champion_name=player_data.get('championName'),
            detected_team_position=player_data.get('detectedTeamPosition'),
            selected_position=player_data.get('selectedPosition'),
            wins=player_data.get('wins'),
            losses=player_data.get('losses'),
            leaves=player_data.get('leaves'),
            leaver=player_data.get('leaver', False),
            was_afk=stats.get('WAS_AFK', 0) > 0,

            # 核心战斗数据
            kills=stats.get('CHAMPIONS_KILLED', 0),
            deaths=stats.get('NUM_DEATHS', 0),
            assists=stats.get('ASSISTS', 0),
            largest_killing_spree=stats.get('LARGEST_KILLING_SPREE'),
            largest_multi_kill=stats.get('LARGEST_MULTI_KILL'),
            largest_critical_strike=stats.get('LARGEST_CRITICAL_STRIKE'),

            # 经济数据
            gold_earned=stats.get('GOLD_EARNED', 0),
            minions_killed=stats.get('MINIONS_KILLED', 0),
            neutral_minions_killed=stats.get('NEUTRAL_MINIONS_KILLED', 0),
            neutral_minions_killed_enemy_jungle=stats.get('NEUTRAL_MINIONS_KILLED_ENEMY_JUNGLE'),
            neutral_minions_killed_your_jungle=stats.get('NEUTRAL_MINIONS_KILLED_YOUR_JUNGLE'),

            # 伤害数据
            total_damage_dealt=stats.get('TOTAL_DAMAGE_DEALT', 0),
            total_damage_dealt_to_champions=stats.get('TOTAL_DAMAGE_DEALT_TO_CHAMPIONS', 0),
            total_damage_taken=stats.get('TOTAL_DAMAGE_TAKEN', 0),
            total_damage_self_mitigated=stats.get('TOTAL_DAMAGE_SELF_MITIGATED'),
            magic_damage_dealt_to_champions=stats.get('MAGIC_DAMAGE_DEALT_TO_CHAMPIONS'),
            physical_damage_dealt_to_champions=stats.get('PHYSICAL_DAMAGE_DEALT_TO_CHAMPIONS'),
            true_damage_dealt_to_champions=stats.get('TRUE_DAMAGE_DEALT_TO_CHAMPIONS'),
            magic_damage_taken=stats.get('MAGIC_DAMAGE_TAKEN'),
            physical_damage_taken=stats.get('PHYSICAL_DAMAGE_TAKEN'),
            true_damage_taken=stats.get('TRUE_DAMAGE_TAKEN'),

            # 建筑和目标
            total_damage_dealt_to_buildings=stats.get('TOTAL_DAMAGE_DEALT_TO_BUILDINGS'),
            total_damage_dealt_to_turrets=stats.get('TOTAL_DAMAGE_DEALT_TO_TURRETS'),
            total_damage_dealt_to_objectives=stats.get('TOTAL_DAMAGE_DEALT_TO_OBJECTIVES'),
            turrets_killed=stats.get('TURRETS_KILLED', 0),
            barracks_killed=stats.get('BARRACKS_KILLED'),

            # 视野数据
            vision_score=stats.get('VISION_SCORE', 0),
            wards_placed=stats.get('WARD_PLACED', 0),
            wards_killed=stats.get('WARD_KILLED', 0),
            vision_wards_bought_in_game=stats.get('VISION_WARDS_BOUGHT_IN_GAME'),
            sight_wards_bought_in_game=stats.get('SIGHT_WARDS_BOUGHT_IN_GAME'),

            # 其他数据
            total_time_crowd_control_dealt=stats.get('TOTAL_TIME_CROWD_CONTROL_DEALT'),
            time_ccing_others=stats.get('TIME_CCING_OTHERS'),
            total_heal=stats.get('TOTAL_HEAL'),
            total_heal_on_teammates=stats.get('TOTAL_HEAL_ON_TEAMMATES'),
            total_damage_shielded_on_teammates=stats.get('TOTAL_DAMAGE_SHIELDED_ON_TEAMMATES'),
            total_time_spent_dead=stats.get('TOTAL_TIME_SPENT_DEAD'),
            level=stats.get('LEVEL'),
            spell1_casts=stats.get('SPELL1_CAST'),
            spell2_casts=stats.get('SPELL2_CAST'),

            # 比赛结果
            win=stats.get('WIN') == 1,
            lose=stats.get('LOSE') == 1,
        )

        # 计算衍生统计数据
        entity.calculate_derived_stats(match_duration_seconds)

        # 提取装备信息
        entity.items = {
            "items": player_data.get('items', []),
            "spell1Id": player_data.get('spell1Id'),
            "spell2Id": player_data.get('spell2Id'),
        }

        # 提取皮肤信息
        entity.skin_info = {
            "skinSplashPath": player_data.get('skinSplashPath'),
            "skinTilePath": player_data.get('skinTilePath'),
            "skinEmblemPaths": player_data.get('skinEmblemPaths', [])
        }

        return entity

    def calculate_derived_stats(self, match_duration_seconds: int):
        """计算衍生统计数据"""
        if match_duration_seconds > 0:
            duration_minutes = match_duration_seconds / 60.0

            # KDA计算
            self.kda_ratio = (self.kills + self.assists) / max(self.deaths, 1)

            # 每分钟数据计算
            self.damage_per_minute = self.total_damage_dealt_to_champions / duration_minutes
            self.gold_per_minute = self.gold_earned / duration_minutes
            self.cs_per_minute = (self.minions_killed + self.neutral_minions_killed) / duration_minutes
            self.vision_per_minute = self.vision_score / duration_minutes

            # 伤害效率计算
            if self.total_damage_taken > 0:
                self.damage_efficiency = self.total_damage_dealt_to_champions / self.total_damage_taken
            else:
                self.damage_efficiency = float('inf') if self.total_damage_dealt_to_champions > 0 else 0

    def to_match_performance(self) -> MatchPerformance:
        """转换为MatchPerformance值对象"""
        return MatchPerformance(
            player_profile_id=str(self.player_profile_id) if self.player_profile_id else "",
            match_id=str(self.raw_match_data_id),
            position=self.detected_team_position or "UNKNOWN",
            match_duration=0,  # 需要从关联的比赛数据获取
            kills=self.kills,
            deaths=self.deaths,
            assists=self.assists,
            damage_dealt=self.total_damage_dealt,
            damage_taken=self.total_damage_taken,
            gold_earned=self.gold_earned,
            cs_score=self.minions_killed + self.neutral_minions_killed,
            vision_score=self.vision_score,
            wards_placed=self.wards_placed,
            wards_cleared=self.wards_killed,
            dragon_kills=0,  # 需要从团队数据中提取
            baron_kills=0,   # 需要从团队数据中提取
            tower_kills=self.turrets_killed,
            objective_damage=self.total_damage_dealt_to_objectives or 0,
            teamfight_participation=0.0,  # 需要计算
            teamfight_damage_share=0.0,   # 需要计算
            teamfight_kills=0,            # 需要从详细数据中提取
            teamfight_deaths=0,           # 需要从详细数据中提取
            match_result=1.0 if self.win else 0.0,
            played_at=self.created_at
        )

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

    @property
    def performance_summary(self) -> Dict[str, Any]:
        """获取表现摘要"""
        return {
            "summoner_name": self.summoner_name,
            "champion_name": self.champion_name,
            "position": self.position_display,
            "kda": f"{self.kills}/{self.deaths}/{self.assists}",
            "kda_ratio": round(self.kda_ratio or 0, 2),
            "gold_earned": self.gold_earned,
            "cs_score": self.minions_killed + self.neutral_minions_killed,
            "damage_to_champions": self.total_damage_dealt_to_champions,
            "vision_score": self.vision_score,
            "result": "胜利" if self.win else "失败"
        }


@dataclass
class RawDataParsingJobEntity(Entity):
    """数据解析任务领域实体"""

    id: int = 0
    raw_match_data_id: int = 0

    # 任务信息
    job_type: str = ""  # parse, link_players, calculate_ratings
    status: str = "pending"  # pending, processing, completed, failed
    priority: int = 5

    # 执行参数和结果
    job_params: Optional[Dict[str, Any]] = None
    result_data: Optional[Dict[str, Any]] = None

    # 执行状态
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create_parse_job(cls, raw_match_data_id: int, priority: int = 5) -> "RawDataParsingJobEntity":
        """创建数据解析任务"""
        return cls(
            raw_match_data_id=raw_match_data_id,
            job_type="parse",
            status="pending",
            priority=priority
        )

    @classmethod
    def create_link_players_job(cls, raw_match_data_id: int, priority: int = 3) -> "RawDataParsingJobEntity":
        """创建选手关联任务"""
        return cls(
            raw_match_data_id=raw_match_data_id,
            job_type="link_players",
            status="pending",
            priority=priority
        )

    @classmethod
    def create_calculate_ratings_job(cls, raw_match_data_id: int, priority: int = 1) -> "RawDataParsingJobEntity":
        """创建评分计算任务"""
        return cls(
            raw_match_data_id=raw_match_data_id,
            job_type="calculate_ratings",
            status="pending",
            priority=priority
        )

    def start_processing(self):
        """开始处理任务"""
        self.status = "processing"
        self.started_at = datetime.utcnow()
        self.error_message = None

    def complete_successfully(self, result_data: Optional[Dict[str, Any]] = None):
        """成功完成任务"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.result_data = result_data
        self.error_message = None

    def fail_with_error(self, error_message: str):
        """任务失败"""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.retry_count += 1

    def reset_for_retry(self):
        """重置任务以便重试"""
        if self.can_retry:
            self.status = "pending"
            self.started_at = None
            self.completed_at = None
            self.error_message = None

    @property
    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.status == "failed" and self.retry_count < self.max_retries

    @property
    def is_running(self) -> bool:
        """检查任务是否正在运行"""
        return self.status == "processing"

    @property
    def duration_seconds(self) -> Optional[float]:
        """获取任务执行时长"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None