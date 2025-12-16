"""
Task Status Service
任务状态服务 - 用于查询Celery任务状态
"""

from typing import Dict, Any, Optional
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app
from app.core.logging import logger
from datetime import datetime


class TaskStatusService:
    """任务状态服务"""
    
    def __init__(self):
        self.celery_app = celery_app
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取Celery任务状态"""
        try:
            task = AsyncResult(task_id, app=self.celery_app)
            
            # 获取任务信息
            task_info = task.info
            
            # 基础状态
            status = task.state
            
            # 构建状态信息
            result = {
                "task_id": task_id,
                "status": status,
                "ready": task.ready(),
                "successful": task.successful() if task.ready() else False,
                "failed": task.failed() if task.ready() else False,
                "progress": task_info.get("current", 0) if task_info else 0,
                "total": task_info.get("total", 100) if task_info else 100,
                "message": task_info.get("status", "") if task_info else "",
                "result": task.result if task.ready() else None,
                "traceback": task.traceback if task.failed() else None
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取任务状态错误: {e}", exc_info=True)
            return {
                "task_id": task_id,
                "status": "UNKNOWN",
                "ready": False,
                "successful": False,
                "failed": False,
                "progress": 0,
                "total": 100,
                "message": f"获取任务状态失败: {str(e)}",
                "result": None,
                "traceback": str(e)
            }
    
    def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """获取任务进度"""
        task_status = self.get_task_status(task_id)
        
        return {
            "task_id": task_id,
            "progress_percentage": (task_status.get("progress", 0) / task_status.get("total", 100)) * 100,
            "current": task_status.get("progress", 0),
            "total": task_status.get("total", 100),
            "status": task_status.get("status"),
            "message": task_status.get("message", "")
        }
    
    def wait_for_task(self, task_id: str, timeout: int = 300) -> Dict[str, Any]:
        """等待任务完成（带超时）"""
        from time import sleep
        
        elapsed_time = 0
        check_interval = 1
        
        while elapsed_time < timeout:
            task_status = self.get_task_status(task_id)
            
            if task_status["ready"]:
                return task_status
            
            sleep(check_interval)
            elapsed_time += check_interval
        
        # 超时
        return {
            "task_id": task_id,
            "status": "TIMEOUT",
            "message": f"任务超时（{timeout}秒）"
        }
