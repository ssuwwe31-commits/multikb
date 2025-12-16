"""
Cache Module
"""

from typing import Any, Optional
import json
import redis
from app.config.settings import settings

class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"缓存获取错误: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ) -> bool:
        """设置缓存"""
        try:
            if expire:
                self.redis_client.setex(key, expire, json.dumps(value))
            else:
                self.redis_client.set(key, json.dumps(value))
            return True
        except Exception as e:
            print(f"缓存设置错误: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"缓存删除错误: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            print(f"缓存检查错误: {e}")
            return False
    
    async def acquire_lock(self, key: str, timeout: int = 300, value: Optional[str] = None) -> bool:
        """尝试获取分布式锁（使用 SET NX EX）
        
        Args:
            key: 锁的 key
            timeout: 锁的超时时间（秒）
            value: 锁的值（用于标识锁的持有者），如果不提供则自动生成 UUID
        
        Returns:
            如果成功获取锁返回 True，否则返回 False
        """
        try:
            import uuid
            lock_value = value if value else str(uuid.uuid4())
            # 使用 SET NX EX 实现原子操作：只有当 key 不存在时才设置，并设置过期时间
            result = self.redis_client.set(key, lock_value, nx=True, ex=timeout)
            return bool(result)
        except Exception as e:
            print(f"获取锁失败: {e}")
            return False
    
    async def release_lock(self, key: str, value: Optional[str] = None) -> bool:
        """释放分布式锁（使用 Lua 脚本确保原子性）"""
        try:
            if value:
                # 使用 Lua 脚本确保只有锁的持有者才能释放
                lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                result = self.redis_client.eval(lua_script, 1, key, value)
                return bool(result)
            else:
                # 如果没有提供 value，直接删除（不安全，但作为后备）
                self.redis_client.delete(key)
                return True
        except Exception as e:
            print(f"释放锁失败: {e}")
            return False

# 全局缓存管理器实例
cache_manager = CacheManager()
