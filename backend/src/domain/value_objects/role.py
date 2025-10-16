"""
Role value objects and enums for authorization system.
"""

from enum import Enum
from dataclasses import dataclass
from typing import ClassVar, Dict, List, Set, Optional

from ..base import ValueObject


class RoleType(Enum):
    """
    Enumeration of system role types.

    Role hierarchy (high to low):
    1. SUPER_ADMIN - Global system administration
    2. REGION_ADMIN - Single region administration
    3. TEAM_CAPTAIN - Team management within region
    4. TEAM_MEMBER - Team member within region
    5. PLAYER - Player within region
    6. USER - Basic user (default)
    """

    SUPER_ADMIN = "SUPER_ADMIN"
    REGION_ADMIN = "REGION_ADMIN"
    TEAM_CAPTAIN = "TEAM_CAPTAIN"
    TEAM_MEMBER = "TEAM_MEMBER"
    PLAYER = "PLAYER"
    USER = "USER"


class SystemRole(Enum):
    """Legacy system role enum for backward compatibility."""

    SUPER_ADMIN = "super_admin"  # 超级管理员 - Level 100
    REGION_ADMIN = "region_admin"  # 赛区管理员 - Level 80
    TEAM_CAPTAIN = "team_captain"  # 队长 - Level 50
    PLAYER = "player"  # 选手 - Level 30
    REGULAR_USER = "regular_user"  # 普通用户 - Level 10


class PermissionAction(Enum):
    """Enumeration of permission actions."""

    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    MANAGE = "MANAGE"
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class PermissionResource(Enum):
    """Enumeration of permission resources."""

    # System resources
    SYSTEM = "SYSTEM"
    USER = "USER"
    ROLE = "ROLE"

    # Region resources
    REGION = "REGION"
    REGION_CONFIG = "REGION_CONFIG"

    # Player resources
    PLAYER = "PLAYER"
    PLAYER_PROFILE = "PLAYER_PROFILE"
    PLAYER_RATING = "PLAYER_RATING"

    # Team resources
    TEAM = "TEAM"
    TEAM_MEMBER = "TEAM_MEMBER"
    TEAM_APPLICATION = "TEAM_APPLICATION"

    # Match resources
    MATCH = "MATCH"
    MATCH_RESULT = "MATCH_RESULT"
    MATCH_DATA = "MATCH_DATA"

    # Tournament resources
    TOURNAMENT = "TOURNAMENT"
    TOURNAMENT_REGISTRATION = "TOURNAMENT_REGISTRATION"


class Permission(Enum):
    """Legacy permission enum for backward compatibility."""

    # 系统管理权限
    MANAGE_SYSTEM = "manage_system"
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"

    # 赛区管理权限
    MANAGE_REGION = "manage_region"
    CREATE_TOURNAMENT = "create_tournament"
    MANAGE_TOURNAMENT = "manage_tournament"

    # 战队管理权限
    CREATE_TEAM = "create_team"
    MANAGE_TEAM = "manage_team"
    RECRUIT_PLAYERS = "recruit_players"

    # 选手权限
    JOIN_TEAM = "join_team"
    PARTICIPATE_MATCH = "participate_match"
    VIEW_STATS = "view_stats"

    # BP相关权限
    CREATE_BP_ROOM = "create_bp_room"
    JOIN_BP_ROOM = "join_bp_room"
    EXECUTE_BP_ACTION = "execute_bp_action"
    MANAGE_BP_ROOM = "manage_bp_room"
    FORCE_BP_ACTION = "force_bp_action"
    VIEW_BP_ROOM = "view_bp_room"

    # 基础用户权限
    VIEW_PUBLIC_DATA = "view_public_data"
    POST_COMMENTS = "post_comments"
    FOLLOW_TEAMS = "follow_teams"


