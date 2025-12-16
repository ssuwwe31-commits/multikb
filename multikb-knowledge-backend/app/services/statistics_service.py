"""
Statistics Service
统计服务
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, or_, distinct
from datetime import datetime, timedelta, date
from app.models.user_statistics import UserStatistics, DocumentTypeStatistics
from app.models.document import Document
from app.models.image import DocumentImage
from app.models.knowledge_base import KnowledgeBase
from app.models.knowledge_base_member import KnowledgeBaseMember
from app.models.search_history import SearchHistory
from app.models.qa_session import QASession
from app.core.logging import logger


class StatisticsService:
    """统计服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_personal_statistics(self, user_id: int, period: str = "all") -> Dict[str, Any]:
        """获取个人数据统计"""
        try:
            # 知识库统计：用户创建的 + 用户作为成员的知识库
            # 使用与知识库列表服务相同的逻辑
            member_join_cond = and_(
                KnowledgeBaseMember.knowledge_base_id == KnowledgeBase.id,
                KnowledgeBaseMember.user_id == user_id
            )
            
            # 统计用户创建的知识库 + 作为成员的知识库（去重）
            kb_count_query = self.db.query(func.count(func.distinct(KnowledgeBase.id))).outerjoin(
                KnowledgeBaseMember,
                member_join_cond
            ).filter(
                or_(
                    KnowledgeBase.user_id == user_id,
                    KnowledgeBaseMember.user_id == user_id
                ),
                KnowledgeBase.is_deleted == False
            )
            
            kb_count = kb_count_query.scalar() or 0
            
            # 活跃知识库统计
            kb_active_query = self.db.query(func.count(func.distinct(KnowledgeBase.id))).outerjoin(
                KnowledgeBaseMember,
                member_join_cond
            ).filter(
                or_(
                    KnowledgeBase.user_id == user_id,
                    KnowledgeBaseMember.user_id == user_id
                ),
                KnowledgeBase.is_deleted == False,
                KnowledgeBase.is_active == True
            )
            
            kb_active = kb_active_query.scalar() or 0
            
            # 获取用户有权限访问的知识库ID列表（用于文档统计）
            kb_ids_query = self.db.query(distinct(KnowledgeBase.id)).outerjoin(
                KnowledgeBaseMember,
                member_join_cond
            ).filter(
                or_(
                    KnowledgeBase.user_id == user_id,
                    KnowledgeBaseMember.user_id == user_id
                ),
                KnowledgeBase.is_deleted == False
            )
            
            kb_ids = [kb_id[0] for kb_id in kb_ids_query.all()]
            
            # 文档统计：统计用户有权限访问的知识库中的所有文档
            docs_query = self.db.query(Document).filter(
                Document.is_deleted == False
            )
            
            # 如果用户有访问权限的知识库列表不为空，则只统计这些知识库的文档
            if kb_ids:
                docs_query = docs_query.filter(Document.knowledge_base_id.in_(kb_ids))
            else:
                # 如果没有知识库，则只统计用户自己上传的文档
                docs_query = docs_query.filter(Document.user_id == user_id)
            
            # 根据时间段过滤
            if period == "week":
                week_ago = datetime.utcnow() - timedelta(days=7)
                docs_query = docs_query.filter(Document.created_at >= week_ago)
            elif period == "month":
                month_ago = datetime.utcnow() - timedelta(days=30)
                docs_query = docs_query.filter(Document.created_at >= month_ago)
            elif period == "year":
                year_ago = datetime.utcnow() - timedelta(days=365)
                docs_query = docs_query.filter(Document.created_at >= year_ago)
            
            doc_count = docs_query.count()
            
            # 按类型统计
            doc_by_type = {}
            doc_by_status = {}
            total_size = 0
            
            docs = docs_query.all()
            for doc in docs:
                # 按类型统计
                file_type = doc.file_type or "unknown"
                doc_by_type[file_type] = doc_by_type.get(file_type, 0) + 1
                
                # 按状态统计
                status = doc.status or "unknown"
                doc_by_status[status] = doc_by_status.get(status, 0) + 1
                
                # 累计大小
                if doc.file_size:
                    total_size += doc.file_size
            
            # 图片统计（基于用户有权限访问的知识库中的文档）
            image_query = self.db.query(DocumentImage).join(
                Document,
                DocumentImage.document_id == Document.id
            ).filter(
                Document.is_deleted == False,
                DocumentImage.is_deleted == False
            )
            
            # 如果用户有访问权限的知识库列表不为空，则只统计这些知识库的图片
            if kb_ids:
                image_query = image_query.filter(Document.knowledge_base_id.in_(kb_ids))
            else:
                # 如果没有知识库，则只统计用户自己上传的文档的图片
                image_query = image_query.filter(Document.user_id == user_id)
            
            if period == "week":
                week_ago = datetime.utcnow() - timedelta(days=7)
                image_query = image_query.filter(DocumentImage.created_at >= week_ago)
            elif period == "month":
                month_ago = datetime.utcnow() - timedelta(days=30)
                image_query = image_query.filter(DocumentImage.created_at >= month_ago)
            elif period == "year":
                year_ago = datetime.utcnow() - timedelta(days=365)
                image_query = image_query.filter(DocumentImage.created_at >= year_ago)
            
            image_count = image_query.count()
            image_by_type: Dict[str, int] = {}
            image_by_status: Dict[str, int] = {}
            image_total_size = 0
            
            images = image_query.all()
            for image in images:
                image_type = (image.image_type or "unknown").lower()
                image_by_type[image_type] = image_by_type.get(image_type, 0) + 1
                
                img_status = image.status or "unknown"
                image_by_status[img_status] = image_by_status.get(img_status, 0) + 1
                
                if image.file_size:
                    image_total_size += image.file_size
            
            # 使用统计
            search_count = self.db.query(SearchHistory).filter(
                SearchHistory.user_id == user_id,
                SearchHistory.is_deleted == False
            ).count()
            
            # ✅ 统计问答次数：使用所有会话的 question_count 总和（问题总数）
            qa_count_result = self.db.query(func.sum(QASession.question_count)).filter(
                QASession.user_id == user_id,
                QASession.status == "active"
            ).scalar()
            qa_count = int(qa_count_result) if qa_count_result is not None else 0
            
            # 上传统计：统计用户有权限访问的知识库中的所有文档数量
            upload_query = self.db.query(Document).filter(
                Document.is_deleted == False
            )
            
            # 如果用户有访问权限的知识库列表不为空，则只统计这些知识库的文档
            if kb_ids:
                upload_query = upload_query.filter(Document.knowledge_base_id.in_(kb_ids))
            else:
                # 如果没有知识库，则只统计用户自己上传的文档
                upload_query = upload_query.filter(Document.user_id == user_id)
            
            upload_count = upload_query.count()
            
            # 最后活跃时间
            last_search = self.db.query(SearchHistory).filter(
                SearchHistory.user_id == user_id,
                SearchHistory.is_deleted == False
            ).order_by(desc(SearchHistory.created_at)).first()
            
            last_active_date = None
            if last_search and last_search.created_at:
                last_active_date = last_search.created_at.date().isoformat()
            
            # 存储统计（简化实现，可以后续优化）
            storage_used = total_size
            storage_limit = 10 * 1024 * 1024 * 1024  # 默认10GB
            
            return {
                "knowledge_bases": {
                    "total": kb_count,
                    "active": kb_active,
                    "total_documents": doc_count
                },
                "documents": {
                    "total": doc_count,
                    "by_type": doc_by_type,
                    "by_status": doc_by_status,
                    "total_size": total_size
                },
                "images": {
                    "total": image_count,
                    "by_type": image_by_type,
                    "by_status": image_by_status,
                    "total_size": image_total_size
                },
                "usage": {
                    "total_searches": search_count,
                    "total_qa_sessions": qa_count,
                    "total_uploads": upload_count,
                    "last_active_date": last_active_date
                },
                "storage": {
                    "used": storage_used,
                    "limit": storage_limit,
                    "percentage": round((storage_used / storage_limit * 100) if storage_limit > 0 else 0, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"获取个人统计数据失败: {e}", exc_info=True)
            raise
    
    async def get_trends(
        self,
        user_id: int,
        metric: str,
        period: str = "month",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取数据趋势"""
        try:
            # 确定日期范围
            if start_date and end_date:
                start = datetime.fromisoformat(start_date).date()
                end = datetime.fromisoformat(end_date).date()
            elif period == "week":
                end = date.today()
                start = end - timedelta(days=7)
            elif period == "month":
                end = date.today()
                start = end - timedelta(days=30)
            elif period == "year":
                end = date.today()
                start = end - timedelta(days=365)
            else:
                end = date.today()
                start = end - timedelta(days=30)
            
            # 根据指标类型查询
            data_points = []
            current_date = start
            
            while current_date <= end:
                if metric == "document_count":
                    count = self.db.query(Document).filter(
                        Document.user_id == user_id,
                        Document.is_deleted == False,
                        func.date(Document.created_at) == current_date
                    ).count()
                elif metric == "search_count":
                    count = self.db.query(SearchHistory).filter(
                        SearchHistory.user_id == user_id,
                        SearchHistory.is_deleted == False,
                        func.date(SearchHistory.created_at) == current_date
                    ).count()
                elif metric == "upload_count":
                    count = self.db.query(Document).filter(
                        Document.user_id == user_id,
                        Document.is_deleted == False,
                        func.date(Document.created_at) == current_date
                    ).count()
                else:
                    count = 0
                
                data_points.append({
                    "date": current_date.isoformat(),
                    "value": count
                })
                
                current_date += timedelta(days=1)
            
            # 计算趋势
            if len(data_points) >= 2:
                first_value = data_points[0]["value"]
                last_value = data_points[-1]["value"]
                
                if first_value > 0:
                    growth_rate = ((last_value - first_value) / first_value) * 100
                else:
                    growth_rate = 100.0 if last_value > 0 else 0.0
                
                if growth_rate > 5:
                    trend = "increasing"
                elif growth_rate < -5:
                    trend = "decreasing"
                else:
                    trend = "stable"
            else:
                growth_rate = 0.0
                trend = "stable"
            
            return {
                "metric": metric,
                "period": period,
                "data": data_points,
                "trend": trend,
                "growth_rate": round(growth_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"获取趋势数据失败: {e}", exc_info=True)
            raise
    
    async def get_knowledge_base_heatmap(self, user_id: int) -> List[Dict[str, Any]]:
        """获取知识库使用热力图"""
        try:
            # 获取用户的知识库
            kbs = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.user_id == user_id,
                KnowledgeBase.is_deleted == False
            ).all()
            
            heatmap = []
            for kb in kbs:
                # 统计使用次数（搜索历史中引用该知识库的次数）
                usage_count = self.db.query(SearchHistory).filter(
                    SearchHistory.user_id == user_id,
                    SearchHistory.knowledge_base_id == kb.id,
                    SearchHistory.is_deleted == False
                ).count()
                
                # 文档数量
                doc_count = self.db.query(Document).filter(
                    Document.knowledge_base_id == kb.id,
                    Document.user_id == user_id,
                    Document.is_deleted == False
                ).count()
                
                # 最后使用时间
                last_search = self.db.query(SearchHistory).filter(
                    SearchHistory.user_id == user_id,
                    SearchHistory.knowledge_base_id == kb.id,
                    SearchHistory.is_deleted == False
                ).order_by(desc(SearchHistory.created_at)).first()
                
                last_used = None
                if last_search and last_search.created_at:
                    last_used = last_search.created_at.isoformat()
                
                heatmap.append({
                    "knowledge_base_id": kb.id,
                    "name": kb.name,
                    "usage_count": usage_count,
                    "document_count": doc_count,
                    "last_used": last_used
                })
            
            # 按使用次数排序
            heatmap.sort(key=lambda x: x["usage_count"], reverse=True)
            
            return heatmap
            
        except Exception as e:
            logger.error(f"获取知识库热力图失败: {e}", exc_info=True)
            raise
