"""
Document API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Request, Body
from typing import List, Optional
import json
from pydantic import BaseModel
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse, DocumentUploadRequest
from app.services.document_service import DocumentService
from app.services.batch_service import BatchService
from app.services.structured_preview_service import StructuredPreviewService
from app.services.auto_tagging_service import AutoTaggingService
from app.dependencies.database import get_db
from sqlalchemy.orm import Session
from app.core.logging import logger
from app.config.settings import settings
from app.services.chunk_service import ChunkService
from app.services.image_service import ImageService
from app.services.minio_storage_service import MinioStorageService
from app.models.document import Document
from app.models.chunk import DocumentChunk
import gzip, json, io, datetime
import os, tempfile
# 预览生成已移至异步任务，此处不再需要导入转换函数
from app.services.opensearch_service import OpenSearchService
from app.services.permission_service import KnowledgeBasePermissionService

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
async def get_documents(
    request: Request,
    page: int = 1,
    size: int = settings.QA_DEFAULT_PAGE_SIZE,
    knowledge_base_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取文档列表 - 根据文档处理流程设计实现"""
    try:
        # 获取当前用户ID
        user_id = get_current_user_id(request)
        logger.info(f"API请求: 获取文档列表，page: {page}, size: {size}, 知识库ID: {knowledge_base_id}, 用户ID: {user_id}")

        # 强烈建议前端在共享场景下总是带上 knowledge_base_id，
        # 否则很难进行准确的权限控制。这里如果未提供，则只返回当前用户自己的文档。
        service = DocumentService(db)
        skip = max(page - 1, 0) * max(size, 1)

        from app.models.document import Document
        from app.models.knowledge_base import KnowledgeBase

        if knowledge_base_id:
            # 检查用户对该知识库是否有查看权限
            perm = KnowledgeBasePermissionService(db)
            perm.ensure_permission(knowledge_base_id, user_id, "doc:view")

            # 共享模式：按知识库过滤，不再按 Document.user_id 强过滤
            base_q = db.query(Document).filter(
                Document.is_deleted == False,  # noqa: E712
                Document.knowledge_base_id == knowledge_base_id,
            )
        else:
            # 未指定知识库时，返回用户有权限的所有知识库下的文档
            # 包括：用户拥有的知识库 + 用户作为成员的知识库
            from app.models.knowledge_base_member import KnowledgeBaseMember
            from sqlalchemy import union_all
            
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
            
            # 获取这些知识库下的所有文档
            base_q = db.query(Document).filter(
                Document.is_deleted == False,  # noqa: E712
                Document.knowledge_base_id.in_(db.query(all_kb_ids.c.kb_id))
            )

        total = base_q.count()
        documents = (
            base_q.order_by(Document.created_at.desc())
            .offset(skip)
            .limit(size)
            .all()
        )

        # 预取知识库名称映射
        kb_ids = {d.knowledge_base_id for d in documents}
        kb_map = {}
        if kb_ids:
            rows = db.query(KnowledgeBase.id, KnowledgeBase.name).filter(KnowledgeBase.id.in_(kb_ids)).all()
            kb_map = {rid: name for rid, name in rows}

        items = []
        for d in documents:
            meta = getattr(d, 'meta', None)
            # 处理metadata字段（可能是字符串或字典）
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except:
                    meta = {}
            elif meta is None:
                meta = {}
            
            title = None
            if isinstance(meta, dict):
                title = meta.get('title') or meta.get('name')
            if not title:
                # 默认使用原始文件名（去扩展名）作为标题
                try:
                    import os
                    title = os.path.splitext(d.original_filename or '')[0] or d.original_filename
                except Exception:
                    title = d.original_filename
            items.append({
                "id": d.id,
                "title": title,
                "file_name": d.original_filename,
                "file_type": d.file_type,
                "file_size": d.file_size,
                "status": d.status,
                "knowledge_base_id": d.knowledge_base_id,
                "knowledge_base_name": kb_map.get(d.knowledge_base_id),
                "metadata": meta,  # 包含 auto_keywords 和 auto_summary
                # 安全扫描字段
                "security_scan_status": getattr(d, 'security_scan_status', 'pending'),
                "security_scan_method": getattr(d, 'security_scan_method', None),
                "security_scan_result": getattr(d, 'security_scan_result', None),
                "security_scan_timestamp": getattr(d, 'security_scan_timestamp', None),
            })

        logger.info(f"API响应: 返回 {len(documents)} 个文档")
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "list": items,
                "total": total,
                "page": page,
                "size": size
            }
        }
        
    except Exception as e:
        logger.error(f"获取文档列表API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档列表失败: {str(e)}"
        )

