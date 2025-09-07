# 转会系统设计文档 (Transfer System Design)

## 1. 转会系统概述

转会系统是 FlyEsports 平台的核心功能之一，负责管理选手在不同战队间的流动。系统采用基于状态机的设计，确保转会过程的原子性和一致性，同时支持复杂的业务规则如转会费计算、转会窗口管理和选手锁定机制。

### 1.1 核心业务场景

- **自由选手签约**: 无合约选手加入战队
- **合约转让**: 有合约选手在战队间转移
- **合约到期**: 选手合约自然到期成为自由选手  
- **解约释放**: 战队主动解除选手合约
- **选手申请**: 选手主动申请加入或离开战队

### 1.2 关键约束条件

- **转会窗口**: 只能在指定时间段内进行转会
- **选手锁定**: 参与比赛的选手在比赛期间被锁定
- **工资帽限制**: 战队总工资不能超过设定上限
- **位置限制**: 每个位置的选手数量有上限
- **合约有效性**: 必须验证合约的法律有效性

## 2. 选手状态管理

### 2.1 选手合约状态枚举

```python
from enum import Enum
from datetime import datetime, timedelta

class ContractStatus(str, Enum):
    """选手合约状态"""
    FREE_AGENT = "free_agent"           # 自由选手
    ACTIVE_CONTRACT = "active_contract" # 有效合约
    EXPIRED_CONTRACT = "expired_contract" # 过期合约
    TERMINATED = "terminated"           # 合约终止
    SUSPENDED = "suspended"             # 暂停状态

class LockStatus(str, Enum):
    """选手锁定状态"""
    UNLOCKED = "unlocked"               # 未锁定
    MATCH_LOCKED = "match_locked"       # 比赛锁定
    TRANSFER_LOCKED = "transfer_locked" # 转会锁定
    DISPUTE_LOCKED = "dispute_locked"   # 争议锁定
```

### 2.2 选手状态管理器

```python
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class PlayerLockInfo:
    """选手锁定信息"""
    lock_type: LockStatus
    lock_reason: str
    locked_until: Optional[datetime]
    locked_by: str  # 锁定操作者
    created_at: datetime

class PlayerStatusManager:
    """选手状态管理器"""
    
    def __init__(self, redis_client, db_session):
        self.redis = redis_client
        self.db = db_session
    
    async def lock_player(
        self,
        player_id: str,
        lock_type: LockStatus,
        reason: str,
        duration_hours: Optional[int] = None,
        locked_by: str = "system"
    ) -> bool:
        """锁定选手"""
        lock_key = f"player_lock:{player_id}"
        
        # 检查是否已被锁定
        existing_lock = await self.redis.get(lock_key)
        if existing_lock:
            return False
        
        # 创建锁定信息
        lock_info = PlayerLockInfo(
            lock_type=lock_type,
            lock_reason=reason,
            locked_until=datetime.utcnow() + timedelta(hours=duration_hours) if duration_hours else None,
            locked_by=locked_by,
            created_at=datetime.utcnow()
        )
        
        # 设置锁定
        ttl = duration_hours * 3600 if duration_hours else None
        await self.redis.setex(
            lock_key,
            ttl or 86400,  # 默认24小时过期
            lock_info.model_dump_json()
        )
        
        return True
    
    async def unlock_player(self, player_id: str, unlocked_by: str = "system") -> bool:
        """解锁选手"""
        lock_key = f"player_lock:{player_id}"
        result = await self.redis.delete(lock_key)
        
        if result:
            # 记录解锁日志
            await self._log_unlock_event(player_id, unlocked_by)
        
        return bool(result)
    
    async def is_player_locked(self, player_id: str) -> tuple[bool, Optional[PlayerLockInfo]]:
        """检查选手是否被锁定"""
        lock_key = f"player_lock:{player_id}"
        lock_data = await self.redis.get(lock_key)
        
        if not lock_data:
            return False, None
        
        lock_info = PlayerLockInfo.model_validate_json(lock_data)
        
        # 检查是否已过期
        if lock_info.locked_until and lock_info.locked_until < datetime.utcnow():
            await self.unlock_player(player_id, "system_expired")
            return False, None
        
        return True, lock_info
```

## 3. 转会窗口管理

### 3.1 转会窗口定义

