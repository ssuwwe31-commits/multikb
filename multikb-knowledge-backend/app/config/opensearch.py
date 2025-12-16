"""
OpenSearch Configuration
"""

from opensearchpy import OpenSearch
from app.config.settings import settings

# 创建OpenSearch客户端
opensearch_client = OpenSearch(
    hosts=[settings.OPENSEARCH_URL],
    use_ssl=settings.OPENSEARCH_USE_SSL,
    verify_certs=settings.OPENSEARCH_VERIFY_CERTS,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
    timeout=30,
    max_retries=3,
    retry_on_timeout=True
)

def get_opensearch():
    """获取OpenSearch客户端"""
    return opensearch_client