@dataclass(frozen=True)
class Role(ValueObject):
    """
    Role value object representing a system role.
    """

    id: int
    name: str
    description: Optional[str] = None
    level: int = 0
    is_system: bool = False

    # Role type mappings
    ROLE_TYPE_MAPPING: ClassVar[Dict[str, RoleType]] = {
        "超级管理员": RoleType.SUPER_ADMIN,
        "赛区管理员": RoleType.REGION_ADMIN,
        "队长": RoleType.TEAM_CAPTAIN,
        "队员": RoleType.TEAM_MEMBER,
        "选手": RoleType.PLAYER,
        "用户": RoleType.USER,
    }

    # Display name mappings
    DISPLAY_NAMES: ClassVar[Dict[RoleType, str]] = {
        RoleType.SUPER_ADMIN: "超级管理员",
        RoleType.REGION_ADMIN: "赛区管理员",
        RoleType.TEAM_CAPTAIN: "队长",
        RoleType.TEAM_MEMBER: "队员",
        RoleType.PLAYER: "选手",
        RoleType.USER: "用户",
    }

    @property
    def role_type(self) -> RoleType:
        """Get the role type enum from name."""
        return self.ROLE_TYPE_MAPPING.get(self.name, RoleType.USER)

    @property
    def display_name(self) -> str:
        """Get the display name for the role."""
        return self.DISPLAY_NAMES.get(self.role_type, self.name)

    def can_manage_role(self, target_role: "Role") -> bool:
        """
        Check if this role can manage the target role.

        Args:
            target_role: The target role to check

        Returns:
            True if this role can manage the target role
        """
        return self.level > target_role.level

    def requires_region(self) -> bool:
        """Check if this role requires a region assignment."""
        return self.role_type in [
            RoleType.REGION_ADMIN,
            RoleType.TEAM_CAPTAIN,
            RoleType.TEAM_MEMBER,
            RoleType.PLAYER,
        ]

    def __str__(self) -> str:
        return f"Role({self.name}, level={self.level})"

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Role):
            return False
        return self.id == other.id


@dataclass(frozen=True)
class PermissionVO(ValueObject):
    """
    Permission value object representing a specific permission.
    """

    id: int
    name: str
    description: Optional[str] = None
    resource: PermissionResource = PermissionResource.SYSTEM
    action: PermissionAction = PermissionAction.READ

    @property
    def full_name(self) -> str:
        """Get the full permission name as resource:action."""
        return f"{self.resource.value}:{self.action.value}"

    def __str__(self) -> str:
        return f"Permission({self.name}: {self.full_name})"

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PermissionVO):
            return False
        return self.id == other.id


@dataclass
class RolePermissions:
    """角色权限配置"""

    role: SystemRole
    permissions: Set[Permission]
    level: int
    description: str

    @property
    def name(self) -> str:
        return self.role.value


