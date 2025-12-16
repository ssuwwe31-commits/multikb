"""
Image API Routes
根据文档处理流程设计实现图片搜索API接口
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response, Request, Query
from typing import List, Optional
from app.schemas.image import ImageResponse, ImageSearchRequest, ImageSearchResponse
from app.services.image_service import ImageService
from app.services.image_search_service import ImageSearchService
from app.services.permission_service import KnowledgeBasePermissionService
from app.dependencies.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import or_, union_all
from app.core.logging import logger
from app.config.settings import settings
from app.services.opensearch_service import OpenSearchService
from app.services.minio_storage_service import MinioStorageService
from app.models.image import DocumentImage
from app.models.document import Document
from app.models.knowledge_base_member import KnowledgeBaseMember
from fastapi import Body

router = APIRouter()

def get_current_user_id(request: Request) -> int:
    """从请求中获取当前用户ID（由中间件设置）"""
    user = getattr(request.state, 'user', None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未认证")
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的用户信息")
    try:
        return int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的用户ID")

@router.get("/")
async def get_images(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    document_id: Optional[int] = None,
    knowledge_base_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取图片列表 - 需要权限控制，只能看到有权限的知识库中的图片"""
    try:
        # 获取当前用户ID
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 获取图片列表，跳过: {skip}, 限制: {limit}, 文档ID: {document_id}, 知识库ID: {knowledge_base_id}, 用户ID: {user_id}")
        
        from app.models.image import DocumentImage
        
        # 构建查询：只能看到有权限的文档的图片
        # 1. 如果指定了 knowledge_base_id，检查权限并过滤
        if knowledge_base_id:
            perm = KnowledgeBasePermissionService(db)
            perm.ensure_permission(knowledge_base_id, user_id, "doc:view")
            # 查询该知识库下的所有文档
            doc_ids = db.query(Document.id).filter(
                Document.knowledge_base_id == knowledge_base_id,
                Document.is_deleted == False
            ).subquery()
            base_query = db.query(DocumentImage).filter(
                DocumentImage.is_deleted == False,
                DocumentImage.document_id.in_(db.query(doc_ids.c.id))
            )
        # 2. 如果指定了 document_id，检查该文档所属知识库的权限
        elif document_id:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
            perm = KnowledgeBasePermissionService(db)
            perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:view")
            base_query = db.query(DocumentImage).filter(
                DocumentImage.is_deleted == False,
                DocumentImage.document_id == document_id
            )
        # 3. 如果都没有指定，只返回当前用户有权限的知识库中的图片
        else:
            # 获取用户有权限的知识库ID列表（owner + member）
            from app.models.knowledge_base import KnowledgeBase
            
            # 用户拥有的知识库ID
            owned_kb_ids_query = db.query(KnowledgeBase.id.label("kb_id")).filter(
                KnowledgeBase.is_deleted == False,
                KnowledgeBase.user_id == user_id
            )
            
            # 用户作为成员的知识库ID
            member_kb_ids_query = db.query(KnowledgeBaseMember.knowledge_base_id.label("kb_id")).filter(
                KnowledgeBaseMember.user_id == user_id
            )
            
            # 合并：用户拥有的 + 用户作为成员的（使用相同的列名 kb_id）
            all_kb_ids = owned_kb_ids_query.union_all(member_kb_ids_query).subquery()
            
            # 获取这些知识库下的所有文档ID
            doc_ids = db.query(Document.id).filter(
                Document.is_deleted == False,
                Document.knowledge_base_id.in_(db.query(all_kb_ids.c.kb_id))
            ).subquery()
            
            base_query = db.query(DocumentImage).filter(
                DocumentImage.is_deleted == False,
                DocumentImage.document_id.in_(db.query(doc_ids.c.id))
            )
        
        total = base_query.count()
        
        # 获取图片列表
        images = (
            base_query.order_by(DocumentImage.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        # 将 MinIO 对象名转换为可访问 URL（优先缩略图）
        scheme = "https" if settings.MINIO_SECURE else "http"
        base = f"{scheme}://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_NAME}"
        def to_url(object_name: str | None) -> str | None:
            if not object_name:
                return None
            if object_name.startswith('http://') or object_name.startswith('https://'):
                return object_name
            return f"{base}/{object_name}"

        # 从请求中获取token（如果有），添加到URL中（用于<img>标签认证）
        token = ""
        if request:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")

        for img in images:
            # 动态属性赋值：如果有缩略图，用缩略图；否则用原图
            preview = getattr(img, 'thumbnail_path', None) or getattr(img, 'image_path', None)
            # 统一改为后端代理，避免前端直连 MinIO
            if preview:
                try:
                    from urllib.parse import quote
                    if token:
                        proxy_url = f"/api/images/file?object={quote(preview, safe='')}&token={token}"
                    else:
                        proxy_url = f"/api/images/file?object={quote(preview, safe='')}"
                    setattr(img, 'image_path', proxy_url)
                except Exception:
                    pass

        logger.info(f"API响应: 返回 {len(images)} 张图片，总数: {total}")
        # 返回分页格式，包含总数和列表
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "list": images,
                "total": total,
                "skip": skip,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"获取图片列表API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取图片列表失败: {str(e)}"
        )

@router.post("/upload")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    document_id: int = None,
    db: Session = Depends(get_db)
):
    """上传图片 - 需要 doc:upload 权限"""
    try:
        logger.info(f"API请求: 上传图片 {file.filename}, 文档ID: {document_id}")
        
        # 获取当前用户ID
        user_id = get_current_user_id(request)
        
        if not document_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文档ID不能为空"
            )
        
        # 权限检查：需要对文档所属知识库具有 doc:upload 权限
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:upload")
        
        service = ImageService(db)
        image = await service.upload_image(file, document_id)
        
        logger.info(f"API响应: 图片上传成功，图片ID: {image.id}")
        return image
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传图片API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传图片失败: {str(e)}"
        )

