"""WebSocket认证中间件"""

from typing import Optional, Tuple
from fastapi import WebSocket, WebSocketException, status
from uuid import uuid4
import structlog

from src.infrastructure.services.jwt_service import JWTService
from src.domain.repositories.user import UserRepository
from src.infrastructure.repositories.user import SQLAlchemyUserRepository
from src.infrastructure.database.connection import database_manager
from src.domain.entities.user import User

logger = structlog.get_logger(__name__)


class WebSocketAuthManager:
    """WebSocket认证管理器"""
    
    def __init__(self):
        self.jwt_service = JWTService()
    
    async def authenticate_websocket(
        self, 
        websocket: WebSocket,
        token: Optional[str] = None
    ) -> Tuple[str, User]:
        """
        WebSocket连接认证
        
        Args:
            websocket: WebSocket连接实例
            token: JWT令牌（可通过查询参数或headers传递）
            
        Returns:
            connection_id: 连接ID
            user: 认证后的用户实体
            
        Raises:
            WebSocketException: 认证失败时抛出
        """
        connection_id = str(uuid4())
        
        try:
            # 获取token - 首先从查询参数获取，然后从headers获取
            if not token:
                # 从查询参数获取token
                token = websocket.query_params.get("token")
            
            if not token:
                # 从headers获取token（如果支持的话）
                auth_header = websocket.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ", 1)[1]
            
            if not token:
                logger.warning(
                    "WebSocket authentication failed: No token provided",
                    connection_id=connection_id
                )
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Authentication token required"
                )
            
            # 验证JWT令牌
            claims = self.jwt_service.verify_access_token(token)
            if not claims:
                logger.warning(
                    "WebSocket authentication failed: Invalid token",
                    connection_id=connection_id
                )
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Invalid or expired token"
                )
            
            # 获取用户信息
            user_repository = SQLAlchemyUserRepository()
            user = await user_repository.find_by_id(claims.user_id)
            
            if not user:
                logger.warning(
                    "WebSocket authentication failed: User not found",
                    connection_id=connection_id,
                    user_id=claims.user_id
                )
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="User not found"
                )
            
            if not user.can_login():
                logger.warning(
                    "WebSocket authentication failed: User cannot login",
                    connection_id=connection_id,
                    user_id=user.id
                )
                raise WebSocketException(
                        code=status.WS_1008_POLICY_VIOLATION,
                        reason="User account is disabled"
                    )
            
            logger.info(
                "WebSocket authentication successful",
                connection_id=connection_id,
                user_id=user.id,
                username=user.username
            )
            
            return connection_id, user
        
        except WebSocketException:
            raise
        except Exception as e:
            logger.error(
                "WebSocket authentication error",
                connection_id=connection_id,
                error=str(e)
            )
            raise WebSocketException(
                code=status.WS_1011_INTERNAL_ERROR,
                reason="Authentication service error"
            )
    
    def extract_room_id_from_path(self, path: str) -> Optional[str]:
        """
        从WebSocket路径中提取房间ID
        
        Args:
            path: WebSocket连接路径
            
        Returns:
            room_id: 房间ID（如果路径中包含）
        """
        try:
            # 假设WebSocket路径格式为 /ws/matches/{match_id}
            path_parts = path.strip("/").split("/")
            if len(path_parts) >= 3 and path_parts[0] == "ws" and path_parts[1] == "matches":
                return path_parts[2]
            return None
        except Exception as e:
            logger.error(
                "Failed to extract room ID from path",
                path=path,
                error=str(e)
            )
            return None


# 全局WebSocket认证管理器实例
websocket_auth_manager = WebSocketAuthManager()