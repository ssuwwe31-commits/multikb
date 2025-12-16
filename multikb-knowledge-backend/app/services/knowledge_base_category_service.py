"""
Knowledge Base Category Service
根据文档处理流程设计实现知识库分类管理服务
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.knowledge_base_category import KnowledgeBaseCategory
from app.models.knowledge_base import KnowledgeBase
from app.core.logging import logger
from app.core.exceptions import CustomException, ErrorCode


class KnowledgeBaseCategoryService:
    """知识库分类服务 - 严格按照设计文档实现"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_category_tree(self, parent_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取分类树 - 根据设计文档实现
        支持三级分类体系
        """
        try:
            logger.info(f"获取分类树，父级ID: {parent_id}")
            
            # 查询符合条件的分类
            query = self.db.query(KnowledgeBaseCategory).filter(
                KnowledgeBaseCategory.is_deleted == False
            )
            
            if parent_id is None:
                # 获取所有顶级分类
                query = query.filter(KnowledgeBaseCategory.parent_id == None)
            else:
                # 获取指定父级的子分类
                query = query.filter(KnowledgeBaseCategory.parent_id == parent_id)
            
            categories = query.order_by(KnowledgeBaseCategory.sort_order).all()
            
            # 构建分类树
            result = []
            for category in categories:
                # 递归获取子分类
                children = self._get_children(category.id)
                
                result.append({
                    "id": category.id,
                    "name": category.name,
                    "description": category.description,
                    "parent_id": category.parent_id,
                    "level": self._calculate_level(category),
                    "icon": getattr(category, 'icon', None),
                    "color": getattr(category, 'color', None),
                    "sort_weight": category.sort_order,
                    "is_active": category.is_active,
                    "knowledge_base_count": self._count_knowledge_bases(category.id),
                    "children": children,
                    "created_at": category.created_at.isoformat() if category.created_at else None,
                    "updated_at": category.updated_at.isoformat() if category.updated_at else None
                })
            
            logger.info(f"分类树获取成功，共 {len(result)} 个分类")
            return result
            
        except Exception as e:
            logger.error(f"获取分类树错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"获取分类树失败: {str(e)}"
            )
    
    def _get_children(self, parent_id: int) -> List[Dict[str, Any]]:
        """递归获取子分类"""
        children = self.db.query(KnowledgeBaseCategory).filter(
            and_(
                KnowledgeBaseCategory.parent_id == parent_id,
                KnowledgeBaseCategory.is_deleted == False
            )
        ).order_by(KnowledgeBaseCategory.sort_order).all()
        
        result = []
        for child in children:
            grandchildren = self._get_children(child.id)
            result.append({
                "id": child.id,
                "name": child.name,
                "description": child.description,
                "parent_id": child.parent_id,
                "level": self._calculate_level(child),
                "icon": getattr(child, 'icon', None),
                "color": getattr(child, 'color', None),
                "sort_weight": child.sort_order,
                "is_active": child.is_active,
                "knowledge_base_count": self._count_knowledge_bases(child.id),
                "children": grandchildren,
                "created_at": child.created_at.isoformat() if child.created_at else None,
                "updated_at": child.updated_at.isoformat() if child.updated_at else None
            })
        
        return result
    
    def _calculate_level(self, category: KnowledgeBaseCategory) -> int:
        """计算分类层级"""
        level = 1
        current = category
        
        while current.parent_id is not None:
            level += 1
            parent = self.db.query(KnowledgeBaseCategory).filter(
                KnowledgeBaseCategory.id == current.parent_id
            ).first()
            
            if not parent:
                break
            current = parent
            
            if level >= 3:  # 三级分类限制
                break
        
        return level
    
    def _count_knowledge_bases(self, category_id: int) -> int:
        """统计分类下的知识库数量"""
        return self.db.query(KnowledgeBase).filter(
            and_(
                KnowledgeBase.category_id == category_id,
                KnowledgeBase.is_deleted == False
            )
        ).count()
    
    def get_category(self, category_id: int) -> Optional[Dict[str, Any]]:
        """获取分类详情"""
        try:
            category = self.db.query(KnowledgeBaseCategory).filter(
                and_(
                    KnowledgeBaseCategory.id == category_id,
                    KnowledgeBaseCategory.is_deleted == False
                )
            ).first()
            
            if not category:
                return None
            
            return {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "parent_id": category.parent_id,
                "level": self._calculate_level(category),
                "icon": getattr(category, 'icon', None),
                "color": getattr(category, 'color', None),
                "sort_weight": category.sort_order,
                "is_active": category.is_active,
                "knowledge_base_count": self._count_knowledge_bases(category.id),
                "created_at": category.created_at.isoformat() if category.created_at else None,
                "updated_at": category.updated_at.isoformat() if category.updated_at else None
            }
            
        except Exception as e:
            logger.error(f"获取分类详情错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"获取分类详情失败: {str(e)}"
            )
    
    def create_category(self, category_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建分类 - 根据设计文档实现"""
        try:
            logger.info(f"创建分类: {category_data.get('name')}")
            
            # 验证父级分类存在性
            parent_id = category_data.get('parent_id')
            if parent_id:
                parent = self.db.query(KnowledgeBaseCategory).filter(
                    KnowledgeBaseCategory.id == parent_id
                ).first()
                
                if not parent:
                    raise CustomException(
                        code=ErrorCode.VALIDATION_ERROR,
                        message=f"父级分类不存在: {parent_id}"
                    )
                
                # 检查层级是否超过三级
                level = self._calculate_level(parent)
                if level >= 3:
                    raise CustomException(
                        code=ErrorCode.VALIDATION_ERROR,
                        message="分类层级不能超过三级"
                    )
            
            # 创建分类
            category = KnowledgeBaseCategory(**category_data)
            self.db.add(category)
            self.db.commit()
            self.db.refresh(category)
            
            logger.info(f"分类创建成功，ID: {category.id}")
            
            return {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "parent_id": category.parent_id,
                "icon": getattr(category, 'icon', None),
                "color": getattr(category, 'color', None),
                "sort_weight": category.sort_order,
                "is_active": category.is_active,
                "created_at": category.created_at.isoformat() if category.created_at else None
            }
            
        except CustomException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建分类错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"创建分类失败: {str(e)}"
            )
    
    def update_category(self, category_id: int, category_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新分类 - 根据设计文档实现"""
        try:
            logger.info(f"更新分类: {category_id}")
            
            category = self.db.query(KnowledgeBaseCategory).filter(
                and_(
                    KnowledgeBaseCategory.id == category_id,
                    KnowledgeBaseCategory.is_deleted == False
                )
            ).first()
            
            if not category:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"分类不存在: {category_id}"
                )
            
            # 更新字段
            for key, value in category_data.items():
                if hasattr(category, key) and value is not None:
                    setattr(category, key, value)
            
            self.db.commit()
            self.db.refresh(category)
            
            logger.info(f"分类更新成功: {category_id}")
            
            return {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "parent_id": category.parent_id,
                "icon": getattr(category, 'icon', None),
                "color": getattr(category, 'color', None),
                "sort_weight": category.sort_order,
                "is_active": category.is_active,
                "updated_at": category.updated_at.isoformat() if category.updated_at else None
            }
            
        except CustomException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新分类错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"更新分类失败: {str(e)}"
            )
    
    def delete_category(self, category_id: int, force: bool = False) -> bool:
        """删除分类 - 根据设计文档实现"""
        try:
            logger.info(f"删除分类: {category_id}, 强制删除: {force}")
            
            category = self.db.query(KnowledgeBaseCategory).filter(
                and_(
                    KnowledgeBaseCategory.id == category_id,
                    KnowledgeBaseCategory.is_deleted == False
                )
            ).first()
            
            if not category:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"分类不存在: {category_id}"
                )
            
            # 检查是否有子分类
            children = self.db.query(KnowledgeBaseCategory).filter(
                KnowledgeBaseCategory.parent_id == category_id
            ).count()
            
            if children > 0:
                raise CustomException(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"分类下还有 {children} 个子分类，无法删除"
                )
            
            # 检查是否有关联文档
            kb_count = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.category_id == category_id
            ).count()
            
            if kb_count > 0:
                if not force:
                    raise CustomException(
                        code=ErrorCode.VALIDATION_ERROR,
                        message=f"分类下还有 {kb_count} 个知识库，请先删除或转移知识库"
                    )
            
            if force:
                # 硬删除
                self.db.delete(category)
            else:
                # 软删除
                category.is_deleted = True
                category.is_active = False
            
            self.db.commit()
            
            logger.info(f"分类删除成功: {category_id}")
            return True
            
        except CustomException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除分类错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"删除分类失败: {str(e)}"
            )
