"""
Knowledge Base Tag Service
根据文档处理流程设计实现知识库标签管理服务
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.models.document import Document
from app.core.logging import logger
from app.core.exceptions import CustomException, ErrorCode


class KnowledgeBaseTagService:
    """知识库标签服务 - 严格按照设计文档实现"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_tags(
        self, 
        tag_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取标签列表 - 根据设计文档实现
        支持系统、用户、自动三种类型
        """
        try:
            logger.info(f"获取标签列表，类型: {tag_type}, 跳过: {skip}, 限制: {limit}")
            
            # 从文档中提取所有标签
            documents = self.db.query(Document).filter(
                and_(
                    Document.is_deleted == False,
                    Document.tags.isnot(None)
                )
            ).all()
            
            # 统计标签使用次数
            tag_count = {}
            for doc in documents:
                if doc.tags:
                    for tag in doc.tags:
                        if tag not in tag_count:
                            tag_count[tag] = {
                                "name": tag,
                                "tag_type": self._detect_tag_type(tag),
                                "usage_count": 0,
                                "color": self._get_tag_color(tag)
                            }
                        tag_count[tag]["usage_count"] += 1
            
            # 转换为列表
            tags = list(tag_count.values())
            
            # 按类型过滤
            if tag_type:
                tags = [tag for tag in tags if tag["tag_type"] == tag_type]
            
            # 按使用次数排序
            tags.sort(key=lambda x: x["usage_count"], reverse=True)
            
            # 应用分页
            paginated_tags = tags[skip:skip + limit]
            
            logger.info(f"标签列表获取成功，共 {len(paginated_tags)} 个标签")
            return {
                "tags": paginated_tags,
                "total": len(tags),
                "skip": skip,
                "limit": limit
            }
            
        except Exception as e:
            logger.error(f"获取标签列表错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"获取标签列表失败: {str(e)}"
            )
    
    def _detect_tag_type(self, tag: str) -> str:
        """检测标签类型"""
        # 系统标签：预定义的标签
        system_tags = ["技术", "产品", "文档", "API", "手册", "用户指南", "开发", "测试", "部署"]
        if tag in system_tags:
            return "system"
        
        # 自动标签：包含特定关键词
        auto_keywords = ["自动", "生成", "推荐", "智能"]
        if any(keyword in tag for keyword in auto_keywords):
            return "auto"
        
        # 用户标签：其他标签
        return "user"
    
    def _get_tag_color(self, tag: str) -> str:
        """获取标签颜色"""
        colors = {
            "技术": "#409eff",
            "产品": "#67c23a",
            "文档": "#e6a23c",
            "API": "#f56c6c",
            "手册": "#909399"
        }
        return colors.get(tag, "#909399")
    
    def get_popular_tags(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取热门标签 - 根据设计文档实现"""
        try:
            logger.info(f"获取热门标签，限制: {limit}")
            
            tags_response = self.get_tags(limit=limit)
            
            # 按使用次数排序并返回top N
            popular_tags = tags_response["tags"][:limit]
            
            logger.info(f"热门标签获取成功，共 {len(popular_tags)} 个标签")
            return popular_tags
            
        except Exception as e:
            logger.error(f"获取热门标签错误: {e}", exc_info=True)
            return []
    
    def suggest_tags(self, document_id: int) -> List[str]:
        """
        智能推荐标签 - 根据设计文档实现
        
        根据文档内容、分类、知识库等信息推荐合适的标签
        """
        try:
            logger.info(f"为文档 {document_id} 推荐标签")
            
            # 获取文档信息
            document = self.db.query(Document).filter(
                Document.id == document_id
            ).first()
            
            if not document:
                logger.warning(f"文档不存在: {document_id}")
                return []
            
            # 基于内容的标签推荐
            suggested_tags = []
            
            # 根据文件名推荐
            if document.original_filename:
                filename_lower = document.original_filename.lower()
                if "manual" in filename_lower or "手册" in filename_lower:
                    suggested_tags.append("手册")
                if "api" in filename_lower or "接口" in filename_lower:
                    suggested_tags.append("API")
                if "guide" in filename_lower or "指南" in filename_lower:
                    suggested_tags.append("用户指南")
            
            # 根据分类推荐
            if hasattr(document, 'category_id') and document.category_id:
                category = self.db.query(Document).filter(
                    Document.category_id == document.category_id
                ).first()
                # TODO: 根据分类推荐标签
            
            # 根据已有标签推荐
            if document.tags:
                # 查找具有相同标签的文档使用的其他标签
                similar_docs = self.db.query(Document).filter(
                    and_(
                        Document.id != document_id,
                        Document.is_deleted == False,
                        Document.tags.isnot(None)
                    )
                ).all()
                
                # 统计出现频率高的标签
                related_tags = {}
                for doc in similar_docs:
                    if doc.tags:
                        for tag in doc.tags:
                            if tag not in suggested_tags and tag not in (document.tags or []):
                                related_tags[tag] = related_tags.get(tag, 0) + 1
                
                # 添加前5个相关标签
                sorted_tags = sorted(related_tags.items(), key=lambda x: x[1], reverse=True)[:5]
                suggested_tags.extend([tag for tag, _ in sorted_tags])
            
            # 去重
            suggested_tags = list(set(suggested_tags))
            
            logger.info(f"为文档 {document_id} 推荐了 {len(suggested_tags)} 个标签")
            return suggested_tags[:10]  # 最多返回10个标签
            
        except Exception as e:
            logger.error(f"推荐标签错误: {e}", exc_info=True)
            return []