# 根据设计文档要求的图片搜索API接口

@router.post("/search-by-image", response_model=List[ImageSearchResponse])
async def search_by_image(
    request: Request,
    file: UploadFile = File(...),
    similarity_threshold: float = settings.SEARCH_VECTOR_THRESHOLD,
    limit: int = 10,
    knowledge_base_id: Optional[List[int]] = None,
    db: Session = Depends(get_db)
):
    """以图找图搜索 - 使用CLIP图像编码器进行512维向量搜索，需要 doc:view 权限"""
    try:
        logger.info(f"API请求: 以图找图搜索，文件: {file.filename}, 相似度阈值: {similarity_threshold}, 知识库ID: {knowledge_base_id}")
        
        # 获取当前用户ID
        user_id = get_current_user_id(request)
        
        # 验证知识库ID并检查权限（如果提供了）
        if knowledge_base_id:
            from app.models.knowledge_base import KnowledgeBase
            kb_ids = knowledge_base_id if isinstance(knowledge_base_id, list) else [knowledge_base_id]
            if len(kb_ids) > 0:
                perm = KnowledgeBasePermissionService(db)
                for kb_id in kb_ids:
                    # 检查用户是否有查看权限
                    perm.ensure_permission(kb_id, user_id, "doc:view")
                
                kbs = db.query(KnowledgeBase).filter(
                    KnowledgeBase.id.in_(kb_ids),
                    KnowledgeBase.is_active == True
                ).all()
                found_ids = {kb.id for kb in kbs}
                missing_ids = set(kb_ids) - found_ids
                if missing_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"以下知识库ID不存在或未激活: {', '.join(map(str, missing_ids))}"
                    )
        
        service = ImageSearchService(db)
        results = await service.search_by_image(
            file=file,
            similarity_threshold=similarity_threshold,
            limit=limit,
            knowledge_base_id=knowledge_base_id
        )
        
        logger.info(f"API响应: 找到 {len(results)} 个相似图片")
        return results
        
    except Exception as e:
        logger.error(f"以图找图搜索API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"以图找图搜索失败: {str(e)}"
        )

