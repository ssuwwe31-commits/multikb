"""
MinIO Configuration
"""

from minio import Minio
from app.config.settings import settings

# 创建MinIO客户端
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ROOT_USER,
    secret_key=settings.MINIO_ROOT_PASSWORD,
    secure=settings.MINIO_SECURE
)

def get_minio():
    """获取MinIO客户端"""
    return minio_client
