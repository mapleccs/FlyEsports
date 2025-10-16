"""
BP阶段相关的Celery异步任务
负责处理BP阶段的计算密集型操作，如状态计算、数据分析、超时处理等
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from celery import Task
import structlog

from .celery_app import celery_app
from ..cache.redis_client import redis_manager
from ..websocket.bp_manager import bp_websocket_manager
from ...domain.services.bp_room_manager import BPRoomManager, BPRoomConfig
from ...domain.services.bp_timer_service import get_bp_timer_service
from ..repositories.champion import SQLAlchemyChampionRepository

logger = structlog.get_logger(__name__)

# 全局BP管理器实例
_bp_manager: Optional[BPRoomManager] = None

def get_bp_manager() -> BPRoomManager:
    """获取BP房间管理器实例"""
    global _bp_manager
    if _bp_manager is None:
        champion_repo = SQLAlchemyChampionRepository()
        timer_service = get_bp_timer_service()
        
        async def event_handler(event):
            """事件处理器，通过WebSocket广播事件"""
            try:
                if hasattr(event, 'room_id'):
                    await bp_websocket_manager.broadcast_to_room(
                        event.room_id,
                        event.__class__.__name__,
                        event.__dict__
                    )
            except Exception as e:
                logger.error(f"事件广播失败: {e}")
        
        _bp_manager = BPRoomManager(champion_repo, timer_service, event_handler)
    return _bp_manager


class BPTask(Task):
    """BP任务基类，提供通用功能"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的回调"""
        logger.error(
            "BP任务执行失败",
            task_id=task_id,
            exception=str(exc),
            args=args,
            kwargs=kwargs
        )


@celery_app.task(base=BPTask, bind=True)
def initialize_bp_session(self, room_id: str, started_by: int = 1) -> Dict[str, Any]:
    """
    初始化BP会话
    
    Args:
        room_id: 房间ID
        started_by: 启动者用户ID
        
    Returns:
        初始化结果
    """
    try:
        logger.info("开始初始化BP会话", room_id=room_id, task_id=self.request.id)

        bp_manager = get_bp_manager()
        
        # 异步启动BP会话
        async def start_session():
            success = await bp_manager.start_bp_session(room_id, started_by)
            if success:
                # 获取房间状态
                status = bp_manager.get_room_status(room_id)
                return {
                    "success": True,
                    "message": "BP会话初始化成功",
                    "room_status": status
                }
            else:
                return {
                    "success": False,
                    "message": "BP会话初始化失败"
                }
        
        # 在新的事件循环中运行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(start_session())
            return result
        finally:
            loop.close()

    except Exception as e:
        logger.error("初始化BP会话失败", room_id=room_id, error=str(e))
        return {
            "success": False,
            "message": f"初始化BP会话失败: {str(e)}"
        }


@celery_app.task(base=BPTask, bind=True)  
def process_bp_action(self, room_id: str, action: str, team: str, champion_id: int, user_id: int) -> Dict[str, Any]:
    """
    处理BP行动（Ban或Pick英雄）
    
    Args:
        room_id: 房间ID
        action: 操作类型 (ban/pick)
        team: 队伍方 (blue/red)
        champion_id: 英雄ID
        user_id: 执行操作的用户ID
        
    Returns:
        处理结果
    """
    try:
        logger.info(
            "开始处理BP行动",
            room_id=room_id,
            action=action,
            team=team,
            champion_id=champion_id,
            user_id=user_id,
            task_id=self.request.id
        )

        bp_manager = get_bp_manager()
        
        # 异步执行BP操作
        async def execute_action():
            result = await bp_manager.execute_bp_action(
                room_id=room_id,
                user_id=user_id,
                action=action,
                team=team,
                champion_id=champion_id
            )
            return result
        
        # 在新的事件循环中运行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(execute_action())
            
            logger.info(
                "BP行动处理完成",
                room_id=room_id,
                action=action,
                champion_id=champion_id,
                success=result.get("success", False)
            )
            
            return result
        finally:
            loop.close()

    except Exception as e:
        logger.error("处理BP行动失败", room_id=room_id, action=action, error=str(e))
        return {
            "success": False,
            "message": f"处理BP行动失败: {str(e)}"
        }


