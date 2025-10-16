"""
认证相关的Pydantic Schema
定义API请求和响应的数据结构
"""
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from typing import Optional
from datetime import datetime


class UserRegistrationRequest(BaseModel):
    """用户注册请求"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    confirm_password: str = Field(..., description="确认密码")
    riot_summoner_name: Optional[str] = Field(
        None, max_length=100, description="Riot召唤师名"
    )

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        """验证密码确认"""
        if (
            hasattr(info, "data")
            and "password" in info.data
            and v != info.data["password"]
        ):
            raise ValueError("密码和确认密码不匹配")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        """验证用户名格式"""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("用户名只能包含字母、数字、下划线和中划线")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "player123",
                "email": "player@example.com",
                "password": "Password123",
                "confirm_password": "Password123",
                "riot_summoner_name": "RiotPlayer",
            }
        }
    )


class UserLoginRequest(BaseModel):
    """用户登录请求"""

    email_or_username: Optional[str] = Field(None, description="邮箱或用户名")
    email: Optional[str] = Field(None, description="邮箱（兼容性字段）")
    username: Optional[str] = Field(None, description="用户名（兼容性字段）")
    password: str = Field(..., description="密码")

    @field_validator("email_or_username")
    @classmethod
    def validate_login_field(cls, v, info):
        """确保至少提供一个登录标识"""
        values = info.data if hasattr(info, "data") else {}
        email = values.get("email")
        username = values.get("username")

        if not v and not email and not username:
            raise ValueError("必须提供邮箱或用户名")
        return v

    @property
    def get_login_identifier(self) -> str:
        """获取登录标识符"""
        if self.email_or_username:
            return self.email_or_username
        elif self.email:
            return self.email
        elif self.username:
            return self.username
        else:
            raise ValueError("缺少登录标识符")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "player@example.com", "password": "Password123"}
        }
    )


class TokenRefreshRequest(BaseModel):
    """令牌刷新请求"""

    refresh_token: str = Field(..., description="刷新令牌")

    class Config:
        schema_extra = {
            "example": {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
        }


class PasswordChangeRequest(BaseModel):
    """密码修改请求"""

    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")
    confirm_new_password: str = Field(..., description="确认新密码")

    @field_validator("confirm_new_password")
    @classmethod
    def passwords_match(cls, v, info):
        """验证新密码确认"""
        if (
            hasattr(info, "data")
            and "new_password" in info.data
            and v != info.data["new_password"]
        ):
            raise ValueError("新密码和确认密码不匹配")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "old_password": "OldPassword123",
                "new_password": "NewPassword123",
                "confirm_new_password": "NewPassword123",
            }
        }
    )


class TokenResponse(BaseModel):
    """令牌响应"""

    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="访问令牌过期时间（秒）")

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
            }
        }


class UserResponse(BaseModel):
    """用户信息响应"""

    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱地址")
    riot_summoner_name: Optional[str] = Field(None, description="Riot召唤师名")
    is_active: bool = Field(..., description="是否激活")
    is_verified: bool = Field(..., description="是否已验证邮箱")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")

    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "username": "player123",
                "email": "player@example.com",
                "riot_summoner_name": "RiotPlayer",
                "is_active": True,
                "is_verified": True,
                "created_at": "2023-12-01T10:00:00Z",
                "updated_at": "2023-12-01T10:00:00Z",
                "last_login_at": "2023-12-01T12:00:00Z",
            }
        }


class LoginResponse(BaseModel):
    """登录响应"""

    user: UserResponse = Field(..., description="用户信息")
    tokens: TokenResponse = Field(..., description="令牌信息")

    class Config:
        schema_extra = {
            "example": {
                "user": {
                    "id": 1,
                    "username": "player123",
                    "email": "player@example.com",
                    "riot_summoner_name": "RiotPlayer",
                    "is_active": True,
                    "is_verified": True,
                    "created_at": "2023-12-01T10:00:00Z",
                    "updated_at": "2023-12-01T10:00:00Z",
                    "last_login_at": "2023-12-01T12:00:00Z",
                },
                "tokens": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 1800,
                },
            }
        }


class MessageResponse(BaseModel):
    """通用消息响应"""

    message: str = Field(..., description="响应消息")

    class Config:
        schema_extra = {"example": {"message": "操作成功完成"}}


class ErrorResponse(BaseModel):
    """错误响应"""

    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: Optional[dict] = Field(None, description="错误详情")

    class Config:
        schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "输入数据验证失败",
                "details": {"field": "username", "issue": "用户名已存在"},
            }
        }
