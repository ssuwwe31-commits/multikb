"""
清理 Celery Beat 调度数据库文件。

如果 Beat 任务被重复触发，可能是调度数据库文件损坏或包含旧的调度记录。
运行此脚本可以清理调度数据库，让 Beat 重新开始调度。

使用方法:
    python scripts/cleanup_beat_schedule.py
"""

import os
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
_current_dir = Path(__file__).parent
_project_root = _current_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app.core.logging import logger


def cleanup_beat_schedule():
    """清理 Celery Beat 调度数据库文件。"""
    # Beat 调度数据库文件路径（默认在当前目录）
    beat_schedule_files = [
        "celerybeat-schedule",  # 默认文件名
        "celerybeat-schedule.db",  # SQLite 数据库文件
        "celerybeat.pid",  # Beat 进程 ID 文件
    ]
    
    cleaned_files = []
    for filename in beat_schedule_files:
        file_path = Path(filename)
        if file_path.exists():
            try:
                file_path.unlink()
                cleaned_files.append(filename)
                logger.info(f"已删除 Beat 调度文件: {filename}")
            except Exception as e:
                logger.error(f"删除文件 {filename} 时出错: {e}")
        else:
            logger.info(f"文件不存在，跳过: {filename}")
    
    if cleaned_files:
        logger.info(f"✅ 已清理 {len(cleaned_files)} 个 Beat 调度文件")
        logger.info("提示: 请重启 Celery Beat 以重新生成调度数据库")
    else:
        logger.info("ℹ️  没有找到需要清理的 Beat 调度文件")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = cleanup_beat_schedule()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"清理 Beat 调度文件时出错: {e}", exc_info=True)
        sys.exit(1)