```python
from datetime import date
from sqlalchemy.orm import Mapped, mapped_column

class TransferWindow(Base):
    """转会窗口"""
    __tablename__ = "transfer_windows"
    
    id: Mapped[str] = mapped_column(primary_key=True)
    region_id: Mapped[str] = mapped_column(ForeignKey("regions.id"))
    season_id: Mapped[str] = mapped_column(ForeignKey("seasons.id"))
    
    window_name: Mapped[str]  # 窗口名称 (e.g., "春季转会窗口")
    start_date: Mapped[date]
    end_date: Mapped[date]
    is_active: Mapped[bool] = mapped_column(default=True)
    
    # 转会限制
    max_transfers_per_team: Mapped[int] = mapped_column(default=3)
    min_contract_duration_days: Mapped[int] = mapped_column(default=30)
    
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

class TransferWindowManager:
    """转会窗口管理器"""
    
    def __init__(self, db_session, cache_client):
        self.db = db_session
        self.cache = cache_client
    
    async def is_transfer_window_open(self, region_id: str, season_id: str) -> bool:
        """检查转会窗口是否开放"""
        cache_key = f"transfer_window:{region_id}:{season_id}"
        cached_result = await self.cache.get(cache_key)
        
        if cached_result is not None:
            return cached_result == "true"
        
        today = date.today()
        window = await self.db.execute(
            select(TransferWindow).where(
                and_(
                    TransferWindow.region_id == region_id,
                    TransferWindow.season_id == season_id,
                    TransferWindow.start_date <= today,
                    TransferWindow.end_date >= today,
                    TransferWindow.is_active == True
                )
            )
        )
        
        is_open = window.scalar() is not None
        
        # 缓存结果（短期缓存，避免频繁查询）
        await self.cache.setex(cache_key, 300, "true" if is_open else "false")
        
        return is_open
    
    async def get_current_window_limits(self, region_id: str, season_id: str) -> Optional[dict]:
        """获取当前转会窗口限制"""
        window = await self.db.execute(
            select(TransferWindow).where(
                and_(
                    TransferWindow.region_id == region_id,
                    TransferWindow.season_id == season_id,
                    TransferWindow.start_date <= date.today(),
                    TransferWindow.end_date >= date.today(),
                    TransferWindow.is_active == True
                )
            )
        )
        
        current_window = window.scalar()
        if not current_window:
            return None
        
        return {
            "max_transfers_per_team": current_window.max_transfers_per_team,
            "min_contract_duration_days": current_window.min_contract_duration_days,
            "window_name": current_window.window_name,
            "end_date": current_window.end_date
        }
```

## 4. 转会费计算系统

### 4.1 转会费计算引擎

```python
from decimal import Decimal
from typing import Dict, Any

class TransferFeeCalculator:
    """转会费计算器"""
    
    BASE_FEE_RATE = Decimal("0.10")  # 基础转会费率10%
    RATING_MULTIPLIERS = {
        (0, 1200): Decimal("0.5"),      # 新手选手
        (1200, 1500): Decimal("1.0"),   # 普通选手  
        (1500, 1800): Decimal("1.5"),   # 优秀选手
        (1800, 2100): Decimal("2.0"),   # 顶级选手
        (2100, float("inf")): Decimal("3.0")  # 职业选手
    }
    
    def __init__(self):
        self.position_modifiers = {
            "TOP": Decimal("1.0"),
            "JUNGLE": Decimal("1.1"),     # 打野稍贵
            "MID": Decimal("1.2"),        # 中单最贵
            "ADC": Decimal("1.1"),
            "SUPPORT": Decimal("0.9")     # 辅助稍便宜
        }
    
    def calculate_transfer_fee(
        self,
        player_rating: int,
        player_position: str,
        current_salary: Decimal,
        contract_remaining_days: int,
        market_factors: Dict[str, Any] = None
    ) -> Decimal:
        """计算转会费"""
        
        # 基础转会费 = 当前薪资 * 基础费率
        base_fee = current_salary * self.BASE_FEE_RATE
        
        # 评分系数
        rating_multiplier = self._get_rating_multiplier(player_rating)
        
        # 位置系数
        position_multiplier = self.position_modifiers.get(player_position, Decimal("1.0"))
        
        # 合约剩余时间系数 (剩余时间越长，转会费越高)
        contract_multiplier = self._calculate_contract_multiplier(contract_remaining_days)
        
        # 市场因素调整
        market_multiplier = self._calculate_market_multiplier(market_factors or {})
        
        # 最终转会费
        transfer_fee = (
            base_fee * 
            rating_multiplier * 
            position_multiplier * 
            contract_multiplier * 
            market_multiplier
        )
        
        # 设置最小和最大转会费
        min_fee = current_salary * Decimal("0.05")  # 最小5%薪资
        max_fee = current_salary * Decimal("2.0")   # 最大200%薪资
        
        return max(min_fee, min(transfer_fee, max_fee))
    
    def _get_rating_multiplier(self, rating: int) -> Decimal:
        """根据评分获取系数"""
        for (min_rating, max_rating), multiplier in self.RATING_MULTIPLIERS.items():
            if min_rating <= rating < max_rating:
                return multiplier
        return Decimal("1.0")
    
    def _calculate_contract_multiplier(self, remaining_days: int) -> Decimal:
        """计算合约剩余时间系数"""
        if remaining_days <= 30:
            return Decimal("0.5")      # 合约即将到期
        elif remaining_days <= 90:
            return Decimal("0.8")      # 短期合约
        elif remaining_days <= 180:
            return Decimal("1.0")      # 中期合约
        else:
            return Decimal("1.3")      # 长期合约
    
    def _calculate_market_multiplier(self, market_factors: Dict[str, Any]) -> Decimal:
        """计算市场因素系数"""
        multiplier = Decimal("1.0")
        
        # 供需关系
        demand_supply_ratio = market_factors.get("demand_supply_ratio", 1.0)
        if demand_supply_ratio > 2.0:
            multiplier *= Decimal("1.2")  # 供不应求
        elif demand_supply_ratio < 0.5:
            multiplier *= Decimal("0.8")  # 供过于求
        
        # 转会季热度
        transfer_season_heat = market_factors.get("transfer_season_heat", 1.0)
        multiplier *= Decimal(str(transfer_season_heat))
        
        return multiplier
```

