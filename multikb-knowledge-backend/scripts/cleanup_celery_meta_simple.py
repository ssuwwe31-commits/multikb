"""
简单清理 Celery 任务元数据脚本
直接删除 Redis 中的任务元数据，解决序列化错误
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def cleanup_all_task_meta():
    """清理所有任务元数据"""
    try:
        from app.tasks.celery_app import celery_app
        from app.config.settings import settings
        
        print("=" * 60)
        print("清理 Celery 任务元数据")
        print("=" * 60)
        print()
        print(f"[INFO] Redis URL: {settings.REDIS_URL}")
        print()
        
        backend = celery_app.backend
        
        # 尝试获取 Redis 客户端
        # Celery Redis backend 的内部结构可能不同，尝试多种方式
        redis_client = None
        
        # 方法1: 直接访问 client 属性
        if hasattr(backend, 'client'):
            redis_client = backend.client
            print("[INFO] 通过 backend.client 获取 Redis 客户端")
        
        # 方法2: 通过 connection 获取
        elif hasattr(backend, 'connection'):
            conn = backend.connection
            if hasattr(conn, 'client'):
                redis_client = conn.client
                print("[INFO] 通过 backend.connection.client 获取 Redis 客户端")
            elif hasattr(conn, '_get_client'):
                redis_client = conn._get_client()
                print("[INFO] 通过 backend.connection._get_client() 获取 Redis 客户端")
        
        # 方法3: 使用 _get_client 方法
        elif hasattr(backend, '_get_client'):
            try:
                redis_client = backend._get_client()
                print("[INFO] 通过 backend._get_client() 获取 Redis 客户端")
            except:
                pass
        
        # 方法4: 直接导入 redis 并使用 settings
        if not redis_client:
            try:
                import redis
                redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
                print("[INFO] 直接使用 redis.Redis.from_url 创建客户端")
            except ImportError:
                print("[ERROR] 无法获取 Redis 客户端，且 redis 模块未安装")
                print()
                print("[TIP] 请手动执行以下 Python 代码：")
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
        
        # 测试连接
        try:
            redis_client.ping()
            print("[SUCCESS] Redis 连接成功")
        except Exception as e:
            print(f"[ERROR] Redis 连接失败: {e}")
            return False
        
        print()
        
        # 查找所有任务元数据
        print("[INFO] 查找任务元数据...")
        try:
            task_meta_keys = redis_client.keys("celery-task-meta-*")
            print(f"[INFO] 找到 {len(task_meta_keys)} 个任务元数据")
        except Exception as e:
            print(f"[ERROR] 查找任务元数据失败: {e}")
            return False
        
        if not task_meta_keys:
            print("[INFO] 没有任务元数据需要清理")
            return True
        
        # 删除所有任务元数据
        print("[INFO] 正在删除所有任务元数据...")
        try:
            # 尝试批量删除
            deleted = redis_client.delete(*task_meta_keys)
            print(f"[SUCCESS] 已删除 {deleted} 个任务元数据")
        except Exception as e:
            print(f"[WARN] 批量删除失败: {e}")
            print("[INFO] 尝试逐个删除...")
            deleted = 0
            for key in task_meta_keys:
                try:
                    if redis_client.delete(key):
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
        
    except ImportError as e:
        print(f"[ERROR] 导入失败: {e}")
        print("[INFO] 请确保在正确的 Python 环境中运行（包含 celery）")
        print()
        print("[TIP] 如果 celery 模块不可用，请使用以下方法：")
        print("1. 激活正确的 Python 环境（conda/venv）")
        print("2. 或使用以下 Python 代码直接清理：")
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
    success = cleanup_all_task_meta()
    sys.exit(0 if success else 1)
