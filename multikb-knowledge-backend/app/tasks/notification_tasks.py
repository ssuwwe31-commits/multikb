"""
Notification Tasks
"""

from celery import current_task
from app.tasks.celery_app import celery_app
from app.models.document import Document
from app.models.task import CeleryTask
from sqlalchemy.orm import Session
from app.config.database import SessionLocal
from datetime import datetime

@celery_app.task(bind=True)
def send_notification_task(self, notification_type: str, data: dict):
    """发送通知任务"""
    db = SessionLocal()
    try:
        # 这里应该实现通知发送逻辑
        # 可以发送邮件、短信、推送通知等
        
        if notification_type == "document_processed":
            document_id = data.get("document_id")
            status = data.get("status")
            
            # 更新文档状态
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = status
                db.commit()
        
        elif notification_type == "task_completed":
            task_id = data.get("task_id")
            result = data.get("result")
            
            # 更新任务状态
            task = db.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
            if task:
                task.status = "completed"
                task.result = str(result)
                task.completed_at = datetime.now()
                db.commit()
        
        elif notification_type == "task_failed":
            task_id = data.get("task_id")
            error = data.get("error")
            
            # 更新任务状态
            task = db.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
            if task:
                task.status = "failed"
                task.error_message = str(error)
                task.completed_at = datetime.now()
                db.commit()
        
        return {"status": "success", "message": "通知发送完成"}
        
    except Exception as e:
        db.rollback()
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise e
    finally:
        db.close()

@celery_app.task
def send_email_notification_task(email: str, subject: str, content: str):
    """发送邮件通知任务"""
    try:
        # 这里应该实现邮件发送逻辑
        # 可以使用SMTP、SendGrid等服务
        
        print(f"发送邮件到 {email}: {subject}")
        print(f"内容: {content}")
        
        return {"status": "success", "message": "邮件发送完成"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@celery_app.task
def send_system_alert_task(alert_type: str, message: str, level: str = "info"):
    """发送系统告警任务"""
    try:
        # 这里应该实现系统告警逻辑
        # 可以发送到监控系统、日志系统等
        
        print(f"系统告警 [{level}]: {alert_type} - {message}")
        
        return {"status": "success", "message": "系统告警发送完成"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@celery_app.task
def batch_send_notifications_task(notifications: list):
    """批量发送通知任务"""
    for notification in notifications:
        send_notification_task.delay(
            notification.get("type"),
            notification.get("data", {})
        )
    
    return {"status": "success", "message": f"已启动 {len(notifications)} 个通知发送任务"}
