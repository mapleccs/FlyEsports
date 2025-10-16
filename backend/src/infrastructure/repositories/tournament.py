"""赛事仓储实现"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.aggregates.tournament import Match, Registration, Tournament
from src.domain.repositories.tournament import TournamentRepository
from src.domain.value_objects.tournament import (
    RegistrationSummary,
    TournamentRules,
    TournamentSchedule,
    TournamentStatus,
    TournamentType,
)
from src.infrastructure.database.models.tournament import (
    MatchCheckIn,
    Tournament as TournamentModel,
    TournamentMatch,
    TournamentRegistration,
)
from src.infrastructure.services.dictionary_service import DictionaryService


class SQLAlchemyTournamentRepository(TournamentRepository):
    """基于SQLAlchemy的赛事仓储实现"""

    def __init__(self, session: AsyncSession, dictionary_service: DictionaryService):
        self.session = session
        self.dictionary_service = dictionary_service
        self._match_status_code_to_id: Dict[str, int] = {}
        self._match_status_id_to_code: Dict[int, str] = {}
        self._checkin_status_code_to_id: Dict[str, int] = {}
        self._checkin_status_id_to_code: Dict[int, str] = {}

    async def save(self, tournament: Tournament) -> Tournament:
        """保存赛事"""
        model = self._to_model(tournament)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)

        # 重新查询以预加载关联数据
        stmt = (
            select(TournamentModel)
            .where(TournamentModel.id == model.id)
            .options(
                selectinload(TournamentModel.registrations),
                selectinload(TournamentModel.matches).selectinload(TournamentMatch.check_ins),
            )
        )
        result = await self.session.execute(stmt)
        refreshed_model = result.scalar_one_or_none()

        if not refreshed_model:
            raise ValueError(f"Tournament {model.id} not found after save")

        return await self._to_domain(refreshed_model)

    async def get_by_id(self, tournament_id: UUID) -> Optional[Tournament]:
        """根据ID获取赛事"""
        stmt = (
            select(TournamentModel)
            .where(TournamentModel.id == tournament_id)
            # 暂时禁用预加载以避免 greenlet_spawn 错误
            # .options(
            #     selectinload(TournamentModel.registrations),
            #     selectinload(TournamentModel.matches).selectinload(TournamentMatch.check_ins),
            # )
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return await self._to_domain(model)
        return None

    async def get_by_region(
        self,
        region_id: int,
        status: Optional[TournamentStatus] = None,
        tournament_type: Optional[TournamentType] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Tournament]:
        """获取赛区的赛事列表"""
        stmt = select(TournamentModel).where(TournamentModel.region_id == region_id)

        # 使用ID字段进行过滤，避免懒加载
        if status:
            status_mapping = {
                'draft': 1, 'upcoming': 2, 'registration_open': 3,
                'registration_closed': 4, 'ongoing': 5, 'completed': 6, 'cancelled': 7
            }
            status_id = status_mapping.get(status.value if hasattr(status, 'value') else status, 1)
            stmt = stmt.where(TournamentModel.status_id == status_id)

        if tournament_type:
            tournament_type_mapping = {'team_based': 1, 'solo_based': 2}
            tournament_type_id = tournament_type_mapping.get(
                tournament_type.value if hasattr(tournament_type, 'value') else tournament_type, 1
            )
            stmt = stmt.where(TournamentModel.tournament_type_id == tournament_type_id)

        stmt = stmt.order_by(TournamentModel.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        tournaments = []
        for model in models:
            try:
                tournament = await self._to_domain(model)
                tournaments.append(tournament)
            except Exception as e:
                # 详细记录错误信息
                import traceback
                print(f"Error in _to_domain for model {model.id}: {e}")
                print(f"Full traceback: {traceback.format_exc()}")
                raise
        return tournaments

    async def get_all(
        self,
        status: Optional[TournamentStatus] = None,
        tournament_type: Optional[TournamentType] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Tournament]:
        """获取所有赛事列表"""
        stmt = select(TournamentModel)

        # 使用ID字段进行过滤，避免懒加载
        if status:
            status_mapping = {
                'draft': 1, 'upcoming': 2, 'registration_open': 3,
                'registration_closed': 4, 'ongoing': 5, 'completed': 6, 'cancelled': 7
            }
            status_id = status_mapping.get(status.value if hasattr(status, 'value') else status, 1)
            stmt = stmt.where(TournamentModel.status_id == status_id)

        if tournament_type:
            tournament_type_mapping = {'team_based': 1, 'solo_based': 2}
            tournament_type_id = tournament_type_mapping.get(
                tournament_type.value if hasattr(tournament_type, 'value') else tournament_type, 1
            )
            stmt = stmt.where(TournamentModel.tournament_type_id == tournament_type_id)

        stmt = stmt.order_by(TournamentModel.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        tournaments = []
        for model in models:
            try:
                tournament = await self._to_domain(model)
                tournaments.append(tournament)
            except Exception as e:
                # 详细记录错误信息
                import traceback
                print(f"Error in _to_domain for model {model.id}: {e}")
                print(f"Full traceback: {traceback.format_exc()}")
                raise
        return tournaments


    async def get_registration_stats(
        self,
        tournament_ids: List[UUID],
    ) -> Dict[UUID, RegistrationSummary]:
        """获取赛事报名统计"""
        if not tournament_ids:
            return {}
        normalized_ids = []
        for tid in tournament_ids:
            if isinstance(tid, UUID):
                normalized_ids.append(tid)
            else:
                normalized_ids.append(UUID(str(tid)))
        stmt = (
            select(
                TournamentRegistration.tournament_id.label("tournament_id"),
                func.count(TournamentRegistration.id).label("total_count"),
                func.sum(
                    case(
                        (TournamentRegistration.participant_type == "team", 1),
                        else_=0,
                    )
                ).label("team_count"),
                func.sum(
                    case(
                        (TournamentRegistration.participant_type == "player", 1),
                        else_=0,
                    )
                ).label("player_count"),
                func.sum(
                    case(
                        (TournamentRegistration.status_id == 2, 1),  # 2 = confirmed
                        else_=0,
                    )
                ).label("confirmed_count"),
            )
            .where(TournamentRegistration.tournament_id.in_(normalized_ids))
            .group_by(TournamentRegistration.tournament_id)
        )
        result = await self.session.execute(stmt)
        stats: Dict[UUID, RegistrationSummary] = {}
        for row in result:
            stats[row.tournament_id] = RegistrationSummary(
                total=row.total_count or 0,
                confirmed=row.confirmed_count or 0,
                team=row.team_count or 0,
                player=row.player_count or 0,
            )
        return stats

    async def get_upcoming_tournaments(
        self,
        region_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[Tournament]:
        """获取即将开始的赛事"""
        # 使用status_id进行查询，避免访问关系字段
        stmt = select(TournamentModel).where(
            TournamentModel.status_id.in_([
                2,  # upcoming
                3,  # registration_open
            ])
        )

        if region_id:
            stmt = stmt.where(TournamentModel.region_id == region_id)

        stmt = stmt.order_by(TournamentModel.registration_start).limit(limit)

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        tournaments = []
        for model in models:
            try:
                tournament = await self._to_domain(model)
                tournaments.append(tournament)
            except Exception as e:
                # 详细记录错误信息
                import traceback
                print(f"Error in _to_domain for model {model.id}: {e}")
                print(f"Full traceback: {traceback.format_exc()}")
                raise
        return tournaments

    async def get_ongoing_tournaments(
        self,
        region_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[Tournament]:
        """获取进行中的赛事"""
        # 使用status_id进行查询，避免访问关系字段
        stmt = select(TournamentModel).where(
            TournamentModel.status_id == 5  # 5 = 'ongoing'
        )

        if region_id:
            stmt = stmt.where(TournamentModel.region_id == region_id)

        stmt = stmt.order_by(TournamentModel.tournament_start).limit(limit)

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        tournaments = []
        for model in models:
            try:
                tournament = await self._to_domain(model)
                tournaments.append(tournament)
            except Exception as e:
                # 详细记录错误信息
                import traceback
                print(f"Error in _to_domain for model {model.id}: {e}")
                print(f"Full traceback: {traceback.format_exc()}")
                raise
        return tournaments

    async def update(self, tournament: Tournament) -> Tournament:
        """更新赛事"""
        stmt = select(TournamentModel).where(TournamentModel.id == tournament.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError(f"Tournament {tournament.id} not found")

        # 反向映射：从字符串值到ID
        format_reverse_mapping = {
            'single_elimination': 1,
            'double_elimination': 2,
            'round_robin': 3,
            'swiss': 4,
            'custom': 5
        }

        tournament_type_reverse_mapping = {
            'team_based': 1,
            'solo_based': 2
        }

        status_reverse_mapping = {
            'draft': 1,
            'upcoming': 2,
            'registration_open': 3,
            'registration_closed': 4,
            'ongoing': 5,
            'completed': 6,
            'cancelled': 7
        }

        # 更新字段，使用ID而不是关系字段
        model.name = tournament.name
        model.status_id = status_reverse_mapping.get(tournament.status, 1)
        model.description = tournament.description
        model.logo_url = tournament.logo_url
        model.banner_url = tournament.banner_url
        model.tournament_type_id = tournament_type_reverse_mapping.get(tournament.tournament_type, 1)

        # 更新规则字段
        model.format_id = format_reverse_mapping.get(tournament.rules.format, 1)
        model.max_participants = tournament.rules.max_participants
        model.min_rank = tournament.rules.min_rank
        model.max_rank = tournament.rules.max_rank
        model.team_size = tournament.rules.team_size

        # 更新时间安排字段
        model.registration_start = tournament.schedule.registration_start
        model.registration_end = tournament.schedule.registration_end
        model.tournament_start = tournament.schedule.tournament_start
        model.tournament_end = tournament.schedule.tournament_end

        model.updated_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(model)

        # 重新创建tournament对象，避免复杂的关联加载
        return await self.get_by_id(tournament.id)

    async def delete(self, tournament_id: UUID) -> bool:
        """删除赛事"""
        stmt = select(TournamentModel).where(TournamentModel.id == tournament_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            await self.session.delete(model)
            await self.session.commit()
            return True
        return False

    async def get_registrations(
        self,
        tournament_id: UUID,
        status: Optional[str] = None,
    ) -> List[Registration]:
        """获取赛事的报名列表"""
        stmt = select(TournamentRegistration).where(
            TournamentRegistration.tournament_id == tournament_id
        )

        if status:
            # 使用本地映射避免额外的异步数据库查询，防止 greenlet_spawn 错误
            status_code_to_id = {
                'pending': 1,
                'confirmed': 2,
                'rejected': 3,
                'cancelled': 4
            }
            status_id = status_code_to_id.get(status)

            if status_id:
                stmt = stmt.where(TournamentRegistration.status_id == status_id)
            else:
                # 如果找不到对应的状态，返回空列表
                return []

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        # 使用本地映射避免额外的异步数据库查询，防止 greenlet_spawn 错误
        status_mapping = {
            1: 'pending',
            2: 'confirmed',
            3: 'rejected',
            4: 'cancelled'
        }

        registrations = []
        for model in models:
            registration = self._registration_to_domain_with_status(model, status_mapping.get(model.status_id, 'pending'))
            registrations.append(registration)
        return registrations

    async def get_registration(
        self,
        tournament_id: UUID,
        participant_id: UUID,
    ) -> Optional[Registration]:
        """获取特定参赛者的报名信息"""
        stmt = select(TournamentRegistration).where(
            and_(
                TournamentRegistration.tournament_id == tournament_id,
                TournamentRegistration.participant_id == participant_id,
            )
        )

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return await self._registration_to_domain(model)
        return None

    async def save_registration(self, registration: Registration) -> Registration:
        """保存报名信息"""
        # 使用本地映射避免额外的异步数据库查询，防止 greenlet_spawn 错误
        status_code_to_id = {
            'pending': 1,
            'confirmed': 2,
            'rejected': 3,
            'cancelled': 4
        }
        status_id = status_code_to_id.get(registration.status, 1)

        model = TournamentRegistration(
            id=registration.registration_id,
            tournament_id=registration.tournament_id,
            participant_id=registration.participant_id,
            participant_type=registration.participant_type,
            status_id=status_id,  # 新的字典表外键
            registered_by=registration.registered_by,
            registered_at=registration.registered_at,
            is_admin_registered=registration.is_admin_registered,
        )

        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)

        return await self._registration_to_domain(model)

    async def update_registration(self, registration: Registration) -> Registration:
        """更新报名信息"""
        stmt = select(TournamentRegistration).where(
            TournamentRegistration.id == registration.registration_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError(f"Registration {registration.registration_id} not found")

        # 使用本地映射避免额外的异步数据库查询，防止 greenlet_spawn 错误
        status_code_to_id = {
            'pending': 1,
            'confirmed': 2,
            'rejected': 3,
            'cancelled': 4
        }
        status_id = status_code_to_id.get(registration.status, 1)

        model.status_id = status_id
        model.updated_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(model)

        return await self._registration_to_domain(model)

    async def get_matches(
        self,
        tournament_id: UUID,
        round_number: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Match]:
        """��ȡ���µı����б�"""
        stmt = (
            select(TournamentMatch)
            .where(TournamentMatch.tournament_id == tournament_id)
            .options(selectinload(TournamentMatch.check_ins))
        )

        if round_number is not None:
            stmt = stmt.where(TournamentMatch.round_number == round_number)

        if status:
            self._ensure_status_mappings()
            status_code = status.value if hasattr(status, "value") else status
            status_id = self._match_status_code_to_id.get(status_code)
            if status_id is None:
                raise ValueError(f"Unknown match status: {status}")
            stmt = stmt.where(TournamentMatch.status_id == status_id)

        stmt = stmt.order_by(TournamentMatch.round_number, TournamentMatch.match_number)

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        matches: List[Match] = []
        for model in models:
            matches.append(await self._match_to_domain(model))
        return matches

    async def get_match(self, match_id: UUID) -> Optional[Match]:
        """获取比赛详情"""
        stmt = (
            select(TournamentMatch)
            .where(TournamentMatch.id == match_id)
            .options(selectinload(TournamentMatch.check_ins))
        )

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return await self._match_to_domain(model)
        return None

    async def save_match(self, match: Match) -> Match:
        """�������"""
        self._ensure_status_mappings()

        status_code = match.status.value if hasattr(match.status, "value") else match.status
        status_id = self._match_status_code_to_id.get(status_code)
        if status_id is None:
            raise ValueError(f"Unknown match status: {status_code}")

        model = TournamentMatch(
            id=match.match_id,
            tournament_id=match.tournament_id,
            round_number=match.round_number,
            blue_side_id=match.blue_side_id,
            red_side_id=match.red_side_id,
            status_id=status_id,
            room_id=match.room_id,
            scheduled_time=self._to_naive_utc(match.scheduled_time),
            started_at=self._to_naive_utc(match.started_at),
            completed_at=self._to_naive_utc(match.completed_at),
            winner_id=match.winner_id,
        )

        # ����ǩ����¼
        for participant_id, check_in_status in match.check_ins.items():
            checkin_code = (
                check_in_status.value if hasattr(check_in_status, "value") else check_in_status
            )
            checkin_status_id = self._checkin_status_code_to_id.get(checkin_code)
            if checkin_status_id is None:
                raise ValueError(f"Unknown check-in status: {check_in_status}")
            check_in = MatchCheckIn(
                match_id=match.match_id,
                participant_id=participant_id,
                status_id=checkin_status_id,
            )
            model.check_ins.append(check_in)

        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)

        return await self._match_to_domain(model)

    async def update_match(self, match: Match) -> Match:
        """���±���"""
        stmt = (
            select(TournamentMatch)
            .where(TournamentMatch.id == match.match_id)
            .options(selectinload(TournamentMatch.check_ins))
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError(f"Match {match.match_id} not found")

        self._ensure_status_mappings()
        status_code = match.status.value if hasattr(match.status, "value") else match.status
        status_id = self._match_status_code_to_id.get(status_code)
        if status_id is None:
            raise ValueError(f"Unknown match status: {match.status}")

        # 更新基本比赛信息
        model.status_id = status_id
        model.blue_side_id = match.blue_side_id
        model.red_side_id = match.red_side_id
        model.round_number = match.round_number
        model.scheduled_time = self._to_naive_utc(match.scheduled_time)
        model.room_id = match.room_id
        model.started_at = self._to_naive_utc(match.started_at)
        model.completed_at = self._to_naive_utc(match.completed_at)
        model.winner_id = match.winner_id
        model.updated_at = datetime.now(timezone.utc)

        # ����ǩ��״̬
        existing_participant_ids = {check_in.participant_id for check_in in model.check_ins}

        # �������е�ǩ����¼
        for check_in in model.check_ins:
            if check_in.participant_id in match.check_ins:
                new_status = match.check_ins[check_in.participant_id]
                checkin_code = new_status.value if hasattr(new_status, "value") else new_status
                checkin_status_id = self._checkin_status_code_to_id.get(checkin_code)
                if checkin_status_id is None:
                    raise ValueError(f"Unknown check-in status: {new_status}")
                check_in.status_id = checkin_status_id
                if checkin_code == "checked_in" and not check_in.checked_in_at:
                    check_in.checked_in_at = datetime.now(timezone.utc)

        # �����µ�ǩ����¼����������ڣ�
        for participant_id, check_in_status in match.check_ins.items():
            if participant_id not in existing_participant_ids:
                checkin_code = (
                    check_in_status.value if hasattr(check_in_status, "value") else check_in_status
                )
                checkin_status_id = self._checkin_status_code_to_id.get(checkin_code)
                if checkin_status_id is None:
                    raise ValueError(f"Unknown check-in status: {check_in_status}")
                check_in = MatchCheckIn(
                    match_id=match.match_id,
                    participant_id=participant_id,
                    status_id=checkin_status_id,
                    checked_in_at=datetime.now(timezone.utc) if checkin_code == "checked_in" else None,
                )
                model.check_ins.append(check_in)

        await self.session.commit()
        await self.session.refresh(model)

        return await self._match_to_domain(model)

    async def get_participant_tournaments(
        self,
        participant_id: UUID,
        status: Optional[TournamentStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Tournament]:
        """获取参赛者参加的赛事列表"""
        subquery = select(TournamentRegistration.tournament_id).where(
            TournamentRegistration.participant_id == participant_id
        )

        stmt = select(TournamentModel).where(
            TournamentModel.id.in_(subquery)
        )

        if status:
            # 使用status_id进行查询，避免访问关系字段
            status_mapping = {
                'draft': 1, 'upcoming': 2, 'registration_open': 3,
                'registration_closed': 4, 'ongoing': 5, 'completed': 6, 'cancelled': 7
            }
            status_id = status_mapping.get(status.value if hasattr(status, 'value') else status, 1)
            stmt = stmt.where(TournamentModel.status_id == status_id)

        stmt = stmt.order_by(TournamentModel.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        tournaments = []
        for model in models:
            try:
                tournament = await self._to_domain(model)
                tournaments.append(tournament)
            except Exception as e:
                # 详细记录错误信息
                import traceback
                print(f"Error in _to_domain for model {model.id}: {e}")
                print(f"Full traceback: {traceback.format_exc()}")
                raise
        return tournaments

    async def get_participant_matches(
        self,
        participant_id: UUID,
        tournament_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> List[Match]:
        """��ȡ�����ߵı����б�"""
        stmt = (
            select(TournamentMatch)
            .where(
                or_(
                    TournamentMatch.blue_side_id == participant_id,
                    TournamentMatch.red_side_id == participant_id,
                )
            )
            .options(selectinload(TournamentMatch.check_ins))
        )

        if tournament_id:
            stmt = stmt.where(TournamentMatch.tournament_id == tournament_id)

        if status:
            self._ensure_status_mappings()
            status_code = status.value if hasattr(status, "value") else status
            status_id = self._match_status_code_to_id.get(status_code)
            if status_id is None:
                raise ValueError(f"Unknown match status: {status}")
            stmt = stmt.where(TournamentMatch.status_id == status_id)

        stmt = stmt.order_by(TournamentMatch.scheduled_time.desc())

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        matches: List[Match] = []
        for model in models:
            matches.append(await self._match_to_domain(model))
        return matches

    async def count_by_status(
        self,
        region_id: Optional[int] = None,
        status: TournamentStatus = None,
    ) -> int:
        """统计特定状态的赛事数量"""
        stmt = select(TournamentModel)

        if region_id:
            stmt = stmt.where(TournamentModel.region_id == region_id)

        if status:
            # 使用status_id进行查询，避免访问关系字段
            status_mapping = {
                'draft': 1, 'upcoming': 2, 'registration_open': 3,
                'registration_closed': 4, 'ongoing': 5, 'completed': 6, 'cancelled': 7
            }
            status_id = status_mapping.get(status.value if hasattr(status, 'value') else status, 1)
            stmt = stmt.where(TournamentModel.status_id == status_id)

        result = await self.session.execute(stmt.with_only_columns(TournamentModel.id))
        return len(result.all())

    async def get_participant_name(self, participant_id: str) -> Optional[str]:
        """获取参赛者名称"""
        from src.infrastructure.database.models.team import Team as TeamModel
        from src.infrastructure.database.models.player_profile import PlayerProfile

        try:
            # 尝试作为team ID查询
            if participant_id.isdigit():
                team_stmt = select(TeamModel.name).where(TeamModel.id == int(participant_id))
                team_result = await self.session.execute(team_stmt)
                team_name = team_result.scalar_one_or_none()
                if team_name:
                    return team_name

            # 尝试作为player profile ID查询
            player_stmt = select(PlayerProfile.player_name, PlayerProfile.summoner_name).where(
                PlayerProfile.profile_id == participant_id
            )
            player_result = await self.session.execute(player_stmt)
            player = player_result.first()
            if player:
                return player.player_name or player.summoner_name or "未知选手"

            return None
        except Exception as e:
            # 如果出错，返回None
            return None

    def _to_model(self, tournament: Tournament) -> TournamentModel:
        """领域对象转数据库模型"""
        # 反向映射：从字符串值到ID
        format_reverse_mapping = {
            'single_elimination': 1,
            'double_elimination': 2,
            'round_robin': 3,
            'swiss': 4,
            'custom': 5
        }

        tournament_type_reverse_mapping = {
            'team_based': 1,
            'solo_based': 2
        }

        status_reverse_mapping = {
            'draft': 1,
            'upcoming': 2,
            'registration_open': 3,
            'registration_closed': 4,
            'ongoing': 5,
            'completed': 6,
            'cancelled': 7
        }

        return TournamentModel(
            id=tournament.id,
            region_id=tournament.region_id,
            name=tournament.name,
            tournament_type_id=tournament_type_reverse_mapping.get(tournament.tournament_type, 1),
            status_id=status_reverse_mapping.get(tournament.status, 1),
            format_id=format_reverse_mapping.get(tournament.rules.format, 1),
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
        )

    async def _to_domain(self, model: TournamentModel) -> Tournament:
        """数据库模型转领域对象"""
        # 使用本地映射避免额外的异步数据库查询，防止 greenlet_spawn 错误
        format_mapping = {
            1: 'single_elimination',
            2: 'double_elimination',
            3: 'round_robin',
            4: 'swiss',
            5: 'custom'
        }

        type_mapping = {
            1: 'team_based',
            2: 'solo_based'
        }

        status_mapping = {
            1: 'draft',
            2: 'upcoming',
            3: 'registration_open',
            4: 'registration_closed',
            5: 'ongoing',
            6: 'completed',
            7: 'cancelled'
        }

        tournament_format = format_mapping.get(model.format_id, 'single_elimination')
        tournament_type = type_mapping.get(model.tournament_type_id, 'team_based')
        status = status_mapping.get(model.status_id, 'draft')

        rules = TournamentRules(
            format=tournament_format,
            max_participants=model.max_participants,
            min_rank=model.min_rank,
            max_rank=model.max_rank,
            team_size=model.team_size,
        )

        schedule = TournamentSchedule(
            registration_start=model.registration_start,
            registration_end=model.registration_end,
            tournament_start=model.tournament_start,
            tournament_end=model.tournament_end,
        )

        tournament = Tournament(
            id=str(model.id),
            region_id=model.region_id,
            name=model.name,
            tournament_type=tournament_type,
            rules=rules,
            schedule=schedule,
            created_by=model.created_by,
            description=model.description,
            logo_url=model.logo_url,
            banner_url=model.banner_url,
            status=status,
            created_at=model.created_at,
            updated_at=model.updated_at,
            from_db=True,
        )

        # 暂时不加载关联数据，避免greenlet错误
        # TODO: 重新启用后需要优化异步加载

        return tournament

    async def _registration_to_domain(self, model: TournamentRegistration) -> Registration:
        """报名模型转领域对象"""
        # 使用本地映射避免额外的异步数据库查询，防止 greenlet_spawn 错误
        status_mapping = {
            1: 'pending',
            2: 'confirmed',
            3: 'rejected',
            4: 'cancelled'
        }
        status_code = status_mapping.get(model.status_id, 'pending')

        return Registration(
            registration_id=model.id,
            tournament_id=model.tournament_id,
            participant_id=model.participant_id,
            participant_type=model.participant_type,
            registered_by=model.registered_by,
            registered_at=model.registered_at,
            status=status_code,
            is_admin_registered=model.is_admin_registered,
        )

    def _registration_to_domain_with_status(self, model: TournamentRegistration, status_code: str) -> Registration:
        """报名模型转领域对象（已提供状态码）"""
        return Registration(
            registration_id=model.id,
            tournament_id=model.tournament_id,
            participant_id=model.participant_id,
            participant_type=model.participant_type,
            registered_by=model.registered_by,
            registered_at=model.registered_at,
            status=status_code,
            is_admin_registered=model.is_admin_registered,
        )


    @staticmethod
    def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
        """Ensure database timestamps are stored as naive UTC"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _to_aware_utc(dt: Optional[datetime]) -> Optional[datetime]:
        """Convert database timestamps to timezone-aware UTC"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _ensure_status_mappings(self) -> None:
        """使用本地映射避免额外的异步数据库查询，防止 greenlet_spawn 错误"""
        if not self._match_status_code_to_id:
            # 硬编码匹配状态映射
            self._match_status_code_to_id = {
                'scheduled': 1,
                'check_in_open': 2,
                'ready': 3,
                'ongoing': 4,
                'completed': 5,
                'cancelled': 6
            }
            self._match_status_id_to_code = {v: k for k, v in self._match_status_code_to_id.items()}

        if not self._checkin_status_code_to_id:
            # 硬编码签到状态映射
            self._checkin_status_code_to_id = {
                'not_checked_in': 1,
                'checked_in': 2,
                'no_show': 3
            }
            self._checkin_status_id_to_code = {v: k for k, v in self._checkin_status_code_to_id.items()}

    async def _match_to_domain(self, model: TournamentMatch) -> Match:
        """����ģ��ת�������"""
        self._ensure_status_mappings()

        status_code = self._match_status_id_to_code.get(model.status_id, 'scheduled')

        match = Match(
            match_id=model.id,
            tournament_id=model.tournament_id,
            round_number=model.round_number,
            blue_side_id=model.blue_side_id,
            red_side_id=model.red_side_id,
            scheduled_time=self._to_aware_utc(model.scheduled_time),
            status=status_code,
            room_id=model.room_id,
            created_at=self._to_aware_utc(model.created_at),
            started_at=self._to_aware_utc(model.started_at),
            completed_at=self._to_aware_utc(model.completed_at),
            winner_id=model.winner_id,
        )

        # ����ǩ����Ϣ
        if hasattr(model, "check_ins") and model.check_ins:
            for check_in in model.check_ins:
                checkin_code = self._checkin_status_id_to_code.get(
                    check_in.status_id, 'not_checked_in'
                )
                match.check_ins[check_in.participant_id] = checkin_code

        return match

    async def delete_match(self, match_id: UUID) -> bool:
        """删除比赛"""
        try:
            # 查找比赛
            stmt = select(TournamentMatch).where(TournamentMatch.id == match_id)
            result = await self.session.execute(stmt)
            match_model = result.scalar_one_or_none()

            if not match_model:
                return False

            # 删除比赛
            await self.session.delete(match_model)
            await self.session.commit()

            return True

        except Exception as e:
            await self.session.rollback()
            raise e

