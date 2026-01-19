"""
直接清理 Redis 中的 Celery 任务元数据
只需要 redis 模块，不需要 celery
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def cleanup_task_meta():
    """清理任务元数据"""
    try:
        import redis
        from app.config.settings import settings
        
        print("=" * 60)
        print("清理 Celery 任务元数据（直接使用 Redis）")
        print("=" * 60)
        print()
        print(f"[INFO] Redis URL: {settings.REDIS_URL}")
        print()
        
        # 连接 Redis
        try:
            client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
            client.ping()
            print("[SUCCESS] Redis 连接成功")
        except Exception as e:
            print(f"[ERROR] Redis 连接失败: {e}")
            return False
        
        print()
        
        # 查找所有任务元数据
        print("[INFO] 查找任务元数据...")
        task_meta_keys = client.keys("celery-task-meta-*")
        print(f"[INFO] 找到 {len(task_meta_keys)} 个任务元数据")
        
        if not task_meta_keys:
            print("[INFO] 没有任务元数据需要清理")
            return True
        
        # 显示前几个任务 ID
        print()
        print("[INFO] 任务列表（前10个）：")
        for i, key in enumerate(task_meta_keys[:10]):
            task_id = key.decode('utf-8') if isinstance(key, bytes) else key
            task_id = task_id.replace('celery-task-meta-', '')
            print(f"  {i+1}. {task_id}")
        if len(task_meta_keys) > 10:
            print(f"  ... 还有 {len(task_meta_keys) - 10} 个任务")
        
        print()
        
        # 删除所有任务元数据
        print("[INFO] 正在删除所有任务元数据...")
        try:
            deleted = client.delete(*task_meta_keys)
            print(f"[SUCCESS] 已删除 {deleted} 个任务元数据")
        except Exception as e:
            print(f"[WARN] 批量删除失败: {e}")
            print("[INFO] 尝试逐个删除...")
            deleted = 0
            for key in task_meta_keys:
                try:
                    if client.delete(key):
                        deleted += 1
                except Exception as e2:
                    print(f"  [ERROR] 删除失败: {key}, {e2}")
            print(f"[INFO] 已删除 {deleted} 个任务元数据")
        
        print()
        print("=" * 60)
        print("[SUCCESS] 清理完成！")
        print("=" * 60)
        print()
        print("[TIP] 请重启 Celery Worker 以确保完全清理")
        
        return True
        
    except ImportError:
        print("[ERROR] redis 模块未安装")
        print()
        print("[TIP] 请安装 redis 模块：")
        print("  pip install redis")
        print()
        print("或者使用以下 Python 代码（在正确的环境中运行）：")
        print()
        print("```python")
        print("import redis")
        print("from app.config.settings import settings")
        print("client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)")
        print("keys = client.keys('celery-task-meta-*')")
        print("if keys:")
        print("    deleted = client.delete(*keys)")
        print("    print(f'已删除 {deleted} 个任务元数据')")
        print("```")
        return False
    except Exception as e:
        print(f"[ERROR] 清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = cleanup_task_meta()
    sys.exit(0 if success else 1)