@router.post("/search-by-text", response_model=List[ImageSearchResponse])
async def search_by_text(
    request: Request,
    search_request: ImageSearchRequest,
    db: Session = Depends(get_db)
):
    """以文找图搜索 - 使用CLIP文本编码器进行512维向量搜索，需要 doc:view 权限"""
    try:
        # 获取当前用户ID
        user_id = get_current_user_id(request)
        
        # 记录前端传入的所有参数
        logger.info(
            f"[以文搜图API] 前端传入参数: "
            f"query_text='{search_request.query_text}', "
            f"similarity_threshold={search_request.similarity_threshold}, "
            f"limit={search_request.limit}, "
            f"knowledge_base_id={search_request.knowledge_base_id}"
        )
        
        # 检查知识库权限（如果提供了）
        if search_request.knowledge_base_id:
            perm = KnowledgeBasePermissionService(db)
            kb_ids = search_request.knowledge_base_id if isinstance(search_request.knowledge_base_id, list) else [search_request.knowledge_base_id]
            for kb_id in kb_ids:
                # 检查用户是否有查看权限
                perm.ensure_permission(kb_id, user_id, "doc:view")
        
        service = ImageSearchService(db)
        results = await service.search_by_text(search_request)
        
        logger.info(f"[以文搜图API] 响应: 找到 {len(results)} 个相关图片")
        return results
        
    except Exception as e:
        logger.error(f"[以文搜图API] 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"以文找图搜索失败: {str(e)}"
        )

