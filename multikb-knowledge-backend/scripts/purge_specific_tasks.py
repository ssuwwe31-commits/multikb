"""
清理队列中特定类型的任务
用于清理重复或不需要的任务
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def purge_specific_tasks():
    """清理特定任务"""
    try:
        from app.tasks.celery_app import celery_app
        
        print("=" * 60)
        print("清理队列中的特定任务")
        print("=" * 60)
        print()
        
        # 方法1: 清理所有队列（最简单）
        print("[方法1] 清理所有队列...")
        try:
            purged = celery_app.control.purge()
            print(f"  ✓ 已清理队列")
            if purged:
                for queue_name, count in purged.items():
                    print(f"    - {queue_name}: {count} 条消息")
        except Exception as e:
            print(f"  ✗ 清理失败: {e}")
        
        print()
        print("=" * 60)
        print("清理完成")
        print("=" * 60)
        print()
        print("[提示] 如果使用命令行，可以运行：")
        print("  celery -A app.tasks.celery_app purge -f")
        
        return True
        
    except ImportError as e:
        print(f"[错误] 导入失败: {e}")
        print("请确保在正确的 Python 环境中运行（包含 celery）")
        return False
    except Exception as e:
        print(f"[错误] 清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = purge_specific_tasks()
    sys.exit(0 if success else 1)
