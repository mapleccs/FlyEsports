"""
用户领域服务
实现用户相关的业务逻辑
"""
from typing import Optional

from src.domain.entities.user import User, UserRegistration
from src.domain.value_objects.user import (
    Email,
    Username,
    PlainPassword,
    PasswordService,
)
from src.domain.repositories.user import UserRepository


class UserDomainService:
    """
    用户领域服务
    处理用户相关的复杂业务逻辑
    """

    def __init__(self, user_repository: UserRepository):
        self._user_repository = user_repository
        self._password_service = PasswordService()

    async def is_email_available(self, email: Email) -> bool:
        """检查邮箱是否可用"""
        return not await self._user_repository.exists_by_email(email)

    async def is_username_available(self, username: Username) -> bool:
        """检查用户名是否可用"""
        return not await self._user_repository.exists_by_username(username)

    async def register_user(self, registration: UserRegistration) -> User:
        """
        注册新用户

        Args:
            registration: 注册数据

        Returns:
            新创建的用户实体

        Raises:
            ValueError: 当用户名或邮箱已存在时
        """
        import structlog

        logger = structlog.get_logger(__name__)

        email = Email(registration.email)
        username = Username(registration.username)
        plain_password = PlainPassword(registration.password)

        # 检查邮箱是否已存在
        if not await self.is_email_available(email):
            raise ValueError(f"邮箱已存在: {email}")

        # 检查用户名是否已存在
        if not await self.is_username_available(username):
            raise ValueError(f"用户名已存在: {username}")

        # 加密密码
        hashed_password = self._password_service.hash_password(plain_password)

        # 创建用户实体
        user = registration.to_domain_user(hashed_password)

        # 保存用户
        saved_user = await self._user_repository.save(user)

        # 为新用户分配默认角色
        try:
            default_role_id = await self._user_repository.get_default_user_role_id()
            if default_role_id is not None:
                role_assigned = await self._user_repository.assign_role_to_user(
                    user_id=saved_user.id,
                    role_id=default_role_id,
                    region_id=None  # 全局角色
                )
                if role_assigned:
                    logger.info(
                        "Default role assigned to new user",
                        user_id=saved_user.id,
                        username=saved_user.username.value,
                        role_id=default_role_id,
                    )
                else:
                    logger.warning(
                        "Failed to assign default role to new user",
                        user_id=saved_user.id,
                        username=saved_user.username.value,
                        role_id=default_role_id,
                    )
            else:
                logger.warning(
                    "No default role found, user registered without role",
                    user_id=saved_user.id,
                    username=saved_user.username.value,
                )
        except Exception as e:
            # 即使角色分配失败，用户注册也应该成功
            # 只记录错误但不抛出异常
            logger.error(
                "Error assigning default role to new user",
                user_id=saved_user.id,
                username=saved_user.username.value,
                error=str(e),
            )

        return saved_user

    async def authenticate_user(
        self, email_or_username: str, password: str
    ) -> Optional[User]:
        """
        用户认证

        Args:
            email_or_username: 邮箱或用户名
            password: 密码

        Returns:
            认证成功的用户实体，失败返回None
        """
        try:
            plain_password = PlainPassword(password)
        except ValueError:
            # 密码格式无效
            return None

        # 尝试通过邮箱查找用户
        user = None
        try:
            email = Email(email_or_username)
            user = await self._user_repository.find_by_email(email)
        except ValueError:
            # 不是有效邮箱，尝试用户名
            pass

        # 如果邮箱查找失败，尝试用户名
        if user is None:
            try:
                username = Username(email_or_username)
                user = await self._user_repository.find_by_username(username)
            except ValueError:
                # 用户名格式也无效
                return None

        # 用户不存在
        if user is None:
            return None

        # 检查用户是否可以登录
        if not user.can_login():
            return None

        # 验证密码
        if not self._password_service.verify_password(
            plain_password, user.password_hash
        ):
            return None

        # 更新最后登录时间
        user.update_last_login()
        await self._user_repository.update(user)

        return user

    async def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> bool:
        """
        修改用户密码

        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码

        Returns:
            是否修改成功
        """
        user = await self._user_repository.find_by_id(user_id)
        if user is None:
            return False

        try:
            old_plain_password = PlainPassword(old_password)
            new_plain_password = PlainPassword(new_password)
        except ValueError:
            return False

        # 验证旧密码
        if not self._password_service.verify_password(
            old_plain_password, user.password_hash
        ):
            return False

        # 生成新密码哈希
        new_hashed_password = self._password_service.hash_password(new_plain_password)

        # 更新密码
        user.update_password(new_hashed_password)
        await self._user_repository.update(user)

        return True

    async def reset_password(self, email: str, new_password: str) -> bool:
        """
        重置用户密码（管理员功能或忘记密码功能）

        Args:
            email: 用户邮箱
            new_password: 新密码

        Returns:
            是否重置成功
        """
        try:
            email_vo = Email(email)
            new_plain_password = PlainPassword(new_password)
        except ValueError:
            return False

        user = await self._user_repository.find_by_email(email_vo)
        if user is None:
            return False

        # 生成新密码哈希
        new_hashed_password = self._password_service.hash_password(new_plain_password)

        # 更新密码
        user.update_password(new_hashed_password)
        await self._user_repository.update(user)

        return True

    async def activate_user(self, user_id: int) -> bool:
        """激活用户"""
        user = await self._user_repository.find_by_id(user_id)
        if user is None:
            return False

        user.activate()
        await self._user_repository.update(user)
        return True

    async def deactivate_user(self, user_id: int) -> bool:
        """停用用户"""
        user = await self._user_repository.find_by_id(user_id)
        if user is None:
            return False

        user.deactivate()
        await self._user_repository.update(user)
        return True

    async def verify_user_email(self, user_id: int) -> bool:
        """验证用户邮箱"""
        user = await self._user_repository.find_by_id(user_id)
        if user is None:
            return False

        user.verify_email()
        await self._user_repository.update(user)
        return True
