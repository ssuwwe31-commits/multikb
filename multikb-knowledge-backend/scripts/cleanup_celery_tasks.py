"""
清理 Celery 失败任务脚本
清理 Redis 中存储的失败任务元数据，解决序列化错误问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import redis
from app.config.settings import settings
from app.core.logging import logger


def cleanup_failed_tasks():
    """清理失败的任务元数据"""
    print("=" * 60)
    print("清理 Celery 失败任务")
    print("=" * 60)
    print()
    
    try:
        # 连接 Redis
        print(f"[INFO] 连接到 Redis: {settings.REDIS_URL}")
        
        # 解析 Redis URL
        if settings.REDIS_URL.startswith("redis://"):
            # 格式: redis://[password@]host:port/db
            redis_url = settings.REDIS_URL
        else:
            # 使用单独配置
            if settings.REDIS_PASSWORD:
                redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            else:
                redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        
        client = redis.Redis.from_url(redis_url, decode_responses=False)
        
        # 测试连接
        client.ping()
        print("[SUCCESS] Redis 连接成功")
        print()
        
        # 查找所有 Celery 任务元数据键
        print("[INFO] 查找 Celery 任务元数据...")
        task_meta_keys = client.keys("celery-task-meta-*")
        print(f"[INFO] 找到 {len(task_meta_keys)} 个任务元数据")
        print()
        
        if not task_meta_keys:
            print("[INFO] 没有找到任务元数据，无需清理")
            return True
        
        # 统计信息
        failed_count = 0
        success_count = 0
        error_count = 0
        deleted_count = 0
        
        # 检查每个任务的状态
        print("[INFO] 检查任务状态...")
        for key in task_meta_keys:
            try:
                task_data = client.get(key)
                if task_data:
                    import json
                    try:
                        # 尝试解析任务数据
                        task_info = json.loads(task_data)
                        status = task_info.get('status', 'UNKNOWN')
                        
                        if status == 'FAILURE':
                            failed_count += 1
                            # 删除失败的任务
                            client.delete(key)
                            deleted_count += 1
                            task_id = key.decode('utf-8').replace('celery-task-meta-', '')
                            print(f"  [DELETED] 失败任务: {task_id[:36]}...")
                        elif status == 'SUCCESS':
                            success_count += 1
                        else:
                            # 对于其他状态（PENDING, STARTED, RETRY等），也删除（可能是旧任务）
                            client.delete(key)
                            deleted_count += 1
                            task_id = key.decode('utf-8').replace('celery-task-meta-', '')
                            print(f"  [DELETED] {status} 任务: {task_id[:36]}...")
                    except (json.JSONDecodeError, ValueError) as e:
                        # 无法解析的任务数据（可能是序列化错误），直接删除
                        error_count += 1
                        client.delete(key)
                        deleted_count += 1
                        task_id = key.decode('utf-8').replace('celery-task-meta-', '')
                        print(f"  [DELETED] 损坏的任务数据: {task_id[:36]}... (错误: {str(e)[:50]})")
            except Exception as e:
                error_count += 1
                print(f"  [ERROR] 处理任务失败: {key}, 错误: {e}")
        
        print()
        print("=" * 60)
        print("[SUMMARY] 清理统计:")
        print(f"  - 总任务数: {len(task_meta_keys)}")
        print(f"  - 失败任务: {failed_count}")
        print(f"  - 成功任务: {success_count}")
        print(f"  - 损坏数据: {error_count}")
        print(f"  - 已删除: {deleted_count}")
        print("=" * 60)
        print()
        
        # 清理其他可能的 Celery 键（可选）
        print("[INFO] 检查其他 Celery 相关键...")
        other_keys = [
            b'_kombu.binding.celery',
            b'_kombu.binding.celery.pidbox',
        ]
        
        # 查找所有 _kombu.binding.* 键
        kombu_keys = client.keys("_kombu.binding.*")
        if kombu_keys:
            print(f"[INFO] 找到 {len(kombu_keys)} 个队列绑定键（保留，不影响任务）")
        
        print()
        print("[SUCCESS] 清理完成！")
        print()
        print("[TIP] 如果问题仍然存在，可以尝试：")
        print("  1. 重启 Celery Worker")
        print("  2. 使用 celery purge 命令清理队列")
        print("     celery -A app.tasks.celery_app purge")
        
        return True
        
    except redis.ConnectionError as e:
        print(f"[ERROR] Redis 连接失败: {e}")
        print(f"[INFO] 请检查 Redis 配置: {settings.REDIS_URL}")
        return False
    except Exception as e:
        print(f"[ERROR] 清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def purge_all_tasks():
    """清理所有任务（更激进的方式）"""
    print("=" * 60)
    print("清理所有 Celery 任务元数据（激进模式）")
    print("=" * 60)
    print()
    
    try:
        # 连接 Redis
        print(f"[INFO] 连接到 Redis: {settings.REDIS_URL}")
        
        if settings.REDIS_URL.startswith("redis://"):
            redis_url = settings.REDIS_URL
        else:
            if settings.REDIS_PASSWORD:
                redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            else:
                redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        
        client = redis.Redis.from_url(redis_url, decode_responses=False)
        client.ping()
        print("[SUCCESS] Redis 连接成功")
        print()
        
        # 查找所有任务元数据
        task_meta_keys = client.keys("celery-task-meta-*")
        print(f"[INFO] 找到 {len(task_meta_keys)} 个任务元数据")
        
        if not task_meta_keys:
            print("[INFO] 没有任务需要清理")
            return True
        
        # 确认删除
        print()
        print("[WARN] 这将删除所有任务元数据！")
        user_input = input("确认删除所有任务元数据？(yes/no): ")
        
        if user_input.lower() != 'yes':
            print("[CANCEL] 已取消")
            return False
        
        # 删除所有任务元数据
        deleted = 0
        for key in task_meta_keys:
            client.delete(key)
            deleted += 1
        
        print(f"[SUCCESS] 已删除 {deleted} 个任务元数据")
        return True
        
    except Exception as e:
        print(f"[ERROR] 清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="清理 Celery 失败任务")
    parser.add_argument(
        "--all",
        action="store_true",
        help="清理所有任务元数据（激进模式）"
    )
    
    args = parser.parse_args()
    
    if args.all:
        success = purge_all_tasks()
    else:
        success = cleanup_failed_tasks()
    
    sys.exit(0 if success else 1)