### 4.2 转会预算管理

```python
class TeamBudgetManager:
    """战队预算管理器"""
    
    def __init__(self, db_session, cache_client):
        self.db = db_session
        self.cache = cache_client
    
    async def check_transfer_budget(
        self,
        team_id: str,
        transfer_fee: Decimal,
        new_player_salary: Decimal
    ) -> tuple[bool, Dict[str, Any]]:
        """检查转会预算"""
        
        # 获取战队当前财务状况
        budget_info = await self._get_team_budget_info(team_id)
        
        total_cost = transfer_fee + new_player_salary
        available_budget = budget_info["remaining_budget"]
        
        # 检查是否超出预算
        budget_sufficient = available_budget >= total_cost
        
        # 检查工资帽限制
        current_salary_total = budget_info["current_salary_total"]
        salary_cap = budget_info["salary_cap"]
        salary_cap_ok = (current_salary_total + new_player_salary) <= salary_cap
        
        return budget_sufficient and salary_cap_ok, {
            "budget_sufficient": budget_sufficient,
            "salary_cap_ok": salary_cap_ok,
            "total_cost": float(total_cost),
            "available_budget": float(available_budget),
            "salary_cap_remaining": float(salary_cap - current_salary_total),
            "budget_info": budget_info
        }
    
    async def _get_team_budget_info(self, team_id: str) -> Dict[str, Any]:
        """获取战队预算信息"""
        cache_key = f"team_budget:{team_id}"
        cached_info = await self.cache.get(cache_key)
        
        if cached_info:
            return json.loads(cached_info)
        
        # 从数据库查询
        result = await self.db.execute("""
            SELECT 
                t.transfer_budget,
                t.salary_cap,
                COALESCE(SUM(pc.salary), 0) as current_salary_total,
                COUNT(pc.id) as active_contracts
            FROM teams t
            LEFT JOIN player_contracts pc ON t.id = pc.team_id 
                AND pc.status = 'active' 
                AND pc.end_date > NOW()
            WHERE t.id = :team_id
            GROUP BY t.id, t.transfer_budget, t.salary_cap
        """, {"team_id": team_id})
        
        row = result.fetchone()
        if not row:
            return {}
        
        info = {
            "transfer_budget": float(row.transfer_budget),
            "salary_cap": float(row.salary_cap),
            "current_salary_total": float(row.current_salary_total),
            "active_contracts": row.active_contracts,
            "remaining_budget": float(row.transfer_budget),  # 简化实现
        }
        
        # 缓存5分钟
        await self.cache.setex(cache_key, 300, json.dumps(info))
        
        return info
```

## 5. 转会流程状态机

### 5.1 转会状态定义

