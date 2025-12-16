"""
OpenSearch Dependencies
"""

from fastapi import Depends
from app.config.opensearch import get_opensearch

def get_opensearch_client():
    """获取OpenSearch客户端"""
    return get_opensearch()
