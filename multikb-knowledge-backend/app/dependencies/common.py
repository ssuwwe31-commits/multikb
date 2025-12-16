"""
Common Dependencies
"""

from fastapi import Depends, Request
from app.dependencies.database import get_db
from app.dependencies.cache import get_cache
from app.dependencies.opensearch import get_opensearch_client
from app.dependencies.minio import get_minio_client
from app.dependencies.ollama import get_ollama_config
from app.dependencies.auth import get_current_user, get_optional_user
from sqlalchemy.orm import Session
from app.core.cache import CacheManager
from opensearchpy import OpenSearch
from minio import Minio
from app.config.ollama import OllamaConfig
from typing import Optional, Dict, Any

def get_common_dependencies(
    db: Session = Depends(get_db),
    cache: CacheManager = Depends(get_cache),
    opensearch: OpenSearch = Depends(get_opensearch_client),
    minio: Minio = Depends(get_minio_client),
    ollama: OllamaConfig = Depends(get_ollama_config),
    user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """获取通用依赖"""
    return {
        "db": db,
        "cache": cache,
        "opensearch": opensearch,
        "minio": minio,
        "ollama": ollama,
        "user": user
    }

def get_request_info(request: Request):
    """获取请求信息"""
    return {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "request_id": getattr(request.state, "request_id", None)
    }
