"""
立即清理 Celery 任务元数据 - 最简单版本
复制此代码到 Python 交互式环境运行即可
"""

# ============================================
# 复制以下代码到 Python 交互式环境运行
# ============================================

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import redis
    from app.config.settings import settings
    
    print("=" * 60)
    print("清理 Celery 任务元数据")
    print("=" * 60)
    print(f"Redis URL: {settings.REDIS_URL}")
    print()
    
    # 连接 Redis
    client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
    client.ping()
    print("✓ Redis 连接成功")
    print()
    
    # 查找并删除所有任务元数据
    keys = client.keys('celery-task-meta-*')
    print(f"找到 {len(keys)} 个任务元数据")
    
    if keys:
        deleted = client.delete(*keys)
        print(f"✓ 已删除 {deleted} 个任务元数据")
    else:
        print("✓ 没有任务元数据需要清理")
    
    print()
    print("=" * 60)
    print("清理完成！请重启 Celery Worker")
    print("=" * 60)
    
except ImportError as e:
    print(f"错误: {e}")
    print("\n请确保已安装 redis 模块:")
    print("  pip install redis")
    print("\n或者激活正确的 Python 环境（conda/venv）")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