@celery_app.task(base=BPTask, bind=True)
def start_action_timer(self, room_id: str, action_id: str, duration: int):
    """
    启动行动计时器
    
    Args:
        room_id: 房间ID
        action_id: 行动ID
        duration: 持续时间（秒）
    """
    try:
        logger.info("启动行动计时器", room_id=room_id, action_id=action_id, duration=duration)

        # 启动WebSocket计时器
        asyncio.create_task(
            bp_websocket_manager.start_room_timer(room_id, duration, action_id)
        )

        # 设置超时任务
        timeout_bp_action.apply_async(
            args=[room_id, action_id],
            countdown=duration
        )

    except Exception as e:
        logger.error("启动行动计时器失败", room_id=room_id, action_id=action_id, error=str(e))


@celery_app.task(base=BPTask, bind=True)
def get_bp_state(self, room_id: str) -> Dict[str, Any]:
    """
    获取BP状态
    
    Args:
        room_id: 房间ID
        
    Returns:
        BP状态
    """
    try:
        bp_manager = get_bp_manager()
        status = bp_manager.get_room_status(room_id)
        
        if status:
            return {
                "success": True,
                "bp_state": status
            }
        else:
            return {
                "success": False,
                "message": "房间不存在"
            }
            
    except Exception as e:
        logger.error("获取BP状态失败", room_id=room_id, error=str(e))
        return {
            "success": False,
            "message": f"获取BP状态失败: {str(e)}"
        }


@celery_app.task(base=BPTask, bind=True)
def timeout_bp_action(self, room_id: str, action_id: str) -> Dict[str, Any]:
    """
    处理BP行动超时
    
    Args:
        room_id: 房间ID
        action_id: 行动ID
        
    Returns:
        处理结果
    """
    try:
        logger.info("处理BP行动超时", room_id=room_id, action_id=action_id)

        # 获取当前BP状态
        bp_state = get_bp_state_sync(room_id)
        if not bp_state:
            return {"success": False, "message": "BP状态不存在"}

        # 检查行动是否已完成
        action = find_action_by_id(bp_state["actions"], action_id)
        if not action or action.get("completed"):
            logger.info("行动已完成，忽略超时", room_id=room_id, action_id=action_id)
            return {"success": True, "message": "行动已完成"}

        # 自动选择英雄（随机选择或默认选择）
        if action["type"] == "ban":
            # 随机选择一个未被ban/pick的英雄进行ban
            available_champions = get_available_champions(bp_state)
            if available_champions:
                selected_champion = available_champions[0]  # 选择第一个可用英雄

                # 调用处理BP行动
                return process_bp_action.delay(
                    room_id,
                    action_id,
                    selected_champion["id"],
                    action.get("actor_id", 0)
                ).get()

        elif action["type"] == "pick":
            # 为pick选择推荐英雄
            recommended_champions = get_recommended_champions(bp_state, action["team"])
            if recommended_champions:
                selected_champion = recommended_champions[0]

                return process_bp_action.delay(
                    room_id,
                    action_id,
                    selected_champion["id"],
                    action.get("actor_id", 0)
                ).get()

        # 如果无法自动选择，跳过该行动
        action["completed"] = True
        action["skipped"] = True
        action["skipped_at"] = datetime.utcnow().isoformat()
        action["skip_reason"] = "timeout"

        # 保存状态并继续下一个行动
        redis_key = f"bp_state:{room_id}"
        redis_manager.set_json(redis_key, bp_state, expire=3600)

        # 广播超时消息
        asyncio.create_task(
            bp_websocket_manager.broadcast_to_room(
                room_id,
                "action_skipped",
                {
                    "action_id": action_id,
                    "reason": "timeout",
                    "message": "操作时间到，已跳过该行动"
                }
            )
        )

        return {"success": True, "message": "行动已因超时跳过"}

    except Exception as e:
        logger.error("处理BP行动超时失败", room_id=room_id, action_id=action_id, error=str(e))
        return {"success": False, "message": f"处理超时失败: {str(e)}"}


