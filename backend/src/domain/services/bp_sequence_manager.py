"""
BP步骤序列管理器

负责管理BP(Ban/Pick)的完整流程，包括步骤定义、状态转换验证和下一步计算。
这是BP系统的核心逻辑组件，遵循标准5v5英雄联盟的BP流程。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from ..value_objects.bp_state import (
    BPStep, 
    BPState, 
    BPActionRecord,
    BPActionCodes,
    BPTeamCodes,
    BPPhaseCodes,
    BPSessionStatusCodes
)
from ..events.bp_events import (
    BPActionExecutedEvent,
    BPTimerStartedEvent,
    BPTimeoutEvent,
    BPSessionCompletedEvent,
    BPStateChangedEvent
)


class BPSequenceManager:
    """BP步骤序列管理器"""
    
    def __init__(self):
        """初始化BP序列管理器"""
        self._bp_sequence = self._create_standard_bp_sequence()
    
    def _create_standard_bp_sequence(self) -> List[BPStep]:
        """创建标准5v5 BP序列
        
        标准BP流程：
        1. 蓝方BAN (3次)
        2. 红方BAN (3次)  
        3. 蓝方PICK (1次)
        4. 红方PICK (2次)
        5. 蓝方PICK (1次)
        6. 红方BAN (2次)
        7. 蓝方BAN (2次)
        8. 红方PICK (1次)
        9. 蓝方PICK (1次)
        10. 红方PICK (1次)
        11. 蓝方PICK (1次)
        """
        sequence = []
        
        # 第一轮BAN阶段 (步骤1-6)
        ban_phase_1_teams = [
            BPTeamCodes.BLUE, BPTeamCodes.RED, BPTeamCodes.BLUE,
            BPTeamCodes.RED, BPTeamCodes.BLUE, BPTeamCodes.RED
        ]
        for i, team in enumerate(ban_phase_1_teams, 1):
            sequence.append(BPStep(
                step_index=i,
                action=BPActionCodes.BAN,
                team=team,
                phase=BPPhaseCodes.BAN_PHASE_1,
                description=f"第一轮BAN - {team.upper()}方第{ban_phase_1_teams[:i].count(team)}个禁用"
            ))
        
        # 第一轮PICK阶段 (步骤7-10)
        pick_phase_1_sequence = [
            (BPTeamCodes.BLUE, 1), (BPTeamCodes.RED, 1),
            (BPTeamCodes.RED, 2), (BPTeamCodes.BLUE, 2)
        ]
        for i, (team, pick_num) in enumerate(pick_phase_1_sequence, 7):
            sequence.append(BPStep(
                step_index=i,
                action=BPActionCodes.PICK,
                team=team,
                phase=BPPhaseCodes.PICK_PHASE_1,
                description=f"第一轮PICK - {team.upper()}方第{pick_num}个选择"
            ))
        
        # 第二轮BAN阶段 (步骤11-14)
        ban_phase_2_sequence = [
            (BPTeamCodes.RED, 1), (BPTeamCodes.BLUE, 1),
            (BPTeamCodes.RED, 2), (BPTeamCodes.BLUE, 2)
        ]
        for i, (team, ban_num) in enumerate(ban_phase_2_sequence, 11):
            sequence.append(BPStep(
                step_index=i,
                action=BPActionCodes.BAN,
                team=team,
                phase=BPPhaseCodes.BAN_PHASE_2,
                description=f"第二轮BAN - {team.upper()}方第{ban_num}个禁用"
            ))
        
        # 第二轮PICK阶段 (步骤15-20)
        pick_phase_2_sequence = [
            (BPTeamCodes.RED, 3), (BPTeamCodes.BLUE, 3),
            (BPTeamCodes.RED, 4), (BPTeamCodes.BLUE, 4),
            (BPTeamCodes.RED, 5), (BPTeamCodes.BLUE, 5)
        ]
        for i, (team, pick_num) in enumerate(pick_phase_2_sequence, 15):
            sequence.append(BPStep(
                step_index=i,
                action=BPActionCodes.PICK,
                team=team,
                phase=BPPhaseCodes.PICK_PHASE_2,
                description=f"第二轮PICK - {team.upper()}方第{pick_num}个选择"
            ))
        
        return sequence
    
    def get_bp_sequence(self) -> List[BPStep]:
        """获取完整BP序列"""
        return self._bp_sequence.copy()
    
    def get_step_by_index(self, step_index: int) -> Optional[BPStep]:
        """根据步骤索引获取BP步骤"""
        if 1 <= step_index <= len(self._bp_sequence):
            return self._bp_sequence[step_index - 1]
        return None
    
    def get_current_step(self, bp_state: BPState) -> Optional[BPStep]:
        """获取当前应该执行的BP步骤"""
        return self.get_step_by_index(bp_state.current_step)
    
    def get_next_step(self, current_step: int) -> Optional[BPStep]:
        """获取下一个BP步骤"""
        return self.get_step_by_index(current_step + 1)
    
    def is_valid_step_transition(self, from_step: int, to_step: int) -> bool:
        """验证步骤转换是否有效"""
        # 基本验证
        if from_step < 0 or to_step < 0:
            return False
        
        # 只能前进一步或保持当前步骤
        if to_step - from_step > 1:
            return False
        
        # 不能后退
        if to_step < from_step:
            return False
        
        # 检查步骤是否在有效范围内
        if to_step > len(self._bp_sequence):
            return False
        
        return True
    
    def is_bp_completed(self, current_step: int) -> bool:
        """检查BP是否已完成"""
        return current_step > len(self._bp_sequence)
    
    def validate_action(self, bp_state: BPState, action: str, team: str, champion_id: int) -> Dict[str, Any]:
        """验证BP操作是否有效
        
        Args:
            bp_state: 当前BP状态
            action: 操作类型 (ban/pick)
            team: 队伍方 (blue/red)
            champion_id: 英雄ID
            
        Returns:
            包含验证结果的字典
        """
        result = {
            "valid": False,
            "error_code": None,
            "error_message": None,
            "warnings": []
        }
        
        # 检查会话状态
        if bp_state.session_status != BPSessionStatusCodes.ACTIVE:
            result["error_code"] = "INVALID_SESSION_STATUS"
            result["error_message"] = f"BP会话状态无效: {bp_state.session_status}"
            return result
        
        # 获取当前应该执行的步骤
        current_step = self.get_current_step(bp_state)
        if not current_step:
            result["error_code"] = "INVALID_CURRENT_STEP"
            result["error_message"] = f"无效的当前步骤: {bp_state.current_step}"
            return result
        
        # 验证操作类型
        if action != current_step.action:
            result["error_code"] = "WRONG_ACTION_TYPE"
            result["error_message"] = f"期望操作: {current_step.action}, 实际操作: {action}"
            return result
        
        # 验证队伍方
        if team != current_step.team:
            result["error_code"] = "WRONG_TEAM"
            result["error_message"] = f"期望队伍: {current_step.team}, 实际队伍: {team}"
            return result
        
        # 验证英雄是否已被使用
        if champion_id in bp_state.used_champions:
            result["error_code"] = "CHAMPION_ALREADY_USED"
            result["error_message"] = f"英雄 {champion_id} 已被ban或pick"
            return result
        
        # 所有验证通过
        result["valid"] = True
        return result
    
    def execute_action(self, bp_state: BPState, action: str, team: str, champion_id: int, user_id: int) -> Dict[str, Any]:
        """执行BP操作
        
        Args:
            bp_state: 当前BP状态
            action: 操作类型
            team: 队伍方
            champion_id: 英雄ID
            user_id: 执行用户ID
            
        Returns:
            包含执行结果的字典
        """
        # 验证操作
        validation_result = self.validate_action(bp_state, action, team, champion_id)
        if not validation_result["valid"]:
            return {
                "success": False,
                "validation_result": validation_result
            }
        
        # 计算操作用时
        time_taken = 0
        if bp_state.step_start_time:
            elapsed = (datetime.utcnow() - bp_state.step_start_time).total_seconds()
            time_taken = int(elapsed)
        
        # 创建操作记录
        action_record = BPActionRecord(
            step_index=bp_state.current_step,
            action=action,
            team=team,
            champion_id=champion_id,
            user_id=user_id,
            executed_at=datetime.utcnow(),
            time_taken=time_taken
        )
        
        # 更新BP状态
        self._update_bp_state_after_action(bp_state, action, team, champion_id, action_record)
        
        # 生成下一步信息
        next_step_info = self._generate_next_step_info(bp_state)
        
        return {
            "success": True,
            "action_record": action_record,
            "next_step_info": next_step_info,
            "bp_completed": self.is_bp_completed(bp_state.current_step)
        }
    
    def _update_bp_state_after_action(self, bp_state: BPState, action: str, team: str, champion_id: int, action_record: BPActionRecord) -> None:
        """执行操作后更新BP状态"""
        # 记录ban/pick结果
        if action == BPActionCodes.BAN:
            if team == BPTeamCodes.BLUE:
                bp_state.blue_bans.append(champion_id)
            else:
                bp_state.red_bans.append(champion_id)
        elif action == BPActionCodes.PICK:
            if team == BPTeamCodes.BLUE:
                bp_state.blue_picks.append(champion_id)
            else:
                bp_state.red_picks.append(champion_id)
        
        # 添加操作记录
        bp_state.action_history.append(action_record)
        
        # 更新步骤
        bp_state.current_step += 1
        
        # 更新阶段
        next_step = self.get_step_by_index(bp_state.current_step)
        if next_step:
            bp_state.current_phase = next_step.phase
        elif self.is_bp_completed(bp_state.current_step):
            bp_state.current_phase = BPPhaseCodes.COMPLETED
            bp_state.session_status = BPSessionStatusCodes.COMPLETED
        
        # 重置步骤开始时间
        bp_state.step_start_time = None
    
    def _generate_next_step_info(self, bp_state: BPState) -> Dict[str, Any]:
        """生成下一步信息"""
        next_step = self.get_step_by_index(bp_state.current_step)
        
        if not next_step:
            return {
                "has_next_step": False,
                "bp_completed": True
            }
        
        return {
            "has_next_step": True,
            "bp_completed": False,
            "step_index": next_step.step_index,
            "action": next_step.action,
            "team": next_step.team,
            "phase": next_step.phase,
            "description": next_step.description
        }
    
    def start_next_step_timer(self, bp_state: BPState) -> Optional[BPTimerStartedEvent]:
        """开始下一步计时器"""
        if bp_state.session_status != BPSessionStatusCodes.ACTIVE:
            return None
        
        current_step = self.get_current_step(bp_state)
        if not current_step:
            return None
        
        # 设置步骤开始时间
        bp_state.step_start_time = datetime.utcnow()
        
        # 创建计时器事件
        return BPTimerStartedEvent(
            room_id="",  # 将由调用者填充
            step_index=current_step.step_index,
            action=current_step.action,
            team=current_step.team,
            time_limit=bp_state.time_per_action,
            occurred_at=datetime.utcnow()
        )
    
    def handle_timeout(self, bp_state: BPState, auto_champion_id: int) -> Optional[BPTimeoutEvent]:
        """处理操作超时"""
        current_step = self.get_current_step(bp_state)
        if not current_step:
            return None
        
        # 创建超时事件
        timeout_event = BPTimeoutEvent(
            room_id="",  # 将由调用者填充
            step_index=current_step.step_index,
            action=current_step.action,
            team=current_step.team,
            auto_selected_champion=auto_champion_id,
            occurred_at=datetime.utcnow()
        )
        
        # 自动执行操作
        self.execute_action(bp_state, current_step.action, current_step.team, auto_champion_id, -1)  # -1 表示系统自动操作
        
        return timeout_event