```python
class TransferStatus(str, Enum):
    """转会状态"""
    INITIATED = "initiated"           # 转会发起
    PENDING_APPROVAL = "pending_approval"  # 等待批准
    APPROVED = "approved"             # 已批准
    REJECTED = "rejected"             # 已拒绝  
    PROCESSING = "processing"         # 处理中
    COMPLETED = "completed"           # 已完成
    CANCELLED = "cancelled"           # 已取消
    FAILED = "failed"                # 失败

class TransferType(str, Enum):
    """转会类型"""
    FREE_SIGNING = "free_signing"     # 自由签约
    CONTRACT_TRANSFER = "contract_transfer"  # 合约转让
    LOAN = "loan"                     # 租借
    CONTRACT_RENEWAL = "contract_renewal"    # 续约
    CONTRACT_TERMINATION = "contract_termination"  # 解约

class TransferRequest(Base):
    """转会请求"""
    __tablename__ = "transfer_requests"
    
    id: Mapped[str] = mapped_column(primary_key=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("player_profiles.id"))
    from_team_id: Mapped[Optional[str]] = mapped_column(ForeignKey("teams.id"))
    to_team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"))
    
    transfer_type: Mapped[TransferType]
    status: Mapped[TransferStatus] = mapped_column(default=TransferStatus.INITIATED)
    
    # 财务信息
    transfer_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    new_salary: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    contract_duration_days: Mapped[int]
    
    # 审批信息
    initiated_by: Mapped[str]  # 发起人
    approved_by: Mapped[Optional[str]]
    approval_notes: Mapped[Optional[str]]
    
    # 时间戳
    initiated_at: Mapped[datetime] = mapped_column(default=func.now())
    approved_at: Mapped[Optional[datetime]]
    completed_at: Mapped[Optional[datetime]]
    
    # 元数据
    metadata: Mapped[Optional[Dict]] = mapped_column(JSON)
```

### 5.2 转会状态机实现

```python
class TransferStateMachine:
    """转会状态机"""
    
    # 定义状态转换规则
    VALID_TRANSITIONS = {
        TransferStatus.INITIATED: [
            TransferStatus.PENDING_APPROVAL,
            TransferStatus.CANCELLED,
            TransferStatus.REJECTED
        ],
        TransferStatus.PENDING_APPROVAL: [
            TransferStatus.APPROVED,
            TransferStatus.REJECTED,
            TransferStatus.CANCELLED
        ],
        TransferStatus.APPROVED: [
            TransferStatus.PROCESSING,
            TransferStatus.CANCELLED
        ],
        TransferStatus.PROCESSING: [
            TransferStatus.COMPLETED,
            TransferStatus.FAILED
        ],
        TransferStatus.REJECTED: [],  # 终态
        TransferStatus.COMPLETED: [], # 终态
        TransferStatus.CANCELLED: [], # 终态
        TransferStatus.FAILED: [
            TransferStatus.INITIATED  # 可以重新发起
        ]
    }
    
    def __init__(self, db_session, event_bus):
        self.db = db_session
        self.event_bus = event_bus
    
    async def transition_to(
        self,
        transfer_id: str,
        new_status: TransferStatus,
        operator: str,
        notes: str = None
    ) -> bool:
        """状态转换"""
        
        # 获取当前转会请求
        transfer = await self.db.get(TransferRequest, transfer_id)
        if not transfer:
            raise ValueError(f"Transfer request {transfer_id} not found")
        
        # 验证状态转换是否有效
        if new_status not in self.VALID_TRANSITIONS.get(transfer.status, []):
            raise ValueError(
                f"Invalid transition from {transfer.status} to {new_status}"
            )
        
        # 执行状态转换前的验证
        await self._validate_transition(transfer, new_status, operator)
        
        # 更新状态
        old_status = transfer.status
        transfer.status = new_status
        
        # 更新相关字段
        if new_status == TransferStatus.APPROVED:
            transfer.approved_by = operator
            transfer.approved_at = datetime.utcnow()
            transfer.approval_notes = notes
        elif new_status == TransferStatus.COMPLETED:
            transfer.completed_at = datetime.utcnow()
        
        await self.db.commit()
        
        # 发布状态变更事件
        await self.event_bus.publish(TransferStatusChanged(
            transfer_id=transfer_id,
            old_status=old_status,
            new_status=new_status,
            operator=operator,
            timestamp=datetime.utcnow()
        ))
        
        # 执行状态转换后的处理
        await self._handle_post_transition(transfer, old_status, new_status)
        
        return True
    
    async def _validate_transition(
        self,
        transfer: TransferRequest,
        new_status: TransferStatus,
        operator: str
    ):
        """验证状态转换"""
        
        if new_status == TransferStatus.APPROVED:
            # 检查操作权限
            if not await self._has_approval_permission(operator, transfer):
                raise PermissionError("Insufficient permissions to approve transfer")
            
            # 检查预算
            budget_ok, budget_info = await self._check_transfer_budget(transfer)
            if not budget_ok:
                raise ValueError(f"Insufficient budget: {budget_info}")
        
        elif new_status == TransferStatus.PROCESSING:
            # 检查选手是否被锁定
            is_locked, lock_info = await self._check_player_lock(transfer.player_id)
            if is_locked:
                raise ValueError(f"Player is locked: {lock_info.lock_reason}")
    
    async def _handle_post_transition(
        self,
        transfer: TransferRequest,
        old_status: TransferStatus,
        new_status: TransferStatus
    ):
        """状态转换后处理"""
        
        if new_status == TransferStatus.PROCESSING:
            # 锁定选手，防止重复转会
            await self._lock_player_for_transfer(transfer.player_id, transfer.id)
            
            # 启动异步转会处理任务
            from tasks.transfer_tasks import process_transfer_task
            process_transfer_task.delay(transfer.id)
        
        elif new_status == TransferStatus.COMPLETED:
            # 解锁选手
            await self._unlock_player(transfer.player_id)
            
            # 更新选手合约信息
            await self._update_player_contract(transfer)
            
            # 发送通知
            await self._send_transfer_notifications(transfer)
        
        elif new_status in [TransferStatus.CANCELLED, TransferStatus.FAILED]:
            # 解锁选手
            await self._unlock_player(transfer.player_id)
```

