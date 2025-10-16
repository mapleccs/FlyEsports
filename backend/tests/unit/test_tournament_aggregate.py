"""赛事聚合根单元测试"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID

from src.domain.aggregates.tournament import (
    Tournament,
    Registration,
    Match,
    TournamentCreatedEvent,
    TournamentPublishedEvent,
    ParticipantRegisteredEvent,
    MatchCreatedEvent,
)
from src.domain.value_objects.tournament import (
    TournamentType,
    TournamentStatus,
    TournamentFormat,
    TournamentRules,
    TournamentSchedule,
    RegistrationStatus,
    MatchStatus,
    CheckInStatus,
)


class TestTournament:
    """赛事聚合根测试"""
    
    @pytest.fixture
    def tournament_schedule(self):
        """创建测试用赛事时间安排"""
        now = datetime.utcnow()
        return TournamentSchedule(
            registration_start=now + timedelta(days=1),
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=10),
            tournament_end=now + timedelta(days=15)
        )
    
    @pytest.fixture
    def tournament_rules(self):
        """创建测试用赛事规则"""
        return TournamentRules(
            format=TournamentFormat.SINGLE_ELIMINATION,
            max_participants=16,
            team_size=5
        )
    
    @pytest.fixture
    def solo_tournament(self, tournament_schedule):
        """创建示例个人赛"""
        solo_rules = TournamentRules(
            format=TournamentFormat.SINGLE_ELIMINATION,
            max_participants=16,
        )
        return Tournament.create(
            region_id=uuid4(),
            name="测试个人赛",
            tournament_type=TournamentType.SOLO_BASED,
            rules=solo_rules,
            schedule=tournament_schedule,
            created_by=uuid4(),
            description="个人赛测试赛事",
        )

    @pytest.fixture
    def sample_tournament(self, tournament_schedule, tournament_rules):
        """创建示例赛事"""
        return Tournament.create(
            region_id=uuid4(),
            name="测试赛事",
            tournament_type=TournamentType.TEAM_BASED,
            rules=tournament_rules,
            schedule=tournament_schedule,
            created_by=uuid4(),
            description="这是一个测试赛事"
        )
    
    def test_tournament_creation(self, sample_tournament, tournament_schedule, tournament_rules):
        """测试赛事创建"""
        # 验证基本属性
        assert sample_tournament.name == "测试赛事"
        assert sample_tournament.tournament_type == TournamentType.TEAM_BASED
        assert sample_tournament.status == TournamentStatus.DRAFT
        assert sample_tournament.description == "这是一个测试赛事"
        assert sample_tournament.rules == tournament_rules
        assert sample_tournament.schedule == tournament_schedule
        
        # 验证初始状态
        assert len(sample_tournament.registrations) == 0
        assert len(sample_tournament.matches) == 0
        assert isinstance(sample_tournament.created_at, datetime)
        assert isinstance(sample_tournament.updated_at, datetime)
        
        # 验证创建事件
        events = sample_tournament._domain_events
        assert len(events) == 1
        assert isinstance(events[0], TournamentCreatedEvent)
        assert events[0].tournament_id == sample_tournament.id
        assert events[0].name == "测试赛事"
    
    def test_tournament_publish(self, sample_tournament):
        """测试赛事发布"""
        # 发布赛事
        sample_tournament.publish()
        
        # 验证状态变更
        assert sample_tournament.status != TournamentStatus.DRAFT
        assert isinstance(sample_tournament.updated_at, datetime)
        
        # 验证发布事件
        events = sample_tournament._domain_events
        publish_events = [e for e in events if isinstance(e, TournamentPublishedEvent)]
        assert len(publish_events) == 1
        assert publish_events[0].tournament_id == sample_tournament.id
    
    def test_tournament_publish_invalid_status(self, sample_tournament):
        """测试无效状态下发布赛事"""
        # 先发布一次
        sample_tournament.publish()
        
        # 尝试再次发布
        with pytest.raises(ValueError, match="只有草稿状态的赛事才能发布"):
            sample_tournament.publish()
    
    def test_participant_registration(self, sample_tournament):
        """测试参赛者报名"""
        # 修改赛事状态为报名开放
        sample_tournament.status = TournamentStatus.REGISTRATION_OPEN
        
        participant_id = uuid4()
        registered_by = uuid4()
        
        # 执行报名
        registration = sample_tournament.register_participant(
            participant_id=participant_id,
            participant_type="team",
            registered_by=registered_by
        )
        
        # 验证报名记录
        assert isinstance(registration, Registration)
        assert registration.participant_id == participant_id
        assert registration.participant_type == "team"
        assert registration.registered_by == registered_by
        assert registration.status == RegistrationStatus.PENDING
        
        # 验证聚合状态更新
        assert len(sample_tournament.registrations) == 1
        assert sample_tournament.registrations[participant_id] == registration
        
        # 验证报名事件
        events = sample_tournament._domain_events
        registration_events = [e for e in events if isinstance(e, ParticipantRegisteredEvent)]
        assert len(registration_events) == 1
        assert registration_events[0].participant_id == participant_id
    
    def test_team_tournament_rejects_player_registration(self, sample_tournament):
        sample_tournament.status = TournamentStatus.REGISTRATION_OPEN
        with pytest.raises(ValueError, match="战队赛只能以战队身份参加"):
            sample_tournament.register_participant(
                participant_id=str(uuid4()),
                participant_type="player",
                registered_by=uuid4(),
            )

    def test_team_tournament_admin_rejects_player_registration(self, sample_tournament):
        with pytest.raises(ValueError, match="战队赛只能以战队身份参加"):
            sample_tournament.admin_register_participant(
                participant_id=str(uuid4()),
                participant_type="player",
                admin_id=uuid4(),
            )

    def test_solo_tournament_accepts_player_registration(self, solo_tournament):
        solo_tournament.status = TournamentStatus.REGISTRATION_OPEN
        registration = solo_tournament.register_participant(
            participant_id=str(uuid4()),
            participant_type="player",
            registered_by=uuid4(),
        )
        assert registration.participant_type == "player"

    def test_solo_tournament_rejects_team_registration(self, solo_tournament):
        solo_tournament.status = TournamentStatus.REGISTRATION_OPEN
        with pytest.raises(ValueError, match="个人赛只能以选手身份参加"):
            solo_tournament.register_participant(
                participant_id=str(uuid4()),
                participant_type="team",
                registered_by=uuid4(),
            )

    def test_registration_when_closed(self, sample_tournament):
        """测试报名关闭时的报名尝试"""
        # 保持默认状态（草稿状态，不允许报名）
        participant_id = uuid4()
        
        with pytest.raises(ValueError, match="当前不在报名期间"):
            sample_tournament.register_participant(
                participant_id=participant_id,
                participant_type="team",
                registered_by=uuid4()
            )
    
    def test_duplicate_registration(self, sample_tournament):
        """测试重复报名"""
        # 设置为报名开放状态
        sample_tournament.status = TournamentStatus.REGISTRATION_OPEN
        
        participant_id = uuid4()
        
        # 第一次报名
        sample_tournament.register_participant(
            participant_id=participant_id,
            participant_type="team",
            registered_by=uuid4()
        )
        
        # 尝试重复报名
        with pytest.raises(ValueError, match="该参赛者已报名"):
            sample_tournament.register_participant(
                participant_id=participant_id,
                participant_type="team",
                registered_by=uuid4()
            )
    
    def test_registration_full(self, sample_tournament):
        """测试报名名额已满"""
        # 设置小的最大参与数用于测试
        sample_tournament.rules.max_participants = 2
        sample_tournament.status = TournamentStatus.REGISTRATION_OPEN
        
        # 报满名额
        for i in range(2):
            registration = sample_tournament.register_participant(
                participant_id=uuid4(),
                participant_type="team",
                registered_by=uuid4()
            )
            # 确认报名
            registration.confirm()
        
        # 尝试再报名
        with pytest.raises(ValueError, match="报名名额已满"):
            sample_tournament.register_participant(
                participant_id=uuid4(),
                participant_type="team",
                registered_by=uuid4()
            )
    
    def test_admin_register_participant(self, sample_tournament):
        """测试管理员直接指定参赛者"""
        participant_id = uuid4()
        admin_id = uuid4()
        
        # 管理员直接报名
        registration = sample_tournament.admin_register_participant(
            participant_id=participant_id,
            participant_type="team",
            admin_id=admin_id
        )
        
        # 验证报名记录
        assert registration.status == RegistrationStatus.CONFIRMED
        assert registration.is_admin_registered is True
        assert registration.registered_by == admin_id
    
    def test_create_match(self, sample_tournament):
        """测试创建比赛"""
        blue_side_id = uuid4()
        red_side_id = uuid4()
        scheduled_time = datetime.utcnow() + timedelta(hours=1)
        
        # 创建比赛
        match = sample_tournament.create_match(
            blue_side_id=blue_side_id,
            red_side_id=red_side_id,
            round_number=1,
            scheduled_time=scheduled_time
        )
        
        # 验证比赛对象
        assert isinstance(match, Match)
        assert match.blue_side_id == blue_side_id
        assert match.red_side_id == red_side_id
        assert match.round_number == 1
        assert match.scheduled_time == scheduled_time
        assert match.status == MatchStatus.SCHEDULED
        
        # 验证聚合状态
        assert len(sample_tournament.matches) == 1
        assert sample_tournament.matches[match.id] == match
        
        # 验证比赛创建事件
        events = sample_tournament._domain_events
        match_events = [e for e in events if isinstance(e, MatchCreatedEvent)]
        assert len(match_events) == 1
        assert match_events[0].match_id == match.id
    
    def test_can_register_logic(self, sample_tournament):
        """测试是否可以报名的逻辑"""
        # 草稿状态不能报名
        assert sample_tournament.can_register() is False
        
        # 报名开放状态可以报名
        sample_tournament.status = TournamentStatus.REGISTRATION_OPEN
        assert sample_tournament.can_register() is True
        
        # 其他状态不能报名
        sample_tournament.status = TournamentStatus.IN_PROGRESS
        assert sample_tournament.can_register() is False
    
    def test_update_status(self, sample_tournament):
        """测试状态更新"""
        original_updated_at = sample_tournament.updated_at
        
        # 模拟状态变更
        sample_tournament.status = TournamentStatus.REGISTRATION_OPEN
        sample_tournament.update_status()
        
        # 验证更新时间改变
        assert sample_tournament.updated_at > original_updated_at
    
    def test_is_registration_full_logic(self, sample_tournament):
        """测试报名名额检查逻辑"""
        # 空报名列表
        assert sample_tournament._is_registration_full() is False
        
        # 添加未确认的报名
        participant_id = uuid4()
        registration = Registration(
            registration_id=uuid4(),
            tournament_id=sample_tournament.id,
            participant_id=participant_id,
            participant_type="team",
            registered_by=uuid4(),
            registered_at=datetime.utcnow(),
            status=RegistrationStatus.PENDING
        )
        sample_tournament.registrations[participant_id] = registration
        assert sample_tournament._is_registration_full() is False
        
        # 确认报名但数量未达到上限
        registration.confirm()
        assert sample_tournament._is_registration_full() is False
        
        # 添加足够多的确认报名
        sample_tournament.rules.max_participants = 1
        assert sample_tournament._is_registration_full() is True


class TestRegistration:
    """报名记录测试"""
    
    @pytest.fixture
    def sample_registration(self):
        """创建示例报名记录"""
        return Registration(
            registration_id=uuid4(),
            tournament_id=uuid4(),
            participant_id=uuid4(),
            participant_type="team",
            registered_by=uuid4(),
            registered_at=datetime.utcnow()
        )
    
    def test_registration_creation(self, sample_registration):
        """测试报名记录创建"""
        assert sample_registration.status == RegistrationStatus.PENDING
        assert sample_registration.is_admin_registered is False
        assert isinstance(sample_registration.registered_at, datetime)
    
    def test_confirm_registration(self, sample_registration):
        """测试确认报名"""
        sample_registration.confirm()
        assert sample_registration.status == RegistrationStatus.CONFIRMED
    
    def test_reject_registration(self, sample_registration):
        """测试拒绝报名"""
        sample_registration.reject()
        assert sample_registration.status == RegistrationStatus.REJECTED
    
    def test_withdraw_registration(self, sample_registration):
        """测试撤回报名"""
        sample_registration.withdraw()
        assert sample_registration.status == RegistrationStatus.WITHDRAWN
        
        # 确认状态下也可以撤回
        confirmed_registration = Registration(
            registration_id=uuid4(),
            tournament_id=uuid4(),
            participant_id=uuid4(),
            participant_type="team",
            registered_by=uuid4(),
            registered_at=datetime.utcnow(),
            status=RegistrationStatus.CONFIRMED
        )
        confirmed_registration.withdraw()
        assert confirmed_registration.status == RegistrationStatus.WITHDRAWN
    
    def test_invalid_status_transitions(self, sample_registration):
        """测试无效的状态转换"""
        # 拒绝后不能再确认
        sample_registration.reject()
        
        with pytest.raises(ValueError, match="只有待审核的报名才能确认"):
            sample_registration.confirm()
        
        # 已撤回的不能再拒绝
        withdrawn_registration = Registration(
            registration_id=uuid4(),
            tournament_id=uuid4(),
            participant_id=uuid4(),
            participant_type="team",
            registered_by=uuid4(),
            registered_at=datetime.utcnow(),
            status=RegistrationStatus.WITHDRAWN
        )
        
        with pytest.raises(ValueError, match="只有待审核的报名才能拒绝"):
            withdrawn_registration.reject()


class TestMatch:
    """比赛测试"""
    
    @pytest.fixture
    def sample_match(self):
        """创建示例比赛"""
        return Match(
            match_id=uuid4(),
            tournament_id=uuid4(),
            round_number=1,
            blue_side_id=uuid4(),
            red_side_id=uuid4(),
            scheduled_time=datetime.utcnow() + timedelta(hours=1)
        )
    
    def test_match_creation(self, sample_match):
        """测试比赛创建"""
        assert sample_match.status == MatchStatus.SCHEDULED
        assert len(sample_match.check_ins) == 0
        assert sample_match.room_id is None
        assert sample_match.winner_id is None
    
    def test_open_check_in(self, sample_match):
        """测试开启签到"""
        participants = [uuid4(), uuid4()]
        
        sample_match.open_check_in(participants)
        
        # 验证状态和房间
        assert sample_match.status == MatchStatus.WAITING_FOR_CHECKIN
        assert sample_match.room_id is not None
        assert len(sample_match.check_ins) == 2
        
        # 验证签到状态初始化
        for participant_id in participants:
            assert sample_match.check_ins[participant_id] == CheckInStatus.NOT_CHECKED_IN
    
    def test_participant_check_in(self, sample_match):
        """测试参赛者签到"""
        participants = [uuid4(), uuid4()]
        sample_match.open_check_in(participants)
        
        # 第一个参赛者签到
        sample_match.check_in_participant(participants[0])
        
        assert sample_match.check_ins[participants[0]] == CheckInStatus.CHECKED_IN
        assert sample_match.status == MatchStatus.CHECKING_IN
        
        # 第二个参赛者签到
        sample_match.check_in_participant(participants[1])
        
        assert sample_match.check_ins[participants[1]] == CheckInStatus.CHECKED_IN
        assert sample_match.status == MatchStatus.READY  # 全部签到完成
    
    def test_invalid_check_in(self, sample_match):
        """测试无效签到"""
        # 未开启签到
        with pytest.raises(ValueError, match="当前不在签到阶段"):
            sample_match.check_in_participant(uuid4())
        
        # 开启签到后测试无效参赛者
        participants = [uuid4()]
        sample_match.open_check_in(participants)
        
        with pytest.raises(ValueError, match="该参赛者不在此比赛中"):
            sample_match.check_in_participant(uuid4())
        
        # 重复签到
        sample_match.check_in_participant(participants[0])
        with pytest.raises(ValueError, match="该参赛者已签到"):
            sample_match.check_in_participant(participants[0])
    
    def test_start_match(self, sample_match):
        """测试开始比赛"""
        # 准备就绪状态
        participants = [uuid4(), uuid4()]
        sample_match.open_check_in(participants)
        for participant in participants:
            sample_match.check_in_participant(participant)
        
        # 开始比赛
        sample_match.start()
        
        assert sample_match.status == MatchStatus.IN_PROGRESS
        assert isinstance(sample_match.started_at, datetime)
    
    def test_complete_match(self, sample_match):
        """测试完成比赛"""
        # 准备比赛进行状态
        participants = [uuid4(), uuid4()]
        sample_match.open_check_in(participants)
        for participant in participants:
            sample_match.check_in_participant(participant)
        sample_match.start()
        
        # 完成比赛
        winner_id = participants[0]
        sample_match.complete(winner_id)
        
        assert sample_match.status == MatchStatus.COMPLETED
        assert sample_match.winner_id == winner_id
        assert isinstance(sample_match.completed_at, datetime)
    
    def test_invalid_winner(self, sample_match):
        """测试无效胜利者"""
        participants = [uuid4(), uuid4()]
        sample_match.open_check_in(participants)
        for participant in participants:
            sample_match.check_in_participant(participant)
        sample_match.start()
        
        # 使用不在比赛中的ID作为胜利者
        invalid_winner = uuid4()
        
        with pytest.raises(ValueError, match="胜利者必须是参赛双方之一"):
            sample_match.complete(invalid_winner)
    
    def test_cancel_match(self, sample_match):
        """测试取消比赛"""
        sample_match.cancel()
        assert sample_match.status == MatchStatus.CANCELLED
        
        # 已完成的比赛不能取消
        completed_match = Match(
            match_id=uuid4(),
            tournament_id=uuid4(),
            round_number=1,
            blue_side_id=uuid4(),
            red_side_id=uuid4(),
            scheduled_time=datetime.utcnow(),
            status=MatchStatus.COMPLETED
        )
        
        with pytest.raises(ValueError, match="无法取消已完成或已取消的比赛"):
            completed_match.cancel()
    
    def test_all_checked_in_logic(self, sample_match):
        """测试全部签到检查逻辑"""
        # 无签到记录
        assert sample_match.all_checked_in() is False
        
        # 部分签到
        participants = [uuid4(), uuid4()]
        sample_match.open_check_in(participants)
        sample_match.check_in_participant(participants[0])
        assert sample_match.all_checked_in() is False
        
        # 全部签到
        sample_match.check_in_participant(participants[1])
        assert sample_match.all_checked_in() is True