@celery_app.task(base=BPTask, bind=True)
def analyze_bp_performance(self, room_id: str) -> Dict[str, Any]:
    """
    分析BP阶段表现（异步分析任务）
    
    Args:
        room_id: 房间ID
        
    Returns:
        分析结果
    """
    try:
        logger.info("开始分析BP表现", room_id=room_id)

        bp_state = get_bp_state_sync(room_id)
        if not bp_state:
            return {"success": False, "message": "BP状态不存在"}

        # 分析队伍组合
        blue_composition = analyze_team_composition(bp_state["blue_picks"])
        red_composition = analyze_team_composition(bp_state["red_picks"])

        # 分析ban策略
        blue_ban_strategy = analyze_ban_strategy(bp_state["blue_bans"], bp_state["red_picks"])
        red_ban_strategy = analyze_ban_strategy(bp_state["red_bans"], bp_state["blue_picks"])

        # 计算胜率预测
        win_rate_prediction = calculate_win_rate_prediction(blue_composition, red_composition)

        analysis_result = {
            "room_id": room_id,
            "blue_team": {
                "composition": blue_composition,
                "ban_strategy": blue_ban_strategy,
                "predicted_win_rate": win_rate_prediction["blue"]
            },
            "red_team": {
                "composition": red_composition,
                "ban_strategy": red_ban_strategy,
                "predicted_win_rate": win_rate_prediction["red"]
            },
            "analysis_time": datetime.utcnow().isoformat(),
            "recommendations": generate_performance_recommendations(bp_state)
        }

        # 保存分析结果
        analysis_key = f"bp_analysis:{room_id}"
        redis_manager.set_json(analysis_key, analysis_result, expire=86400)  # 24小时过期

        logger.info("BP表现分析完成", room_id=room_id)

        return {
            "success": True,
            "analysis": analysis_result
        }

    except Exception as e:
        logger.error("分析BP表现失败", room_id=room_id, error=str(e))
        return {"success": False, "message": f"分析失败: {str(e)}"}


# 辅助函数

def generate_standard_bp_flow() -> List[Dict[str, Any]]:
    """生成标准BP流程"""
    actions = []
    order = 1

    # 第一轮Ban (蓝方先ban): B-R-B-R-B-R
    for i in range(3):
        actions.append({
            "id": f"ban1_blue_{i + 1}",
            "order": order,
            "type": "ban",
            "team": "blue",
            "completed": False,
            "time_limit": 30
        })
        order += 1

        actions.append({
            "id": f"ban1_red_{i + 1}",
            "order": order,
            "type": "ban",
            "team": "red",
            "completed": False,
            "time_limit": 30
        })
        order += 1

    # Pick阶段: B-R-R-B-B-R-R-B-B-R
    pick_sequence = [
        ("blue", 1), ("red", 1), ("red", 2), ("blue", 2), ("blue", 3),
        ("red", 3), ("red", 4), ("blue", 4), ("blue", 5), ("red", 5)
    ]

    for team, pick_num in pick_sequence:
        actions.append({
            "id": f"pick_{team}_{pick_num}",
            "order": order,
            "type": "pick",
            "team": team,
            "completed": False,
            "time_limit": 30
        })
        order += 1

    return actions


def get_bp_state_sync(room_id: str) -> Optional[Dict[str, Any]]:
    """同步获取BP状态"""
    redis_key = f"bp_state:{room_id}"
    return redis_manager.get_json(redis_key)


async def get_bp_state(room_id: str) -> Optional[Dict[str, Any]]:
    """异步获取BP状态"""
    return get_bp_state_sync(room_id)


