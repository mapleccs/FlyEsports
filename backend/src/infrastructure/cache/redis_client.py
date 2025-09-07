import redis.asyncio as redis
from typing import Any, Optional
import json
import structlog

from src.core.config import settings

logger = structlog.get_logger(__name__)


class RedisManager:
    def __init__(self):
        self._redis: redis.Redis | None = None
    
    @property
    def client(self) -> redis.Redis:
        if self._redis is None:
            raise RuntimeError("Redis client not initialized. Call connect() first.")
        return self._redis
    
    def get_client(self) -> redis.Redis:
        """Get the Redis client instance."""
        return self.client
    
    async def connect(self) -> None:
        logger.info("Connecting to Redis", redis_url=settings.REDIS_URL.split("@")[-1])
        
        self._redis = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30,
        )
        
        # Test connection
        await self._redis.ping()
        
        logger.info("Redis connected successfully")
    
    async def disconnect(self) -> None:
        if self._redis:
            logger.info("Disconnecting from Redis")
            await self._redis.close()
            self._redis = None
            logger.info("Redis disconnected successfully")
    
    async def get(self, key: str) -> Optional[str]:
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        
        try:
            value = await self._redis.get(key)
            return value
        except Exception as e:
            logger.error(f"Failed to get key '{key}' from Redis", error=str(e))
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            result = await self._redis.set(key, value, ex=expire)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to set key '{key}' in Redis", error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        
        try:
            result = await self._redis.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to delete key '{key}' from Redis", error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        
        try:
            result = await self._redis.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to check existence of key '{key}' in Redis", error=str(e))
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        
        try:
            result = await self._redis.expire(key, seconds)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to set expiration for key '{key}' in Redis", error=str(e))
            return False
    
    async def get_json(self, key: str) -> Optional[Any]:
        value = await self.get(key)
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON for key '{key}'", error=str(e))
            return None
    
    async def set_json(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        return await self.set(key, value, expire)


# Global Redis manager instance
redis_manager = RedisManager()