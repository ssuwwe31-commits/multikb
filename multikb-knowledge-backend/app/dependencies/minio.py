"""
MinIO Dependencies
"""

from fastapi import Depends
from app.config.minio import get_minio

def get_minio_client():
    """获取MinIO客户端"""
    return get_minio()
