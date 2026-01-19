"""
检查 Celery 状态脚本
检查队列、任务元数据和 Worker 状态
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_celery_status():
    """检查 Celery 状态"""
    try:
        import redis
        from app.config.settings import settings
        
        print("=" * 60)
        print("检查 Celery 状态")
        print("=" * 60)
        print()
        
        # 1. 检查 Redis 连接
        print("[1] 检查 Redis 连接...")
        try:
            client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
            client.ping()
            print(f"  ✓ Redis 连接成功: {settings.REDIS_URL}")
        except Exception as e:
            print(f"  ✗ Redis 连接失败: {e}")
            return False
        
        print()
        
        # 2. 检查任务元数据
        print("[2] 检查任务元数据...")
        task_meta_keys = client.keys("celery-task-meta-*")
        print(f"  找到 {len(task_meta_keys)} 个任务元数据")
        
        if task_meta_keys:
            print("  前10个任务ID:")
            for i, key in enumerate(task_meta_keys[:10]):
                task_id = key.decode('utf-8') if isinstance(key, bytes) else key
                task_id = task_id.replace('celery-task-meta-', '')
                print(f"    {i+1}. {task_id}")
            if len(task_meta_keys) > 10:
                print(f"    ... 还有 {len(task_meta_keys) - 10} 个任务")
        else:
            print("  ✓ 没有任务元数据")
        
        print()
        
        # 3. 检查队列中的消息
        print("[3] 检查队列中的消息...")
        try:
            from app.tasks.celery_app import celery_app
            
            # 获取所有队列
            queues = []
            for queue_name in ['default', 'code', 'document', 'vector', 'index', 'image', 'version', 'cleanup', 'notification', 'observability', 'security_scan']:
                try:
                    queue = celery_app.control.inspect().active_queues()
                    if queue:
                        queues.append(queue_name)
                except:
                    pass
            
            # 使用 inspect 检查活动任务
            inspect = celery_app.control.inspect()
            active = inspect.active()
            scheduled = inspect.scheduled()
            reserved = inspect.reserved()
            
            if active:
                print(f"  活动任务: {len(active.get(list(active.keys())[0] if active else [], []))} 个")
                for worker, tasks in active.items():
                    for task in tasks:
                        print(f"    - {task['name']} [{task['id']}]")
            else:
                print("  ✓ 没有活动任务")
            
            if scheduled:
                print(f"  计划任务: {len(scheduled.get(list(scheduled.keys())[0] if scheduled else [], []))} 个")
            else:
                print("  ✓ 没有计划任务")
            
            if reserved:
                print(f"  保留任务: {len(reserved.get(list(reserved.keys())[0] if reserved else [], []))} 个")
            else:
                print("  ✓ 没有保留任务")
                
        except Exception as e:
            print(f"  ⚠️ 无法检查队列状态: {e}")
            print("  （可能需要 Worker 正在运行）")
        
        print()
        print("=" * 60)
        print("检查完成")
        print("=" * 60)
        print()
        
        # 建议
        if task_meta_keys:
            print("[建议] 发现任务元数据，可以运行清理脚本：")
            print("  python scripts/cleanup_redis_task_meta.py")
        else:
            print("[建议] 任务元数据已清理，如果问题仍然存在：")
            print("  1. 重启 Celery Worker")
            print("  2. 检查是否有任务正在执行")
        
        return True
        
    except ImportError as e:
        print(f"[错误] 导入失败: {e}")
        print("请确保在正确的 Python 环境中运行（包含 redis 和 celery）")
        return False
    except Exception as e:
        print(f"[错误] 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = check_celery_status()
    sys.exit(0 if success else 1)
