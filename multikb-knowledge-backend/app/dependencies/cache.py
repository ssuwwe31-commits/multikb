"""
Cache Dependencies
"""

from fastapi import Depends
from app.config.redis import get_redis
from app.core.cache import cache_manager

def get_cache():
    """获取缓存管理器"""
    return cache_manager
