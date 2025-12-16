"""
Search History Service
搜索历史服务
"""

from typing import List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from app.models.search_history import SearchHistory, SearchHotword
from app.config.settings import settings
from app.core.logging import logger


class SearchHistoryService:
    """搜索历史服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def save_search_history(
        self,
        user_id: int,
        query_text: str,
        search_type: str,
        knowledge_base_id: Optional[Union[int, List[int]]] = None,
        result_count: int = 0,
        search_time_ms: Optional[int] = None
    ) -> SearchHistory:
        """保存搜索历史"""
        try:
            # 限制查询文本长度
            query_text = query_text[:500] if len(query_text) > 500 else query_text
            
            # 处理知识库ID：如果是列表，只取第一个（数据库字段是INT类型）
            kb_id_for_db = None
            if knowledge_base_id is not None:
                if isinstance(knowledge_base_id, list):
                    if len(knowledge_base_id) > 0:
                        kb_id_for_db = knowledge_base_id[0]  # 只存储第一个ID
                elif isinstance(knowledge_base_id, int):
                    kb_id_for_db = knowledge_base_id
            
            history = SearchHistory(
                user_id=user_id,
                query_text=query_text,
                search_type=search_type,
                knowledge_base_id=kb_id_for_db,
                result_count=result_count,
                search_time_ms=search_time_ms
            )
            self.db.add(history)
            self.db.commit()
            self.db.refresh(history)
            
            # 更新搜索热词
            await self._update_hotword(query_text)
            
            return history
        except Exception as e:
            logger.error(f"保存搜索历史失败: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    async def _update_hotword(self, keyword: str):
        """更新搜索热词统计"""
        try:
            # 提取关键词（简单处理，可以后续优化）
            keyword = keyword.strip()[:200]
            if not keyword:
                return
            
            # 查找或创建热词记录
            hotword = self.db.query(SearchHotword).filter(
                SearchHotword.keyword == keyword,
                SearchHotword.is_deleted == False
            ).first()
            
            if hotword:
                hotword.search_count += 1
                hotword.last_searched_at = datetime.utcnow()
            else:
                hotword = SearchHotword(
                    keyword=keyword,
                    search_count=1,
                    last_searched_at=datetime.utcnow()
                )
                self.db.add(hotword)
            
            self.db.commit()
        except Exception as e:
            logger.warning(f"更新搜索热词失败: {e}")
            self.db.rollback()
            # 不抛出异常，避免影响主流程
    
    async def get_search_history(
        self,
        user_id: Optional[int] = None,
        limit: int = settings.SEARCH_HISTORY_DEFAULT_LIMIT,
        offset: int = 0
    ) -> List[SearchHistory]:
        """获取搜索历史"""
        try:
            # 统一限制返回数量，避免查询过多记录
            if limit is None or limit <= 0:
                limit = settings.SEARCH_HISTORY_DEFAULT_LIMIT
            limit = min(max(1, limit), settings.SEARCH_HISTORY_MAX_LIMIT)
            offset = max(0, offset)
            
            query = self.db.query(SearchHistory).filter(
                SearchHistory.is_deleted == False
            )
            
            if user_id:
                query = query.filter(SearchHistory.user_id == user_id)
            
            query = query.order_by(desc(SearchHistory.created_at))
            query = query.offset(offset).limit(limit)
            
            return query.all()
        except Exception as e:
            logger.error(f"获取搜索历史失败: {e}", exc_info=True)
            raise
    
    async def delete_search_history(self, history_id: int, user_id: Optional[int] = None) -> bool:
        """删除搜索历史（软删除）"""
        try:
            query = self.db.query(SearchHistory).filter(
                SearchHistory.id == history_id,
                SearchHistory.is_deleted == False
            )
            
            if user_id:
                query = query.filter(SearchHistory.user_id == user_id)
            
            history = query.first()
            if not history:
                return False
            
            history.is_deleted = True
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"删除搜索历史失败: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    async def clear_search_history(self, user_id: int) -> int:
        """清空用户搜索历史（软删除）"""
        try:
            count = self.db.query(SearchHistory).filter(
                SearchHistory.user_id == user_id,
                SearchHistory.is_deleted == False
            ).update({"is_deleted": True})
            
            self.db.commit()
            return count
        except Exception as e:
            logger.error(f"清空搜索历史失败: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    async def get_hotwords(self, limit: int = 20, period: str = "week") -> List[SearchHotword]:
        """获取搜索热词"""
        try:
            query = self.db.query(SearchHotword).filter(
                SearchHotword.is_deleted == False
            )
            
            # 根据时间段过滤（简化实现，可以后续优化）
            if period == "day":
                from datetime import timedelta
                cutoff = datetime.utcnow() - timedelta(days=1)
                query = query.filter(SearchHotword.last_searched_at >= cutoff)
            elif period == "week":
                from datetime import timedelta
                cutoff = datetime.utcnow() - timedelta(days=7)
                query = query.filter(SearchHotword.last_searched_at >= cutoff)
            elif period == "month":
                from datetime import timedelta
                cutoff = datetime.utcnow() - timedelta(days=30)
                query = query.filter(SearchHotword.last_searched_at >= cutoff)
            
            query = query.order_by(desc(SearchHotword.search_count))
            query = query.limit(limit)
            
            return query.all()
        except Exception as e:
            logger.error(f"获取搜索热词失败: {e}", exc_info=True)
            raise
