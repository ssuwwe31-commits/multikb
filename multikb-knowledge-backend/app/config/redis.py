"""
Redis Configuration
"""

import redis
from app.config.settings import settings

# 创建Redis连接
redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True
)

def get_redis():
    """获取Redis客户端"""
    return redis_client
