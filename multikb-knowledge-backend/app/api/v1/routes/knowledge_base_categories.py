"""
Knowledge Base Categories API Routes
根据文档处理流程设计实现知识库分类管理API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.core.logging import logger
from app.services.knowledge_base_category_service import KnowledgeBaseCategoryService
from app.core.exceptions import CustomException

router = APIRouter()

@router.get("/categories")
async def get_categories(
    page: int = 1,
    size: int = 20,
    parent_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取分类树 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 获取分类树，page: {page}, size: {size}, 父级ID: {parent_id}")
        
        service = KnowledgeBaseCategoryService(db)
        categories = service.get_category_tree(parent_id)
        
        # 应用分页
        start_idx = max(page - 1, 0) * max(size, 1)
        end_idx = start_idx + size
        paginated_categories = categories[start_idx:end_idx]
        
        logger.info(f"API响应: 返回 {len(paginated_categories)} 个分类")
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "list": paginated_categories,
                "total": len(categories),
                "page": page,
                "size": size
            }
        }
        
    except CustomException as e:
        logger.error(f"获取分类树API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取分类树API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取分类树失败: {str(e)}"
        )

@router.post("/categories")
async def create_category(
    name: str,
    description: Optional[str] = None,
    parent_id: Optional[int] = None,
    icon: Optional[str] = None,
    color: Optional[str] = None,
    sort_weight: int = 0,
    db: Session = Depends(get_db)
):
    """创建分类 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 创建分类 {name}, 父级ID: {parent_id}")
        
        service = KnowledgeBaseCategoryService(db)
        category = service.create_category({
            "name": name,
            "description": description,
            "parent_id": parent_id,
            "sort_order": sort_weight
        })
        
        logger.info(f"API响应: 分类创建成功，ID: {category['id']}")
        return category
        
    except CustomException as e:
        logger.error(f"创建分类API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建分类API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建分类失败: {str(e)}"
        )

@router.put("/categories/{category_id}")
async def update_category(
    category_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    icon: Optional[str] = None,
    color: Optional[str] = None,
    sort_weight: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """更新分类 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 更新分类 {category_id}")
        
        service = KnowledgeBaseCategoryService(db)
        category_data = {}
        if name is not None:
            category_data["name"] = name
        if description is not None:
            category_data["description"] = description
        if sort_weight is not None:
            category_data["sort_order"] = sort_weight
        
        category = service.update_category(category_id, category_data)
        
        logger.info(f"API响应: 分类更新成功")
        return category
        
    except CustomException as e:
        logger.error(f"更新分类API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"更新分类API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新分类失败: {str(e)}"
        )

@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """删除分类 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 删除分类 {category_id}, 强制删除: {force}")
        
        service = KnowledgeBaseCategoryService(db)
        service.delete_category(category_id, force)
        
        logger.info(f"API响应: 分类删除成功")
        return {"message": "分类删除成功"}
        
    except CustomException as e:
        logger.error(f"删除分类API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"删除分类API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除分类失败: {str(e)}"
        )
