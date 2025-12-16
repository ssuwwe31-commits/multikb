"""
清理 Redis 中的 Celery 任务结果
用于修复异常序列化问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from app.config.settings import settings
from app.core.logging import logger
import redis
from urllib.parse import urlparse

def cleanup_celery_tasks():
    """清理 Redis 中的 Celery 任务结果"""
    try:
        # 解析 Redis URL
        redis_url = settings.REDIS_URL
        logger.info(f"连接 Redis: {redis_url}")
        
        # 解析 URL
        parsed = urlparse(redis_url)
        host = parsed.hostname or settings.REDIS_HOST
        port = parsed.port or settings.REDIS_PORT
        password = parsed.password or settings.REDIS_PASSWORD or None
        db = int(parsed.path.lstrip('/')) if parsed.path else settings.REDIS_DB
        
        # 连接 Redis
        r = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=False  # 保持二进制模式，因为 Celery 存储的是二进制数据
        )
        
        # 测试连接
        r.ping()
        logger.info("[OK] Redis 连接成功")
        
        # 查找所有 Celery 任务相关的键
        # Celery 使用以下键模式：
        # - celery-task-meta-{task_id}  # 任务结果
        # - celery-task-{task_id}       # 任务状态（某些版本）
        patterns = [
            "celery-task-meta-*",
            "celery-task-*",
            "_kombu.binding.*",  # Kombu 绑定（可选，通常不需要清理）
        ]
        
        total_deleted = 0
        
        for pattern in patterns:
            # 使用 SCAN 而不是 KEYS，避免阻塞 Redis
            cursor = 0
            deleted_count = 0
            
            while True:
                cursor, keys = r.scan(cursor, match=pattern, count=100)
                
                if keys:
                    # 删除找到的键
                    deleted = r.delete(*keys)
                    deleted_count += deleted
                    logger.info(f"清理模式 {pattern}: 找到 {len(keys)} 个键，删除 {deleted} 个")
                
                if cursor == 0:
                    break
            
            total_deleted += deleted_count
        
        logger.info(f"[OK] 清理完成，共删除 {total_deleted} 个键")
        
        # 可选：清理 Celery Beat 调度信息（如果需要）
        beat_keys = r.keys("celery-beat-*")
        if beat_keys:
            deleted = r.delete(*beat_keys)
            logger.info(f"清理 Celery Beat 键: 删除 {deleted} 个")
            total_deleted += deleted
        
        logger.info(f"[OK] 总共清理了 {total_deleted} 个键")
        
        return total_deleted
        
    except redis.ConnectionError as e:
        logger.error(f"[ERROR] Redis 连接失败: {e}")
        logger.error("请检查 Redis 配置和连接")
        return 0
    except Exception as e:
        logger.error(f"[ERROR] 清理失败: {e}", exc_info=True)
        return 0

if __name__ == "__main__":
    logger.info("开始清理 Redis 中的 Celery 任务结果...")
    deleted = cleanup_celery_tasks()
    if deleted > 0:
        logger.info(f"[OK] 清理完成，共删除 {deleted} 个键")
    else:
        logger.info("[INFO] 没有找到需要清理的键，或清理过程中出现错误")
