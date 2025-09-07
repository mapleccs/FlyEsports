"""
用户Repository实现
基于SQLAlchemy的用户数据访问实现
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from src.domain.entities.user import User, UserProfile
from src.domain.repositories.user import UserRepository, UserProfileRepository
from src.domain.value_objects.user import Email, Username, HashedPassword, RiotSummonerName
from src.infrastructure.database.models.user import User as UserModel
from src.infrastructure.database.connection import database_manager


class SQLAlchemyUserRepository(UserRepository):
    """
    基于SQLAlchemy的用户Repository实现
    """
    
    def __init__(self):
        self._db_manager = database_manager
    
    async def save(self, user: User) -> User:
        """保存用户"""
        async with self._db_manager.get_session() as session:
            if user.id is None:
                # 新用户
                user_model = UserModel(
                    username=user.username.value,
                    email=user.email.value,
                    password_hash=user.password_hash.value,
                    riot_summoner_name=user.riot_summoner_name.value,
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    last_login_at=user.last_login_at
                )
                session.add(user_model)
                await session.flush()  # 获取ID
                
                # 更新领域实体的ID
                user.id = user_model.id
                user.created_at = user_model.created_at
                user.updated_at = user_model.updated_at
                
                return user
            else:
                # 更新现有用户
                return await self.update(user)
    
    async def find_by_id(self, user_id: int) -> Optional[User]:
        """根据ID查找用户"""
        async with self._db_manager.get_session() as session:
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model is None:
                return None
            
            return self._model_to_entity(user_model)
    
    async def find_by_email(self, email: Email) -> Optional[User]:
        """根据邮箱查找用户"""
        async with self._db_manager.get_session() as session:
            stmt = select(UserModel).where(UserModel.email == email.value)
            result = await session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model is None:
                return None
            
            return self._model_to_entity(user_model)
    
    async def find_by_username(self, username: Username) -> Optional[User]:
        """根据用户名查找用户"""
        async with self._db_manager.get_session() as session:
            stmt = select(UserModel).where(UserModel.username == username.value)
            result = await session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model is None:
                return None
            
            return self._model_to_entity(user_model)
    
    async def exists_by_email(self, email: Email) -> bool:
        """检查邮箱是否已存在"""
        async with self._db_manager.get_session() as session:
            stmt = select(func.count(UserModel.id)).where(UserModel.email == email.value)
            result = await session.execute(stmt)
            count = result.scalar()
            return count > 0
    
    async def exists_by_username(self, username: Username) -> bool:
        """检查用户名是否已存在"""
        async with self._db_manager.get_session() as session:
            stmt = select(func.count(UserModel.id)).where(UserModel.username == username.value)
            result = await session.execute(stmt)
            count = result.scalar()
            return count > 0
    
    async def update(self, user: User) -> User:
        """更新用户"""
        async with self._db_manager.get_session() as session:
            stmt = select(UserModel).where(UserModel.id == user.id)
            result = await session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model is None:
                raise ValueError(f"用户不存在: {user.id}")
            
            # 更新模型字段
            user_model.username = user.username.value
            user_model.email = user.email.value
            user_model.password_hash = user.password_hash.value
            user_model.riot_summoner_name = user.riot_summoner_name.value
            user_model.is_active = user.is_active
            user_model.is_verified = user.is_verified
            user_model.last_login_at = user.last_login_at
            user_model.updated_at = datetime.utcnow()
            
            # 更新领域实体
            user.updated_at = user_model.updated_at
            
            return user
    
    async def delete(self, user_id: int) -> bool:
        """删除用户"""
        async with self._db_manager.get_session() as session:
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model is None:
                return False
            
            await session.delete(user_model)
            return True
    
    async def find_active_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """查找活跃用户列表"""
        async with self._db_manager.get_session() as session:
            stmt = (
                select(UserModel)
                .where(UserModel.is_active == True)
                .order_by(UserModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            user_models = result.scalars().all()
            
            return [self._model_to_entity(model) for model in user_models]
    
    async def count_users_by_status(self, is_active: bool) -> int:
        """根据状态统计用户数量"""
        async with self._db_manager.get_session() as session:
            stmt = select(func.count(UserModel.id)).where(UserModel.is_active == is_active)
            result = await session.execute(stmt)
            return result.scalar()
    
    def _model_to_entity(self, model: UserModel) -> User:
        """将数据库模型转换为领域实体"""
        return User(
            id=model.id,
            username=Username(model.username),
            email=Email(model.email),
            password_hash=HashedPassword(model.password_hash),
            riot_summoner_name=RiotSummonerName(model.riot_summoner_name),
            is_active=model.is_active,
            is_verified=model.is_verified,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_login_at=model.last_login_at
        )


class SQLAlchemyUserProfileRepository(UserProfileRepository):
    """
    用户档案Repository实现（暂时使用用户表的扩展字段）
    """
    
    def __init__(self):
        self._db_manager = database_manager
    
    async def save(self, profile: UserProfile) -> UserProfile:
        """保存用户档案（暂未实现独立的档案表）"""
        # 注意：当前数据库设计中没有独立的用户档案表
        # 这里返回原对象，实际实现需要创建档案表
        return profile
    
    async def find_by_user_id(self, user_id: int) -> Optional[UserProfile]:
        """根据用户ID查找档案"""
        # 暂未实现独立的档案表
        return None
    
    async def update(self, profile: UserProfile) -> UserProfile:
        """更新用户档案"""
        # 暂未实现独立的档案表
        return profile
    
    async def delete(self, user_id: int) -> bool:
        """删除用户档案"""
        # 暂未实现独立的档案表
        return True