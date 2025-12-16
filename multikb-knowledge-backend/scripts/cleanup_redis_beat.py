"""
清理 Redis 中与 Celery Beat 和任务锁相关的数据。

如果 Beat 任务被重复触发，可能是 Redis 中存储了旧的锁或任务数据。
运行此脚本可以清理这些数据。

使用方法:
    python scripts/cleanup_redis_beat.py
"""

import os
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
_current_dir = Path(__file__).parent
_project_root = _current_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app.config.settings import settings
from app.core.logging import logger
import redis


def cleanup_redis_beat():
    """清理 Redis 中与 Beat 和任务锁相关的数据。"""
    try:
        # 解析 Redis URL
        redis_url = settings.REDIS_URL
        logger.info(f"连接到 Redis: {redis_url}")
        
        # 创建 Redis 客户端
        redis_client = redis.from_url(redis_url, decode_responses=False)
        
        # 测试连接
        redis_client.ping()
        logger.info("✅ Redis 连接成功")
        
        # 需要清理的键模式
        patterns_to_clean = [
            "celery_beat_instance_lock",  # Beat 实例锁
            "sync_active_clusters_lock",  # 同步任务锁
            "health_check_clusters_lock",  # 健康检查任务锁
            "celery-task-meta-*",  # Celery 任务结果
            "celery-task-*",  # Celery 任务数据
            "_kombu.binding.*",  # Kombu 绑定
            "celerybeat-schedule*",  # Beat 调度数据（如果使用 Redis 存储）
        ]
        
        cleaned_keys = []
        total_deleted = 0
        
        for pattern in patterns_to_clean:
            try:
                if "*" in pattern:
                    # 使用 SCAN 查找匹配的键
                    cursor = 0
                    keys_to_delete = []
                    
                    while True:
                        cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                        keys_to_delete.extend(keys)
                        if cursor == 0:
                            break
                    
                    if keys_to_delete:
                        deleted = redis_client.delete(*keys_to_delete)
                        total_deleted += deleted
                        cleaned_keys.extend([k.decode() if isinstance(k, bytes) else k for k in keys_to_delete])
                        logger.info(f"已删除 {deleted} 个匹配 '{pattern}' 的键")
                    else:
                        logger.info(f"未找到匹配 '{pattern}' 的键")
                else:
                    # 直接删除单个键
                    if redis_client.exists(pattern):
                        redis_client.delete(pattern)
                        total_deleted += 1
                        cleaned_keys.append(pattern)
                        logger.info(f"已删除键: {pattern}")
                    else:
                        logger.info(f"键不存在，跳过: {pattern}")
            except Exception as e:
                logger.error(f"清理模式 '{pattern}' 时出错: {e}")
        
        # 清理 Beat 调度相关的键（如果使用 Redis 作为 Beat 调度器）
        beat_schedule_keys = [
            "celerybeat-schedule",
            "celerybeat-schedule.db",
        ]
        
        for key in beat_schedule_keys:
            try:
                if redis_client.exists(key):
                    redis_client.delete(key)
                    total_deleted += 1
                    cleaned_keys.append(key)
                    logger.info(f"已删除 Beat 调度键: {key}")
            except Exception as e:
                logger.error(f"删除键 '{key}' 时出错: {e}")
        
        if cleaned_keys:
            logger.info(f"✅ 已清理 {total_deleted} 个 Redis 键")
            logger.info(f"清理的键列表（前10个）: {cleaned_keys[:10]}")
            if len(cleaned_keys) > 10:
                logger.info(f"... 还有 {len(cleaned_keys) - 10} 个键")
        else:
            logger.info("ℹ️  没有找到需要清理的 Redis 键")
        
        logger.info("提示: 请重启 Celery Beat 和 Worker 以重新初始化")
        
        return 0
        
    except redis.ConnectionError as e:
        logger.error(f"❌ 无法连接到 Redis: {e}")
        logger.error("请检查 Redis 服务是否运行，以及 REDIS_URL 配置是否正确")
        return 1
    except Exception as e:
        logger.error(f"清理 Redis 数据时出错: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    try:
        exit_code = cleanup_redis_beat()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"执行清理脚本时出错: {e}", exc_info=True)
        sys.exit(1)