@router.post("/upload-from-url")
async def upload_document_from_url(
    request: Request,
    url: str = Form(...),
    knowledge_base_id: int = Form(...),
    category_id: Optional[int] = Form(None),
    tags: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    filename: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    从URL导入文档 - 下载文件后执行完整的上传流程
    
    请求参数：
    - url: 文档URL (必填)
    - knowledge_base_id: 知识库ID (必填)
    - category_id: 分类ID (可选)
    - tags: 标签列表JSON字符串 (可选)
    - metadata: 元数据JSON字符串 (可选)
    - filename: 自定义文件名 (可选)
    
    响应内容：
    - document_id: 文档唯一标识
    - task_id: 处理任务标识
    - file_info: 文件信息
    - knowledge_base_info: 知识库信息
    - tag_info: 标签信息
    - upload_time: 上传时间
    """
    try:
        logger.info(f"API请求: 从URL导入文档 {url}")
        
        # 获取当前用户ID（用于数据隔离）
        user_id = get_current_user_id(request)
        
        # 解析tags
        parsed_tags = []
        if tags:
            try:
                parsed_tags = json.loads(tags)
            except json.JSONDecodeError:
                logger.warning(f"标签格式错误: {tags}，使用空列表")
                parsed_tags = []
        
        # 解析metadata
        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                logger.warning(f"元数据格式错误: {metadata}，使用空对象")
                parsed_metadata = {}
        
        logger.info(f"解析参数: category_id={category_id}, tags={parsed_tags}, metadata={parsed_metadata}")
        
        # 权限：当前用户必须对该知识库拥有 doc:upload 权限
        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(knowledge_base_id, user_id, "doc:upload")

        # 调用服务从URL导入文档
        service = DocumentService(db)
        result = await service.upload_document_from_url(
            url=url,
            knowledge_base_id=knowledge_base_id,
            category_id=category_id,
            tags=parsed_tags,
            metadata=parsed_metadata,
            user_id=user_id,
            filename=filename
        )
        
        logger.info(f"API响应: 从URL导入文档成功，文档ID: {result['document_id']}, 任务ID: {result.get('task_id')}")
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "document_id": result['document_id'],
                "task_id": result.get('task_id'),
                "file_info": {
                    "filename": filename or result.get('original_filename', 'unknown'),
                    "size": result.get('file_size'),
                    "type": result.get('file_type')
                },
                "knowledge_base_info": {
                    "knowledge_base_id": knowledge_base_id,
                    "category_id": category_id
                },
                "tag_info": {
                    "tags": parsed_tags
                },
                "upload_time": result.get('upload_timestamp')
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从URL导入文档API错误: {e}", exc_info=True)
        return {"code": 1, "message": f"从URL导入文档失败: {str(e)}"}

@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    knowledge_base_id: int = Form(...),
    category_id: Optional[int] = Form(None),
    tags: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    上传文档 - 根据文档处理流程设计实现
    
    请求参数：
    - file: 文件对象 (multipart/form-data)
    - knowledge_base_id: 知识库ID (必填)
    - category_id: 分类ID (可选)
    - tags: 标签列表JSON字符串 (可选)
    - metadata: 元数据JSON字符串 (可选)
    
    响应内容：
    - document_id: 文档唯一标识
    - task_id: 处理任务标识
    - file_info: 文件信息
    - knowledge_base_info: 知识库信息
    - tag_info: 标签信息
    - upload_time: 上传时间
    """
    try:
        logger.info(f"API请求: 上传文档 {file.filename}, 知识库ID: {knowledge_base_id}")
        
        # 获取当前用户ID（用于数据隔离）
        user_id = get_current_user_id(request)
        
        # 解析tags
        parsed_tags = []
        if tags:
            try:
                parsed_tags = json.loads(tags)
            except json.JSONDecodeError:
                logger.warning(f"标签格式错误: {tags}，使用空列表")
                parsed_tags = []
        
        # 解析metadata
        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                logger.warning(f"元数据格式错误: {metadata}，使用空对象")
                parsed_metadata = {}
        
        logger.info(f"解析参数: category_id={category_id}, tags={parsed_tags}, metadata={parsed_metadata}")
        
        # 权限：当前用户必须对该知识库拥有 doc:upload 权限
        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(knowledge_base_id, user_id, "doc:upload")

        # 调用服务上传文档
        service = DocumentService(db)
        result = await service.upload_document(
            file=file,
            knowledge_base_id=knowledge_base_id,
            category_id=category_id,
            tags=parsed_tags,
            metadata=parsed_metadata,
            user_id=user_id
        )
        
        logger.info(f"API响应: 文档上传成功，文档ID: {result['document_id']}, 任务ID: {result.get('task_id')}")
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "document_id": result['document_id'],
                "task_id": result.get('task_id'),
                "file_info": {
                    "filename": file.filename,
                    "size": result.get('file_size'),
                    "type": result.get('file_type')
                },
                "knowledge_base_info": {
                    "knowledge_base_id": knowledge_base_id,
                    "category_id": category_id
                },
                "tag_info": {
                    "tags": parsed_tags
                },
                "upload_time": result.get('upload_timestamp')
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文档API错误: {e}", exc_info=True)
        return {"code": 1, "message": f"上传文档失败: {str(e)}"}

@router.get("/{doc_id}")
async def get_document(
    request: Request,
    doc_id: int,
    db: Session = Depends(get_db)
):
    """获取文档详情 - 根据文档处理流程设计实现"""
    try:
        logger.info(f"API请求: 获取文档详情 {doc_id}")

        # 先获取文档，便于后续进行权限检查
        service = DocumentService(db)
        doc = await service.get_document(doc_id)
        
        if not doc:
            logger.warning(f"API响应: 文档不存在 {doc_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )

        # 权限：用户必须在文档所属知识库下具备 doc:view 权限
        user_id = get_current_user_id(request)
        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:view")
        # 构造统一响应
        from app.models.knowledge_base import KnowledgeBase
        kb_name = None
        try:
            kb_name = db.query(KnowledgeBase.name).filter(KnowledgeBase.id == doc.knowledge_base_id).scalar()
        except Exception:
            kb_name = None
        # 处理metadata字段（SQLAlchemy JSON列会自动反序列化为dict，但需要处理None和字符串情况）
        metadata = getattr(doc, 'meta', None)
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        elif metadata is None:
            metadata = {}
        # 确保metadata是dict类型
        if not isinstance(metadata, dict):
            metadata = {}
        
        # 从metadata中获取title
        title = None
        if isinstance(metadata, dict):
            title = metadata.get('title') or metadata.get('name')
        if not title:
            try:
                import os
                title = os.path.splitext(doc.original_filename or '')[0] or doc.original_filename
            except Exception:
                title = doc.original_filename
        
        payload = {
            "id": doc.id,
            "title": title,
            "file_name": doc.original_filename,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "status": doc.status,
            "knowledge_base_id": doc.knowledge_base_id,
            "knowledge_base_name": kb_name,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "metadata": metadata,  # 包含 auto_keywords 和 auto_summary
            # 安全扫描字段
            "security_scan_status": getattr(doc, 'security_scan_status', 'pending'),
            "security_scan_method": getattr(doc, 'security_scan_method', None),
            "security_scan_result": getattr(doc, 'security_scan_result', None),
            "security_scan_timestamp": getattr(doc, 'security_scan_timestamp', None),
        }
        
        # 调试日志：检查metadata内容
        if isinstance(metadata, dict):
            has_keywords = 'auto_keywords' in metadata
            has_summary = 'auto_summary' in metadata
            keywords_count = len(metadata.get('auto_keywords', [])) if has_keywords else 0
            summary_len = len(metadata.get('auto_summary', '')) if has_summary else 0
            logger.info(f"API响应: 返回文档详情 {doc.original_filename}, metadata类型: {type(metadata)}, 包含auto_keywords: {has_keywords}(数量:{keywords_count}), 包含auto_summary: {has_summary}(长度:{summary_len})")
            if has_keywords or has_summary:
                logger.debug(f"文档 {doc.id} metadata完整内容: {metadata}")
        else:
            logger.info(f"API响应: 返回文档详情 {doc.original_filename}, metadata类型: {type(metadata)}, 不是字典类型")
        return {"code": 0, "message": "ok", "data": payload}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档详情API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档详情失败: {str(e)}"
        )

@router.get("/{doc_id}/sheets")
async def get_document_sheets(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """获取 Excel 文档的 Sheet 列表（仅 Excel 文档）"""
    try:
        user_id = get_current_user_id(request)
        document = db.query(Document).filter(Document.id == doc_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")

        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(document.knowledge_base_id, user_id, "doc:view")
        
        # 检查文件类型
        file_type = (document.file_type or '').lower()
        file_suffix = (document.original_filename or '').split('.')[-1].lower()
        is_excel = file_suffix in ('xlsx', 'xls', 'xlsb', 'csv') or file_type in ('excel', 'xlsx', 'xls', 'csv')
        
        if not is_excel:
            raise HTTPException(status_code=400, detail="该接口仅支持 Excel 文档")
        
        # 从 metadata 中读取 sheet 信息
        metadata = document.meta or {}
        if isinstance(metadata, str):
            import json
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        sheets_info = metadata.get('sheets', [])
        items = []
        for sheet in sheets_info:
            items.append({
                "name": sheet.get('name'),
                "rows": sheet.get('rows', 0),
                "columns": sheet.get('columns', 0),
                "preview_samples": metadata.get('preview_samples', {}).get(sheet.get('name'), []),
                "header_detected": sheet.get('header_detected', False),
                "has_merge": sheet.get('has_merge', False),
                "has_formula": sheet.get('has_formula', False),
                "sheet_type": sheet.get('sheet_type', 'tabular'),
                "layout_features": sheet.get('layout_features', []),
            })
        
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "items": items,
                "total": len(items)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 Sheet 列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取 Sheet 列表失败: {str(e)}")

@router.get("/{doc_id}/chunks")
async def get_document_chunks(
    request: Request,
    doc_id: int,
    page: int = 1,
    size: int = settings.QA_DEFAULT_PAGE_SIZE,
    include_content: bool = False,
    chunk_type: Optional[str] = Query(None, description="过滤 chunk 类型: tabular/text/summary"),
    db: Session = Depends(get_db)
):
    """获取指定文档的分块列表（兼容前端 /documents/{id}/chunks）"""
    try:
        user_id = get_current_user_id(request)
        # 权限：需要对文档所属知识库具有 doc:view 权限
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:view")

        skip = max(page - 1, 0) * max(size, 1)
        service = ChunkService(db)
        # 如果指定了 chunk_type，需要在查询后过滤
        rows = await service.get_chunks(skip=skip, limit=size * 2 if chunk_type else size, document_id=doc_id)
        items = []

        # 若数据库未存文本，尝试从 MinIO 的 chunks.jsonl.gz 读取对应范围
        content_map = {}
        try:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                created: datetime.datetime = getattr(doc, 'created_at', None) or datetime.datetime.utcnow()
                year = created.strftime('%Y')
                month = created.strftime('%m')
                object_name = f"documents/{year}/{month}/{doc_id}/parsed/chunks/chunks.jsonl.gz"
                minio = MinioStorageService()
                obj = minio.client.get_object(minio.bucket_name, object_name)
                gz_bytes = obj.read()
                obj.close(); obj.release_conn()
                with gzip.GzipFile(fileobj=io.BytesIO(gz_bytes), mode='rb') as gz:
                    idx_start = skip
                    idx_end = skip + size
                    current_index = 0
                    for line in gz:
                        try:
                            d = json.loads(line.decode('utf-8'))
                        except Exception:
                            continue
                        idx = d.get('index') or d.get('chunk_index')
                        if idx is None:
                            idx = current_index
                        current_index += 1
                        if idx < idx_start or idx >= idx_end:
                            continue
                        content_map[int(idx)] = d.get('content') or ''
        except Exception:
            content_map = {}

        from sqlalchemy import func
        from app.models.chunk_version import ChunkVersion
        filtered_count = 0
        for c in rows:
            # 过滤 chunk_type
            if chunk_type:
                chunk_type_attr = getattr(c, "chunk_type", "text") or "text"
                if chunk_type_attr.lower() != chunk_type.lower():
                    continue
                filtered_count += 1
                if filtered_count > size:
                    break
            
            idx = getattr(c, 'chunk_index', None)
            content = getattr(c, 'content', None)
            if (not content) and (idx is not None) and (idx in content_map):
                content = content_map[idx]
            
            # 解析 meta 字段（包含表格数据 table_data）
            meta_dict = None
            if c.meta:
                try:
                    meta_dict = json.loads(c.meta) if isinstance(c.meta, str) else c.meta
                    # ✅ 调试：检查表格块的 meta 数据
                    if getattr(c, "chunk_type", "text") == "table":
                        logger.debug(f"[表格调试] 块 #{idx} (ID={c.id}): meta_dict={meta_dict}")
                        if meta_dict and isinstance(meta_dict, dict):
                            table_data = meta_dict.get('table_data')
                            table_group_uid = meta_dict.get('table_group_uid')
                            table_id = meta_dict.get('table_id')
                            
                            # ✅ 新设计：表格数据通过 API 懒加载，meta 中只存储 table_group_uid 或 table_id
                            if table_data:
                                logger.debug(f"[表格调试] 块 #{idx}: table_data.html={bool(table_data.get('html'))}, "
                                           f"table_data.cells={bool(table_data.get('cells'))}, "
                                           f"rows={table_data.get('rows', 0)}, "
                                           f"columns={table_data.get('columns', 0)}")
                            elif table_group_uid or table_id:
                                # ✅ 有懒加载标识符，这是正常的，不需要警告
                                logger.debug(f"[表格调试] 块 #{idx}: 使用懒加载方式，table_group_uid={table_group_uid}, table_id={table_id}")
                            else:
                                # ⚠️ 既没有 table_data，也没有懒加载标识符，这才是问题
                                logger.warning(f"[表格调试] ⚠️ 块 #{idx} (ID={c.id}): meta 中既缺少 table_data，也缺少 table_group_uid/table_id！meta_dict 内容: {meta_dict.keys() if isinstance(meta_dict, dict) else 'N/A'}")
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"[表格调试] 解析块 #{idx} 的 meta 失败: {e}, meta_raw={c.meta[:100] if c.meta else None}")
                    meta_dict = {}
            
            # 计算版本与修改时间兜底
            try:
                max_ver = db.query(func.max(ChunkVersion.version_number)).filter(
                    ChunkVersion.chunk_id == c.id
                ).scalar() or 0
            except Exception:
                max_ver = 0
            safe_version = max(int(getattr(c, 'version', 0) or 0), int(max_ver)) or 1
            latest_ver = None
            if max_ver:
                try:
                    latest_ver = db.query(ChunkVersion).filter(
                        ChunkVersion.chunk_id == c.id,
                        ChunkVersion.version_number == int(max_ver)
                    ).first()
                except Exception:
                    latest_ver = None
            modified_dt = getattr(c, 'last_modified_at', None) or (getattr(latest_ver, 'created_at', None) if latest_ver else None) or getattr(c, 'created_at', None)

            items.append({
                "id": c.id,
                "document_id": c.document_id,
                "chunk_index": idx,
                **({"content": content} if include_content else {}),
                "chunk_type": getattr(c, "chunk_type", "text"),
                "char_count": len(content or getattr(c, "content", "") or ""),
                "created_at": getattr(c, "created_at", None),
                "version": safe_version,
                "last_modified_at": modified_dt,
                "meta": meta_dict,  # ✅ 新增：返回 meta 字段，包含表格数据 table_data
            })
        return {"code": 0, "message": "ok", "data": {"list": items, "total": len(items), "page": page, "size": size}}
    except Exception as e:
        logger.error(f"获取文档分块失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文档分块失败: {str(e)}")

@router.get("/{doc_id}/chunks/{chunk_id}")
async def get_document_chunk_detail(
    request: Request,
    doc_id: int,
    chunk_id: int,
    db: Session = Depends(get_db)
):
    """获取单个分块详情（含内容）。当数据库未存文本时，从 MinIO 读取对应文本。"""
    try:
        user_id = get_current_user_id(request)
        from app.models.chunk import DocumentChunk
        chunk = db.query(DocumentChunk).filter(
            DocumentChunk.id == chunk_id,
            DocumentChunk.document_id == doc_id
        ).first()
        if not chunk:
            raise HTTPException(status_code=404, detail="分块不存在")

        # 权限：需要对文档所属知识库具有 doc:view 权限
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:view")

        # 读取内容：优先 DB；否则从 MinIO 归档映射定位
        content = chunk.content or ""
        if not content:
            try:
                created = getattr(chunk, 'created_at', None)
                doc = db.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    created = getattr(doc, 'created_at', created) or datetime.datetime.utcnow()
                year = created.strftime('%Y')
                month = created.strftime('%m')
                object_name = f"documents/{year}/{month}/{doc_id}/parsed/chunks/chunks.jsonl.gz"
                minio = MinioStorageService()
                obj = minio.client.get_object(minio.bucket_name, object_name)
                import gzip, json
                try:
                    with gzip.GzipFile(fileobj=obj, mode='rb') as gz:
                        for line in gz:
                            try:
                                item = json.loads(line)
                                # 归档里使用的是 index（chunk_index），兼容旧字段 chunk_id
                                item_index = item.get("index")
                                if item_index is None:
                                    item_index = item.get("chunk_id")
                                if item_index is not None and int(item_index) == int(getattr(chunk, 'chunk_index', 0)):
                                    content = item.get("content", "")
                                    break
                            except Exception:
                                continue
                finally:
                    try:
                        obj.close(); obj.release_conn()
                    except Exception:
                        pass
            except Exception:
                content = ""

        # 解析 meta 字段（包含表格数据 table_data）
        import json
        meta_dict = None
        if chunk.meta:
            try:
                meta_dict = json.loads(chunk.meta) if isinstance(chunk.meta, str) else chunk.meta
            except (json.JSONDecodeError, TypeError):
                meta_dict = {}
        
        data = {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "chunk_index": getattr(chunk, 'chunk_index', None),
            "chunk_type": getattr(chunk, 'chunk_type', 'text'),
            "content": content,
            "char_count": len(content or getattr(chunk, 'content', '') or ''),
            "version": getattr(chunk, 'version', 1),
            "created_at": getattr(chunk, 'created_at', None),
            "last_modified_at": getattr(chunk, 'last_modified_at', None),
            "meta": meta_dict,  # ✅ 新增：返回 meta 字段，包含表格数据 table_data
        }
        return {"code": 0, "message": "ok", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分块详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取分块详情失败: {str(e)}")

@router.get("/{doc_id}/images")
async def get_document_images(
    request: Request,
    doc_id: int,
    db: Session = Depends(get_db)
):
    """获取指定文档的图片列表（兼容前端 /documents/{id}/images）"""
    try:
        user_id = get_current_user_id(request)
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:view")

        service = ImageService(db)
        imgs = db.query(service.model).filter(service.model.document_id == doc_id, service.model.is_deleted == False).all()
        items = []
        minio = MinioStorageService()
        for im in imgs:
            # 为前端 <img> 生成可访问 URL（签名）
            url = None
            try:
                from datetime import timedelta
                url = minio.client.presigned_get_object(minio.bucket_name, im.image_path, expires=timedelta(hours=1))
            except Exception:
                url = f"/{im.image_path}"
            items.append({
                "id": im.id,
                "document_id": im.document_id,
                "image_path": im.image_path,
                "thumbnail_path": getattr(im, "thumbnail_path", None),
                "url": url,
                "width": getattr(im, "width", None),
                "height": getattr(im, "height", None),
                "description": getattr(im, "description", ""),
                "ocr_text": getattr(im, "ocr_text", ""),
                "created_at": getattr(im, "created_at", None),
            })
        return {"code": 0, "message": "ok", "data": items}
    except Exception as e:
        logger.error(f"获取文档图片失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文档图片失败: {str(e)}")

@router.get("/{doc_id}/preview")
async def get_document_preview(
    request: Request,
    doc_id: int,
    db: Session = Depends(get_db)
):
    """返回原始文档的直链；若为 Office 文档则返回已预生成的 PDF/HTML 预览（如果存在）。"""
    try:
        user_id = get_current_user_id(request)
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        if not doc.file_path:
            raise HTTPException(status_code=404, detail="缺少原始文件路径")

        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:view")

        minio = MinioStorageService()
        # 原始直链
        from datetime import timedelta
        original_url = minio.client.presigned_get_object(minio.bucket_name, doc.file_path, expires=timedelta(hours=1))

        # 推断类型
        content_type = "application/octet-stream"
        try:
            stat = minio.client.stat_object(minio.bucket_name, doc.file_path)
            if getattr(stat, 'content_type', None):
                content_type = stat.content_type
        except Exception:
            pass

        # 如果是 Office 文档，优先使用已转换的PDF（如果存在）
        ext = os.path.splitext(doc.file_path)[1].lower()
        is_office = ext in {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}
        
        # 优化文本文件的 content_type 检测
        if ext in {".txt", ".md", ".log", ".conf", ".ini", ".sh", ".bat", ".py", ".js", ".ts", ".json", ".xml", ".yaml", ".yml", ".css", ".html"}:
            import mimetypes
            guessed_type = mimetypes.guess_type(doc.file_path)[0]
            if guessed_type and guessed_type.startswith('text/'):
                content_type = guessed_type
            elif content_type == "application/octet-stream":
                # 如果没有检测到，默认设为 text/plain
                content_type = "text/plain"
        
        doc_meta = doc.meta or {}
        converted_html_url = None
        if isinstance(doc_meta, dict):
            converted_html_url = doc_meta.get("converted_html_url")

        # 如果是Office文档，检查是否有预生成的预览
        if is_office:
            logger.info(f"文档 {doc_id} 是Office文档 ({ext})，检查预生成的预览")
            pdf_preview_url = None
            html_preview_url = None
            
            # 检查数据库中的PDF预览路径
            if doc.converted_pdf_url:
                logger.debug(f"文档 {doc_id} 数据库中有PDF预览路径: {doc.converted_pdf_url}")
                try:
                    minio.client.stat_object(minio.bucket_name, doc.converted_pdf_url)
                    pdf_preview_url = minio.client.presigned_get_object(
                        minio.bucket_name, 
                        doc.converted_pdf_url, 
                        expires=timedelta(hours=1)
                    )
                    logger.info(f"文档 {doc_id} 使用已预生成的PDF预览: {doc.converted_pdf_url}")
                except Exception as e:
                    logger.warning(f"文档 {doc_id} 预生成的PDF预览不存在: {doc.converted_pdf_url}, 错误: {e}")
            else:
                logger.debug(f"文档 {doc_id} 数据库中没有PDF预览路径")
            
            # 检查数据库中的HTML预览路径
            if converted_html_url:
                logger.debug(f"文档 {doc_id} 数据库中有HTML预览路径: {converted_html_url}")
                try:
                    minio.client.stat_object(minio.bucket_name, converted_html_url)
                    html_preview_url = minio.client.presigned_get_object(
                        minio.bucket_name,
                        converted_html_url,
                        expires=timedelta(hours=1)
                    )
                    logger.info(f"文档 {doc_id} 使用已预生成的HTML预览: {converted_html_url}")
                except Exception as e:
                    logger.warning(f"文档 {doc_id} 预生成的HTML预览不存在: {converted_html_url}, 错误: {e}")
            else:
                logger.debug(f"文档 {doc_id} 数据库中没有HTML预览路径")
            
            # 如果PDF预览存在，优先返回PDF
            if pdf_preview_url:
                logger.info(f"文档 {doc_id} 返回PDF预览 (HTML预览{'可用' if html_preview_url else '不可用'})")
                return {
                    "code": 0,
                    "message": "ok",
                    "data": {
                        "preview_url": pdf_preview_url,
                        "content_type": "application/pdf",
                        "original_url": original_url,
                        "html_preview_url": html_preview_url
                    }
                }
            
            # 如果只有HTML预览，返回HTML
            if html_preview_url:
                logger.info(f"文档 {doc_id} 返回HTML预览 (PDF预览不可用)")
                return {
                    "code": 0,
                    "message": "ok",
                    "data": {
                        "preview_url": html_preview_url,
                        "content_type": "text/html",
                        "original_url": original_url,
                        "html_preview_url": html_preview_url
                    }
                }
            
            # 如果预览都不存在，记录日志并返回原始文件
            logger.info(f"文档 {doc_id} 的预览尚未生成（可能正在处理中），返回原始文件URL")

        # 默认返回原始直链（非Office文档或Office文档预览不存在时）
        html_preview_url = None
        # 对于非Office文档，尝试获取HTML预览（如果有）
        if not is_office:
            html_candidate = converted_html_url or (f"documents/{doc.created_at.strftime('%Y')}/{doc.created_at.strftime('%m')}/{doc.id}/preview/preview.html" if doc.created_at else None)
            if html_candidate:
                try:
                    minio.client.stat_object(minio.bucket_name, html_candidate)
                    html_preview_url = minio.client.presigned_get_object(minio.bucket_name, html_candidate, expires=timedelta(hours=1))
                except Exception:
                    html_preview_url = None
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "preview_url": original_url,
                "content_type": content_type,
                "original_url": original_url,
                "html_preview_url": html_preview_url
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取原文直链失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取原文直链失败: {str(e)}")

@router.get("/{doc_id}/chunks/{chunk_id}/content-opensearch")
async def get_chunk_content_from_opensearch(
    request: Request,
    doc_id: int,
    chunk_id: int,
    source: str = Query("db", description="优先数据源: db 或 os"),
    db: Session = Depends(get_db)
):
    """优先从数据库读取块内容，必要时回退至 OpenSearch。"""
    try:
        user_id = get_current_user_id(request)
        from app.models.chunk import DocumentChunk

        def load_meta(raw_meta):
            if not raw_meta:
                return {}
            try:
                return json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta
            except (json.JSONDecodeError, TypeError):
                return {}

        def build_image_fields(meta_dict: dict):
            image_path = meta_dict.get('image_path')
            image_id = meta_dict.get('image_id')
            image_url = None
            if image_path:
                from datetime import timedelta
                minio = MinioStorageService()
                try:
                    image_url = minio.client.presigned_get_object(minio.bucket_name, image_path, expires=timedelta(hours=1))
                except Exception:
                    image_url = f"/{image_path}"
            return image_id, image_path, image_url

        def load_textual_content_from_archive(document_id: int, chunk_index: int) -> str:
            """当数据库未存储正文时，从 MinIO 归档中补齐文本/表格内容。"""
            if chunk_index is None:
                return ""
            try:
                doc = db.query(Document).filter(Document.id == document_id).first()
                if not doc:
                    return ""
                created = getattr(doc, "created_at", None) or datetime.datetime.utcnow()
                year = created.strftime("%Y")
                month = created.strftime("%m")
                object_name = f"documents/{year}/{month}/{document_id}/parsed/chunks/chunks.jsonl.gz"
                minio = MinioStorageService()
                obj = minio.client.get_object(minio.bucket_name, object_name)
                try:
                    with gzip.GzipFile(fileobj=obj, mode="rb") as gz:
                        for line in gz:
                            try:
                                data = json.loads(line.decode("utf-8"))
                            except Exception:
                                continue
                            idx = data.get("index")
                            if idx is None:
                                idx = data.get("chunk_index")
                            if idx is None:
                                continue
                            if int(idx) == int(chunk_index):
                                return data.get("content") or ""
                finally:
                    try:
                        obj.close()
                        obj.release_conn()
                    except Exception:
                        pass
            except Exception as archive_err:
                logger.debug(f"MinIO 归档读取 chunk_index={chunk_index} 失败: {archive_err}")
            return ""

        def build_payload(chunk_type: str, content_value: str, meta_dict: dict, extra: dict = None):
            payload = {
                "chunk_id": chunk_id,
                "chunk_type": chunk_type,
                "content": content_value,
                "char_count": len(content_value),
                "meta": meta_dict or {}
            }
            if extra:
                payload.update(extra)
            return {"code": 0, "message": "ok", "data": payload}

        # 1. 默认走数据库（也是唯一包含 MinIO 信息的权威源）
        if source.lower() != "os":
            chunk = db.query(DocumentChunk).filter(
                DocumentChunk.id == chunk_id,
                DocumentChunk.document_id == doc_id
            ).first()
            if chunk:
                # 权限：需要对文档所属知识库具有 doc:view 权限
                doc = db.query(Document).filter(Document.id == doc_id).first()
                if not doc:
                    raise HTTPException(status_code=404, detail="文档不存在")
                perm = KnowledgeBasePermissionService(db)
                perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:view")

                meta_dict = load_meta(chunk.meta)
                chunk_type = (chunk.chunk_type or "text").lower()
                content = chunk.content or ""
                extra_fields = {
                    "chunk_index": getattr(chunk, 'chunk_index', None),
                    "document_id": chunk.document_id
                }

                if chunk_type == 'image':
                    image_id, image_path, image_url = build_image_fields(meta_dict)
                    if image_url:
                        content = image_url
                    extra_fields.update({
                        "image_id": image_id,
                        "image_path": image_path,
                        "image_url": image_url,
                    })
                else:
                    if not content:
                        archive_content = load_textual_content_from_archive(chunk.document_id, extra_fields["chunk_index"])
                        if archive_content:
                            content = archive_content

                return build_payload(chunk_type, content, meta_dict, extra_fields)

        # 2. 若显式要求读取 OpenSearch 或数据库缺失，再访问 OS
        osvc = OpenSearchService()
        source_doc = {}
        try:
            res = osvc.client.get(index=osvc.document_index, id=f"chunk_{chunk_id}")
            source_doc = res.get("_source", {}) if isinstance(res, dict) else {}
        except Exception as e:
            logger.debug(f"OpenSearch 未找到 chunk_{chunk_id}: {e}")
            source_doc = {}

        if source_doc and int(source_doc.get("document_id", 0)) == int(doc_id):
            chunk_type = (source_doc.get("chunk_type", "text") or "text").lower()
            metadata = source_doc.get("metadata") or {}
            content = source_doc.get("content", "") or ""
            extra_fields = {}
            chunk_index = None
            try:
                chunk_index = int(metadata.get("chunk_index", metadata.get("index")))
            except Exception:
                chunk_index = metadata.get("chunk_index") or metadata.get("index")
            if chunk_index is not None:
                extra_fields["chunk_index"] = chunk_index
                extra_fields["document_id"] = doc_id

            if chunk_type == "image":
                image_id, image_path, image_url = build_image_fields(metadata)
                if image_url:
                    content = image_url
                extra_fields.update({
                    "image_id": image_id,
                    "image_path": image_path,
                    "image_url": image_url,
                })
            else:
                if not content and chunk_index is not None:
                    archive_content = load_textual_content_from_archive(doc_id, chunk_index)
                    if archive_content:
                        content = archive_content
            return build_payload(chunk_type, content, metadata, extra_fields)

        return {"code": 1, "message": "未找到该块或文档不匹配", "data": None}
    except Exception as e:
        logger.error(f"读取OpenSearch块内容失败: {e}")
        return {"code": 1, "message": f"读取失败: {str(e)}"}

@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    request: Request,
    doc_id: int,
    document: DocumentUpdate,
    db: Session = Depends(get_db)
):
    """更新文档 - 根据文档处理流程设计实现"""
    try:
        logger.info(f"API请求: 更新文档 {doc_id}")

        # 权限：需要对文档所属知识库具有 doc:edit 权限
        existing = db.query(Document).filter(
            Document.id == doc_id,
            Document.is_deleted == False  # noqa: E712
        ).first()
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )
        user_id = get_current_user_id(request)
        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(existing.knowledge_base_id, user_id, "doc:edit")

        # 乐观并发控制：如果前端传了 expected_updated_at，则要求与当前 updated_at 完全一致
        if document.expected_updated_at is not None and existing.updated_at is not None:
            if existing.updated_at != document.expected_updated_at:
                logger.warning(
                    "文档更新冲突: doc_id=%s, expected=%s, actual=%s",
                    doc_id,
                    document.expected_updated_at,
                    existing.updated_at,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="文档已被其他用户更新，请刷新后重试",
                )

        service = DocumentService(db)
        doc = await service.update_document(doc_id, document)
        
        if not doc:
            logger.warning(f"API响应: 文档不存在 {doc_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )
        
        logger.info(f"API响应: 文档更新成功 {doc.original_filename}")
        return doc
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文档API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新文档失败: {str(e)}"
        )

@router.delete("/{doc_id}")
async def delete_document(
    request: Request,
    doc_id: int,
    db: Session = Depends(get_db),
):
    """删除文档 - 根据文档处理流程设计实现"""
    try:
        logger.info(f"API请求: 删除文档 {doc_id}")

        # 加载文档以便做权限判断
        doc = db.query(Document).filter(Document.id == doc_id, Document.is_deleted == False).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )

        user_id = get_current_user_id(request)
        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:delete")

        service = DocumentService(db)
        success = await service.delete_document(doc_id)
        
        if not success:
            logger.warning(f"API响应: 文档不存在 {doc_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )
        
        logger.info(f"API响应: 文档删除成功 {doc_id}")
        return {
            "code": 0,
            "message": "ok",
            "data": {"document_id": doc_id, "deleted": True}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文档失败: {str(e)}"
        )

@router.post("/batch-upload")
async def batch_upload_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    knowledge_base_id: int = Form(...),
    category_id: Optional[int] = Form(None),
    tags: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    批量上传文档 - 根据文档处理流程设计实现
    
    请求参数：
    - files: 文件列表 (multipart/form-data)
    - knowledge_base_id: 知识库ID (必填)
    - category_id: 分类ID (可选)
    - tags: 标签列表JSON字符串 (可选)
    - metadata: 元数据JSON字符串 (可选)
    
    响应内容：
    - success_count: 成功数量
    - fail_count: 失败数量
    - results: 结果列表
    """
    try:
        logger.info(f"API请求: 批量上传文档，文件数量: {len(files)}, 知识库ID: {knowledge_base_id}")
        
        # 获取当前用户ID
        user_id = get_current_user_id(request)

        # 权限：批量上传也视为 doc:upload
        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(knowledge_base_id, user_id, "doc:upload")
        
        # 解析tags
        parsed_tags = []
        if tags:
            try:
                parsed_tags = json.loads(tags)
            except json.JSONDecodeError:
                logger.warning(f"标签格式错误: {tags}，使用空列表")
                parsed_tags = []
        
        # 解析metadata
        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                logger.warning(f"元数据格式错误: {metadata}，使用空对象")
                parsed_metadata = {}
        
        # 创建批次记录
        batch_service = BatchService(db)
        batch = batch_service.create_batch(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            total_files=len(files)
        )
        
        service = DocumentService(db)
        results = []
        success_count = 0
        fail_count = 0
        
        # 处理文件列表（包括ZIP解包后的文件）
        files_to_process = []
        
        for file in files:
            # 检测ZIP文件并解包
            if file.filename and file.filename.lower().endswith('.zip'):
                try:
                    logger.info(f"检测到ZIP文件: {file.filename}，开始解包")
                    import zipfile
                    import io
                    from starlette.datastructures import UploadFile
                    
                    # 读取ZIP文件内容
                    zip_content = await file.read()
                    zip_file = zipfile.ZipFile(io.BytesIO(zip_content))
                    
                    # 解包ZIP文件
                    extracted_count = 0
                    for zip_info in zip_file.namelist():
                        # 跳过目录和隐藏文件
                        if zip_info.endswith('/') or zip_info.startswith('__MACOSX/') or zip_info.startswith('.DS_Store'):
                            continue
                        
                        # 检查文件扩展名（只处理支持的文档类型）
                        supported_extensions = ['.docx', '.pdf', '.pptx', '.txt', '.log', '.md', '.markdown', '.mkd', '.xlsx', '.xls', '.csv', '.json', '.xml', '.html', '.htm']
                        if not any(zip_info.lower().endswith(ext) for ext in supported_extensions):
                            logger.warning(f"ZIP内文件 {zip_info} 不支持，跳过")
                            continue
                        
                        # 读取文件内容
                        try:
                            file_content = zip_file.read(zip_info)
                            # 创建UploadFile对象
                            extracted_file = UploadFile(
                                filename=zip_info.split('/')[-1],  # 只使用文件名，忽略路径
                                file=io.BytesIO(file_content),
                                size=len(file_content)
                            )
                            files_to_process.append(extracted_file)
                            extracted_count += 1
                        except Exception as e:
                            logger.error(f"解包ZIP内文件 {zip_info} 失败: {e}")
                            continue
                    
                    logger.info(f"ZIP文件 {file.filename} 解包完成，共提取 {extracted_count} 个文件")
                    
                    # 更新批次总数（减去ZIP文件本身，加上解包后的文件数）
                    batch.total_files = batch.total_files - 1 + extracted_count
                    db.commit()
                    
                except Exception as e:
                    logger.error(f"ZIP文件 {file.filename} 解包失败: {e}", exc_info=True)
                    # ZIP解包失败，标记批次失败
                    batch_service.update_batch_progress(batch.id, failed=True)
                    batch_service.update_batch_error_summary(batch.id, {
                        "zip_unpack_error": str(e),
                        "zip_filename": file.filename
                    })
                    results.append({
                        "filename": file.filename,
                        "status": "failed",
                        "error": f"ZIP解包失败: {str(e)}"
                    })
                    fail_count += 1
            else:
                # 非ZIP文件，直接添加到处理列表
                files_to_process.append(file)
        
        # 处理所有文件（包括ZIP解包后的文件）
        for file in files_to_process:
            try:
                logger.info(f"处理文件: {file.filename}")
                # 在metadata中添加batch_id
                file_metadata = parsed_metadata.copy()
                file_metadata['batch_id'] = batch.id
                
                result = await service.upload_document(
                    file=file,
                    knowledge_base_id=knowledge_base_id,
                    category_id=category_id,
                    tags=parsed_tags,
                    metadata=file_metadata,
                    user_id=user_id
                )
                
                # 更新文档的batch_id
                document = db.query(Document).filter(Document.id == result['document_id']).first()
                if document:
                    document.batch_id = batch.id
                    db.commit()
                
                # 更新批次进度
                batch_service.update_batch_progress(batch.id, success=True)
                
                results.append({
                    "filename": file.filename,
                    "document_id": result['document_id'],
                    "task_id": result.get('task_id'),
                    "status": "success"
                })
                success_count += 1
            except Exception as e:
                logger.error(f"文件 {file.filename} 上传失败: {e}")
                # 更新批次进度
                batch_service.update_batch_progress(batch.id, failed=True)
                
                results.append({
                    "filename": file.filename,
                    "status": "failed",
                    "error": str(e)
                })
                fail_count += 1
        
        logger.info(f"API响应: 批量上传完成，成功: {success_count}, 失败: {fail_count}")
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "batch_id": batch.id,
                "success_count": success_count,
                "fail_count": fail_count,
                "total": len(files),
                "results": results
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量上传文档API错误: {e}", exc_info=True)
        return {"code": 1, "message": f"批量上传文档失败: {str(e)}"}

class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    document_ids: List[int]

class BatchMoveRequest(BaseModel):
    """批量移动请求"""
    document_ids: List[int]
    target_knowledge_base_id: int
    target_category_id: Optional[int] = None

class BatchTagsAddRequest(BaseModel):
    """批量添加标签请求"""
    document_ids: List[int]
    tags: List[str]

class BatchTagsRemoveRequest(BaseModel):
    """批量删除标签请求"""
    document_ids: List[int]
    tags: List[str]

class BatchTagsReplaceRequest(BaseModel):
    """批量替换标签请求"""
    document_ids: List[int]
    tags: List[str]

@router.post("/batch/delete")
async def batch_delete_documents(
    request: Request,
    delete_request: BatchDeleteRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    批量删除文档 - 根据文档处理流程设计实现
    
    请求参数：
    - document_ids: 文档ID列表
    
    响应内容：
    - deleted_count: 成功删除数量
    - failed_count: 失败数量
    - failed_ids: 失败的文档ID列表
    """
    try:
        # 获取当前用户ID
        user_id = get_current_user_id(request)
        document_ids = delete_request.document_ids
        logger.info(f"API请求: 批量删除文档，文档数量: {len(document_ids)}, 用户ID: {user_id}")
        
        if not document_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文档ID列表不能为空"
            )
        
        service = DocumentService(db)
        deleted_count = 0
        failed_count = 0
        failed_ids = []
        
        # 预加载文档，按 knowledge_base_id 归组以减少权限查询次数
        docs = db.query(Document).filter(
            Document.id.in_(document_ids),
            Document.is_deleted == False
        ).all()
        doc_map = {d.id: d for d in docs}

        perm = KnowledgeBasePermissionService(db)
        kb_perm_cache: dict[int, bool] = {}

        for doc_id in document_ids:
            try:
                doc = doc_map.get(doc_id)
                if not doc:
                    logger.warning(f"文档不存在或已删除: {doc_id}")
                    failed_ids.append(doc_id)
                    failed_count += 1
                    continue

                kb_id = doc.knowledge_base_id
                # 针对同一知识库的多个文档，复用权限结果
                if kb_id not in kb_perm_cache:
                    try:
                        perm.ensure_permission(kb_id, user_id, "doc:delete")
                        kb_perm_cache[kb_id] = True
                    except HTTPException:
                        kb_perm_cache[kb_id] = False
                if not kb_perm_cache.get(kb_id):
                    logger.warning(f"无权删除文档: {doc_id}, 用户ID: {user_id}")
                    failed_ids.append(doc_id)
                    failed_count += 1
                    continue

                success = await service.delete_document(doc_id, hard=True)
                if success:
                    deleted_count += 1
                    logger.info(f"文档删除成功: {doc_id}")
                else:
                    failed_ids.append(doc_id)
                    failed_count += 1
                    logger.warning(f"文档删除失败: {doc_id}")
            except Exception as e:
                logger.error(f"删除文档 {doc_id} 失败: {e}", exc_info=True)
                failed_ids.append(doc_id)
                failed_count += 1
        
        logger.info(f"API响应: 批量删除完成，成功: {deleted_count}, 失败: {failed_count}")
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "deleted_count": deleted_count,
                "failed_count": failed_count,
                "failed_ids": failed_ids,
                "total": len(document_ids)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量删除文档API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量删除文档失败: {str(e)}"
        )

