"""赛事应用服务"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4
import math
import random

from src.domain.aggregates.tournament import Match, Registration, Tournament
from src.domain.repositories.tournament import TournamentRepository
from src.domain.value_objects.tournament import (
    MatchStatus,
    RegistrationStatus,
    RegistrationSummary,
    TournamentFormat,
    TournamentRules,
    TournamentSchedule,
    TournamentStatus,
    TournamentType,
)


class TournamentService:
    """赛事服务"""

    def __init__(self, tournament_repository: TournamentRepository):
        self.tournament_repository = tournament_repository

    async def create_tournament(
        self,
        region_id: int,
        name: str,
        tournament_type: TournamentType,
        format: TournamentFormat,
        max_participants: int,
        registration_start: datetime,
        registration_end: datetime,
        tournament_start: datetime,
        tournament_end: datetime,
        created_by: int,
        description: Optional[str] = None,
        logo_url: Optional[str] = None,
        banner_url: Optional[str] = None,
        min_rank: Optional[str] = None,
        max_rank: Optional[str] = None,
        team_size: Optional[int] = None,
    ) -> Tournament:
        """创建赛事"""
        rules = TournamentRules(
            format=format,
            max_participants=max_participants,
            min_rank=min_rank,
            max_rank=max_rank,
            team_size=team_size,
        )

        schedule = TournamentSchedule(
            registration_start=registration_start,
            registration_end=registration_end,
            tournament_start=tournament_start,
            tournament_end=tournament_end,
        )

        tournament = Tournament.create(
            region_id=region_id,
            name=name,
            tournament_type=tournament_type,
            rules=rules,
            schedule=schedule,
            created_by=created_by,
            description=description,
            logo_url=logo_url,
            banner_url=banner_url,
        )

        return await self.tournament_repository.save(tournament)

    async def publish_tournament(self, tournament_id: UUID) -> Tournament:
        """发布赛事"""
        tournament = await self.tournament_repository.get_by_id(tournament_id)
        if not tournament:
            raise ValueError(f"Tournament {tournament_id} not found")

        tournament.publish()
        return await self.tournament_repository.update(tournament)

    async def get_tournament(self, tournament_id: UUID) -> Optional[Tournament]:
        """获取赛事详情"""
        return await self.tournament_repository.get_by_id(tournament_id)

    async def get_region_tournaments(
        self,
        region_id: Optional[int] = None,
        status: Optional[TournamentStatus] = None,
        tournament_type: Optional[TournamentType] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Tournament]:
        """获取赛区赛事列表"""
        if region_id is not None:
            return await self.tournament_repository.get_by_region(
                region_id=region_id,
                status=status,
                tournament_type=tournament_type,
                limit=limit,
                offset=offset,
            )
        else:
            # 如果没有指定region_id，获取所有赛事
            return await self.tournament_repository.get_all(
                status=status,
                tournament_type=tournament_type,
                limit=limit,
                offset=offset,
            )


    async def get_registration_stats(
        self,
        tournament_ids: List[UUID],
    ) -> Dict[UUID, RegistrationSummary]:
        """获取赛事报名统计"""
        if not tournament_ids:
            return {}
        return await self.tournament_repository.get_registration_stats(tournament_ids)

    async def get_upcoming_tournaments(
        self,
        region_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[Tournament]:
        """获取即将开始的赛事"""
        return await self.tournament_repository.get_upcoming_tournaments(
            region_id=region_id,
            limit=limit,
        )

    async def get_ongoing_tournaments(
        self,
        region_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[Tournament]:
        """获取进行中的赛事"""
        return await self.tournament_repository.get_ongoing_tournaments(
            region_id=region_id,
            limit=limit,
        )

    async def register_for_tournament(
        self,
        tournament_id: UUID,
        participant_id: str,
        participant_type: str,
        registered_by: int,
    ) -> Registration:
        """报名参赛"""
        tournament = await self.tournament_repository.get_by_id(tournament_id)
        if not tournament:
            raise ValueError(f"Tournament {tournament_id} not found")

        registration = tournament.register_participant(
            participant_id=participant_id,
            participant_type=participant_type,
            registered_by=registered_by,
        )

        await self.tournament_repository.update(tournament)
        return await self.tournament_repository.save_registration(registration)

    async def admin_register_participant(
        self,
        tournament_id: UUID,
        participant_id: str,
        participant_type: str,
        admin_id: int,
    ) -> Registration:
        """管理员指定参赛者"""
        tournament = await self.tournament_repository.get_by_id(tournament_id)
        if not tournament:
            raise ValueError(f"Tournament {tournament_id} not found")

        registration = tournament.admin_register_participant(
            participant_id=participant_id,
            participant_type=participant_type,
            admin_id=admin_id,
        )

        await self.tournament_repository.update(tournament)
        return await self.tournament_repository.save_registration(registration)

    async def get_tournament_registrations(
        self,
        tournament_id: UUID,
        status: Optional[str] = None,
    ) -> List[Registration]:
        """获取赛事报名列表"""
        return await self.tournament_repository.get_registrations(
            tournament_id=tournament_id,
            status=status,
        )

    async def confirm_registration(
        self,
        tournament_id: UUID,
        participant_id: UUID,
    ) -> Registration:
        """确认报名"""
        registration = await self.tournament_repository.get_registration(
            tournament_id=tournament_id,
            participant_id=participant_id,
        )

        if not registration:
            raise ValueError("Registration not found")

        registration.confirm()
        return await self.tournament_repository.update_registration(registration)

    async def reject_registration(
        self,
        tournament_id: UUID,
        participant_id: UUID,
    ) -> Registration:
        """拒绝报名"""
        registration = await self.tournament_repository.get_registration(
            tournament_id=tournament_id,
            participant_id=participant_id,
        )

        if not registration:
            raise ValueError("Registration not found")

        registration.reject()
        return await self.tournament_repository.update_registration(registration)

    async def withdraw_registration(
        self,
        tournament_id: UUID,
        participant_id: UUID,
    ) -> Registration:
        """退出报名"""
        registration = await self.tournament_repository.get_registration(
            tournament_id=tournament_id,
            participant_id=participant_id,
        )

        if not registration:
            raise ValueError("Registration not found")

        registration.withdraw()
        return await self.tournament_repository.update_registration(registration)

    async def create_match(
        self,
        tournament_id: UUID,
        blue_side_id: UUID,
        red_side_id: UUID,
        round_number: int = 1,
        scheduled_time: Optional[datetime] = None,
    ) -> Match:
        """创建比赛"""
        tournament = await self.tournament_repository.get_by_id(tournament_id)
        if not tournament:
            raise ValueError(f"Tournament {tournament_id} not found")

        # 如果scheduled_time有时区信息，转换为naive datetime
        if scheduled_time and scheduled_time.tzinfo is not None:
            scheduled_time = scheduled_time.replace(tzinfo=None)

        match = tournament.create_match(
            blue_side_id=blue_side_id,
            red_side_id=red_side_id,
            round_number=round_number,
            scheduled_time=scheduled_time,
        )

        await self.tournament_repository.update(tournament)
        return await self.tournament_repository.save_match(match)

    async def get_match(self, match_id: UUID) -> Optional[Match]:
        """获取比赛详情"""
        return await self.tournament_repository.get_match(match_id)

    async def get_participant_name(self, participant_id: str) -> Optional[str]:
        """获取参赛者名称"""
        return await self.tournament_repository.get_participant_name(participant_id)

    async def get_tournament_matches(
        self,
        tournament_id: UUID,
        round_number: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Match]:
        """获取赛事比赛列表"""
        return await self.tournament_repository.get_matches(
            tournament_id=tournament_id,
            round_number=round_number,
            status=status,
        )

    async def open_match_check_in(
        self,
        match_id: UUID,
        participants: List[UUID],
    ) -> Match:
        """开启比赛签到"""
        match = await self.tournament_repository.get_match(match_id)
        if not match:
            raise ValueError(f"Match {match_id} not found")

        match.open_check_in(participants)
        return await self.tournament_repository.update_match(match)

    async def check_in_participant(
        self,
        match_id: UUID,
        participant_id: UUID,
    ) -> Match:
        """参赛者签到"""
        match = await self.tournament_repository.get_match(match_id)
        if not match:
            raise ValueError(f"Match {match_id} not found")

        match.check_in_participant(participant_id)
        return await self.tournament_repository.update_match(match)

    async def start_match(self, match_id: UUID) -> Match:
        """开始比赛"""
        match = await self.tournament_repository.get_match(match_id)
        if not match:
            raise ValueError(f"Match {match_id} not found")

        match.start()
        return await self.tournament_repository.update_match(match)

    async def update_match(
        self,
        match_id: UUID,
        blue_side_id: Optional[str] = None,
        red_side_id: Optional[str] = None,
        scheduled_time: Optional[datetime] = None,
        round_number: Optional[int] = None,
    ) -> Match:
        """更新比赛信息"""
        match = await self.tournament_repository.get_match(match_id)
        if not match:
            raise ValueError(f"Match {match_id} not found")

        # 只允许更新未开始的比赛
        if match.status not in [MatchStatus.SCHEDULED, MatchStatus.WAITING_FOR_CHECKIN]:
            raise ValueError("只能更新未开始的比赛")

        # 更新参赛者信息
        if blue_side_id is not None:
            match.blue_side_id = blue_side_id

        if red_side_id is not None:
            match.red_side_id = red_side_id

        # 更新比赛时间
        if scheduled_time is not None:
            match.scheduled_time = scheduled_time

        # 更新轮次
        if round_number is not None:
            match.round_number = round_number

        return await self.tournament_repository.update_match(match)

    async def force_checkin_all_participants(self, match_id: UUID) -> Match:
        """管理员强制全员签到"""
        match = await self.tournament_repository.get_match(match_id)
        if not match:
            raise ValueError(f"Match {match_id} not found")

        match.force_checkin_all()
        return await self.tournament_repository.update_match(match)

    async def complete_match(
        self,
        match_id: UUID,
        winner_id: UUID,
    ) -> Match:
        """完成比赛"""
        match = await self.tournament_repository.get_match(match_id)
        if not match:
            raise ValueError(f"Match {match_id} not found")

        match.complete(winner_id)
        return await self.tournament_repository.update_match(match)

    async def cancel_match(self, match_id: UUID) -> Match:
        """取消比赛"""
        match = await self.tournament_repository.get_match(match_id)
        if not match:
            raise ValueError(f"Match {match_id} not found")

        match.cancel()
        return await self.tournament_repository.update_match(match)

    async def get_participant_tournaments(
        self,
        participant_id: UUID,
        status: Optional[TournamentStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Tournament]:
        """获取参赛者的赛事列表"""
        return await self.tournament_repository.get_participant_tournaments(
            participant_id=participant_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def get_participant_matches(
        self,
        participant_id: UUID,
        tournament_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> List[Match]:
        """获取参赛者的比赛列表"""
        return await self.tournament_repository.get_participant_matches(
            participant_id=participant_id,
            tournament_id=tournament_id,
            status=status,
        )

    async def update_tournament(
        self,
        tournament_id: UUID,
        updates: dict,
    ) -> Tournament:
        """更新赛事信息"""
        tournament = await self.tournament_repository.get_by_id(tournament_id)
        if not tournament:
            raise ValueError(f"Tournament {tournament_id} not found")

        # 更新基本信息
        if 'name' in updates:
            tournament.name = updates['name']
        if 'description' in updates:
            tournament.description = updates['description']
        if 'tournament_type' in updates:
            tournament.tournament_type = updates['tournament_type']
        if 'logo_url' in updates:
            tournament.logo_url = updates['logo_url']
        if 'banner_url' in updates:
            tournament.banner_url = updates['banner_url']
        if 'status' in updates:
            tournament.status = updates['status']

        # 更新规则
        if any(key in updates for key in ['format', 'max_participants', 'min_rank', 'max_rank', 'team_size']):
            new_rules = TournamentRules(
                format=updates.get('format', tournament.rules.format),
                max_participants=updates.get('max_participants', tournament.rules.max_participants),
                min_rank=updates.get('min_rank', tournament.rules.min_rank),
                max_rank=updates.get('max_rank', tournament.rules.max_rank),
                team_size=updates.get('team_size', tournament.rules.team_size),
            )
            tournament.rules = new_rules

        # 更新时间安排
        if any(key in updates for key in ['registration_start', 'registration_end', 'tournament_start', 'tournament_end']):
            new_schedule = TournamentSchedule(
                registration_start=updates.get('registration_start', tournament.schedule.registration_start),
                registration_end=updates.get('registration_end', tournament.schedule.registration_end),
                tournament_start=updates.get('tournament_start', tournament.schedule.tournament_start),
                tournament_end=updates.get('tournament_end', tournament.schedule.tournament_end),
            )
            tournament.schedule = new_schedule

        tournament.updated_at = datetime.now(timezone.utc)
        return await self.tournament_repository.update(tournament)

    async def delete_tournament(self, tournament_id: UUID) -> None:
        """删除赛事"""
        tournament = await self.tournament_repository.get_by_id(tournament_id)
        if not tournament:
            raise ValueError(f"Tournament {tournament_id} not found")

        # 检查是否可以删除（没有进行中的比赛等）
        if tournament.status in [TournamentStatus.ONGOING, TournamentStatus.COMPLETED]:
            raise ValueError("无法删除已开始或已完成的赛事")

        await self.tournament_repository.delete(tournament_id)

    async def update_tournament_status(
        self,
        tournament_id: UUID,
        new_status: TournamentStatus
    ) -> Tournament:
        """更新赛事状态"""
        tournament = await self.tournament_repository.get_by_id(tournament_id)
        if not tournament:
            raise ValueError(f"Tournament {tournament_id} not found")

        tournament.status = new_status
        tournament.updated_at = datetime.now(timezone.utc)

        # 直接在 repository 调用数据库更新，然后重新获取
        await self.tournament_repository.update(tournament)

        # 重新获取更新后的数据，避免_to_domain 在 update 过程中的问题
        return await self.tournament_repository.get_by_id(tournament_id)

    async def generate_bracket(self, tournament_id: UUID, auto_assign_byes: bool = True) -> List[Match]:
        """生成赛程对阵表

        Args:
            tournament_id: 赛事ID
            auto_assign_byes: 是否自动分配轮空，默认为True
        """
        tournament = await self.tournament_repository.get_by_id(tournament_id)
        if not tournament:
            raise ValueError(f"Tournament {tournament_id} not found")

        # 获取已确认的参赛者
        registrations = await self.tournament_repository.get_registrations(
            tournament_id=tournament_id,
            status="confirmed"
        )

        if len(registrations) < 2:
            raise ValueError("至少需要2个确认参赛者才能生成对阵表")

        # 随机排序参赛者
        participants = [reg.participant_id for reg in registrations]
        random.shuffle(participants)

        # 根据赛制生成对阵表
        if tournament.rules.format == TournamentFormat.SINGLE_ELIMINATION:
            matches = await self._generate_single_elimination_bracket(
                tournament_id, participants, auto_assign_byes
            )
        elif tournament.rules.format == TournamentFormat.DOUBLE_ELIMINATION:
            matches = await self._generate_double_elimination_bracket(
                tournament_id, participants, auto_assign_byes
            )
        elif tournament.rules.format == TournamentFormat.ROUND_ROBIN:
            matches = await self._generate_round_robin_bracket(
                tournament_id, participants
            )
        else:
            raise ValueError(f"不支持的赛制: {tournament.rules.format}")

        # 保存所有比赛
        # 在批量保存前确保状态映射已初始化，避免在循环中重复初始化
        if hasattr(self.tournament_repository, '_ensure_status_mappings'):
            self.tournament_repository._ensure_status_mappings()

        saved_matches = []
        for match in matches:
            saved_match = await self.tournament_repository.save_match(match)
            saved_matches.append(saved_match)

        return saved_matches

    async def _generate_single_elimination_bracket(
        self, tournament_id: UUID, participants: List[str], auto_assign_byes: bool = True
    ) -> List[Match]:
        """生成单败淘汰赛对阵表

        Args:
            tournament_id: 赛事ID
            participants: 参赛者列表
            auto_assign_byes: 是否自动分配轮空，默认为True
        """
        matches = []
        current_participants = participants.copy()
        round_number = 1

        while len(current_participants) > 1:
            round_matches = []
            next_round_participants = []

            # 如果参赛者数量为奇数，根据配置决定是否自动分配轮空
            if len(current_participants) % 2 == 1:
                if auto_assign_byes:
                    bye_participant = current_participants.pop()
                    next_round_participants.append(bye_participant)
                else:
                    # 如果不自动分配轮空，保持奇数参赛者，让最后一个参赛者无对手
                    pass

            # 配对生成比赛
            for i in range(0, len(current_participants), 2):
                blue_side = current_participants[i]
                red_side = current_participants[i + 1]

                match = Match(
                    match_id=uuid4(),
                    tournament_id=tournament_id,
                    blue_side_id=blue_side,
                    red_side_id=red_side,
                    round_number=round_number,
                    scheduled_time=datetime.now(timezone.utc),
                    status=MatchStatus.SCHEDULED,
                )

                round_matches.append(match)
                # 胜者待定，将在比赛完成后确定
                next_round_participants.append(None)

            matches.extend(round_matches)
            current_participants = next_round_participants
            round_number += 1

        return matches

    async def _generate_double_elimination_bracket(
        self, tournament_id: UUID, participants: List[str], auto_assign_byes: bool = True
    ) -> List[Match]:
        """生成双败淘汰赛对阵表

        Args:
            tournament_id: 赛事ID
            participants: 参赛者列表
            auto_assign_byes: 是否自动分配轮空，默认为True
        """
        # 双败淘汰赛需要胜者组和败者组
        matches = []

        # 先生成胜者组第一轮
        winners_bracket = participants.copy()
        round_number = 1

        # 胜者组
        while len(winners_bracket) > 1:
            round_matches = []
            next_round = []

            # 轮空处理
            if len(winners_bracket) % 2 == 1:
                bye_participant = winners_bracket.pop()
                next_round.append(bye_participant)

            # 配对生成比赛
            for i in range(0, len(winners_bracket), 2):
                match = Match(
                    match_id=uuid4(),
                    tournament_id=tournament_id,
                    blue_side_id=winners_bracket[i],
                    red_side_id=winners_bracket[i + 1],
                    round_number=round_number,
                    scheduled_time=datetime.now(timezone.utc),
                    status=MatchStatus.SCHEDULED,
                )
                round_matches.append(match)
                next_round.append(None)  # 胜者待定

            matches.extend(round_matches)
            winners_bracket = next_round
            round_number += 1

        # 注意：这里简化了败者组的生成逻辑
        # 实际的双败淘汰赛败者组需要复杂的配对逻辑

        return matches

    async def _generate_round_robin_bracket(
        self, tournament_id: UUID, participants: List[str]
    ) -> List[Match]:
        """生成循环积分赛对阵表"""
        matches = []
        round_number = 1

        # 每个参赛者都要与其他参赛者进行一场比赛
        for i in range(len(participants)):
            for j in range(i + 1, len(participants)):
                match = Match(
                    match_id=uuid4(),
                    tournament_id=tournament_id,
                    blue_side_id=participants[i],
                    red_side_id=participants[j],
                    round_number=round_number,
                    scheduled_time=datetime.now(timezone.utc),
                    status=MatchStatus.SCHEDULED,
                )
                matches.append(match)

        return matches

    async def advance_winner_to_next_round(
        self, completed_match: Match
    ) -> Optional[Match]:
        """将胜者推进到下一轮比赛"""
        if not completed_match.winner_id:
            raise ValueError("比赛尚未完成，无法推进胜者")

        # 查找下一轮需要此胜者的比赛
        next_round_matches = await self.tournament_repository.get_matches(
            tournament_id=completed_match.tournament_id,
            round_number=completed_match.round_number + 1,
            status="scheduled"
        )

        # 简化逻辑：找到第一个需要参赛者的比赛位置
        for next_match in next_round_matches:
            if next_match.blue_side_id is None:
                next_match.blue_side_id = completed_match.winner_id
                return await self.tournament_repository.update_match(next_match)
            elif next_match.red_side_id is None:
                next_match.red_side_id = completed_match.winner_id
                return await self.tournament_repository.update_match(next_match)

        # 如果没有找到合适的位置，可能是最后一轮
        return None

    async def confirm_registration(
        self,
        tournament_id: UUID,
        registration_id: UUID
    ) -> Registration:
        """确认报名"""
        # 获取报名记录
        registration = await self.tournament_repository.get_registration(
            tournament_id=tournament_id,
            participant_id=str(registration_id)  # 这里需要修正，应该直接查找注册ID
        )

        # 由于现有方法没有直接通过registration_id查找的功能，
        # 我们先获取所有报名记录，然后找到匹配的
        registrations = await self.tournament_repository.get_registrations(tournament_id)
        target_registration = None

        for reg in registrations:
            if str(reg.registration_id) == str(registration_id):
                target_registration = reg
                break

        if not target_registration:
            raise ValueError(f"报名记录 {registration_id} 不存在")

        if target_registration.tournament_id != tournament_id:
            raise ValueError("报名记录与赛事不匹配")

        if target_registration.status == "confirmed":
            raise ValueError("该报名已经是确认状态")

        if target_registration.status == "rejected":
            raise ValueError("无法确认已拒绝的报名")

        # 创建新的Registration对象，更新状态
        updated_registration = Registration(
            registration_id=target_registration.registration_id,
            tournament_id=target_registration.tournament_id,
            participant_id=target_registration.participant_id,
            participant_type=target_registration.participant_type,
            status="confirmed",
            registered_by=target_registration.registered_by,
            registered_at=target_registration.registered_at,
            is_admin_registered=target_registration.is_admin_registered
        )

        return await self.tournament_repository.update_registration(updated_registration)

    async def confirm_registrations_batch(
        self,
        tournament_id: UUID,
        registration_ids: List[UUID]
    ) -> Dict:
        """批量确认报名"""
        confirmed_count = 0
        failed_count = 0
        errors = []

        for reg_id in registration_ids:
            try:
                await self.confirm_registration(tournament_id, reg_id)
                confirmed_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"报名 {reg_id}: {str(e)}")

        return {
            "confirmed_count": confirmed_count,
            "failed_count": failed_count,
            "errors": errors if errors else None
        }

    async def reject_registration(
        self,
        tournament_id: UUID,
        registration_id: UUID,
        reason: Optional[str] = None
    ) -> Registration:
        """拒绝报名"""
        # 获取所有报名记录，找到匹配的
        registrations = await self.tournament_repository.get_registrations(tournament_id)
        target_registration = None

        for reg in registrations:
            if str(reg.registration_id) == str(registration_id):
                target_registration = reg
                break

        if not target_registration:
            raise ValueError(f"报名记录 {registration_id} 不存在")

        if target_registration.tournament_id != tournament_id:
            raise ValueError("报名记录与赛事不匹配")

        if target_registration.status == "rejected":
            raise ValueError("该报名已经是拒绝状态")

        if target_registration.status == "confirmed":
            raise ValueError("无法拒绝已确认的报名")

        # 创建新的Registration对象，更新状态
        updated_registration = Registration(
            registration_id=target_registration.registration_id,
            tournament_id=target_registration.tournament_id,
            participant_id=target_registration.participant_id,
            participant_type=target_registration.participant_type,
            status="rejected",
            registered_by=target_registration.registered_by,
            registered_at=target_registration.registered_at,
            is_admin_registered=target_registration.is_admin_registered
        )

        # 保存更新后的报名状态
        return await self.tournament_repository.update_registration_status(updated_registration)

    async def delete_match(self, match_id: UUID) -> bool:
        """删除比赛"""
        try:
            # 获取比赛信息
            match = await self.tournament_repository.get_match(match_id)
            if not match:
                return False

            # 检查比赛状态
            if match.status not in ['scheduled', 'waiting_for_checkin']:
                raise ValueError("只能删除未开始的比赛")

            # 删除比赛
            success = await self.tournament_repository.delete_match(match_id)
            return success

        except Exception as e:
            logger.error(f"删除比赛失败: {str(e)}")
            return False