## 6. 异步转会处理

### 6.1 Celery转会任务

```python
from celery import shared_task
from celery.exceptions import Retry

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_transfer_task(self, transfer_id: str):
    """处理转会的异步任务"""
    
    try:
        processor = TransferProcessor()
        result = await processor.process_transfer(transfer_id)
        
        if not result.success:
            if result.retryable:
                raise self.retry(countdown=60)
            else:
                # 标记为失败
                await processor.mark_transfer_failed(transfer_id, result.error)
        
        return result.to_dict()
        
    except Exception as exc:
        # 记录错误日志
        logger.error(f"Transfer processing failed: {transfer_id}, error: {exc}")
        
        # 尝试重试
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        
        # 达到最大重试次数，标记为失败
        await TransferProcessor().mark_transfer_failed(
            transfer_id, 
            f"Task failed after {self.max_retries} retries: {str(exc)}"
        )

class TransferProcessor:
    """转会处理器"""
    
    def __init__(self):
        self.db = get_db_session()
        self.payment_service = PaymentService()
        self.contract_service = ContractService()
        self.notification_service = NotificationService()
    
    async def process_transfer(self, transfer_id: str) -> 'ProcessResult':
        """处理转会"""
        
        transfer = await self.db.get(TransferRequest, transfer_id)
        if not transfer:
            return ProcessResult(success=False, error="Transfer not found")
        
        try:
            # 1. 执行财务交易
            if transfer.transfer_fee and transfer.transfer_fee > 0:
                payment_result = await self.payment_service.process_transfer_payment(
                    from_team_id=transfer.to_team_id,
                    to_team_id=transfer.from_team_id,
                    amount=transfer.transfer_fee,
                    reference=f"transfer_{transfer_id}"
                )
                
                if not payment_result.success:
                    return ProcessResult(
                        success=False, 
                        error=f"Payment failed: {payment_result.error}",
                        retryable=payment_result.retryable
                    )
            
            # 2. 终止旧合约（如果有）
            if transfer.from_team_id:
                await self.contract_service.terminate_contract(
                    player_id=transfer.player_id,
                    team_id=transfer.from_team_id,
                    reason="transfer"
                )
            
            # 3. 创建新合约
            new_contract = await self.contract_service.create_contract(
                player_id=transfer.player_id,
                team_id=transfer.to_team_id,
                salary=transfer.new_salary,
                duration_days=transfer.contract_duration_days,
                transfer_reference=transfer_id
            )
            
            if not new_contract:
                # 回滚财务交易
                if transfer.transfer_fee and transfer.transfer_fee > 0:
                    await self.payment_service.refund_transfer_payment(
                        payment_result.transaction_id
                    )
                
                return ProcessResult(
                    success=False,
                    error="Failed to create new contract",
                    retryable=True
                )
            
            # 4. 更新转会状态
            await self._update_transfer_status(
                transfer_id, 
                TransferStatus.COMPLETED
            )
            
            # 5. 发送通知
            await self.notification_service.send_transfer_completion_notifications(
                transfer
            )
            
            return ProcessResult(success=True)
            
        except Exception as e:
            logger.error(f"Transfer processing error: {e}")
            return ProcessResult(
                success=False,
                error=str(e),
                retryable=True
            )

@dataclass
class ProcessResult:
    success: bool
    error: Optional[str] = None
    retryable: bool = False
    transaction_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "error": self.error,
            "retryable": self.retryable,
            "transaction_id": self.transaction_id
        }
```

