"""
Cache Service
"""

from typing import Any, Optional, Dict, List
from sqlalchemy.orm import Session
from app.core.logging import logger
from app.core.cache import cache_manager

class CacheService:
    """缓存服务 - 根据文档处理流程设计实现"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_document_cache(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """获取文档缓存"""
        try:
            cache_key = f"document:info:{doc_id}"
            cached_data = cache_manager.get(cache_key)
            
            if cached_data:
                logger.debug(f"文档缓存命中: {doc_id}")
            else:
                logger.debug(f"文档缓存未命中: {doc_id}")
            
            return cached_data
            
        except Exception as e:
            logger.error(f"获取文档缓存错误: {e}", exc_info=True)
            return None
    
    def set_document_cache(self, doc_id: int, data: Dict[str, Any], ex: int = 3600) -> bool:
        """设置文档缓存"""
        try:
            cache_key = f"document:info:{doc_id}"
            success = cache_manager.set(cache_key, data, ex)
            
            if success:
                logger.debug(f"文档缓存设置成功: {doc_id}")
            else:
                logger.warning(f"文档缓存设置失败: {doc_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"设置文档缓存错误: {e}", exc_info=True)
            return False
    
    def delete_document_cache(self, doc_id: int) -> bool:
        """删除文档缓存"""
        try:
            cache_key = f"document:info:{doc_id}"
            success = cache_manager.delete(cache_key)
            
            if success:
                logger.debug(f"文档缓存删除成功: {doc_id}")
            else:
                logger.warning(f"文档缓存删除失败: {doc_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除文档缓存错误: {e}", exc_info=True)
            return False
    
    def get_knowledge_base_cache(self, kb_id: int) -> Optional[Dict[str, Any]]:
        """获取知识库缓存"""
        try:
            cache_key = f"kb:info:{kb_id}"
            cached_data = cache_manager.get(cache_key)
            
            if cached_data:
                logger.debug(f"知识库缓存命中: {kb_id}")
            else:
                logger.debug(f"知识库缓存未命中: {kb_id}")
            
            return cached_data
            
        except Exception as e:
            logger.error(f"获取知识库缓存错误: {e}", exc_info=True)
            return None
    
    def set_knowledge_base_cache(self, kb_id: int, data: Dict[str, Any], ex: int = 3600) -> bool:
        """设置知识库缓存"""
        try:
            cache_key = f"kb:info:{kb_id}"
            success = cache_manager.set(cache_key, data, ex)
            
            if success:
                logger.debug(f"知识库缓存设置成功: {kb_id}")
            else:
                logger.warning(f"知识库缓存设置失败: {kb_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"设置知识库缓存错误: {e}", exc_info=True)
            return False
    
    def get_search_results_cache(self, query: str, kb_id: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """获取搜索结果缓存"""
        try:
            cache_key = f"search:results:{hash(query)}:{kb_id or 'all'}"
            cached_data = cache_manager.get(cache_key)
            
            if cached_data:
                logger.debug(f"搜索结果缓存命中: {query[:50]}...")
            else:
                logger.debug(f"搜索结果缓存未命中: {query[:50]}...")
            
            return cached_data
            
        except Exception as e:
            logger.error(f"获取搜索结果缓存错误: {e}", exc_info=True)
            return None
    
    def set_search_results_cache(self, query: str, results: List[Dict[str, Any]], kb_id: Optional[int] = None, ex: int = 1800) -> bool:
        """设置搜索结果缓存"""
        try:
            cache_key = f"search:results:{hash(query)}:{kb_id or 'all'}"
            success = cache_manager.set(cache_key, results, ex)
            
            if success:
                logger.debug(f"搜索结果缓存设置成功: {query[:50]}...")
            else:
                logger.warning(f"搜索结果缓存设置失败: {query[:50]}...")
            
            return success
            
        except Exception as e:
            logger.error(f"设置搜索结果缓存错误: {e}", exc_info=True)
            return False
    
    def clear_document_related_cache(self, doc_id: int) -> bool:
        """清除文档相关缓存"""
        try:
            logger.info(f"清除文档相关缓存: {doc_id}")
            
            # 清除文档缓存
            self.delete_document_cache(doc_id)
            
            # 清除搜索结果缓存（包含该文档的搜索结果）
            pattern = f"search:results:*"
            deleted_count = cache_manager.delete_pattern(pattern)
            
            logger.info(f"文档相关缓存清除完成: {doc_id}, 清除缓存数量: {deleted_count}")
            return True
            
        except Exception as e:
            logger.error(f"清除文档相关缓存错误: {e}", exc_info=True)
            return False
