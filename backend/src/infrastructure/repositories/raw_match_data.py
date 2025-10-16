"""
原始比赛数据仓储实现
基于SQLAlchemy的原始比赛数据仓储实现
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.raw_match_data import RawMatchDataEntity, RawPlayerPerformanceEntity, RawDataParsingJobEntity
from src.domain.repositories.raw_match_data import (
    RawMatchDataRepository,
    RawPlayerPerformanceRepository,
    RawDataParsingJobRepository
)
from src.infrastructure.database.models.raw_match_data import (
    RawMatchData,
    RawPlayerPerformance,
    RawDataParsingJob
)


class SQLAlchemyRawMatchDataRepository(RawMatchDataRepository):
    """基于SQLAlchemy的原始比赛数据仓储实现"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, raw_match_data: RawMatchDataEntity) -> RawMatchDataEntity:
        """保存或更新原始比赛数据"""
        if raw_match_data.id:
            # 更新现有记录
            model = await self.session.get(RawMatchData, raw_match_data.id)
            if model:
                model = self._entity_to_model(raw_match_data, model)
            else:
                raise ValueError(f"RawMatchData with id {raw_match_data.id} not found")
        else:
            # 创建新记录
            model = self._entity_to_model(raw_match_data)
            self.session.add(model)

        await self.session.flush()
        await self.session.refresh(model)

        # 保存选手表现数据
        if raw_match_data.player_performances:
            for performance in raw_match_data.player_performances:
                performance.raw_match_data_id = model.id
                perf_model = self._performance_entity_to_model(performance)
                self.session.add(perf_model)

        # 保存解析任务
        if raw_match_data.parsing_jobs:
            for job in raw_match_data.parsing_jobs:
                job.raw_match_data_id = model.id
                job_model = self._job_entity_to_model(job)
                self.session.add(job_model)

        await self.session.commit()
        return self._model_to_entity(model)

    async def find_by_id(self, raw_match_data_id: int) -> Optional[RawMatchDataEntity]:
        """根据ID查找原始比赛数据"""
        stmt = self.session.query(RawMatchData).options(
            selectinload(RawMatchData.player_performances),
            selectinload(RawMatchData.parsing_jobs)
        ).filter(RawMatchData.id == raw_match_data_id)

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def find_by_game_id(self, game_id: int) -> Optional[RawMatchDataEntity]:
        """根据游戏ID查找原始比赛数据"""
        stmt = self.session.query(RawMatchData).options(
            selectinload(RawMatchData.player_performances),
            selectinload(RawMatchData.parsing_jobs)
        ).filter(RawMatchData.game_id == game_id)

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def find_by_bp_room_id(self, bp_room_id: str) -> List[RawMatchDataEntity]:
        """根据BP房间ID查找原始比赛数据"""
        stmt = self.session.query(RawMatchData).options(
            selectinload(RawMatchData.player_performances),
            selectinload(RawMatchData.parsing_jobs)
        ).filter(RawMatchData.bp_room_id == bp_room_id).order_by(desc(RawMatchData.created_at))

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_by_tournament_id(
        self,
        tournament_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[RawMatchDataEntity]:
        """根据赛事ID查找原始比赛数据"""
        stmt = self.session.query(RawMatchData).options(
            selectinload(RawMatchData.player_performances),
            selectinload(RawMatchData.parsing_jobs)
        ).filter(RawMatchData.tournament_id == tournament_id).order_by(desc(RawMatchData.played_at))

        if limit:
            stmt = stmt.limit(limit)
        if offset:
            stmt = stmt.offset(offset)

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_unparsed(self, limit: Optional[int] = None) -> List[RawMatchDataEntity]:
        """查找未解析的原始比赛数据"""
        stmt = self.session.query(RawMatchData).filter(
            RawMatchData.is_parsed == False,
            RawMatchData.is_valid == True
        ).order_by(asc(RawMatchData.created_at))

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def find_invalid(self, limit: Optional[int] = None) -> List[RawMatchDataEntity]:
        """查找无效的原始比赛数据"""
        stmt = self.session.query(RawMatchData).filter(
            RawMatchData.is_valid == False
        ).order_by(desc(RawMatchData.created_at))

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def count_by_tournament(self, tournament_id: UUID) -> int:
        """统计赛事的比赛数据数量"""
        stmt = self.session.query(func.count(RawMatchData.id)).filter(
            RawMatchData.tournament_id == tournament_id
        )

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_date_range(self, start_date: datetime, end_date: datetime) -> int:
        """统计日期范围内的比赛数据数量"""
        stmt = self.session.query(func.count(RawMatchData.id)).filter(
            RawMatchData.played_at.between(start_date, end_date)
        )

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists_by_game_id(self, game_id: int) -> bool:
        """检查游戏ID是否已存在"""
        stmt = self.session.query(func.count(RawMatchData.id)).filter(
            RawMatchData.game_id == game_id
        )

        result = await self.session.execute(stmt)
        count = result.scalar() or 0
        return count > 0

    async def delete(self, raw_match_data: RawMatchDataEntity) -> None:
        """删除原始比赛数据"""
        if raw_match_data.id:
            model = await self.session.get(RawMatchData, raw_match_data.id)
            if model:
                await self.session.delete(model)
                await self.session.commit()

    def _entity_to_model(
        self,
        entity: RawMatchDataEntity,
        model: Optional[RawMatchData] = None
    ) -> RawMatchData:
        """实体转换为模型"""
        if model is None:
            model = RawMatchData()

        model.game_id = entity.game_id
        model.bp_room_id = entity.bp_room_id
        model.tournament_id = entity.tournament_id
        model.match_id = entity.match_id
        model.match_game_id = entity.match_game_id
        model.game_mode = entity.game_mode
        model.game_type = entity.game_type
        model.game_length = entity.game_length
        model.queue_type = entity.queue_type
        model.is_ranked = entity.is_ranked
        model.winning_team_id = entity.winning_team_id
        model.is_surrender = entity.is_surrender
        model.is_early_surrender = entity.is_early_surrender
        model.end_of_game_timestamp = entity.end_of_game_timestamp
        model.played_at = entity.played_at
        model.raw_data = entity.raw_data
        model.is_parsed = entity.is_parsed
        model.parsing_errors = entity.parsing_errors
        model.parsed_at = entity.parsed_at
        model.data_version = entity.data_version
        model.is_valid = entity.is_valid
        model.validation_errors = entity.validation_errors

        return model

    def _model_to_entity(self, model: RawMatchData) -> RawMatchDataEntity:
        """模型转换为实体"""
        entity = RawMatchDataEntity(
            id=model.id,
            game_id=model.game_id,
            bp_room_id=model.bp_room_id,
            tournament_id=model.tournament_id,
            match_id=model.match_id,
            match_game_id=model.match_game_id,
            game_mode=model.game_mode,
            game_type=model.game_type,
            game_length=model.game_length,
            queue_type=model.queue_type,
            is_ranked=model.is_ranked,
            winning_team_id=model.winning_team_id,
            is_surrender=model.is_surrender,
            is_early_surrender=model.is_early_surrender,
            end_of_game_timestamp=model.end_of_game_timestamp,
            played_at=model.played_at,
            raw_data=model.raw_data,
            is_parsed=model.is_parsed,
            parsing_errors=model.parsing_errors,
            parsed_at=model.parsed_at,
            data_version=model.data_version,
            is_valid=model.is_valid,
            validation_errors=model.validation_errors,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

        # 转换选手表现数据
        if hasattr(model, 'player_performances') and model.player_performances:
            entity.player_performances = [
                self._performance_model_to_entity(perf)
                for perf in model.player_performances
            ]

        # 转换解析任务
        if hasattr(model, 'parsing_jobs') and model.parsing_jobs:
            entity.parsing_jobs = [
                self._job_model_to_entity(job)
                for job in model.parsing_jobs
            ]

        return entity

    def _performance_entity_to_model(
        self,
        entity: RawPlayerPerformanceEntity,
        model: Optional[RawPlayerPerformance] = None
    ) -> RawPlayerPerformance:
        """选手表现实体转换为模型"""
        if model is None:
            model = RawPlayerPerformance()

        # 复制所有属性
        for attr in [
            'raw_match_data_id', 'player_profile_id', 'puuid', 'summoner_id',
            'summoner_name', 'riot_id_game_name', 'riot_id_tag_line', 'current_level',
            'team_id', 'champion_id', 'champion_name', 'detected_team_position',
            'selected_position', 'wins', 'losses', 'leaves', 'leaver', 'was_afk',
            'kills', 'deaths', 'assists', 'largest_killing_spree', 'largest_multi_kill',
            'largest_critical_strike', 'gold_earned', 'minions_killed',
            'neutral_minions_killed', 'neutral_minions_killed_enemy_jungle',
            'neutral_minions_killed_your_jungle', 'total_damage_dealt',
            'total_damage_dealt_to_champions', 'total_damage_taken',
            'total_damage_self_mitigated', 'magic_damage_dealt_to_champions',
            'physical_damage_dealt_to_champions', 'true_damage_dealt_to_champions',
            'magic_damage_taken', 'physical_damage_taken', 'true_damage_taken',
            'total_damage_dealt_to_buildings', 'total_damage_dealt_to_turrets',
            'total_damage_dealt_to_objectives', 'turrets_killed', 'barracks_killed',
            'vision_score', 'wards_placed', 'wards_killed', 'vision_wards_bought_in_game',
            'sight_wards_bought_in_game', 'total_time_crowd_control_dealt',
            'time_ccing_others', 'total_heal', 'total_heal_on_teammates',
            'total_damage_shielded_on_teammates', 'total_time_spent_dead', 'level',
            'spell1_casts', 'spell2_casts', 'spell1_id', 'spell2_id', 'team_objective',
            'objective_damage', 'perk_primary_style', 'perk_sub_style',
            'perk0', 'perk1', 'perk2', 'perk3', 'perk4', 'perk5',
            'items', 'skin_info', 'kda_ratio', 'damage_per_minute', 'gold_per_minute',
            'cs_per_minute', 'vision_per_minute', 'kill_participation', 'damage_efficiency',
            'win', 'lose', 'is_linked_to_profile', 'linking_confidence', 'manual_verification'
        ]:
            if hasattr(entity, attr):
                setattr(model, attr, getattr(entity, attr))

        return model

    def _performance_model_to_entity(self, model: RawPlayerPerformance) -> RawPlayerPerformanceEntity:
        """选手表现模型转换为实体"""
        return RawPlayerPerformanceEntity(
            id=model.id,
            raw_match_data_id=model.raw_match_data_id,
            player_profile_id=model.player_profile_id,
            puuid=model.puuid,
            summoner_id=model.summoner_id,
            summoner_name=model.summoner_name,
            riot_id_game_name=model.riot_id_game_name,
            riot_id_tag_line=model.riot_id_tag_line,
            current_level=model.current_level,
            team_id=model.team_id,
            champion_id=model.champion_id,
            champion_name=model.champion_name,
            detected_team_position=model.detected_team_position,
            selected_position=model.selected_position,
            wins=model.wins,
            losses=model.losses,
            leaves=model.leaves,
            leaver=model.leaver,
            was_afk=model.was_afk,
            kills=model.kills,
            deaths=model.deaths,
            assists=model.assists,
            largest_killing_spree=model.largest_killing_spree,
            largest_multi_kill=model.largest_multi_kill,
            largest_critical_strike=model.largest_critical_strike,
            gold_earned=model.gold_earned,
            minions_killed=model.minions_killed,
            neutral_minions_killed=model.neutral_minions_killed,
            neutral_minions_killed_enemy_jungle=model.neutral_minions_killed_enemy_jungle,
            neutral_minions_killed_your_jungle=model.neutral_minions_killed_your_jungle,
            total_damage_dealt=model.total_damage_dealt,
            total_damage_dealt_to_champions=model.total_damage_dealt_to_champions,
            total_damage_taken=model.total_damage_taken,
            total_damage_self_mitigated=model.total_damage_self_mitigated,
            magic_damage_dealt_to_champions=model.magic_damage_dealt_to_champions,
            physical_damage_dealt_to_champions=model.physical_damage_dealt_to_champions,
            true_damage_dealt_to_champions=model.true_damage_dealt_to_champions,
            magic_damage_taken=model.magic_damage_taken,
            physical_damage_taken=model.physical_damage_taken,
            true_damage_taken=model.true_damage_taken,
            total_damage_dealt_to_buildings=model.total_damage_dealt_to_buildings,
            total_damage_dealt_to_turrets=model.total_damage_dealt_to_turrets,
            total_damage_dealt_to_objectives=model.total_damage_dealt_to_objectives,
            turrets_killed=model.turrets_killed,
            barracks_killed=model.barracks_killed,
            vision_score=model.vision_score,
            wards_placed=model.wards_placed,
            wards_killed=model.wards_killed,
            vision_wards_bought_in_game=model.vision_wards_bought_in_game,
            sight_wards_bought_in_game=model.sight_wards_bought_in_game,
            total_time_crowd_control_dealt=model.total_time_crowd_control_dealt,
            time_ccing_others=model.time_ccing_others,
            total_heal=model.total_heal,
            total_heal_on_teammates=model.total_heal_on_teammates,
            total_damage_shielded_on_teammates=model.total_damage_shielded_on_teammates,
            total_time_spent_dead=model.total_time_spent_dead,
            level=model.level,
            spell1_casts=model.spell1_casts,
            spell2_casts=model.spell2_casts,
            spell1_id=model.spell1_id,
            spell2_id=model.spell2_id,
            team_objective=model.team_objective,
            objective_damage=model.objective_damage,
            perk_primary_style=model.perk_primary_style,
            perk_sub_style=model.perk_sub_style,
            perk0=model.perk0,
            perk1=model.perk1,
            perk2=model.perk2,
            perk3=model.perk3,
            perk4=model.perk4,
            perk5=model.perk5,
            items=model.items,
            skin_info=model.skin_info,
            kda_ratio=model.kda_ratio,
            damage_per_minute=model.damage_per_minute,
            gold_per_minute=model.gold_per_minute,
            cs_per_minute=model.cs_per_minute,
            vision_per_minute=model.vision_per_minute,
            kill_participation=model.kill_participation,
            damage_efficiency=model.damage_efficiency,
            win=model.win,
            lose=model.lose,
            is_linked_to_profile=model.is_linked_to_profile,
            linking_confidence=model.linking_confidence,
            manual_verification=model.manual_verification,
            created_at=model.created_at
        )

    def _job_entity_to_model(
        self,
        entity: RawDataParsingJobEntity,
        model: Optional[RawDataParsingJob] = None
    ) -> RawDataParsingJob:
        """解析任务实体转换为模型"""
        if model is None:
            model = RawDataParsingJob()

        model.raw_match_data_id = entity.raw_match_data_id
        model.job_type = entity.job_type
        model.status = entity.status
        model.priority = entity.priority
        model.job_params = entity.job_params
        model.started_at = entity.started_at
        model.completed_at = entity.completed_at
        model.error_message = entity.error_message
        model.retry_count = entity.retry_count
        model.max_retries = entity.max_retries
        model.result_data = entity.result_data

        return model

    def _job_model_to_entity(self, model: RawDataParsingJob) -> RawDataParsingJobEntity:
        """解析任务模型转换为实体"""
        return RawDataParsingJobEntity(
            id=model.id,
            raw_match_data_id=model.raw_match_data_id,
            job_type=model.job_type,
            status=model.status,
            priority=model.priority,
            job_params=model.job_params,
            result_data=model.result_data,
            started_at=model.started_at,
            completed_at=model.completed_at,
            error_message=model.error_message,
            retry_count=model.retry_count,
            max_retries=model.max_retries,
            created_at=model.created_at,
            updated_at=model.updated_at
        )


class SQLAlchemyRawPlayerPerformanceRepository(RawPlayerPerformanceRepository):
    """基于SQLAlchemy的原始选手表现数据仓储实现"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, performance: RawPlayerPerformanceEntity) -> RawPlayerPerformanceEntity:
        """保存或更新选手表现数据"""
        # 实现保存逻辑
        if performance.id:
            model = await self.session.get(RawPlayerPerformance, performance.id)
            if model:
                model = self._entity_to_model(performance, model)
            else:
                raise ValueError(f"RawPlayerPerformance with id {performance.id} not found")
        else:
            model = self._entity_to_model(performance)
            self.session.add(model)

        await self.session.commit()
        await self.session.refresh(model)
        return self._model_to_entity(model)

    # 实现其他方法...
    # (省略其他方法的详细实现，类似上面的模式)


class SQLAlchemyRawDataParsingJobRepository(RawDataParsingJobRepository):
    """基于SQLAlchemy的数据解析任务仓储实现"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, job: RawDataParsingJobEntity) -> RawDataParsingJobEntity:
        """保存或更新解析任务"""
        # 实现保存逻辑
        if job.id:
            model = await self.session.get(RawDataParsingJob, job.id)
            if model:
                model = self._entity_to_model(job, model)
            else:
                raise ValueError(f"RawDataParsingJob with id {job.id} not found")
        else:
            model = self._entity_to_model(job)
            self.session.add(model)

        await self.session.commit()
        await self.session.refresh(model)
        return self._model_to_entity(model)

    # 实现其他方法...
    # (省略其他方法的详细实现)

    def _entity_to_model(
        self,
        entity: RawDataParsingJobEntity,
        model: Optional[RawDataParsingJob] = None
    ) -> RawDataParsingJob:
        """实体转换为模型"""
        if model is None:
            model = RawDataParsingJob()

        model.raw_match_data_id = entity.raw_match_data_id
        model.job_type = entity.job_type
        model.status = entity.status
        model.priority = entity.priority
        model.job_params = entity.job_params
        model.started_at = entity.started_at
        model.completed_at = entity.completed_at
        model.error_message = entity.error_message
        model.retry_count = entity.retry_count
        model.max_retries = entity.max_retries
        model.result_data = entity.result_data

        return model

    def _model_to_entity(self, model: RawDataParsingJob) -> RawDataParsingJobEntity:
        """模型转换为实体"""
        return RawDataParsingJobEntity(
            id=model.id,
            raw_match_data_id=model.raw_match_data_id,
            job_type=model.job_type,
            status=model.status,
            priority=model.priority,
            job_params=model.job_params,
            result_data=model.result_data,
            started_at=model.started_at,
            completed_at=model.completed_at,
            error_message=model.error_message,
            retry_count=model.retry_count,
            max_retries=model.max_retries,
            created_at=model.created_at,
            updated_at=model.updated_at
        )