## 7. 转会历史与统计

### 7.1 转会历史记录

```python
class TransferHistory(Base):
    """转会历史记录"""
    __tablename__ = "transfer_history"
    
    id: Mapped[str] = mapped_column(primary_key=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("player_profiles.id"))
    from_team_id: Mapped[Optional[str]] = mapped_column(ForeignKey("teams.id"))
    to_team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"))
    
    transfer_type: Mapped[TransferType]
    transfer_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    contract_duration_days: Mapped[int]
    salary: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    
    # 转会时的选手数据
    player_rating_at_transfer: Mapped[int]
    player_position: Mapped[str]
    player_age_at_transfer: Mapped[int]
    
    # 市场数据
    market_value_at_transfer: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    season_id: Mapped[str] = mapped_column(ForeignKey("seasons.id"))
    region_id: Mapped[str] = mapped_column(ForeignKey("regions.id"))
    
    completed_at: Mapped[datetime] = mapped_column(default=func.now())
    
    # 关联关系
    player: Mapped["PlayerProfile"] = relationship("PlayerProfile")
    from_team: Mapped[Optional["Team"]] = relationship("Team", foreign_keys=[from_team_id])
    to_team: Mapped["Team"] = relationship("Team", foreign_keys=[to_team_id])

class TransferAnalytics:
    """转会数据分析"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def get_market_trends(
        self,
        region_id: str,
        season_id: str,
        position: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取转会市场趋势"""
        
        base_query = select(TransferHistory).where(
            and_(
                TransferHistory.region_id == region_id,
                TransferHistory.season_id == season_id,
                TransferHistory.transfer_fee.isnot(None)
            )
        )
        
        if position:
            base_query = base_query.where(TransferHistory.player_position == position)
        
        transfers = await self.db.execute(base_query)
        transfer_data = transfers.scalars().all()
        
        if not transfer_data:
            return {}
        
        # 计算统计指标
        fees = [float(t.transfer_fee) for t in transfer_data if t.transfer_fee]
        salaries = [float(t.salary) for t in transfer_data]
        
        return {
            "total_transfers": len(transfer_data),
            "total_transfer_value": sum(fees),
            "average_transfer_fee": sum(fees) / len(fees) if fees else 0,
            "median_transfer_fee": sorted(fees)[len(fees)//2] if fees else 0,
            "average_salary": sum(salaries) / len(salaries) if salaries else 0,
            "position_distribution": self._calculate_position_distribution(transfer_data),
            "age_distribution": self._calculate_age_distribution(transfer_data),
            "rating_impact": self._calculate_rating_impact(transfer_data)
        }
    
    async def get_team_transfer_summary(
        self,
        team_id: str,
        season_id: str
    ) -> Dict[str, Any]:
        """获取战队转会汇总"""
        
        # 转入
        transfers_in = await self.db.execute(
            select(TransferHistory).where(
                and_(
                    TransferHistory.to_team_id == team_id,
                    TransferHistory.season_id == season_id
                )
            )
        )
        
        # 转出
        transfers_out = await self.db.execute(
            select(TransferHistory).where(
                and_(
                    TransferHistory.from_team_id == team_id,
                    TransferHistory.season_id == season_id
                )
            )
        )
        
        in_data = transfers_in.scalars().all()
        out_data = transfers_out.scalars().all()
        
        # 计算净支出
        spent = sum(float(t.transfer_fee or 0) for t in in_data)
        earned = sum(float(t.transfer_fee or 0) for t in out_data)
        net_spending = spent - earned
        
        return {
            "transfers_in": len(in_data),
            "transfers_out": len(out_data),
            "total_spent": spent,
            "total_earned": earned,
            "net_spending": net_spending,
            "current_squad_cost": await self._calculate_squad_cost(team_id),
            "position_changes": self._analyze_position_changes(in_data, out_data)
        }
```

## 8. 转会通知与事件

### 8.1 转会事件定义

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TransferStatusChanged(DomainEvent):
    """转会状态变更事件"""
    transfer_id: str
    old_status: TransferStatus
    new_status: TransferStatus
    operator: str
    timestamp: datetime

@dataclass
class PlayerTransferCompleted(DomainEvent):
    """选手转会完成事件"""
    transfer_id: str
    player_id: str
    from_team_id: Optional[str]
    to_team_id: str
    transfer_fee: Optional[Decimal]
    new_salary: Decimal
    completed_at: datetime

