# FlyEsports 异步处理架构设计

## 目录
- [1. 异步处理概述](#1-异步处理概述)
- [2. Celery任务队列架构](#2-celery任务队列架构)
- [3. 事件驱动架构](#3-事件驱动架构)
- [4. 消息队列设计](#4-消息队列设计)
- [5. 任务分类与优先级](#5-任务分类与优先级)
- [6. 任务监控与重试](#6-任务监控与重试)
- [7. 分布式任务调度](#7-分布式任务调度)
- [8. 性能优化策略](#8-性能优化策略)
- [9. 错误处理与恢复](#9-错误处理与恢复)
- [10. 运维监控方案](#10-运维监控方案)

## 1. 异步处理概述

### 1.1 设计目标

FlyEsports异步处理系统旨在解决以下核心问题：
- **响应性**: 保证API接口的快速响应，避免长时间阻塞
- **可靠性**: 确保重要业务任务最终能够成功执行
- **可扩展性**: 支持水平扩展，应对业务增长
- **可观测性**: 提供完整的任务执行监控和报警机制

### 1.2 异步场景识别

```python
# 需要异步处理的业务场景
ASYNC_SCENARIOS = {
    # 计算密集型任务
    'rating_calculation': {
        'description': '选手评分计算',
        'estimated_time': '5-30秒',
        'priority': 'HIGH',
        'retry_policy': 'exponential_backoff'
    },
    
    'six_dimension_analysis': {
        'description': '6维度性能分析',
        'estimated_time': '10-60秒', 
        'priority': 'MEDIUM',
        'retry_policy': 'linear_backoff'
    },
    
    # I/O密集型任务
    'riot_api_sync': {
        'description': 'Riot API数据同步',
        'estimated_time': '30-120秒',
        'priority': 'MEDIUM',
        'retry_policy': 'exponential_backoff'
    },
    
    'email_notifications': {
        'description': '邮件通知发送',
        'estimated_time': '5-15秒',
        'priority': 'LOW',
        'retry_policy': 'linear_backoff'
    },
    
    # 批量处理任务
    'leaderboard_rebuild': {
        'description': '排行榜重建',
        'estimated_time': '60-300秒',
        'priority': 'MEDIUM',
        'retry_policy': 'no_retry'
    },
    
    'daily_statistics': {
        'description': '每日统计报告生成',
        'estimated_time': '300-1800秒',
        'priority': 'LOW',
        'retry_policy': 'single_retry'
    }
}
```

### 1.3 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway Layer                        │
│          (接收请求，立即返回task_id)                          │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                  Message Broker Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │  Redis Cluster  │  │  RabbitMQ       │  │  Event Store    ││
│  │   (Primary)     │  │  (Backup)       │  │  (Persistent)   ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                   Worker Pool Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │ High Priority   │  │ Medium Priority │  │  Low Priority   ││
│  │   Workers       │  │    Workers      │  │    Workers      ││
│  │   (4 nodes)     │  │   (2 nodes)     │  │   (1 node)      ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                  Result Storage Layer                       │
│          Redis (Task Results) + Database (Audit)           │
└─────────────────────────────────────────────────────────────┘
```

## 2. Celery任务队列架构

### 2.1 Celery配置

```python
# src/infrastructure/tasks/celery_config.py
from celery import Celery
from kombu import Exchange, Queue
from datetime import timedelta
import os

# Celery应用实例
celery_app = Celery('flyesports')

# Broker配置 - 使用Redis作为主要消息代理
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

# 队列配置
CELERY_TASK_QUEUES = (
    # 高优先级队列 - 用户直接交互的任务
    Queue(
        'high_priority',
        Exchange('high_priority', type='direct'),
        routing_key='high_priority',
        queue_arguments={
            'x-max-priority': 10,
            'x-message-ttl': 300000,  # 5分钟TTL
            'x-max-length': 10000,    # 最大队列长度
        }
    ),
    
    # 中等优先级队列 - 系统维护任务
    Queue(
        'medium_priority',
        Exchange('medium_priority', type='direct'),
        routing_key='medium_priority',
        queue_arguments={
            'x-max-priority': 5,
            'x-message-ttl': 1800000,  # 30分钟TTL
            'x-max-length': 50000,
        }
    ),
    
    # 低优先级队列 - 批量处理任务
    Queue(
        'low_priority',
        Exchange('low_priority', type='direct'),
        routing_key='low_priority',
        queue_arguments={
            'x-max-priority': 1,
            'x-message-ttl': 3600000,  # 1小时TTL
            'x-max-length': 100000,
        }
    ),
    
    # 死信队列 - 处理失败的任务
    Queue(
        'dead_letter',
        Exchange('dead_letter', type='direct'),
        routing_key='dead_letter',
        queue_arguments={
            'x-message-ttl': 86400000,  # 24小时TTL
        }
    ),
)

# 任务路由配置
CELERY_TASK_ROUTES = {
    # 评分计算任务 - 高优先级
    'flyesports.tasks.rating.*': {
        'queue': 'high_priority',
        'routing_key': 'high_priority',
    },
    
    # 匹配处理任务 - 高优先级
    'flyesports.tasks.matches.*': {
        'queue': 'high_priority', 
        'routing_key': 'high_priority',
    },
    
    # 排行榜更新任务 - 中等优先级
    'flyesports.tasks.leaderboard.*': {
        'queue': 'medium_priority',
        'routing_key': 'medium_priority',
    },
    
    # 数据同步任务 - 中等优先级
    'flyesports.tasks.sync.*': {
        'queue': 'medium_priority',
        'routing_key': 'medium_priority',
    },
    
    # 报告生成任务 - 低优先级
    'flyesports.tasks.reports.*': {
        'queue': 'low_priority',
        'routing_key': 'low_priority',
    },
    
    # 通知任务 - 低优先级
    'flyesports.tasks.notifications.*': {
        'queue': 'low_priority',
        'routing_key': 'low_priority',
    },
}

# Celery应用配置
celery_app.conf.update(
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    task_queues=CELERY_TASK_QUEUES,
    task_routes=CELERY_TASK_ROUTES,
    
    # 序列化设置
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    
    # 时区设置
    timezone='UTC',
    enable_utc=True,
    
    # 任务执行设置
    task_acks_late=True,                    # 任务完成后再确认
    task_reject_on_worker_lost=True,        # Worker丢失时拒绝任务
    worker_prefetch_multiplier=1,           # 预取任务数量
    task_compression='gzip',                # 任务压缩
    
    # 结果设置
    result_expires=3600,                    # 结果过期时间1小时
    task_track_started=True,                # 跟踪任务开始状态
    task_send_sent_event=True,              # 发送任务发送事件
    
    # Worker设置
    worker_send_task_events=True,           # 发送任务事件
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
    
    # 监控设置
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # 安全设置
    task_always_eager=False,                # 生产环境设为False
    task_eager_propagates=False,
    
    # 错误处理
    task_reject_on_worker_lost=True,
    task_acks_late=True,
)
```

### 2.2 基础任务类设计

```python
# src/infrastructure/tasks/base.py
from celery import Task
from celery.exceptions import Retry, WorkerLostError
from typing import Any, Optional, Dict
import logging
import time
from datetime import datetime, timedelta
from ..database.connection import get_async_session
from ..cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class BaseTask(Task):
    """基础任务类，提供通用功能"""
    
    # 重试配置
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 700
    retry_jitter = True
    
    def __init__(self):
        self.db_session = None
        self.redis_client = None
    
    def before_start(self, task_id: str, args: tuple, kwargs: dict):
        """任务开始前的钩子"""
        logger.info(f"Starting task {self.name} with ID {task_id}")
        
        # 记录任务开始时间
        self.start_time = time.time()
        
        # 初始化数据库连接
        self.db_session = get_async_session()
        self.redis_client = get_redis_client()
        
        # 记录任务状态到Redis
        task_info = {
            'task_id': task_id,
            'task_name': self.name,
            'status': 'STARTED',
            'started_at': datetime.utcnow().isoformat(),
            'args': str(args),
            'kwargs': str(kwargs)
        }
        self.redis_client.setex(
            f"task:status:{task_id}", 
            3600,  # 1小时过期
            json.dumps(task_info)
        )
    
    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict):
        """任务成功完成的钩子"""
        execution_time = time.time() - self.start_time
        logger.info(f"Task {self.name}[{task_id}] succeeded in {execution_time:.2f}s")
        
        # 更新任务状态
        task_info = {
            'task_id': task_id,
            'task_name': self.name,
            'status': 'SUCCESS',
            'completed_at': datetime.utcnow().isoformat(),
            'execution_time': execution_time,
            'result': str(retval)[:1000]  # 限制结果长度
        }
        self.redis_client.setex(
            f"task:status:{task_id}",
            3600,
            json.dumps(task_info)
        )
        
        # 清理资源
        self._cleanup_resources()
    
    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo):
        """任务失败的钩子"""
        execution_time = time.time() - self.start_time
        logger.error(f"Task {self.name}[{task_id}] failed after {execution_time:.2f}s: {exc}")
        
        # 更新任务状态
        task_info = {
            'task_id': task_id,
            'task_name': self.name,
            'status': 'FAILURE',
            'failed_at': datetime.utcnow().isoformat(),
            'execution_time': execution_time,
            'error': str(exc),
            'traceback': str(einfo)
        }
        self.redis_client.setex(
            f"task:status:{task_id}",
            86400,  # 失败任务保存24小时
            json.dumps(task_info)
        )
        
        # 清理资源
        self._cleanup_resources()
    
    def on_retry(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo):
        """任务重试的钩子"""
        logger.warning(f"Task {self.name}[{task_id}] retry #{self.request.retries}: {exc}")
        
        # 更新任务状态
        task_info = {
            'task_id': task_id,
            'task_name': self.name,
            'status': 'RETRY',
            'retry_count': self.request.retries,
            'last_retry_at': datetime.utcnow().isoformat(),
            'error': str(exc)
        }
        self.redis_client.setex(
            f"task:status:{task_id}",
            3600,
            json.dumps(task_info)
        )
    
    def _cleanup_resources(self):
        """清理资源"""
        if self.db_session:
            self.db_session.close()
        # Redis连接池会自动管理，无需手动关闭

class RetryableTask(BaseTask):
    """可重试任务基类"""
    
    def retry_with_backoff(self, exc: Exception, **kwargs):
        """使用指数退避重试"""
        retry_count = self.request.retries
        
        # 计算退避时间
        backoff_time = min(
            self.retry_backoff_max,
            (2 ** retry_count) * self.retry_kwargs.get('countdown', 60)
        )
        
        # 添加随机抖动
        if self.retry_jitter:
            import random
            backoff_time += random.uniform(0, backoff_time * 0.1)
        
        kwargs.update({'countdown': backoff_time})
        raise self.retry(exc=exc, **kwargs)

class CriticalTask(RetryableTask):
    """关键任务基类 - 失败后需要告警"""
    
    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo):
        """关键任务失败处理"""
        super().on_failure(exc, task_id, args, kwargs, einfo)
        
        # 发送告警
        self._send_critical_alert(task_id, exc, args, kwargs)
    
    def _send_critical_alert(self, task_id: str, exc: Exception, args: tuple, kwargs: dict):
        """发送关键任务失败告警"""
        from ..notifications.alert_service import AlertService
        
        alert_service = AlertService()
        alert_service.send_task_failure_alert(
            task_id=task_id,
            task_name=self.name,
            exception=exc,
            args=args,
            kwargs=kwargs
        )
```

## 3. 事件驱动架构

### 3.1 事件总线设计

```python
# src/infrastructure/events/event_bus.py
from abc import ABC, abstractmethod
from typing import List, Callable, Dict, Type, Any
import asyncio
import json
import logging
from datetime import datetime
from ..cache.redis_client import get_redis_client
from ...domain.events.base import DomainEvent

logger = logging.getLogger(__name__)

class EventBus(ABC):
    """事件总线抽象基类"""
    
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """发布事件"""
        pass
    
    @abstractmethod
    async def subscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        """订阅事件"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        """取消订阅"""
        pass

class RedisEventBus(EventBus):
    """基于Redis Streams的事件总线"""
    
    def __init__(self):
        self.redis = get_redis_client()
        self.handlers: Dict[str, List[Callable]] = {}
        self.consumer_tasks: List[asyncio.Task] = []
        self.consumer_groups: Dict[str, str] = {}
    
    async def publish(self, event: DomainEvent) -> None:
        """发布事件到Redis Stream"""
        try:
            stream_name = f"events:{event.__class__.__name__}"
            event_data = event.to_dict()
            
            # 添加发布时间戳
            event_data['published_at'] = datetime.utcnow().isoformat()
            
            # 发布到Redis Stream
            message_id = await self.redis.xadd(stream_name, event_data)
            
            logger.info(f"Published event {event.__class__.__name__} to stream {stream_name} with ID {message_id}")
            
            # 可选：同时发布到pub/sub频道用于实时通知
            await self.redis.publish(f"notifications:{stream_name}", json.dumps(event_data))
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.__class__.__name__}: {e}")
            raise
    
    async def subscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        """订阅事件"""
        event_name = event_type.__name__
        
        if event_name not in self.handlers:
            self.handlers[event_name] = []
            # 启动消费者任务
            await self._start_consumer_for_event(event_name)
        
        self.handlers[event_name].append(handler)
        logger.info(f"Subscribed handler {handler.__name__} to event {event_name}")
    
    async def unsubscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        """取消订阅"""
        event_name = event_type.__name__
        
        if event_name in self.handlers:
            if handler in self.handlers[event_name]:
                self.handlers[event_name].remove(handler)
                logger.info(f"Unsubscribed handler {handler.__name__} from event {event_name}")
    
    async def _start_consumer_for_event(self, event_name: str):
        """为特定事件启动消费者"""
        stream_name = f"events:{event_name}"
        group_name = f"handlers_{event_name}"
        consumer_name = f"consumer_{event_name}_{id(self)}"
        
        # 创建消费者组
        try:
            await self.redis.xgroup_create(stream_name, group_name, id='0', mkstream=True)
        except Exception:
            # 组可能已存在
            pass
        
        self.consumer_groups[event_name] = group_name
        
        # 启动消费者任务
        consumer_task = asyncio.create_task(
            self._consume_event_stream(stream_name, group_name, consumer_name, event_name)
        )
        self.consumer_tasks.append(consumer_task)
    
    async def _consume_event_stream(
        self, 
        stream_name: str, 
        group_name: str, 
        consumer_name: str, 
        event_name: str
    ):
        """消费事件流"""
        logger.info(f"Starting consumer for stream {stream_name}")
        
        while True:
            try:
                # 读取消息
                messages = await self.redis.xreadgroup(
                    group_name,
                    consumer_name,
                    {stream_name: '>'},
                    count=10,
                    block=1000  # 阻塞1秒
                )
                
                for stream, events in messages:
                    for event_id, fields in events:
                        await self._process_event(stream_name, event_id, fields, event_name)
                        
            except asyncio.CancelledError:
                logger.info(f"Consumer for {stream_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Error in consumer for {stream_name}: {e}")
                await asyncio.sleep(5)  # 错误后等待5秒再继续
    
    async def _process_event(
        self, 
        stream_name: str, 
        event_id: str, 
        fields: Dict[str, Any], 
        event_name: str
    ):
        """处理单个事件"""
        try:
            # 获取事件处理器
            handlers = self.handlers.get(event_name, [])
            
            if not handlers:
                logger.warning(f"No handlers found for event {event_name}")
                await self.redis.xack(stream_name, self.consumer_groups[event_name], event_id)
                return
            
            # 并行执行所有处理器
            handler_tasks = []
            for handler in handlers:
                if asyncio.iscoroutinefunction(handler):
                    task = asyncio.create_task(handler(fields))
                else:
                    # 同步处理器在线程池中执行
                    task = asyncio.create_task(
                        asyncio.get_event_loop().run_in_executor(None, handler, fields)
                    )
                handler_tasks.append(task)
            
            # 等待所有处理器完成
            results = await asyncio.gather(*handler_tasks, return_exceptions=True)
            
            # 检查是否有处理器失败
            failed_handlers = [
                (i, result) for i, result in enumerate(results) 
                if isinstance(result, Exception)
            ]
            
            if failed_handlers:
                logger.error(f"Some handlers failed for event {event_name}: {failed_handlers}")
                # 可以选择不确认消息，让其重试
                return
            
            # 确认消息处理完成
            await self.redis.xack(stream_name, self.consumer_groups[event_name], event_id)
            logger.debug(f"Successfully processed event {event_id} from stream {stream_name}")
            
        except Exception as e:
            logger.error(f"Failed to process event {event_id} from stream {stream_name}: {e}")
            # 不确认消息，让其可以重试

class EventHandler:
    """事件处理器基类"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.db_session = None
        self.redis_client = None
    
    async def initialize(self):
        """初始化处理器"""
        self.db_session = get_async_session()
        self.redis_client = get_redis_client()
    
    async def handle(self, event_data: Dict[str, Any]) -> None:
        """处理事件 - 子类需要重写此方法"""
        raise NotImplementedError
    
    async def cleanup(self):
        """清理资源"""
        if self.db_session:
            await self.db_session.close()
```

### 3.2 具体事件处理器

```python
# src/application/event_handlers/player_event_handlers.py
from ..infrastructure.events.event_bus import EventHandler
from ..infrastructure.tasks.rating_tasks import calculate_player_rating_task
from ..infrastructure.tasks.leaderboard_tasks import update_leaderboard_task
from ..infrastructure.tasks.notification_tasks import send_rating_update_notification
import logging

logger = logging.getLogger(__name__)

class PlayerRatingUpdatedEventHandler(EventHandler):
    """选手评分更新事件处理器"""
    
    async def handle(self, event_data: dict) -> None:
        """处理选手评分更新事件"""
        try:
            profile_id = event_data['profile_id']
            old_rating = event_data['old_rating']
            new_rating = event_data['new_rating']
            region_id = event_data.get('region_id')
            
            logger.info(f"Handling rating update for player {profile_id}: {old_rating} -> {new_rating}")
            
            # 1. 异步更新排行榜
            if region_id:
                update_leaderboard_task.delay(region_id, profile_id, new_rating)
            
            # 2. 清除相关缓存
            await self._invalidate_player_cache(profile_id)
            
            # 3. 发送通知（如果评分变化显著）
            rating_change = abs(new_rating - old_rating)
            if rating_change > 5.0:  # 评分变化超过5分
                send_rating_update_notification.delay(
                    profile_id, old_rating, new_rating, rating_change
                )
            
            # 4. 更新选手统计数据
            await self._update_player_statistics(profile_id, new_rating)
            
        except Exception as e:
            logger.error(f"Failed to handle PlayerRatingUpdatedEvent: {e}")
            raise
    
    async def _invalidate_player_cache(self, profile_id: str):
        """清除选手相关缓存"""
        cache_keys = [
            f"player:profile:{profile_id}",
            f"player:rating:{profile_id}",
            f"player:stats:{profile_id}:*"
        ]
        
        for key in cache_keys:
            if '*' in key:
                # 模式匹配删除
                keys = await self.redis_client.keys(key)
                if keys:
                    await self.redis_client.delete(*keys)
            else:
                await self.redis_client.delete(key)
    
    async def _update_player_statistics(self, profile_id: str, new_rating: float):
        """更新选手统计数据"""
        # 这里可以更新各种统计指标
        # 比如最高评分、评分历史趋势等
        stats_key = f"player:stats:{profile_id}"
        current_stats = await self.redis_client.hgetall(stats_key)
        
        # 更新最高评分
        highest_rating = max(
            float(current_stats.get('highest_rating', 0)),
            new_rating
        )
        
        await self.redis_client.hset(stats_key, 'highest_rating', highest_rating)
        await self.redis_client.hset(stats_key, 'latest_rating', new_rating)
        await self.redis_client.expire(stats_key, 86400)  # 24小时过期

class PlayerSignedEventHandler(EventHandler):
    """选手签约事件处理器"""
    
    async def handle(self, event_data: dict) -> None:
        """处理选手签约事件"""
        try:
            profile_id = event_data['profile_id']
            team_id = event_data['team_id']
            locked_rating = event_data['locked_rating']
            
            logger.info(f"Handling player signing: {profile_id} -> {team_id} at rating {locked_rating}")
            
            # 1. 更新战队缓存
            await self._update_team_cache(team_id)
            
            # 2. 更新选手状态缓存
            await self._update_player_status_cache(profile_id, 'LOCKED', team_id)
            
            # 3. 发送签约通知
            from ..tasks.notification_tasks import send_player_signed_notification
            send_player_signed_notification.delay(profile_id, team_id, locked_rating)
            
            # 4. 更新赛区统计
            region_id = event_data.get('region_id')
            if region_id:
                await self._update_region_statistics(region_id, 'player_signed')
                
        except Exception as e:
            logger.error(f"Failed to handle PlayerSignedEvent: {e}")
            raise
    
    async def _update_team_cache(self, team_id: str):
        """更新战队缓存"""
        # 清除战队相关缓存，强制重新加载
        cache_keys = [
            f"team:profile:{team_id}",
            f"team:roster:{team_id}",
            f"team:cost:{team_id}"
        ]
        await self.redis_client.delete(*cache_keys)
    
    async def _update_player_status_cache(self, profile_id: str, status: str, team_id: str = None):
        """更新选手状态缓存"""
        status_key = f"player:status:{profile_id}"
        await self.redis_client.hset(status_key, 'contract_status', status)
        if team_id:
            await self.redis_client.hset(status_key, 'current_team_id', team_id)
        await self.redis_client.expire(status_key, 3600)  # 1小时过期
    
    async def _update_region_statistics(self, region_id: str, event_type: str):
        """更新赛区统计"""
        stats_key = f"region:stats:{region_id}"
        await self.redis_client.hincrby(stats_key, f"{event_type}_count", 1)
        await self.redis_client.hset(stats_key, 'last_activity', datetime.utcnow().isoformat())
        await self.redis_client.expire(stats_key, 86400)  # 24小时过期
```

## 4. 消息队列设计

### 4.1 队列管理

```python
# src/infrastructure/tasks/queue_manager.py
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass
from ..cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)

@dataclass
class QueueStats:
    """队列统计信息"""
    name: str
    length: int
    workers: int
    processing: int
    processed_total: int
    failed_total: int
    avg_processing_time: float

class QueueManager:
    """队列管理器"""
    
    def __init__(self):
        self.redis = get_redis_client()
        self.queue_configs = {
            'high_priority': {
                'max_length': 10000,
                'max_workers': 8,
                'alert_threshold': 1000
            },
            'medium_priority': {
                'max_length': 50000,
                'max_workers': 4,
                'alert_threshold': 5000
            },
            'low_priority': {
                'max_length': 100000,
                'max_workers': 2,
                'alert_threshold': 10000
            }
        }
    
    async def get_queue_stats(self, queue_name: str) -> Optional[QueueStats]:
        """获取队列统计信息"""
        try:
            # 从Celery获取队列长度
            queue_length = await self._get_celery_queue_length(queue_name)
            
            # 从Redis获取统计数据
            stats_key = f"queue:stats:{queue_name}"
            stats = await self.redis.hgetall(stats_key)
            
            return QueueStats(
                name=queue_name,
                length=queue_length,
                workers=int(stats.get('workers', 0)),
                processing=int(stats.get('processing', 0)),
                processed_total=int(stats.get('processed_total', 0)),
                failed_total=int(stats.get('failed_total', 0)),
                avg_processing_time=float(stats.get('avg_processing_time', 0))
            )
            
        except Exception as e:
            logger.error(f"Failed to get queue stats for {queue_name}: {e}")
            return None
    
    async def monitor_queue_health(self, queue_name: str) -> Dict[str, any]:
        """监控队列健康状态"""
        stats = await self.get_queue_stats(queue_name)
        if not stats:
            return {'status': 'unknown', 'alerts': ['Failed to get queue stats']}
        
        alerts = []
        status = 'healthy'
        
        config = self.queue_configs.get(queue_name, {})
        
        # 检查队列长度
        alert_threshold = config.get('alert_threshold', 1000)
        if stats.length > alert_threshold:
            alerts.append(f"Queue length ({stats.length}) exceeds threshold ({alert_threshold})")
            status = 'warning'
        
        # 检查工作进程数
        max_workers = config.get('max_workers', 4)
        if stats.workers < max_workers * 0.5:  # 少于50%的工作进程
            alerts.append(f"Low worker count ({stats.workers}/{max_workers})")
            status = 'warning'
        
        # 检查失败率
        if stats.processed_total > 0:
            failure_rate = stats.failed_total / (stats.processed_total + stats.failed_total) * 100
            if failure_rate > 10:  # 失败率超过10%
                alerts.append(f"High failure rate ({failure_rate:.1f}%)")
                status = 'critical'
        
        # 检查处理时间
        if stats.avg_processing_time > 300:  # 平均处理时间超过5分钟
            alerts.append(f"High avg processing time ({stats.avg_processing_time:.1f}s)")
            if status != 'critical':
                status = 'warning'
        
        return {
            'status': status,
            'stats': stats,
            'alerts': alerts
        }
    
    async def _get_celery_queue_length(self, queue_name: str) -> int:
        """获取Celery队列长度"""
        # 这里需要根据实际的Celery配置来实现
        # 可能需要通过Redis或RabbitMQ的API来获取
        try:
            # 如果使用Redis作为broker
            queue_key = f"celery:queue:{queue_name}"
            return await self.redis.llen(queue_key)
        except Exception:
            return 0
    
    async def purge_failed_tasks(self, queue_name: str, max_age_hours: int = 24) -> int:
        """清理失败的任务"""
        try:
            # 获取失败任务的键模式
            failed_pattern = f"celery-task-meta-*"
            failed_keys = await self.redis.keys(failed_pattern)
            
            purged_count = 0
            current_time = time.time()
            
            for key in failed_keys:
                task_data = await self.redis.get(key)
                if task_data:
                    task_info = json.loads(task_data)
                    
                    # 检查是否是失败的任务且超过指定时间
                    if (task_info.get('status') == 'FAILURE' and
                        current_time - task_info.get('date_done', 0) > max_age_hours * 3600):
                        await self.redis.delete(key)
                        purged_count += 1
            
            logger.info(f"Purged {purged_count} failed tasks from {queue_name}")
            return purged_count
            
        except Exception as e:
            logger.error(f"Failed to purge failed tasks from {queue_name}: {e}")
            return 0

# 队列监控任务
from celery.schedules import crontab

@celery_app.task(bind=True)
def monitor_queue_health_task(self):
    """定期监控队列健康状态"""
    queue_manager = QueueManager()
    
    async def _monitor():
        for queue_name in ['high_priority', 'medium_priority', 'low_priority']:
            health = await queue_manager.monitor_queue_health(queue_name)
            
            if health['status'] in ['warning', 'critical']:
                # 发送告警
                from ..notifications.alert_service import AlertService
                alert_service = AlertService()
                await alert_service.send_queue_alert(queue_name, health)
    
    # 运行异步监控
    import asyncio
    asyncio.run(_monitor())

# 添加到定时任务
celery_app.conf.beat_schedule.update({
    'monitor-queue-health': {
        'task': 'monitor_queue_health_task',
        'schedule': crontab(minute='*/5'),  # 每5分钟检查一次
    },
})
```

### 4.2 死信队列处理

```python
# src/infrastructure/tasks/dead_letter_handler.py
from typing import List, Dict, Any
import json
import logging
from datetime import datetime, timedelta
from .base import BaseTask

logger = logging.getLogger(__name__)

class DeadLetterHandler:
    """死信队列处理器"""
    
    def __init__(self):
        self.redis = get_redis_client()
        self.max_retry_attempts = 3
        self.dead_letter_retention = timedelta(days=7)  # 保留7天
    
    async def process_dead_letters(self) -> Dict[str, int]:
        """处理死信队列中的消息"""
        stats = {
            'processed': 0,
            'requeued': 0,
            'discarded': 0,
            'errors': 0
        }
        
        try:
            # 获取死信队列中的消息
            dead_letters = await self._get_dead_letter_messages()
            
            for message in dead_letters:
                try:
                    stats['processed'] += 1
                    
                    # 分析失败原因
                    failure_reason = await self._analyze_failure(message)
                    
                    # 决定如何处理
                    action = await self._decide_action(message, failure_reason)
                    
                    if action == 'requeue':
                        await self._requeue_message(message)
                        stats['requeued'] += 1
                    elif action == 'discard':
                        await self._discard_message(message)
                        stats['discarded'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing dead letter {message.get('id', 'unknown')}: {e}")
                    stats['errors'] += 1
            
            logger.info(f"Dead letter processing complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to process dead letters: {e}")
            stats['errors'] += 1
            return stats
    
    async def _get_dead_letter_messages(self) -> List[Dict[str, Any]]:
        """获取死信队列中的消息"""
        try:
            # 从Redis获取死信消息
            messages = []
            cursor = 0
            
            while True:
                cursor, keys = await self.redis.scan(
                    cursor, 
                    match="dead_letter:*", 
                    count=100
                )
                
                if keys:
                    values = await self.redis.mget(keys)
                    for key, value in zip(keys, values):
                        if value:
                            try:
                                message = json.loads(value)
                                message['key'] = key
                                messages.append(message)
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON in dead letter {key}")
                
                if cursor == 0:
                    break
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get dead letter messages: {e}")
            return []
    
    async def _analyze_failure(self, message: Dict[str, Any]) -> str:
        """分析失败原因"""
        try:
            error_info = message.get('error', {})
            error_type = error_info.get('type', 'unknown')
            error_message = error_info.get('message', '')
            
            # 根据错误类型分类
            if 'ConnectionError' in error_type or 'TimeoutError' in error_type:
                return 'network_issue'
            elif 'ValidationError' in error_type:
                return 'data_validation'
            elif 'PermissionError' in error_type or 'Unauthorized' in error_message:
                return 'permission_issue'
            elif 'ResourceNotFound' in error_type:
                return 'missing_resource'
            else:
                return 'unknown_error'
                
        except Exception:
            return 'analysis_failed'
    
    async def _decide_action(self, message: Dict[str, Any], failure_reason: str) -> str:
        """决定如何处理失败的消息"""
        try:
            retry_count = message.get('retry_count', 0)
            task_age = datetime.utcnow() - datetime.fromisoformat(message.get('created_at', ''))
            
            # 检查重试次数
            if retry_count >= self.max_retry_attempts:
                return 'discard'
            
            # 检查消息年龄
            if task_age > self.dead_letter_retention:
                return 'discard'
            
            # 根据失败原因决定
            if failure_reason == 'network_issue':
                # 网络问题可以重试
                return 'requeue'
            elif failure_reason == 'data_validation':
                # 数据验证错误通常不应该重试
                return 'discard'
            elif failure_reason == 'permission_issue':
                # 权限问题需要人工干预
                await self._escalate_to_admin(message, failure_reason)
                return 'discard'
            else:
                # 其他情况谨慎重试
                if retry_count < 2:
                    return 'requeue'
                else:
                    return 'discard'
                    
        except Exception as e:
            logger.error(f"Failed to decide action for message: {e}")
            return 'discard'
    
    async def _requeue_message(self, message: Dict[str, Any]):
        """重新排队消息"""
        try:
            # 增加重试计数
            message['retry_count'] = message.get('retry_count', 0) + 1
            message['requeued_at'] = datetime.utcnow().isoformat()
            
            # 确定目标队列
            original_queue = message.get('queue', 'medium_priority')
            
            # 重新提交到Celery
            from celery import current_app
            current_app.send_task(
                message['task'],
                args=message.get('args', []),
                kwargs=message.get('kwargs', {}),
                queue=original_queue,
                countdown=60 * (2 ** message['retry_count'])  # 指数退避
            )
            
            # 从死信队列中移除
            await self.redis.delete(message['key'])
            
            logger.info(f"Requeued message {message.get('id')} to {original_queue}")
            
        except Exception as e:
            logger.error(f"Failed to requeue message: {e}")
            raise
    
    async def _discard_message(self, message: Dict[str, Any]):
        """丢弃消息"""
        try:
            # 记录到审计日志
            await self._log_discarded_message(message)
            
            # 从死信队列中移除
            await self.redis.delete(message['key'])
            
            logger.info(f"Discarded message {message.get('id')}")
            
        except Exception as e:
            logger.error(f"Failed to discard message: {e}")
            raise
    
    async def _escalate_to_admin(self, message: Dict[str, Any], reason: str):
        """升级到管理员处理"""
        try:
            from ..notifications.alert_service import AlertService
            
            alert_service = AlertService()
            await alert_service.send_dead_letter_alert(message, reason)
            
        except Exception as e:
            logger.error(f"Failed to escalate dead letter to admin: {e}")
    
    async def _log_discarded_message(self, message: Dict[str, Any]):
        """记录被丢弃的消息"""
        try:
            log_entry = {
                'message_id': message.get('id'),
                'task': message.get('task'),
                'discarded_at': datetime.utcnow().isoformat(),
                'reason': 'dead_letter_processing',
                'retry_count': message.get('retry_count', 0),
                'original_error': message.get('error', {})
            }
            
            # 保存到审计日志
            audit_key = f"audit:dead_letters:{datetime.utcnow().strftime('%Y-%m-%d')}"
            await self.redis.lpush(audit_key, json.dumps(log_entry))
            await self.redis.expire(audit_key, 86400 * 30)  # 保留30天
            
        except Exception as e:
            logger.error(f"Failed to log discarded message: {e}")

# 定时处理死信队列的任务
@celery_app.task(bind=True)
def process_dead_letters_task(self):
    """定期处理死信队列"""
    handler = DeadLetterHandler()
    
    async def _process():
        return await handler.process_dead_letters()
    
    # 运行处理
    import asyncio
    stats = asyncio.run(_process())
    
    return stats

# 添加到定时任务（每小时执行一次）
celery_app.conf.beat_schedule.update({
    'process-dead-letters': {
        'task': 'process_dead_letters_task',
        'schedule': crontab(minute=0),  # 每小时执行
    },
})
```

## 5. 任务分类与优先级

### 5.1 任务分类体系

```python
# src/infrastructure/tasks/task_registry.py
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging

class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0    # 关键任务，最高优先级
    HIGH = 1        # 高优先级，用户直接交互
    MEDIUM = 2      # 中等优先级，系统维护
    LOW = 3         # 低优先级，批量处理
    BACKGROUND = 4  # 后台任务，最低优先级

class TaskCategory(Enum):
    """任务类别"""
    RATING = "rating"               # 评分计算
    MATCH = "match"                 # 比赛处理
    LEADERBOARD = "leaderboard"     # 排行榜更新
    NOTIFICATION = "notification"   # 通知发送
    SYNC = "sync"                   # 数据同步
    REPORT = "report"               # 报告生成
    MAINTENANCE = "maintenance"     # 系统维护
    CLEANUP = "cleanup"             # 数据清理

@dataclass
class TaskConfig:
    """任务配置"""
    name: str
    category: TaskCategory
    priority: TaskPriority
    queue: str
    max_retries: int = 3
    timeout: int = 300  # 5分钟
    rate_limit: Optional[str] = None
    depends_on: Optional[list] = None
    description: str = ""

class TaskRegistry:
    """任务注册表"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskConfig] = {}
        self._register_default_tasks()
    
    def _register_default_tasks(self):
        """注册默认任务配置"""
        
        # 评分计算任务
        self.register(TaskConfig(
            name="calculate_player_rating",
            category=TaskCategory.RATING,
            priority=TaskPriority.HIGH,
            queue="high_priority",
            max_retries=3,
            timeout=60,
            rate_limit="10/m",  # 每分钟最多10个
            description="计算单个选手的评分更新"
        ))
        
        self.register(TaskConfig(
            name="batch_calculate_ratings",
            category=TaskCategory.RATING,
            priority=TaskPriority.MEDIUM,
            queue="medium_priority",
            max_retries=2,
            timeout=300,
            rate_limit="2/m",
            description="批量计算多个选手评分"
        ))
        
        # 比赛处理任务
        self.register(TaskConfig(
            name="process_match_result",
            category=TaskCategory.MATCH,
            priority=TaskPriority.CRITICAL,
            queue="high_priority",
            max_retries=5,
            timeout=120,
            description="处理比赛结果"
        ))
        
        self.register(TaskConfig(
            name="analyze_six_dimensions",
            category=TaskCategory.MATCH,
            priority=TaskPriority.MEDIUM,
            queue="medium_priority",
            max_retries=3,
            timeout=180,
            description="分析6维度表现数据"
        ))
        
        # 排行榜任务
        self.register(TaskConfig(
            name="update_region_leaderboard",
            category=TaskCategory.LEADERBOARD,
            priority=TaskPriority.MEDIUM,
            queue="medium_priority",
            max_retries=2,
            timeout=180,
            rate_limit="1/30s",  # 30秒内最多1个
            description="更新赛区排行榜"
        ))
        
        self.register(TaskConfig(
            name="rebuild_all_leaderboards",
            category=TaskCategory.LEADERBOARD,
            priority=TaskPriority.LOW,
            queue="low_priority",
            max_retries=1,
            timeout=1800,
            rate_limit="1/h",  # 每小时最多1个
            description="重建所有排行榜"
        ))
        
        # 通知任务
        self.register(TaskConfig(
            name="send_email_notification",
            category=TaskCategory.NOTIFICATION,
            priority=TaskPriority.LOW,
            queue="low_priority",
            max_retries=3,
            timeout=30,
            rate_limit="100/m",
            description="发送邮件通知"
        ))
        
        # 数据同步任务
        self.register(TaskConfig(
            name="sync_riot_api_data",
            category=TaskCategory.SYNC,
            priority=TaskPriority.MEDIUM,
            queue="medium_priority",
            max_retries=5,
            timeout=300,
            rate_limit="30/m",
            description="同步Riot API数据"
        ))
        
        # 报告生成任务
        self.register(TaskConfig(
            name="generate_daily_report",
            category=TaskCategory.REPORT,
            priority=TaskPriority.BACKGROUND,
            queue="low_priority",
            max_retries=2,
            timeout=1800,
            rate_limit="1/d",
            description="生成每日报告"
        ))
        
        # 维护任务
        self.register(TaskConfig(
            name="cleanup_expired_data",
            category=TaskCategory.CLEANUP,
            priority=TaskPriority.BACKGROUND,
            queue="low_priority",
            max_retries=1,
            timeout=3600,
            rate_limit="1/d",
            description="清理过期数据"
        ))
    
    def register(self, task_config: TaskConfig):
        """注册任务配置"""
        self.tasks[task_config.name] = task_config
        logging.info(f"Registered task: {task_config.name}")
    
    def get_config(self, task_name: str) -> Optional[TaskConfig]:
        """获取任务配置"""
        return self.tasks.get(task_name)
    
    def get_tasks_by_category(self, category: TaskCategory) -> Dict[str, TaskConfig]:
        """按类别获取任务"""
        return {
            name: config for name, config in self.tasks.items() 
            if config.category == category
        }
    
    def get_tasks_by_priority(self, priority: TaskPriority) -> Dict[str, TaskConfig]:
        """按优先级获取任务"""
        return {
            name: config for name, config in self.tasks.items() 
            if config.priority == priority
        }

# 全局任务注册表实例
task_registry = TaskRegistry()
```

### 5.2 智能任务调度

```python
# src/infrastructure/tasks/smart_scheduler.py
from typing import List, Dict, Any, Optional
import asyncio
import time
import logging
from datetime import datetime, timedelta
from .task_registry import task_registry, TaskPriority, TaskCategory

logger = logging.getLogger(__name__)

class TaskScheduler:
    """智能任务调度器"""
    
    def __init__(self):
        self.redis = get_redis_client()
        self.queue_thresholds = {
            'high_priority': 1000,
            'medium_priority': 5000,
            'low_priority': 10000
        }
        self.load_balancing_enabled = True
    
    async def schedule_task(
        self,
        task_name: str,
        args: tuple = (),
        kwargs: Dict[str, Any] = None,
        eta: Optional[datetime] = None,
        countdown: Optional[int] = None
    ) -> str:
        """智能调度任务"""
        kwargs = kwargs or {}
        
        # 获取任务配置
        task_config = task_registry.get_config(task_name)
        if not task_config:
            raise ValueError(f"Task {task_name} not found in registry")
        
        # 检查速率限制
        if task_config.rate_limit:
            if not await self._check_rate_limit(task_name, task_config.rate_limit):
                raise ValueError(f"Rate limit exceeded for task {task_name}")
        
        # 选择最佳队列
        optimal_queue = await self._select_optimal_queue(task_config)
        
        # 计算优先级分数
        priority_score = await self._calculate_priority_score(task_config, args, kwargs)
        
        # 提交任务
        from celery import current_app
        result = current_app.send_task(
            task_name,
            args=args,
            kwargs=kwargs,
            queue=optimal_queue,
            priority=priority_score,
            eta=eta,
            countdown=countdown,
            retry=task_config.max_retries > 0,
            retry_policy={
                'max_retries': task_config.max_retries,
                'interval_start': 1,
                'interval_step': 2,
                'interval_max': 60,
            } if task_config.max_retries > 0 else None
        )
        
        # 记录调度信息
        await self._log_task_scheduled(task_name, result.id, optimal_queue, priority_score)
        
        return result.id
    
    async def _check_rate_limit(self, task_name: str, rate_limit: str) -> bool:
        """检查速率限制"""
        try:
            # 解析速率限制 (例如: "10/m", "1/h", "100/d")
            limit, period = rate_limit.split('/')
            limit = int(limit)
            
            period_seconds = {
                's': 1, 'm': 60, 'h': 3600, 'd': 86400
            }.get(period, 60)
            
            # 使用滑动窗口计数器
            window_key = f"rate_limit:{task_name}:{int(time.time() // period_seconds)}"
            
            current_count = await self.redis.incr(window_key)
            if current_count == 1:
                await self.redis.expire(window_key, period_seconds)
            
            return current_count <= limit
            
        except Exception as e:
            logger.error(f"Failed to check rate limit for {task_name}: {e}")
            return True  # 发生错误时允许执行
    
    async def _select_optimal_queue(self, task_config: TaskConfig) -> str:
        """选择最优队列"""
        if not self.load_balancing_enabled:
            return task_config.queue
        
        try:
            # 获取各队列的当前负载
            queue_loads = {}
            for queue_name in ['high_priority', 'medium_priority', 'low_priority']:
                queue_length = await self._get_queue_length(queue_name)
                threshold = self.queue_thresholds.get(queue_name, 1000)
                queue_loads[queue_name] = queue_length / threshold
            
            # 如果默认队列负载不高，使用默认队列
            default_queue = task_config.queue
            if queue_loads.get(default_queue, 0) < 0.8:  # 负载小于80%
                return default_queue
            
            # 否则寻找负载最低的可用队列
            priority = task_config.priority
            
            if priority in [TaskPriority.CRITICAL, TaskPriority.HIGH]:
                # 高优先级任务只能使用高优先级队列
                available_queues = ['high_priority']
            elif priority == TaskPriority.MEDIUM:
                # 中等优先级任务可以降级到低优先级队列
                available_queues = ['medium_priority', 'low_priority']
            else:
                # 低优先级任务只使用低优先级队列
                available_queues = ['low_priority']
            
            # 选择负载最低的队列
            best_queue = min(
                available_queues,
                key=lambda q: queue_loads.get(q, 0)
            )
            
            if best_queue != default_queue:
                logger.info(f"Load balancing: routing task {task_config.name} from {default_queue} to {best_queue}")
            
            return best_queue
            
        except Exception as e:
            logger.error(f"Failed to select optimal queue, using default: {e}")
            return task_config.queue
    
    async def _calculate_priority_score(
        self,
        task_config: TaskConfig,
        args: tuple,
        kwargs: Dict[str, Any]
    ) -> int:
        """计算任务优先级分数"""
        base_score = {
            TaskPriority.CRITICAL: 9,
            TaskPriority.HIGH: 7,
            TaskPriority.MEDIUM: 5,
            TaskPriority.LOW: 3,
            TaskPriority.BACKGROUND: 1
        }.get(task_config.priority, 5)
        
        # 根据任务特征调整优先级
        modifier = 0
        
        # 评分计算任务的紧急程度
        if task_config.category == TaskCategory.RATING:
            # 如果是比赛结束后的评分计算，提高优先级
            if 'match_id' in kwargs:
                modifier += 1
        
        # 用户直接触发的任务优先级更高
        if kwargs.get('user_initiated', False):
            modifier += 1
        
        # 系统资源紧张时，降低非关键任务优先级
        system_load = await self._get_system_load()
        if system_load > 0.8 and task_config.priority not in [TaskPriority.CRITICAL, TaskPriority.HIGH]:
            modifier -= 1
        
        return max(0, min(9, base_score + modifier))
    
    async def _get_queue_length(self, queue_name: str) -> int:
        """获取队列长度"""
        try:
            # 这里需要根据实际的消息队列实现
            # 如果使用Redis作为broker
            return await self.redis.llen(f"celery:queue:{queue_name}")
        except Exception:
            return 0
    
    async def _get_system_load(self) -> float:
        """获取系统负载"""
        try:
            # 简单的负载指标：所有队列的平均负载
            total_load = 0
            for queue_name, threshold in self.queue_thresholds.items():
                length = await self._get_queue_length(queue_name)
                total_load += length / threshold
            
            return total_load / len(self.queue_thresholds)
        except Exception:
            return 0.0
    
    async def _log_task_scheduled(
        self,
        task_name: str,
        task_id: str,
        queue: str,
        priority: int
    ):
        """记录任务调度信息"""
        try:
            schedule_info = {
                'task_name': task_name,
                'task_id': task_id,
                'queue': queue,
                'priority': priority,
                'scheduled_at': datetime.utcnow().isoformat()
            }
            
            # 保存到Redis，用于监控和分析
            await self.redis.lpush('task:scheduled', json.dumps(schedule_info))
            await self.redis.ltrim('task:scheduled', 0, 9999)  # 保留最近10000条
            
        except Exception as e:
            logger.error(f"Failed to log task scheduling: {e}")

# 全局任务调度器实例
task_scheduler = TaskScheduler()
```

## 继续下一部分...

由于内容很长，我将继续完成剩余部分。您希望我继续创建完整的异步处理架构设计文档吗？