@router.post("/batch/move")
async def batch_move_documents(
    request: Request,
    move_request: BatchMoveRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    批量移动文档 - 根据文档处理流程设计实现
    
    请求参数：
    - document_ids: 文档ID列表
    - target_knowledge_base_id: 目标知识库ID
    - target_category_id: 目标分类ID（可选）
    
    响应内容：
    - moved_count: 成功移动数量
    - failed_count: 失败数量
    - failed_ids: 失败的文档ID列表
    """
    try:
        # 获取当前用户ID
        user_id = get_current_user_id(request)
        document_ids = move_request.document_ids
        target_kb_id = move_request.target_knowledge_base_id
        target_category_id = move_request.target_category_id
        
        logger.info(f"API请求: 批量移动文档，文档数量: {len(document_ids)}, 目标知识库ID: {target_kb_id}, 用户ID: {user_id}")
        
        if not document_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文档ID列表不能为空"
            )
        
        # 验证目标知识库是否存在且当前用户在其中具有 doc:edit 权限
        from app.models.knowledge_base import KnowledgeBase
        target_kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == target_kb_id,
            KnowledgeBase.is_deleted == False
        ).first()
        
        if not target_kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目标知识库不存在"
            )

        perm = KnowledgeBasePermissionService(db)
        # 移入目标知识库需要具备 doc:edit 权限
        perm.ensure_permission(target_kb_id, user_id, "doc:edit")
        
        service = DocumentService(db)
        moved_count = 0
        failed_count = 0
        failed_ids = []
        
        perm = KnowledgeBasePermissionService(db)

        for doc_id in document_ids:
            try:
                doc = db.query(Document).filter(
                    Document.id == doc_id,
                    Document.is_deleted == False
                ).first()

                if not doc:
                    logger.warning(f"文档不存在: {doc_id}")
                    failed_ids.append(doc_id)
                    failed_count += 1
                    continue

                # 验证在源知识库上具有 doc:edit 权限
                try:
                    perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:edit")
                except HTTPException:
                    logger.warning(f"无权移动文档: {doc_id}, 用户ID: {user_id}")
                    failed_ids.append(doc_id)
                    failed_count += 1
                    continue

                # 如果目标知识库与当前相同，只更新分类
                if doc.knowledge_base_id == target_kb_id:
                    if target_category_id is not None:
                        doc.category_id = target_category_id
                        db.commit()
                        moved_count += 1
                        logger.info(f"文档分类更新成功: {doc_id}")
                    else:
                        # 无需移动
                        moved_count += 1
                        logger.info(f"文档已在目标知识库: {doc_id}")
                else:
                    # 更新知识库和分类
                    doc.knowledge_base_id = target_kb_id
                    if target_category_id is not None:
                        doc.category_id = target_category_id
                    db.commit()
                    moved_count += 1
                    logger.info(f"文档移动成功: {doc_id} -> 知识库 {target_kb_id}")
            except Exception as e:
                logger.error(f"移动文档 {doc_id} 失败: {e}", exc_info=True)
                db.rollback()
                failed_ids.append(doc_id)
                failed_count += 1
        
        logger.info(f"API响应: 批量移动完成，成功: {moved_count}, 失败: {failed_count}")
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "moved_count": moved_count,
                "failed_count": failed_count,
                "failed_ids": failed_ids,
                "total": len(document_ids)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量移动文档API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量移动文档失败: {str(e)}"
        )

@router.post("/batch/tags/add")
async def batch_add_tags(
    request: Request,
    tags_request: BatchTagsAddRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    批量添加标签
    
    请求参数：
    - document_ids: 文档ID列表
    - tags: 要添加的标签列表
    
    响应内容：
    - updated_count: 成功更新数量
    """
    try:
        user_id = get_current_user_id(request)
        document_ids = tags_request.document_ids
        tags_to_add = tags_request.tags
        
        logger.info(f"API请求: 批量添加标签，文档数量: {len(document_ids)}, 标签: {tags_to_add}, 用户ID: {user_id}")
        
        if not document_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文档ID列表不能为空")
        if not tags_to_add:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="标签列表不能为空")
        
        perm = KnowledgeBasePermissionService(db)
        updated_count = 0
        for doc_id in document_ids:
            try:
                doc = db.query(Document).filter(
                    Document.id == doc_id,
                    Document.is_deleted == False
                ).first()

                if not doc:
                    continue

                try:
                    perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:edit")
                except HTTPException:
                    continue

                # 获取现有标签
                current_tags = doc.tags if doc.tags else []
                if not isinstance(current_tags, list):
                    current_tags = []

                # 合并标签（去重）
                new_tags = list(set(current_tags + tags_to_add))
                doc.tags = new_tags
                db.commit()
                updated_count += 1
            except Exception as e:
                logger.error(f"添加标签失败 {doc_id}: {e}")
                db.rollback()
        
        return {
            "code": 0,
            "message": "ok",
            "data": {"updated_count": updated_count}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量添加标签API错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"批量添加标签失败: {str(e)}")