@dataclass 
class TransferWindowOpened(DomainEvent):
    """转会窗口开启事件"""
    region_id: str
    season_id: str
    window_id: str
    start_date: date
    end_date: date

class TransferNotificationService:
    """转会通知服务"""
    
    def __init__(self, notification_client, template_service):
        self.notification = notification_client
        self.templates = template_service
    
    async def handle_transfer_status_changed(self, event: TransferStatusChanged):
        """处理转会状态变更事件"""
        
        # 获取转会详细信息
        transfer = await self._get_transfer_details(event.transfer_id)
        
        # 根据状态发送不同通知
        if event.new_status == TransferStatus.PENDING_APPROVAL:
            await self._notify_approval_required(transfer)
        elif event.new_status == TransferStatus.APPROVED:
            await self._notify_transfer_approved(transfer)
        elif event.new_status == TransferStatus.REJECTED:
            await self._notify_transfer_rejected(transfer)
        elif event.new_status == TransferStatus.COMPLETED:
            await self._notify_transfer_completed(transfer)
    
    async def _notify_transfer_completed(self, transfer: TransferRequest):
        """通知转会完成"""
        
        # 通知选手
        await self.notification.send_notification(
            user_id=transfer.player_id,
            title="转会完成",
            message=f"恭喜！您已成功转会至 {transfer.to_team.name}",
            type="transfer_completed",
            data={"transfer_id": transfer.id}
        )
        
        # 通知新战队
        team_members = await self._get_team_members(transfer.to_team_id)
        for member in team_members:
            await self.notification.send_notification(
                user_id=member.user_id,
                title="新队员加入",
                message=f"{transfer.player.username} 已加入战队",
                type="team_member_joined",
                data={"transfer_id": transfer.id, "player_id": transfer.player_id}
            )
        
        # 通知原战队（如果有）
        if transfer.from_team_id:
            old_team_members = await self._get_team_members(transfer.from_team_id)
            for member in old_team_members:
                await self.notification.send_notification(
                    user_id=member.user_id,
                    title="队员离队",
                    message=f"{transfer.player.username} 已转会离队",
                    type="team_member_left",
                    data={"transfer_id": transfer.id, "player_id": transfer.player_id}
                )
        
        # 公告通知（重要转会）
        if transfer.transfer_fee and transfer.transfer_fee >= 10000:  # 高价转会
            await self._publish_transfer_announcement(transfer)
```

## 9. API接口设计

### 9.1 转会管理API

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer

router = APIRouter(prefix="/api/v1/transfers", tags=["transfers"])
security = HTTPBearer()

@router.post("/request")
async def initiate_transfer_request(
    request: TransferRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """发起转会请求"""
    
    # 验证转会窗口
    if not await TransferWindowManager(db).is_transfer_window_open(
        request.region_id, request.season_id
    ):
        raise HTTPException(400, "Transfer window is not open")
    
    # 验证选手锁定状态
    is_locked, lock_info = await PlayerStatusManager().is_player_locked(
        request.player_id
    )
    if is_locked:
        raise HTTPException(400, f"Player is locked: {lock_info.lock_reason}")
    
    # 计算转会费
    transfer_fee = await TransferFeeCalculator().calculate_transfer_fee(
        player_rating=request.player_rating,
        player_position=request.player_position,
        current_salary=request.current_salary,
        contract_remaining_days=request.contract_remaining_days
    )
    
    # 检查预算
    budget_ok, budget_info = await TeamBudgetManager().check_transfer_budget(
        request.to_team_id, transfer_fee, request.new_salary
    )
    if not budget_ok:
        raise HTTPException(400, f"Insufficient budget: {budget_info}")
    
    # 创建转会请求
    transfer_request = TransferRequest(
        id=generate_id(),
        player_id=request.player_id,
        from_team_id=request.from_team_id,
        to_team_id=request.to_team_id,
        transfer_type=request.transfer_type,
        transfer_fee=transfer_fee,
        new_salary=request.new_salary,
        contract_duration_days=request.contract_duration_days,
        initiated_by=current_user.id
    )
    
    db.add(transfer_request)
    await db.commit()
    
    return {"transfer_id": transfer_request.id, "estimated_fee": float(transfer_fee)}

@router.put("/{transfer_id}/approve")
async def approve_transfer(
    transfer_id: str,
    approval: TransferApproval,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """批准转会请求"""
    
    state_machine = TransferStateMachine(db, EventBus())
    
    try:
        success = await state_machine.transition_to(
            transfer_id=transfer_id,
            new_status=TransferStatus.APPROVED,
            operator=current_user.id,
            notes=approval.notes
        )
        
        if success:
            return {"message": "Transfer approved successfully"}
        else:
            raise HTTPException(400, "Failed to approve transfer")
            
    except ValueError as e:
        raise HTTPException(400, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))

@router.get("/market-analysis")
async def get_market_analysis(
    region_id: str = Query(...),
    season_id: str = Query(...),
    position: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """获取转会市场分析"""
    
    analytics = TransferAnalytics(db)
    trends = await analytics.get_market_trends(region_id, season_id, position)
    
    return {
        "region_id": region_id,
        "season_id": season_id,
        "position": position,
        "market_trends": trends
    }

@router.get("/history/{player_id}")
async def get_player_transfer_history(
    player_id: str,
    limit: int = Query(10, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """获取选手转会历史"""
    
    history = await db.execute(
        select(TransferHistory)
        .where(TransferHistory.player_id == player_id)
        .order_by(desc(TransferHistory.completed_at))
        .limit(limit)
        .offset(offset)
    )
    
    transfers = history.scalars().all()
    
    return {
        "player_id": player_id,
        "transfers": [
            {
                "id": t.id,
                "from_team": t.from_team.name if t.from_team else None,
                "to_team": t.to_team.name,
                "transfer_fee": float(t.transfer_fee) if t.transfer_fee else None,
                "salary": float(t.salary),
                "contract_duration_days": t.contract_duration_days,
                "completed_at": t.completed_at.isoformat(),
                "transfer_type": t.transfer_type
            }
            for t in transfers
        ]
    }
```

