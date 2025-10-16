"""
BP房间仓储实现
实现BP房间相关的数据访问操作
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import and_, or_, select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from src.domain.repositories.bp_room import BPRoomRepository
from src.infrastructure.database.models.bp_room import BPRoom, BPRoomParticipant
from src.infrastructure.database.models.dictionary import DictBPRoomStatuses, DictBPParticipantRoles
from src.infrastructure.database.connection import database_manager

logger = structlog.get_logger(__name__)


class SQLAlchemyBPRoomRepository(BPRoomRepository):
    """基于SQLAlchemy的BP房间仓储实现"""

    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session

    async def _get_session(self) -> AsyncSession:
        """获取数据库会话"""
        if self.session:
            return self.session
        return database_manager.get_session()
    
    async def _get_status_ids(self, session: AsyncSession, status_codes: list) -> list:
        """根据状态代码获取状态ID列表"""
        status_subquery = select(DictBPRoomStatuses.id).where(
            DictBPRoomStatuses.code.in_(status_codes)
        )
        result = await session.execute(status_subquery)
        return [row[0] for row in result.fetchall()]

    async def create_room(
        self,
        name: str,
        creator_user_id: int,
        description: Optional[str] = None,
        room_type_id: int = 1,
        bp_config: Optional[Dict[str, Any]] = None,
        team_a_id: Optional[int] = None,
        team_b_id: Optional[int] = None
    ) -> BPRoom:
        """创建BP房间"""
        session = await self._get_session()
        
        # 使用默认BP配置
        default_config = {
            "ban_count": 5,
            "pick_count": 5,
            "ban_time": 30,
            "pick_time": 30,
            "side_selection": "random",
            "enable_swap": True,
            "enable_chat": True
        }
        
        if bp_config:
            default_config.update(bp_config)

        # 获取默认状态ID
        status_result = await session.execute(
            select(DictBPRoomStatuses.id).where(DictBPRoomStatuses.code == "waiting")
        )
        waiting_status_id = status_result.scalar_one_or_none()

        if not waiting_status_id:
            raise ValueError("Default BP room status 'waiting' not found in dictionary")
        
        room = BPRoom(
            name=name,
            description=description,
            room_type_id=room_type_id,
            creator_user_id=creator_user_id,
            team_a_id=team_a_id,
            team_b_id=team_b_id,
            bp_config=default_config,
            status_id=waiting_status_id
        )

        session.add(room)
        await session.flush()  # 刷新以获取ID

        # 创建者自动成为管理员
        # 获取管理员角色ID
        role_result = await session.execute(
            select(DictBPParticipantRoles.id).where(DictBPParticipantRoles.code == "admin")
        )
        admin_role_id = role_result.scalar_one_or_none()

        if not admin_role_id:
            raise ValueError("BP participant role 'admin' not found in dictionary")
        
        creator_participant = BPRoomParticipant(
            room_id=room.id,
            user_id=creator_user_id,
            role_id=admin_role_id,
            is_active=True
        )
        session.add(creator_participant)

        try:
            await session.commit()
            await session.refresh(room)
            
            # 预加载关联数据
            stmt = (
                select(BPRoom)
                .where(BPRoom.id == room.id)
                .options(
                    selectinload(BPRoom.participants),
                    selectinload(BPRoom.creator),
                    selectinload(BPRoom.team_a),
                    selectinload(BPRoom.team_b)
                )
            )
            result = await session.execute(stmt)
            room = result.scalar_one_or_none()

            if not room:
                raise ValueError("BP room not found after creation")

            logger.info(
                "BP房间创建成功",
                room_id=room.id,
                name=room.name,
                creator_user_id=creator_user_id
            )
            
            return room
            
        except Exception as e:
            await session.rollback()
            logger.error("创建BP房间失败", error=str(e))
            raise

    async def get_room_by_id(self, room_id: str) -> Optional[BPRoom]:
        """根据ID获取房间"""
        session = await self._get_session()
        
        stmt = (
            select(BPRoom)
            .where(BPRoom.id == room_id)
            .options(
                selectinload(BPRoom.participants),
                selectinload(BPRoom.creator),
                selectinload(BPRoom.team_a),
                selectinload(BPRoom.team_b)
            )
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_room(self, room: BPRoom) -> BPRoom:
        """更新房间信息"""
        session = await self._get_session()
        
        try:
            session.add(room)
            await session.commit()
            await session.refresh(room)
            return room
        except Exception as e:
            await session.rollback()
            logger.error("更新BP房间失败", room_id=room.id, error=str(e))
            raise

    async def delete_room(self, room_id: str) -> bool:
        """删除房间"""
        session = await self._get_session()
        
        try:
            stmt = delete(BPRoom).where(BPRoom.id == room_id)
            result = await session.execute(stmt)
            await session.commit()
            
            deleted_count = result.rowcount
            logger.info("BP房间删除成功", room_id=room_id, deleted=deleted_count > 0)
            return deleted_count > 0
            
        except Exception as e:
            await session.rollback()
            logger.error("删除BP房间失败", room_id=room_id, error=str(e))
            raise

    async def get_rooms_by_creator(self, creator_user_id: int) -> List[BPRoom]:
        """获取用户创建的房间列表"""
        session = await self._get_session()
        
        stmt = (
            select(BPRoom)
            .where(BPRoom.creator_user_id == creator_user_id)
            .options(
                selectinload(BPRoom.participants),
                selectinload(BPRoom.team_a),
                selectinload(BPRoom.team_b)
            )
            .order_by(BPRoom.created_at.desc())
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_rooms_by_status(self, status: str) -> List[BPRoom]:
        """根据状态获取房间列表"""
        session = await self._get_session()
        
        # 根据状态代码获取状态ID
        status_ids = await self._get_status_ids(session, [status])
        if not status_ids:
            return []
        
        stmt = (
            select(BPRoom)
            .where(BPRoom.status_id.in_(status_ids))
            .options(
                selectinload(BPRoom.participants).selectinload(BPRoomParticipant.role),
                selectinload(BPRoom.creator),
                selectinload(BPRoom.team_a),
                selectinload(BPRoom.team_b),
                selectinload(BPRoom.status),
                selectinload(BPRoom.room_type)
            )
            .order_by(BPRoom.created_at.desc())
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_public_rooms(
        self,
        limit: int = 20,
        offset: int = 0,
        room_type: Optional[str] = None
    ) -> List[BPRoom]:
        """获取公开房间列表"""
        session = await self._get_session()
        
        # 只显示等待中和准备中的房间  
        valid_status_ids = await self._get_status_ids(session, ["waiting", "ready"])
        
        conditions = [
            BPRoom.status_id.in_(valid_status_ids)
        ]
        
        if room_type:
            conditions.append(BPRoom.room_type == room_type)
        
        stmt = (
            select(BPRoom)
            .where(and_(*conditions))
            .options(
                selectinload(BPRoom.participants).selectinload(BPRoomParticipant.role),
                selectinload(BPRoom.creator),
                selectinload(BPRoom.team_a),
                selectinload(BPRoom.team_b),
                selectinload(BPRoom.status),
                selectinload(BPRoom.room_type)
            )
            .order_by(BPRoom.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def add_participant(
        self,
        room_id: str,
        user_id: int,
        team_side: Optional[str] = None,
        role: str = "observer"
    ) -> BPRoomParticipant:
        """添加房间参与者"""
        session = await self._get_session()
        
        # 检查用户是否已经在房间中
        existing = await self.get_participant(room_id, user_id)
        if existing and existing.is_active:
            raise ValueError(f"用户 {user_id} 已经在房间 {room_id} 中")
        
        # 验证角色并获取角色ID
        # 映射前端角色到数据库角色
        role_mapping = {
            "player": "member",  # player映射为member
            "admin": "admin",
            "observer": "observer"
        }
        
        db_role = role_mapping.get(role, "observer")
        role_result = await session.execute(
            select(DictBPParticipantRoles.id).where(DictBPParticipantRoles.code == db_role)
        )
        role_id = role_result.scalar_one_or_none()
        
        if not role_id:
            # 默认使用observer角色
            observer_result = await session.execute(
                select(DictBPParticipantRoles.id).where(DictBPParticipantRoles.code == "observer")
            )
            role_id = observer_result.scalar_one_or_none()

            if not role_id:
                raise ValueError("BP participant role 'observer' not found in dictionary")
        
        participant = BPRoomParticipant(
            room_id=room_id,
            user_id=user_id,
            team_side=team_side,
            role_id=role_id,
            is_active=True,
            is_ready=False
        )
        
        try:
            session.add(participant)
            await session.commit()
            await session.refresh(participant)
            
            logger.info(
                "用户加入BP房间",
                room_id=room_id,
                user_id=user_id,
                team_side=team_side,
                role=role
            )
            
            return participant
            
        except Exception as e:
            await session.rollback()
            logger.error("添加房间参与者失败", error=str(e))
            raise

    async def remove_participant(self, room_id: str, user_id: int) -> bool:
        """移除房间参与者"""
        session = await self._get_session()
        
        try:
            # 软删除：设置为非活跃状态并记录离开时间
            stmt = (
                update(BPRoomParticipant)
                .where(
                    and_(
                        BPRoomParticipant.room_id == room_id,
                        BPRoomParticipant.user_id == user_id
                    )
                )
                .values(
                    is_active=False,
                    left_at=func.now()
                )
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            updated_count = result.rowcount
            logger.info(
                "用户离开BP房间",
                room_id=room_id,
                user_id=user_id,
                removed=updated_count > 0
            )
            
            return updated_count > 0
            
        except Exception as e:
            await session.rollback()
            logger.error("移除房间参与者失败", error=str(e))
            raise

    async def update_participant(
        self,
        room_id: str,
        user_id: int,
        team_side: Optional[str] = None,
        role: Optional[str] = None,
        is_ready: Optional[bool] = None
    ) -> Optional[BPRoomParticipant]:
        """更新参与者信息"""
        session = await self._get_session()
        
        # 构建更新字段
        update_data = {}
        if team_side is not None:
            update_data["team_side"] = team_side
        if role is not None:
            # 映射前端角色到数据库角色
            role_mapping = {
                "player": "member",  # player映射为member
                "admin": "admin",
                "observer": "observer"
            }
            
            db_role = role_mapping.get(role, "observer")
            role_result = await session.execute(
                select(DictBPParticipantRoles.id).where(DictBPParticipantRoles.code == db_role)
            )
            role_id = role_result.scalar_one_or_none()
            if role_id:
                update_data["role_id"] = role_id
            else:
                logger.warning(f"无效的角色: {role}")
        if is_ready is not None:
            update_data["is_ready"] = is_ready
        
        if not update_data:
            logger.warning("没有提供更新数据")
            return await self.get_participant(room_id, user_id)
        
        try:
            stmt = (
                update(BPRoomParticipant)
                .where(
                    and_(
                        BPRoomParticipant.room_id == room_id,
                        BPRoomParticipant.user_id == user_id,
                        BPRoomParticipant.is_active == True
                    )
                )
                .values(**update_data)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                return await self.get_participant(room_id, user_id)
            else:
                logger.warning("参与者不存在或已非活跃", room_id=room_id, user_id=user_id)
                return None
                
        except Exception as e:
            await session.rollback()
            logger.error("更新参与者信息失败", error=str(e))
            raise

    async def get_participant(
        self,
        room_id: str,
        user_id: int
    ) -> Optional[BPRoomParticipant]:
        """获取房间参与者"""
        session = await self._get_session()
        
        stmt = (
            select(BPRoomParticipant)
            .where(
                and_(
                    BPRoomParticipant.room_id == room_id,
                    BPRoomParticipant.user_id == user_id,
                    BPRoomParticipant.is_active == True
                )
            )
            .options(selectinload(BPRoomParticipant.user))
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_participants_by_room(self, room_id: str) -> List[BPRoomParticipant]:
        """获取房间所有参与者"""
        session = await self._get_session()
        
        stmt = (
            select(BPRoomParticipant)
            .where(
                and_(
                    BPRoomParticipant.room_id == room_id,
                    BPRoomParticipant.is_active == True
                )
            )
            .options(selectinload(BPRoomParticipant.user))
            .order_by(BPRoomParticipant.joined_at)
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_active_rooms(self, user_id: int) -> List[BPRoom]:
        """获取用户当前参与的活跃房间"""
        session = await self._get_session()
        
        stmt = (
            select(BPRoom)
            .join(BPRoomParticipant)
            .where(
                and_(
                    BPRoomParticipant.user_id == user_id,
                    BPRoomParticipant.is_active == True,
                    BPRoom.status_id.in_(
                        await self._get_status_ids(session, [
                            "waiting",
                            "ready", 
                            "bp_active"
                        ])
                    )
                )
            )
            .options(
                selectinload(BPRoom.participants),
                selectinload(BPRoom.creator),
                selectinload(BPRoom.team_a),
                selectinload(BPRoom.team_b)
            )
            .order_by(BPRoom.created_at.desc())
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update_room_status(self, room_id: str, status: str) -> bool:
        """更新房间状态"""
        session = await self._get_session()
        
        try:
            update_data = {}
            
            # 获取状态ID并更新时间字段
            status_result = await session.execute(
                select(DictBPRoomStatuses.id).where(DictBPRoomStatuses.code == status)
            )
            status_id = status_result.scalar_one_or_none()
            if not status_id:
                raise ValueError(f"Invalid status code: {status}")
            
            update_data["status_id"] = status_id
            
            if status == "bp_active":
                update_data["started_at"] = func.now()
            elif status == "completed":
                update_data["completed_at"] = func.now()
            
            stmt = (
                update(BPRoom)
                .where(BPRoom.id == room_id)
                .values(**update_data)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            updated = result.rowcount > 0
            logger.info(
                "房间状态更新",
                room_id=room_id,
                status=status,
                updated=updated
            )
            
            return updated
            
        except Exception as e:
            await session.rollback()
            logger.error("更新房间状态失败", error=str(e))
            raise

    async def update_bp_state(self, room_id: str, bp_state: Dict[str, Any]) -> bool:
        """更新BP状态数据"""
        session = await self._get_session()
        
        try:
            stmt = (
                update(BPRoom)
                .where(BPRoom.id == room_id)
                .values(bp_state=bp_state)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            updated = result.rowcount > 0
            logger.debug("BP状态更新", room_id=room_id, updated=updated)
            
            return updated
            
        except Exception as e:
            await session.rollback()
            logger.error("更新BP状态失败", error=str(e))
            raise

    async def start_room(self, room_id: str) -> bool:
        """开始房间BP阶段"""
        return await self.update_room_status(room_id, "bp_active")

    async def complete_room(self, room_id: str) -> bool:
        """完成房间BP阶段"""
        return await self.update_room_status(room_id, "completed")

    async def archive_completed_rooms(self, before_date: datetime) -> int:
        """归档完成的房间"""
        session = await self._get_session()
        
        try:
            stmt = (
                update(BPRoom)
                .where(
                    and_(
                        BPRoom.status_id.in_(
                            await self._get_status_ids(session, ["completed"])
                        ),
                        BPRoom.completed_at < before_date
                    )
                )
                .values(status_id=(
                    await self._get_status_ids(session, ["archived"])
                )[0])
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            archived_count = result.rowcount
            logger.info(f"归档了 {archived_count} 个完成的房间")
            
            return archived_count
            
        except Exception as e:
            await session.rollback()
            logger.error("归档房间失败", error=str(e))
            raise