@router.post("/batch/tags/remove")
async def batch_remove_tags(
    request: Request,
    tags_request: BatchTagsRemoveRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    批量删除标签
    
    请求参数：
    - document_ids: 文档ID列表
    - tags: 要删除的标签列表
    
    响应内容：
    - updated_count: 成功更新数量
    """
    try:
        user_id = get_current_user_id(request)
        document_ids = tags_request.document_ids
        tags_to_remove = tags_request.tags
        
        logger.info(f"API请求: 批量删除标签，文档数量: {len(document_ids)}, 标签: {tags_to_remove}, 用户ID: {user_id}")
        
        if not document_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文档ID列表不能为空")
        if not tags_to_remove:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="标签列表不能为空")
        
        perm = KnowledgeBasePermissionService(db)
        updated_count = 0
        for doc_id in document_ids:
            try:
                doc = db.query(Document).filter(
                    Document.id == doc_id,
                    Document.is_deleted == False
                ).first()

                if not doc:
                    continue

                try:
                    perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:edit")
                except HTTPException:
                    continue

                # 获取现有标签
                current_tags = doc.tags if doc.tags else []
                if not isinstance(current_tags, list):
                    current_tags = []

                # 移除标签
                new_tags = [t for t in current_tags if t not in tags_to_remove]
                doc.tags = new_tags
                db.commit()
                updated_count += 1
            except Exception as e:
                logger.error(f"删除标签失败 {doc_id}: {e}")
                db.rollback()
        
        return {
            "code": 0,
            "message": "ok",
            "data": {"updated_count": updated_count}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量删除标签API错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"批量删除标签失败: {str(e)}")

@router.post("/batch/tags/replace")
async def batch_replace_tags(
    request: Request,
    tags_request: BatchTagsReplaceRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    批量替换标签
    
    请求参数：
    - document_ids: 文档ID列表
    - tags: 新的标签列表（将完全替换现有标签）
    
    响应内容：
    - updated_count: 成功更新数量
    """
    try:
        user_id = get_current_user_id(request)
        document_ids = tags_request.document_ids
        new_tags = tags_request.tags
        
        logger.info(f"API请求: 批量替换标签，文档数量: {len(document_ids)}, 新标签: {new_tags}, 用户ID: {user_id}")
        
        if not document_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文档ID列表不能为空")
        
        perm = KnowledgeBasePermissionService(db)
        updated_count = 0
        for doc_id in document_ids:
            try:
                doc = db.query(Document).filter(
                    Document.id == doc_id,
                    Document.is_deleted == False
                ).first()

                if not doc:
                    continue

                try:
                    perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:edit")
                except HTTPException:
                    continue

                # 直接替换标签
                doc.tags = new_tags
                db.commit()
                updated_count += 1
            except Exception as e:
                logger.error(f"替换标签失败 {doc_id}: {e}")
                db.rollback()
        
        return {
            "code": 0,
            "message": "ok",
            "data": {"updated_count": updated_count}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量替换标签API错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"批量替换标签失败: {str(e)}")

@router.get("/{doc_id}/toc")
async def get_document_toc(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    获取文档目录
    
    响应内容：
    - toc: 目录树形结构
    """
    try:
        user_id = get_current_user_id(request)

        doc = db.query(Document).filter(
            Document.id == doc_id,
            Document.is_deleted == False
        ).first()

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )

        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:view")
        
        from app.services.document_toc_service import DocumentTOCService
        toc_service = DocumentTOCService(db)
        toc = await toc_service.get_document_toc(doc_id)
        
        return {
            "code": 0,
            "message": "ok",
            "data": {"toc": toc}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档目录API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档目录失败: {str(e)}"
        )

@router.get("/{doc_id}/search")
async def search_in_document(
    doc_id: int,
    request: Request,
    query: str = Query(..., description="搜索关键词"),
    page: Optional[int] = Query(None, description="指定页码（可选）"),
    db: Session = Depends(get_db)
):
    """
    在文档内搜索关键词
    
    响应内容：
    - results: 搜索结果列表
    - total: 结果总数
    """
    try:
        user_id = get_current_user_id(request)

        doc = db.query(Document).filter(
            Document.id == doc_id,
            Document.is_deleted == False
        ).first()

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )

        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(doc.knowledge_base_id, user_id, "doc:view")
        
        # 从OpenSearch搜索文档内容
        from app.services.opensearch_service import OpenSearchService
        os_service = OpenSearchService()
        
        # 构建查询
        must_clauses = [
            {"term": {"document_id": doc_id}},
            {"match": {"content": {"query": query}}}
        ]
        
        # 添加高亮
        highlight_config = os_service._build_highlight_config(query, fields=["content"])
        
        search_body = {
            "query": {"bool": {"must": must_clauses}},
            "size": 100,  # 文档内搜索返回更多结果
            "_source": ["chunk_id", "content", "chunk_type", "metadata"],
            **highlight_config
        }
        
        response = os_service.client.search(
            index=os_service.document_index,
            body=search_body
        )
        
        # 处理结果
        results = []
        for hit in response["hits"]["hits"]:
            content = hit["_source"].get("content", "")
            highlighted = os_service._extract_highlight(hit, "content")
            
            # 提取页码（从metadata）
            metadata = hit["_source"].get("metadata", {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            page_num = metadata.get("page_number")
            if page_num and page and page_num != page:
                continue  # 如果指定了页码，过滤结果
            
            results.append({
                "page": page_num,
                "position": hit.get("_score", 0),
                "context": content[:200] + "..." if len(content) > 200 else content,
                "highlight": highlighted or content[:200],
                "chunk_id": hit["_source"].get("chunk_id")
            })
        
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "results": results,
                "total": len(results)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档内搜索API错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档内搜索失败: {str(e)}"
        )

@router.get("/batch/{batch_id}/status")
async def get_batch_status(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """获取批次状态 - 根据设计文档实现"""
    try:
        batch_service = BatchService(db)
        status_data = batch_service.get_batch_status(batch_id)
        
        if not status_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"批次 {batch_id} 不存在"
            )
        
        return {
            "code": 0,
            "message": "ok",
            "data": status_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取批次状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取批次状态失败: {str(e)}"
        )

@router.get("/{doc_id}/structured-preview")
async def get_structured_preview(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """获取结构化预览 - 根据设计文档实现"""
    try:
        preview_service = StructuredPreviewService(db)
        preview_data = preview_service.get_preview(doc_id)
        
        if not preview_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在或不支持结构化预览"
            )
        
        return {
            "code": 0,
            "message": "ok",
            "data": preview_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取结构化预览失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取结构化预览失败: {str(e)}"
        )

@router.post("/{doc_id}/regenerate-summary")
async def regenerate_summary(
    request: Request,
    doc_id: int,
    db: Session = Depends(get_db)
):
    """
    重新生成标签和摘要 - 根据设计文档实现

    权限要求：
    - 需要对文档所属知识库具有 doc:edit 权限（viewer 只能查看，不能触发生成）
    """
    try:
        # 获取当前用户ID
        user_id = get_current_user_id(request)

        # 检查文档是否存在
        document = db.query(Document).filter(
            Document.id == doc_id,
            Document.is_deleted == False  # noqa: E712
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )

        # 权限检查：需要 doc:edit 权限
        perm = KnowledgeBasePermissionService(db)
        perm.ensure_permission(document.knowledge_base_id, user_id, "doc:edit")

        # 检查是否有chunk数据
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc_id,
            DocumentChunk.is_deleted == False  # noqa: E712
        ).count()

        if chunks == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文档没有分块数据，无法生成摘要。请先完成文档处理。"
            )

        tagging_service = AutoTaggingService(db)
        result = await tagging_service.regenerate_tags_and_summary(doc_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="生成标签和摘要失败：无法获取文档内容或LLM生成失败。请检查文档是否已处理完成，以及Ollama服务是否正常。"
            )

        return {
            "code": 0,
            "message": "ok",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新生成标签和摘要失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新生成标签和摘要失败: {str(e)}"
        )

@router.post("/{doc_id}/reprocess")
def reprocess_document(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """重新处理文档 - 根据文档处理流程设计实现"""
    try:
        logger.info(f"API请求: 重新处理文档 {doc_id}")
        
        service = DocumentService(db)
        success = service.reprocess_document(doc_id)
        
        if not success:
            logger.warning(f"API响应: 文档不存在 {doc_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )
        
        logger.info(f"API响应: 文档重新处理已启动 {doc_id}")
        return {"code": 0, "message": "ok"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新处理文档API错误: {e}", exc_info=True)
        return {"code": 1, "message": f"重新处理文档失败: {str(e)}"}
