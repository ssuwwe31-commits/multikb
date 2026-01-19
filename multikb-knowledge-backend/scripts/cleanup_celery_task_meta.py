"""
快速清理 Celery 任务元数据脚本
直接使用 Celery backend 清理，无需额外依赖
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def cleanup_task_meta():
    """清理损坏的任务元数据"""
    try:
        from app.tasks.celery_app import celery_app
        
        print("=" * 60)
        print("清理 Celery 任务元数据")
        print("=" * 60)
        print()
        
        backend = celery_app.backend
        print(f"[INFO] Backend 类型: {type(backend).__name__}")
        
        # 获取 Redis 客户端
        redis_client = None
        
        # 尝试多种方式获取 Redis 客户端
        if hasattr(backend, 'client'):
            redis_client = backend.client
        elif hasattr(backend, '_get_client'):
            redis_client = backend._get_client()
        elif hasattr(backend, 'connection'):
            conn = backend.connection
            if hasattr(conn, 'client'):
                redis_client = conn.client
            elif hasattr(conn, '_get_client'):
                redis_client = conn._get_client()
        
        if not redis_client:
            # 尝试通过 backend 的 _get_client 方法
            try:
                # Redis backend 通常有这个方法
                if hasattr(backend, '_get_client'):
                    redis_client = backend._get_client()
                elif hasattr(backend, 'connection') and hasattr(backend.connection, 'client'):
                    redis_client = backend.connection.client
            except:
                pass
        
        if not redis_client:
            print("[ERROR] 无法获取 Redis 客户端")
            print("[TIP] 请尝试手动清理，或使用以下 Python 代码：")
            print()
            print("```python")
            print("import redis")
            print("from app.config.settings import settings")
            print("client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)")
            print("keys = client.keys('celery-task-meta-*')")
            print("if keys:")
            print("    client.delete(*keys)")
            print("    print(f'已删除 {len(keys)} 个任务元数据')")
            print("```")
            return False
        
        # 查找所有任务元数据
        print("[INFO] 查找任务元数据...")
        task_meta_keys = redis_client.keys("celery-task-meta-*")
        print(f"[INFO] 找到 {len(task_meta_keys)} 个任务元数据")
        
        if not task_meta_keys:
            print("[INFO] 没有任务元数据需要清理")
            return True
        
        # 删除所有任务元数据
        print("[INFO] 正在删除任务元数据...")
        deleted = 0
        
        # 批量删除（如果支持）
        try:
            if len(task_meta_keys) > 0:
                deleted = redis_client.delete(*task_meta_keys)
        except Exception as e:
            # 如果不支持批量删除，逐个删除
            print(f"[WARN] 批量删除失败，改为逐个删除: {e}")
            for key in task_meta_keys:
                try:
                    redis_client.delete(key)
                    deleted += 1
                except Exception as e2:
                    print(f"  [ERROR] 删除失败: {key}, {e2}")
        
        print()
        print("=" * 60)
        print(f"[SUCCESS] 已删除 {deleted} 个任务元数据")
        print("=" * 60)
        print()
        print("[TIP] 请重启 Celery Worker 以确保完全清理")
        
        return True
        
    except ImportError as e:
        print(f"[ERROR] 导入失败: {e}")
        print("[INFO] 请确保在正确的 Python 环境中运行（包含 celery 和 redis）")
        return False
    except Exception as e:
        print(f"[ERROR] 清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = cleanup_task_meta()
    sys.exit(0 if success else 1)