def validate_bp_action(bp_state: Dict[str, Any], action_id: str, champion_id: int, user_id: int) -> Dict[str, Any]:
    """验证BP行动有效性"""
    # 检查是否为当前行动
    if bp_state.get("current_action_id") != action_id:
        return {"valid": False, "reason": "不是当前行动"}

    # 检查英雄是否已被ban或pick
    all_banned = [c["id"] for c in bp_state.get("blue_bans", []) + bp_state.get("red_bans", [])]
    all_picked = [p["champion"]["id"] for p in bp_state.get("blue_picks", []) + bp_state.get("red_picks", [])]

    if champion_id in all_banned or champion_id in all_picked:
        return {"valid": False, "reason": "英雄已被禁用或选择"}

    return {"valid": True}


def find_action_by_id(actions: List[Dict[str, Any]], action_id: str) -> Optional[Dict[str, Any]]:
    """根据ID查找行动"""
    for action in actions:
        if action["id"] == action_id:
            return action
    return None


def find_next_action(actions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """查找下一个未完成的行动"""
    for action in sorted(actions, key=lambda x: x["order"]):
        if not action.get("completed", False):
            return action
    return None


def get_champion_data(champion_id: int) -> Optional[Dict[str, Any]]:
    """获取英雄数据"""
    # TODO: 从数据库或缓存获取真实英雄数据
    # 这里返回模拟数据
    mock_champions = {
        1: {"id": 1, "name": "艾希", "title": "寒冰射手", "iconUrl": "/images/champions/ashe.jpg"},
        2: {"id": 2, "name": "盖伦", "title": "德玛西亚之力", "iconUrl": "/images/champions/garen.jpg"},
        3: {"id": 3, "name": "亚索", "title": "疾风剑豪", "iconUrl": "/images/champions/yasuo.jpg"},
        4: {"id": 4, "name": "锤石", "title": "魂锁典狱长", "iconUrl": "/images/champions/thresh.jpg"},
        5: {"id": 5, "name": "盲僧", "title": "李青", "iconUrl": "/images/champions/leesin.jpg"},
    }
    return mock_champions.get(champion_id)


def get_available_champions(bp_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """获取可用英雄列表"""
    # TODO: 实现真实的可用英雄逻辑
    all_champions = [get_champion_data(i) for i in range(1, 6)]
    return [c for c in all_champions if c]


def get_recommended_champions(bp_state: Dict[str, Any], team: str) -> List[Dict[str, Any]]:
    """获取推荐英雄"""
    # TODO: 实现英雄推荐算法
    return get_available_champions(bp_state)


def analyze_team_composition(picks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析队伍组合"""
    # TODO: 实现队伍组合分析
    return {
        "synergy_score": 75,
        "balance_score": 80,
        "late_game_potential": 70,
        "early_game_strength": 85
    }


def analyze_ban_strategy(bans: List[Dict[str, Any]], opponent_picks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析ban策略"""
    # TODO: 实现ban策略分析
    return {
        "effectiveness": 70,
        "target_focus": "jungle",
        "counter_rate": 60
    }


def calculate_win_rate_prediction(blue_comp: Dict[str, Any], red_comp: Dict[str, Any]) -> Dict[str, float]:
    """计算胜率预测"""
    # TODO: 实现胜率预测算法
    blue_score = sum(blue_comp.values()) / len(blue_comp)
    red_score = sum(red_comp.values()) / len(red_comp)

    total = blue_score + red_score
    return {
        "blue": blue_score / total * 100,
        "red": red_score / total * 100
    }


def generate_performance_recommendations(bp_state: Dict[str, Any]) -> List[str]:
    """生成表现建议"""
    # TODO: 实现智能建议生成
    return [
        "蓝方应该注意前期对线压制",
        "红方需要控制野区资源",
        "双方都需要重视团战配合"
    ]


def calculate_bp_result(bp_state: Dict[str, Any]) -> Dict[str, Any]:
    """计算BP结果"""
    return {
        "blue_team": {
            "bans": bp_state.get("blue_bans", []),
            "picks": bp_state.get("blue_picks", [])
        },
        "red_team": {
            "bans": bp_state.get("red_bans", []),
            "picks": bp_state.get("red_picks", [])
        },
        "duration": "calculated_duration",
        "completed_at": datetime.utcnow().isoformat()
    }