@router.get("/similar/{image_id}", response_model=List[ImageSearchResponse])
async def get_similar_images(
    image_id: int,
    similarity_threshold: float = settings.SEARCH_VECTOR_THRESHOLD,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取相似图片 - 根据设计文档实现（已迁移到QA模块）"""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="此API已迁移到 /api/qa/sessions/{session_id}/image-search，请使用新的API端点"
    )

@router.post("/upload-and-search", response_model=dict)
async def upload_and_search(
    file: UploadFile = File(...),
    search_type: str = "image",
    similarity_threshold: float = settings.SEARCH_VECTOR_THRESHOLD,
    limit: int = 10,
    knowledge_base_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """上传图片并搜索 - 根据设计文档实现（已迁移到QA模块）"""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="此API已迁移到 /api/qa/sessions/{session_id}/image-search，请使用新的API端点"
    )

@router.get("/vectors/{image_id}")
async def get_image_vectors(
    image_id: int,
    db: Session = Depends(get_db)
):
    """获取图片向量信息 - 根据设计文档实现"""
    try:
        logger.info(f"API请求: 获取图片向量信息，图片ID: {image_id}")
        
        service = ImageSearchService(db)
        vector_info = await service.get_image_vectors(image_id)
        
        logger.info(f"API响应: 获取图片向量信息成功")
        return vector_info
        
    except Exception as e:
        logger.error(f"获取图片向量信息API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取图片向量信息失败: {str(e)}"
        )

@router.get("/file")
async def get_image_file(
    request: Request,
    object: str = Query(..., description="MinIO对象路径"),
    db: Session = Depends(get_db)
):
    """图片代理：通过 MinIO 读取并返回图片二进制，避免前端直连 MinIO。需要 doc:view 权限"""
    try:
        # 获取当前用户ID
        user_id = get_current_user_id(request)
        
        # 权限检查：需要通过图片路径找到对应的文档，然后检查权限
        # 图片路径格式通常是：documents/{document_id}/images/...
        # 尝试从路径中提取 document_id
        try:
            parts = object.split('/')
            if 'documents' in parts:
                doc_idx = parts.index('documents')
                if doc_idx + 1 < len(parts):
                    doc_id_str = parts[doc_idx + 1]
                    try:
                        doc_id = int(doc_id_str)
                        doc = db.query(Document).filter(Document.id == doc_id).first()
                        if doc:
                            perm = KnowledgeBasePermissionService(db)
                            perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:view")
                    except (ValueError, TypeError):
                        pass  # 如果无法解析文档ID，跳过权限检查（向后兼容）
        except Exception:
            pass  # 如果权限检查失败，继续执行（向后兼容）
        
        minio = MinioStorageService()
        data = minio.download_file(object)

        lower = object.lower()
        if lower.endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif lower.endswith(".png"):
            content_type = "image/png"
        elif lower.endswith(".gif"):
            content_type = "image/gif"
        elif lower.endswith(".webp"):
            content_type = "image/webp"
        else:
            content_type = "application/octet-stream"

        return Response(content=data, media_type=content_type)
    except Exception as e:
        logger.error(f"图片代理错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片不存在或无法访问")

@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    request: Request,
    image_id: int,
    db: Session = Depends(get_db)
):
    """获取图片详情 - 需要 doc:view 权限"""
    try:
        logger.info(f"API请求: 获取图片详情，图片ID: {image_id}")
        
        # 获取当前用户ID
        user_id = get_current_user_id(request)
        
        service = ImageService(db)
        image = await service.get_image(image_id)
        if not image:
            logger.warning(f"图片不存在: {image_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="图片不存在"
            )
        
        # 权限检查：需要对图片所属文档的知识库具有 doc:view 权限
        doc = db.query(Document).filter(Document.id == image.document_id).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:view")
        # 优先从 OpenSearch 读取向量信息；若缺失再兜底
        try:
            os_service = OpenSearchService()
            vec_meta = await os_service.get_image_vector_info(image_id)
            if vec_meta:
                if vec_meta.get('dimension') and not getattr(image, 'vector_dim', None):
                    setattr(image, 'vector_dim', vec_meta.get('dimension'))
                # 使用索引中的模型版本标注
                if vec_meta.get('model') and not getattr(image, 'vector_model', None):
                    setattr(image, 'vector_model', vec_meta.get('model'))
        except Exception:
            pass

        # 字段兜底：图片类型/向量模型/向量维度
        try:
            # 推断图片类型
            img_path = getattr(image, 'image_path', None)
            if not getattr(image, 'image_type', None) and isinstance(img_path, str):
                ext = img_path.split('.')[-1].lower() if '.' in img_path else ''
                guessed = 'jpeg' if ext in ['jpg', 'jpeg'] else (ext if ext in ['png','gif','webp','bmp'] else None)
                if guessed:
                    setattr(image, 'image_type', guessed)
            # 默认向量信息（系统使用 CLIP ViT-B/32 生成 512 维）
            if not getattr(image, 'vector_model', None):
                setattr(image, 'vector_model', 'CLIP ViT-B/32')
            if not getattr(image, 'vector_dim', None):
                setattr(image, 'vector_dim', 512)
        except Exception:
            pass

        # 统一返回可访问的图片URL（包含token用于认证）
        try:
            from urllib.parse import quote
            # 从请求中获取token（如果有），添加到URL中
            token = ""
            if request:
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header.replace("Bearer ", "")
            
            if img_path:
                if token:
                    proxy_url = f"/api/images/file?object={quote(img_path, safe='')}&token={token}"
                else:
                    proxy_url = f"/api/images/file?object={quote(img_path, safe='')}"
                setattr(image, 'image_path', proxy_url)
        except Exception:
            pass

        logger.info(f"API响应: 获取图片详情成功")
        return image
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图片详情API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取图片详情失败: {str(e)}"
        )

@router.post("/{image_id}/retry-ocr")
async def retry_image_ocr(
    request: Request,
    image_id: int,
    db: Session = Depends(get_db)
):
    """重新触发图片OCR + 向量化 + 索引 - 需要 doc:edit 权限"""
    # 获取当前用户ID
    user_id = get_current_user_id(request)
    
    service = ImageService(db)
    image = service.db.query(DocumentImage).filter(
        DocumentImage.id == image_id,
        DocumentImage.is_deleted == False
    ).first()
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片不存在")
    
    # 权限检查：需要对图片所属文档的知识库具有 doc:edit 权限
    doc = db.query(Document).filter(Document.id == image.document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
    perm = KnowledgeBasePermissionService(db)
    perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:edit")
    
    if image.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片已处理完成，无需重试")
    success = service.process_image_sync(image_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="重试失败，请稍后再试")
    return {"status": "success", "message": "图片OCR已重新执行"}