## 10. 性能优化与监控

### 10.1 缓存策略

```python
class TransferCacheManager:
    """转会缓存管理器"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.default_ttl = 3600  # 1小时
    
    async def cache_transfer_fee_calculation(
        self,
        calculation_params: dict,
        result: Decimal
    ):
        """缓存转会费计算结果"""
        cache_key = f"transfer_fee:{hash(str(calculation_params))}"
        await self.redis.setex(
            cache_key,
            self.default_ttl,
            str(result)
        )
    
    async def get_cached_transfer_fee(self, calculation_params: dict) -> Optional[Decimal]:
        """获取缓存的转会费"""
        cache_key = f"transfer_fee:{hash(str(calculation_params))}"
        result = await self.redis.get(cache_key)
        return Decimal(result) if result else None
    
    async def invalidate_team_budget_cache(self, team_id: str):
        """清除战队预算缓存"""
        cache_key = f"team_budget:{team_id}"
        await self.redis.delete(cache_key)
    
    async def cache_market_analysis(
        self,
        region_id: str,
        season_id: str,
        position: Optional[str],
        analysis_data: dict
    ):
        """缓存市场分析数据"""
        cache_key = f"market_analysis:{region_id}:{season_id}:{position or 'all'}"
        await self.redis.setex(
            cache_key,
            7200,  # 2小时
            json.dumps(analysis_data, default=str)
        )

class TransferMetrics:
    """转会系统监控指标"""
    
    def __init__(self, metrics_collector):
        self.metrics = metrics_collector
    
    def record_transfer_initiated(self, transfer_type: TransferType):
        """记录转会发起"""
        self.metrics.counter("transfer_initiated_total").labels(
            type=transfer_type
        ).inc()
    
    def record_transfer_completed(self, transfer_type: TransferType, duration_seconds: float):
        """记录转会完成"""
        self.metrics.counter("transfer_completed_total").labels(
            type=transfer_type
        ).inc()
        
        self.metrics.histogram("transfer_duration_seconds").labels(
            type=transfer_type
        ).observe(duration_seconds)
    
    def record_transfer_failed(self, transfer_type: TransferType, error_type: str):
        """记录转会失败"""
        self.metrics.counter("transfer_failed_total").labels(
            type=transfer_type,
            error=error_type
        ).inc()
```

## 11. 总结

转会系统设计涵盖了选手状态管理、转会窗口管理、转会费计算、状态机流程控制、异步处理等核心功能。系统采用事件驱动架构，支持复杂的业务规则，并通过缓存和监控确保高性能和可靠性。

关键设计亮点：
- 基于状态机的转会流程控制，确保状态转换的正确性
- 动态转会费计算，考虑多种市场因素
- 选手锁定机制，避免并发转会冲突
- 异步处理架构，支持大规模转会操作
- 完整的事件通知系统，保证信息及时传达
- 丰富的数据分析功能，支持市场趋势分析

该系统为 FlyEsports 平台提供了完整的转会管理解决方案，既满足当前业务需求，又具备良好的扩展性和可维护性。