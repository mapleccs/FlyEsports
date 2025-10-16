"""简单单元测试，不依赖复杂配置"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

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

from src.domain.aggregates.tournament import (
    Tournament,
    Registration,
    Match,
    TournamentCreatedEvent,
)


class TestTournamentValueObjects:
    """测试赛事值对象"""
    
    def test_tournament_rules_creation(self):
        """测试赛事规则创建"""
        rules = TournamentRules(
            format=TournamentFormat.SINGLE_ELIMINATION,
            max_participants=16,
            team_size=5
        )
        
        assert rules.format == TournamentFormat.SINGLE_ELIMINATION
        assert rules.max_participants == 16
        assert rules.team_size == 5
    
    def test_tournament_schedule_creation(self):
        """测试赛事时间安排创建"""
        now = datetime.utcnow()
        schedule = TournamentSchedule(
            registration_start=now + timedelta(days=1),
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=10),
            tournament_end=now + timedelta(days=15)
        )
        
        assert schedule.registration_start == now + timedelta(days=1)
        assert schedule.registration_end == now + timedelta(days=7)
        assert schedule.tournament_start == now + timedelta(days=10)
        assert schedule.tournament_end == now + timedelta(days=15)
    
    def test_registration_status_enum(self):
        """测试报名状态枚举"""
        assert RegistrationStatus.PENDING.value == "pending"
        assert RegistrationStatus.CONFIRMED.value == "confirmed"
        assert RegistrationStatus.REJECTED.value == "rejected"
        assert RegistrationStatus.WITHDRAWN.value == "withdrawn"
    
    def test_match_status_enum(self):
        """测试比赛状态枚举"""
        assert MatchStatus.SCHEDULED.value == "scheduled"
        assert MatchStatus.WAITING_FOR_CHECKIN.value == "waiting_for_checkin"
        assert MatchStatus.CHECKING_IN.value == "checking_in"
        assert MatchStatus.READY.value == "ready"
        assert MatchStatus.IN_PROGRESS.value == "in_progress"
        assert MatchStatus.COMPLETED.value == "completed"
        assert MatchStatus.CANCELLED.value == "cancelled"


class TestTournamentAggregate:
    """测试赛事聚合根"""
    
    def test_tournament_creation(self):
        """测试赛事创建"""
        now = datetime.utcnow()
        schedule = TournamentSchedule(
            registration_start=now + timedelta(days=1),
            registration_end=now + timedelta(days=7),
            tournament_start=now + timedelta(days=10),
            tournament_end=now + timedelta(days=15)
        )
        
        rules = TournamentRules(
            format=TournamentFormat.SINGLE_ELIMINATION,
            max_participants=16,
            team_size=5
        )
        
        tournament = Tournament.create(
            region_id=uuid4(),
            name="测试赛事",
            tournament_type=TournamentType.TEAM_BASED,
            rules=rules,
            schedule=schedule,
            created_by=uuid4()
        )
        
        assert tournament.name == "测试赛事"
        assert tournament.tournament_type == TournamentType.TEAM_BASED
        assert tournament.status == TournamentStatus.DRAFT
        assert tournament.rules == rules
        assert tournament.schedule == schedule
        assert len(tournament.registrations) == 0
        assert len(tournament.matches) == 0
        
        # 验证创建事件
        events = tournament.get_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], TournamentCreatedEvent)
    
    def test_registration_creation(self):
        """测试报名记录创建"""
        registration = Registration(
            registration_id=uuid4(),
            tournament_id=uuid4(),
            participant_id=uuid4(),
            participant_type="team",
            registered_by=uuid4(),
            registered_at=datetime.utcnow()
        )
        
        assert registration.status == RegistrationStatus.PENDING
        assert registration.is_admin_registered is False
        assert isinstance(registration.registered_at, datetime)
    
    def test_registration_status_transitions(self):
        """测试报名状态转换"""
        registration = Registration(
            registration_id=uuid4(),
            tournament_id=uuid4(),
            participant_id=uuid4(),
            participant_type="team",
            registered_by=uuid4(),
            registered_at=datetime.utcnow()
        )
        
        # 确认报名
        registration.confirm()
        assert registration.status == RegistrationStatus.CONFIRMED
        
        # 创建新的报名用于拒绝测试
        new_registration = Registration(
            registration_id=uuid4(),
            tournament_id=uuid4(),
            participant_id=uuid4(),
            participant_type="team",
            registered_by=uuid4(),
            registered_at=datetime.utcnow()
        )
        
        # 拒绝报名
        new_registration.reject()
        assert new_registration.status == RegistrationStatus.REJECTED
    
    def test_match_creation(self):
        """测试比赛创建"""
        match = Match(
            match_id=uuid4(),
            tournament_id=uuid4(),
            round_number=1,
            blue_side_id=uuid4(),
            red_side_id=uuid4(),
            scheduled_time=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert match.status == MatchStatus.SCHEDULED
        assert match.round_number == 1
        assert len(match.check_ins) == 0
        assert match.room_id is None
        assert match.winner_id is None


class TestDomainEvents:
    """测试领域事件"""
    
    def test_tournament_created_event(self):
        """测试赛事创建事件"""
        event = TournamentCreatedEvent(
            tournament_id=uuid4(),
            name="测试赛事",
            region_id=uuid4(),
            tournament_type=TournamentType.TEAM_BASED,
            created_by=uuid4()
        )
        
        assert isinstance(event.tournament_id, type(uuid4()))
        assert event.name == "测试赛事"
        assert event.tournament_type == TournamentType.TEAM_BASED
        assert hasattr(event, 'event_id')
        assert hasattr(event, 'occurred_at')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])