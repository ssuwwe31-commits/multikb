"""
Celery Configuration

注意：实际使用的 Celery 应用在 app.tasks.celery_app 中，
它包含完整的任务路由配置。这里保持向后兼容，直接导入。
"""

# 统一使用 app.tasks.celery_app，它包含完整的任务路由配置
from app.tasks.celery_app import celery_app

def get_celery():
    """获取Celery应用"""
    return celery_app