# 定义各角色的权限配置
ROLE_PERMISSIONS_MAP = {
    SystemRole.SUPER_ADMIN: RolePermissions(
        role=SystemRole.SUPER_ADMIN,
        level=100,
        description="超级管理员 - 拥有系统最高权限",
        permissions={
            Permission.MANAGE_SYSTEM,
            Permission.MANAGE_USERS,
            Permission.MANAGE_ROLES,
            Permission.MANAGE_REGION,
            Permission.CREATE_TOURNAMENT,
            Permission.MANAGE_TOURNAMENT,
            Permission.CREATE_TEAM,
            Permission.MANAGE_TEAM,
            Permission.RECRUIT_PLAYERS,
            Permission.JOIN_TEAM,
            Permission.PARTICIPATE_MATCH,
            Permission.VIEW_STATS,
            # BP权限
            Permission.CREATE_BP_ROOM,
            Permission.JOIN_BP_ROOM,
            Permission.EXECUTE_BP_ACTION,
            Permission.MANAGE_BP_ROOM,
            Permission.FORCE_BP_ACTION,
            Permission.VIEW_BP_ROOM,
            # 基础权限
            Permission.VIEW_PUBLIC_DATA,
            Permission.POST_COMMENTS,
            Permission.FOLLOW_TEAMS,
        },
    ),
    SystemRole.REGION_ADMIN: RolePermissions(
        role=SystemRole.REGION_ADMIN,
        level=80,
        description="赛区管理员 - 管理特定赛区的赛事和用户",
        permissions={
            Permission.MANAGE_REGION,
            Permission.CREATE_TOURNAMENT,
            Permission.MANAGE_TOURNAMENT,
            Permission.CREATE_TEAM,
            Permission.MANAGE_TEAM,
            Permission.RECRUIT_PLAYERS,
            Permission.JOIN_TEAM,
            Permission.PARTICIPATE_MATCH,
            Permission.VIEW_STATS,
            # BP权限
            Permission.CREATE_BP_ROOM,
            Permission.JOIN_BP_ROOM,
            Permission.EXECUTE_BP_ACTION,
            Permission.MANAGE_BP_ROOM,
            Permission.FORCE_BP_ACTION,
            Permission.VIEW_BP_ROOM,
            # 基础权限
            Permission.VIEW_PUBLIC_DATA,
            Permission.POST_COMMENTS,
            Permission.FOLLOW_TEAMS,
        },
    ),
    SystemRole.TEAM_CAPTAIN: RolePermissions(
        role=SystemRole.TEAM_CAPTAIN,
        level=50,
        description="队长 - 管理战队成员和参赛事务",
        permissions={
            Permission.CREATE_TEAM,
            Permission.MANAGE_TEAM,
            Permission.RECRUIT_PLAYERS,
            Permission.JOIN_TEAM,
            Permission.PARTICIPATE_MATCH,
            Permission.VIEW_STATS,
            # BP权限 (队长可以执行BP操作)
            Permission.CREATE_BP_ROOM,
            Permission.JOIN_BP_ROOM,
            Permission.EXECUTE_BP_ACTION,
            Permission.VIEW_BP_ROOM,
            # 基础权限
            Permission.VIEW_PUBLIC_DATA,
            Permission.POST_COMMENTS,
            Permission.FOLLOW_TEAMS,
        },
    ),
    SystemRole.PLAYER: RolePermissions(
        role=SystemRole.PLAYER,
        level=30,
        description="选手 - 参与比赛和战队活动",
        permissions={
            Permission.JOIN_TEAM,
            Permission.PARTICIPATE_MATCH,
            Permission.VIEW_STATS,
            # BP权限 (选手可以观看BP)
            Permission.JOIN_BP_ROOM,
            Permission.VIEW_BP_ROOM,
            # 基础权限
            Permission.VIEW_PUBLIC_DATA,
            Permission.POST_COMMENTS,
            Permission.FOLLOW_TEAMS,
        },
    ),
    SystemRole.REGULAR_USER: RolePermissions(
        role=SystemRole.REGULAR_USER,
        level=10,
        description="普通用户 - 观看和参与基础社交功能",
        permissions={
            # BP权限 (普通用户只能观看)
            Permission.VIEW_BP_ROOM,
            # 基础权限
            Permission.VIEW_PUBLIC_DATA,
            Permission.POST_COMMENTS,
            Permission.FOLLOW_TEAMS,
        },
    ),
}


def get_role_permissions(role: SystemRole) -> RolePermissions:
    """获取角色权限配置"""
    return ROLE_PERMISSIONS_MAP.get(role)


def has_permission(
    user_roles: List[SystemRole], required_permission: Permission
) -> bool:
    """检查用户是否拥有指定权限"""
    for role in user_roles:
        role_perms = get_role_permissions(role)
        if role_perms and required_permission in role_perms.permissions:
            return True
    return False


def get_highest_role_level(user_roles: List[SystemRole]) -> int:
    """获取用户最高角色级别"""
    if not user_roles:
        return 0

    max_level = 0
    for role in user_roles:
        role_perms = get_role_permissions(role)
        if role_perms and role_perms.level > max_level:
            max_level = role_perms.level

    return max_level


def can_assign_role(assigner_roles: List[SystemRole], target_role: SystemRole) -> bool:
    """检查是否有权限分配指定角色"""
    assigner_level = get_highest_role_level(assigner_roles)
    target_role_perms = get_role_permissions(target_role)

    if not target_role_perms:
        return False

    # 只能分配比自己级别低的角色
    return assigner_level > target_role_perms.level
