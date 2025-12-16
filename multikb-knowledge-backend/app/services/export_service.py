"""
Export Service
导出服务
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
import json
import os
import tempfile
from app.models.export_task import ExportTask
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.chunk import DocumentChunk
from app.models.qa_session import QASession
from app.models.qa_question import QAQuestion
from app.models.image import DocumentImage
from app.services.minio_storage_service import MinioStorageService
from app.services.opensearch_service import OpenSearchService
from app.core.logging import logger
from datetime import timedelta


class ExportService:
    """导出服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.minio = MinioStorageService()
        self.opensearch = OpenSearchService()
    
    async def export_knowledge_base(
        self,
        user_id: int,
        kb_id: int,
        format: str = "markdown",
        include_documents: bool = True,
        include_chunks: bool = False
    ) -> ExportTask:
        """导出知识库"""
        try:
            # 验证知识库归属权
            kb = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.user_id == user_id,
                KnowledgeBase.is_deleted == False
            ).first()
            
            if not kb:
                raise ValueError("知识库不存在或无权限")
            
            # 创建导出任务
            task = ExportTask(
                user_id=user_id,
                export_type="knowledge_base",
                target_id=kb_id,
                export_format=format,
                status="processing"
            )
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            
            # 生成导出文件
            if format == "markdown":
                content = await self._export_kb_to_markdown(kb_id, include_documents, include_chunks)
            elif format == "json":
                content = await self._export_kb_to_json(kb_id, include_documents, include_chunks)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
            
            # 保存到MinIO
            file_name = f"kb_{kb_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}"
            object_name = f"exports/{user_id}/{file_name}"
            
            # 上传到MinIO
            import io
            self.minio.client.put_object(
                self.minio.bucket_name,
                object_name,
                io.BytesIO(content.encode('utf-8') if isinstance(content, str) else json.dumps(content).encode('utf-8')),
                length=len(content.encode('utf-8') if isinstance(content, str) else json.dumps(content).encode('utf-8'))
            )
            
            # 更新任务状态
            task.status = "completed"
            task.file_path = object_name
            task.file_size = len(content.encode('utf-8') if isinstance(content, str) else json.dumps(content).encode('utf-8'))
            task.completed_at = datetime.utcnow()
            self.db.commit()
            
            return task
            
        except Exception as e:
            logger.error(f"导出知识库失败: {e}", exc_info=True)
            if 'task' in locals():
                task.status = "failed"
                task.error_message = str(e)
                self.db.commit()
            raise
    
    async def _export_kb_to_markdown(self, kb_id: int, include_documents: bool, include_chunks: bool) -> str:
        """导出知识库为Markdown格式"""
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            return ""
        
        lines = [f"# {kb.name}\n"]
        if kb.description:
            lines.append(f"{kb.description}\n")
        lines.append("\n---\n")
        
        if include_documents:
            docs = self.db.query(Document).filter(
                Document.knowledge_base_id == kb_id,
                Document.is_deleted == False
            ).order_by(Document.created_at).all()
            
            for doc in docs:
                lines.append(f"\n## {doc.original_filename}\n")
                if doc.meta and isinstance(doc.meta, dict) and doc.meta.get("title"):
                    lines.append(f"**标题**: {doc.meta['title']}\n")
                
                # 添加文档基本信息
                if doc.file_type:
                    lines.append(f"**文件类型**: {doc.file_type}\n")
                if doc.file_size:
                    lines.append(f"**文件大小**: {self._format_file_size(doc.file_size)}\n")
                if doc.status:
                    lines.append(f"**状态**: {doc.status}\n")
                
                # 获取文档内容
                chunks = self.db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc.id,
                    DocumentChunk.is_deleted == False
                ).order_by(DocumentChunk.chunk_index).all()
                
                if chunks:
                    if include_chunks:
                        # 包含分块：显示每个分块的详细信息
                        for chunk in chunks:
                            lines.append(f"\n### 分块 {chunk.chunk_index}\n")
                            if chunk.chunk_type:
                                lines.append(f"**类型**: {chunk.chunk_type}\n")
                            
                            # 处理图片类型的分块
                            if chunk.chunk_type == 'image':
                                image_url = self._get_chunk_image_url(chunk)
                                if image_url:
                                    lines.append(f"![图片 {chunk.chunk_index}]({image_url})\n")
                                else:
                                    lines.append(f"*（图片不可用）*\n")
                            else:
                                lines.append(f"{chunk.content or ''}\n")
                    else:
                        # 不包含分块：合并所有分块内容作为完整文档
                        lines.append("\n**文档内容**:\n")
                        content_parts = []
                        for chunk in chunks:
                            if chunk.chunk_type == 'image':
                                # 图片类型：使用Markdown图片语法
                                image_url = self._get_chunk_image_url(chunk)
                                if image_url:
                                    content_parts.append(f"![图片 {chunk.chunk_index}]({image_url})")
                                else:
                                    content_parts.append(f"*（图片 {chunk.chunk_index} 不可用）*")
                            elif chunk.content:
                                content_parts.append(chunk.content)
                        if content_parts:
                            lines.append("\n".join(content_parts))
                            lines.append("\n")
                else:
                    lines.append("\n*（该文档暂无内容）*\n")
                
                lines.append("\n---\n")
        
        return "\n".join(lines)
    
    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    async def _export_kb_to_json(self, kb_id: int, include_documents: bool, include_chunks: bool) -> Dict[str, Any]:
        """导出知识库为JSON格式"""
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            return {}
        
        result = {
            "knowledge_base": {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "created_at": kb.created_at.isoformat() if kb.created_at else None
            },
            "documents": []
        }
        
        if include_documents:
            docs = self.db.query(Document).filter(
                Document.knowledge_base_id == kb_id,
                Document.is_deleted == False
            ).order_by(Document.created_at).all()
            
            for doc in docs:
                doc_data = {
                    "id": doc.id,
                    "title": doc.original_filename,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "status": doc.status,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None
                }
                
                # 获取文档元数据
                if doc.meta and isinstance(doc.meta, dict):
                    if doc.meta.get("title"):
                        doc_data["meta_title"] = doc.meta["title"]
                
                # 获取文档内容
                chunks = self.db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc.id,
                    DocumentChunk.is_deleted == False
                ).order_by(DocumentChunk.chunk_index).all()
                
                if chunks:
                    if include_chunks:
                        # 包含分块：显示每个分块的详细信息
                        chunk_list = []
                        for chunk in chunks:
                            chunk_data = {
                                "id": chunk.id,
                                "chunk_index": chunk.chunk_index,
                                "chunk_type": chunk.chunk_type
                            }
                            # 处理图片类型的分块
                            if chunk.chunk_type == 'image':
                                image_url = self._get_chunk_image_url(chunk)
                                chunk_data["image_url"] = image_url
                                chunk_data["content"] = image_url or ""
                            else:
                                chunk_data["content"] = chunk.content or ""
                            chunk_list.append(chunk_data)
                        doc_data["chunks"] = chunk_list
                    else:
                        # 不包含分块：合并所有分块内容作为完整文档
                        content_parts = []
                        for chunk in chunks:
                            if chunk.chunk_type == 'image':
                                image_url = self._get_chunk_image_url(chunk)
                                if image_url:
                                    content_parts.append(f"[图片 {chunk.chunk_index}]({image_url})")
                            elif chunk.content:
                                content_parts.append(chunk.content)
                        doc_data["content"] = "\n".join(content_parts)
                        doc_data["chunk_count"] = len(chunks)
                
                result["documents"].append(doc_data)
        
        return result
    
    async def export_document(
        self,
        user_id: int,
        doc_id: int,
        format: str = "markdown",
        include_chunks: bool = True,
        include_images: bool = False,
        export_original: bool = False
    ) -> ExportTask:
        """导出文档
        
        Args:
            user_id: 用户ID
            doc_id: 文档ID
            format: 导出格式 (markdown/json/original)
            include_chunks: 是否包含分块信息
            include_images: 是否包含图片
            export_original: 是否导出原始文档（直接从MinIO获取）
        """
        try:
            # 验证文档归属权
            doc = self.db.query(Document).filter(
                Document.id == doc_id,
                Document.user_id == user_id,
                Document.is_deleted == False
            ).first()
            
            if not doc:
                raise ValueError("文档不存在或无权限")
            
            # 创建导出任务
            task = ExportTask(
                user_id=user_id,
                export_type="document",
                target_id=doc_id,
                export_format=format,
                status="processing"
            )
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            
            # 如果导出原始文档，直接从MinIO获取
            if export_original and doc.file_path:
                logger.info(f"导出原始文档: {doc.file_path}")
                file_content = self.minio.download_file(doc.file_path)
                
                # 获取原始文件扩展名
                original_ext = os.path.splitext(doc.original_filename)[1] or os.path.splitext(doc.file_path)[1]
                file_name = f"doc_{doc_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{original_ext}"
                object_name = f"exports/{user_id}/{file_name}"
                
                # 上传到MinIO
                import io
                self.minio.client.put_object(
                    self.minio.bucket_name,
                    object_name,
                    io.BytesIO(file_content),
                    length=len(file_content)
                )
                
                # 更新任务状态
                task.status = "completed"
                task.file_path = object_name
                task.file_size = len(file_content)
                task.completed_at = datetime.utcnow()
                self.db.commit()
                
                return task
            
            # 生成导出文件
            if format == "markdown":
                content = await self._export_doc_to_markdown(doc_id, include_chunks, include_images)
            elif format == "json":
                content = await self._export_doc_to_json(doc_id, include_chunks, include_images)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
            
            # 保存到MinIO
            file_name = f"doc_{doc_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}"
            object_name = f"exports/{user_id}/{file_name}"
            
            # 上传到MinIO
            import io
            self.minio.client.put_object(
                self.minio.bucket_name,
                object_name,
                io.BytesIO(content.encode('utf-8') if isinstance(content, str) else json.dumps(content).encode('utf-8')),
                length=len(content.encode('utf-8') if isinstance(content, str) else json.dumps(content).encode('utf-8'))
            )
            
            # 更新任务状态
            task.status = "completed"
            task.file_path = object_name
            task.file_size = len(content.encode('utf-8') if isinstance(content, str) else json.dumps(content).encode('utf-8'))
            task.completed_at = datetime.utcnow()
            self.db.commit()
            
            return task
            
        except Exception as e:
            logger.error(f"导出文档失败: {e}", exc_info=True)
            if 'task' in locals():
                task.status = "failed"
                task.error_message = str(e)
                self.db.commit()
            raise
    
    def _get_chunks_from_opensearch(self, doc_id: int) -> List[Dict[str, Any]]:
        """从OpenSearch获取文档的所有块信息"""
        try:
            # 构建查询：获取指定文档的所有块
            search_body = {
                "query": {
                    "term": {"document_id": doc_id}
                },
                "size": 10000,  # 获取所有块（可根据需要调整）
                "sort": [{"metadata.chunk_index": {"order": "asc"}}],
                "_source": ["chunk_id", "content", "chunk_type", "metadata", "document_id"]
            }
            
            response = self.opensearch.client.search(
                index=self.opensearch.document_index,
                body=search_body
            )
            
            chunks = []
            for hit in response.get("hits", {}).get("hits", []):
                source = hit.get("_source", {})
                metadata = source.get("metadata", {})
                chunk_index = metadata.get("chunk_index") or metadata.get("index")
                
                chunks.append({
                    "chunk_id": source.get("chunk_id"),
                    "chunk_index": chunk_index,
                    "chunk_type": source.get("chunk_type", "text"),
                    "content": source.get("content", ""),
                    "metadata": metadata
                })
            
            # 按chunk_index排序
            chunks.sort(key=lambda x: x.get("chunk_index", 0) or 0)
            return chunks
            
        except Exception as e:
            logger.warning(f"从OpenSearch获取块信息失败，回退到数据库: {e}")
            # 回退到数据库查询
            db_chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc_id,
                DocumentChunk.is_deleted == False
            ).order_by(DocumentChunk.chunk_index).all()
            
            return [{
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "chunk_type": chunk.chunk_type or "text",
                "content": chunk.content or "",
                "metadata": json.loads(chunk.meta) if chunk.meta and isinstance(chunk.meta, str) else (chunk.meta if isinstance(chunk.meta, dict) else {})
            } for chunk in db_chunks]
    
    async def _export_doc_to_markdown(self, doc_id: int, include_chunks: bool, include_images: bool = False) -> str:
        """导出文档为Markdown格式"""
        doc = self.db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return ""
        
        lines = [f"# {doc.original_filename}\n"]
        if doc.meta and isinstance(doc.meta, dict) and doc.meta.get("title"):
            lines.append(f"**标题**: {doc.meta['title']}\n")
        lines.append(f"**文件类型**: {doc.file_type}\n")
        lines.append(f"**状态**: {doc.status}\n")
        lines.append("\n---\n")
        
        # 如果包含图片，先列出所有图片
        if include_images:
            images = self.db.query(DocumentImage).filter(
                DocumentImage.document_id == doc_id,
                DocumentImage.is_deleted == False
            ).order_by(DocumentImage.id).all()
            
            if images:
                lines.append("\n## 文档图片\n")
                for img in images:
                    image_url = self._get_image_url(img)
                    if image_url:
                        lines.append(f"![图片 {img.id}]({image_url})\n")
                        if img.ocr_text:
                            lines.append(f"*OCR文本: {img.ocr_text[:100]}...*\n")
                    lines.append("\n")
                lines.append("---\n")
        
        # 从OpenSearch获取块信息
        chunks_data = self._get_chunks_from_opensearch(doc_id)
        
        if chunks_data:
            if include_chunks:
                for chunk in chunks_data:
                    chunk_index = chunk.get("chunk_index", 0)
                    chunk_type = chunk.get("chunk_type", "text")
                    content = chunk.get("content", "")
                    metadata = chunk.get("metadata", {})
                    
                    lines.append(f"\n## 分块 {chunk_index}\n")
                    if chunk_type:
                        lines.append(f"**类型**: {chunk_type}\n")
                    
                    # 处理图片类型的分块
                    if chunk_type == 'image':
                        image_path = metadata.get("image_path")
                        if image_path:
                            image_url = self._get_image_url_from_path(image_path)
                            if image_url:
                                lines.append(f"![图片 {chunk_index}]({image_url})\n")
                            else:
                                lines.append(f"*（图片不可用）*\n")
                        else:
                            lines.append(f"*（图片不可用）*\n")
                    else:
                        lines.append(f"{content}\n")
                    lines.append("\n---\n")
            else:
                # 不包含分块：合并所有分块内容
                lines.append("\n## 文档内容\n")
                content_parts = []
                for chunk in chunks_data:
                    chunk_index = chunk.get("chunk_index", 0)
                    chunk_type = chunk.get("chunk_type", "text")
                    content = chunk.get("content", "")
                    metadata = chunk.get("metadata", {})
                    
                    if chunk_type == 'image':
                        image_path = metadata.get("image_path")
                        if image_path:
                            image_url = self._get_image_url_from_path(image_path)
                            if image_url:
                                content_parts.append(f"![图片 {chunk_index}]({image_url})")
                    elif content:
                        content_parts.append(content)
                if content_parts:
                    lines.append("\n".join(content_parts))
                    lines.append("\n")
        
        return "\n".join(lines)
    
    async def _export_doc_to_json(self, doc_id: int, include_chunks: bool, include_images: bool = False) -> Dict[str, Any]:
        """导出文档为JSON格式"""
        doc = self.db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return {}
        
        result = {
            "document": {
                "id": doc.id,
                "title": doc.original_filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "status": doc.status,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            },
            "chunks": [],
            "images": []
        }
        
        # 如果包含图片，添加图片列表
        if include_images:
            images = self.db.query(DocumentImage).filter(
                DocumentImage.document_id == doc_id,
                DocumentImage.is_deleted == False
            ).order_by(DocumentImage.id).all()
            
            for img in images:
                result["images"].append({
                    "id": img.id,
                    "image_path": img.image_path,
                    "image_url": self._get_image_url(img),
                    "width": img.width,
                    "height": img.height,
                    "ocr_text": img.ocr_text,
                    "description": getattr(img, 'description', None)
                })
        
        # 从OpenSearch获取块信息
        chunks_data = self._get_chunks_from_opensearch(doc_id)
        
        if chunks_data:
            if include_chunks:
                for chunk in chunks_data:
                    chunk_index = chunk.get("chunk_index", 0)
                    chunk_type = chunk.get("chunk_type", "text")
                    content = chunk.get("content", "")
                    metadata = chunk.get("metadata", {})
                    
                    chunk_data = {
                        "id": chunk.get("chunk_id"),
                        "chunk_index": chunk_index,
                        "chunk_type": chunk_type
                    }
                    # 处理图片类型的分块
                    if chunk_type == 'image':
                        image_path = metadata.get("image_path")
                        if image_path:
                            image_url = self._get_image_url_from_path(image_path)
                            chunk_data["image_url"] = image_url
                            chunk_data["content"] = image_url or ""
                        else:
                            chunk_data["content"] = ""
                    else:
                        chunk_data["content"] = content
                    result["chunks"].append(chunk_data)
            else:
                # 不包含分块：合并内容
                content_parts = []
                for chunk in chunks_data:
                    chunk_index = chunk.get("chunk_index", 0)
                    chunk_type = chunk.get("chunk_type", "text")
                    content = chunk.get("content", "")
                    metadata = chunk.get("metadata", {})
                    
                    if chunk_type == 'image':
                        image_path = metadata.get("image_path")
                        if image_path:
                            image_url = self._get_image_url_from_path(image_path)
                            if image_url:
                                content_parts.append(f"[图片 {chunk_index}]({image_url})")
                    elif content:
                        content_parts.append(content)
                result["content"] = "\n".join(content_parts)
                result["chunk_count"] = len(chunks_data)
        
        return result
    
    def _get_chunk_image_url(self, chunk: DocumentChunk) -> Optional[str]:
        """从分块中获取图片URL"""
        try:
            if chunk.meta:
                meta = json.loads(chunk.meta) if isinstance(chunk.meta, str) else chunk.meta
                image_path = meta.get('image_path')
                if image_path:
                    return self._get_image_url_from_path(image_path)
        except Exception as e:
            logger.warning(f"获取分块图片URL失败: {e}")
        return None
    
    def _get_image_url(self, image: DocumentImage) -> Optional[str]:
        """获取图片的访问URL"""
        if image.image_path:
            return self._get_image_url_from_path(image.image_path)
        return None
    
    def _get_image_url_from_path(self, image_path: str) -> Optional[str]:
        """从图片路径生成访问URL（签名URL）"""
        try:
            # 生成1小时有效的签名URL
            url = self.minio.client.presigned_get_object(
                self.minio.bucket_name,
                image_path,
                expires=timedelta(hours=1)
            )
            return url
        except Exception as e:
            logger.warning(f"生成图片签名URL失败: {e}")
            # 如果生成签名URL失败，返回相对路径
            return f"/api/images/file?object={image_path}"
    
    async def export_qa_history(
        self,
        user_id: int,
        format: str = "json",
        session_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> ExportTask:
        """导出问答历史"""
        try:
            # ✅ 转换session_id：如果是字符串（UUID格式），先查询对应的数据库ID
            session_db_id = None
            if session_id:
                try:
                    # 尝试作为整数ID
                    session_db_id = int(session_id)
                except (ValueError, TypeError):
                    # 如果是字符串（UUID格式），通过session_id查询数据库ID
                    session = self.db.query(QASession).filter(
                        QASession.session_id == session_id,
                        QASession.user_id == user_id,
                        QASession.is_deleted == False
                    ).first()
                    if session:
                        session_db_id = session.id
                    else:
                        raise ValueError(f"会话不存在: {session_id}")
            
            # 创建导出任务
            task = ExportTask(
                user_id=user_id,
                export_type="qa_history",
                target_id=session_db_id,
                export_format=format,
                status="processing"
            )
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            
            # 查询问答历史
            qa_query = (
                self.db.query(QAQuestion)
                .join(QASession, QAQuestion.session_id == QASession.id)
                .filter(
                    QASession.user_id == user_id,
                    QASession.is_deleted == False,
                    QAQuestion.is_deleted == False
                )
            )
            
            if session_db_id:
                qa_query = qa_query.filter(QASession.id == session_db_id)
            
            if start_date:
                from datetime import datetime
                start = datetime.fromisoformat(start_date)
                qa_query = qa_query.filter(QAQuestion.created_at >= start)
            
            if end_date:
                from datetime import datetime
                end = datetime.fromisoformat(end_date)
                qa_query = qa_query.filter(QAQuestion.created_at <= end)
            
            qa_records = qa_query.order_by(QAQuestion.created_at).all()
            
            # 生成导出文件
            if format == "json":
                content = await self._export_qa_to_json(qa_records)
            elif format == "csv":
                content = await self._export_qa_to_csv(qa_records)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
            
            # 保存到MinIO
            file_name = f"qa_history_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}"
            object_name = f"exports/{user_id}/{file_name}"
            
            # 上传到MinIO
            import io
            self.minio.client.put_object(
                self.minio.bucket_name,
                object_name,
                io.BytesIO(content.encode('utf-8')),
                length=len(content.encode('utf-8'))
            )
            
            # 更新任务状态
            task.status = "completed"
            task.file_path = object_name
            task.file_size = len(content.encode('utf-8'))
            task.completed_at = datetime.utcnow()
            self.db.commit()
            
            return task
            
        except Exception as e:
            logger.error(f"导出问答历史失败: {e}", exc_info=True)
            if 'task' in locals():
                task.status = "failed"
                task.error_message = str(e)
                self.db.commit()
            raise
    
    async def _export_qa_to_json(self, qa_records: list) -> str:
        """导出问答历史为JSON格式"""
        records = []
        for qa in qa_records:
            records.append({
                "session_id": qa.session_id,
                "question": qa.question,
                "answer": qa.answer,
                "created_at": qa.created_at.isoformat() if qa.created_at else None
            })
        return json.dumps(records, ensure_ascii=False, indent=2)
    
    async def _export_qa_to_csv(self, qa_records: list) -> str:
        """导出问答历史为CSV格式"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(["会话ID", "问题", "答案", "创建时间"])
        
        # 写入数据
        for qa in qa_records:
            writer.writerow([
                qa.session_id,
                qa.question or "",
                qa.answer or "",
                qa.created_at.isoformat() if qa.created_at else ""
            ])
        
        return output.getvalue()
    
    def get_export_task(self, task_id: int, user_id: int) -> Optional[ExportTask]:
        """获取导出任务"""
        return self.db.query(ExportTask).filter(
            ExportTask.id == task_id,
            ExportTask.user_id == user_id,
            ExportTask.is_deleted == False
        ).first()
    
    def get_export_tasks(
        self, 
        user_id: int, 
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ExportTask]:
        """获取导出任务列表"""
        logger.info(
            "获取导出任务列表: user_id=%s, status=%s, limit=%s, offset=%s",
            user_id,
            status,
            limit,
            offset
        )
        query = self.db.query(ExportTask).filter(
            ExportTask.user_id == user_id,
            ExportTask.is_deleted == False
        )
        
        if status:
            query = query.filter(ExportTask.status == status)
        
        query = query.order_by(ExportTask.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        tasks = query.all()
        logger.info("导出任务列表获取完成: user_id=%s, 任务数=%s", user_id, len(tasks))
        return tasks
    
    async def get_export_download_url(self, task_id: int, user_id: int) -> Optional[str]:
        """获取导出文件下载URL"""
        task = self.get_export_task(task_id, user_id)
        if not task or task.status != "completed" or not task.file_path:
            return None
        
        from datetime import timedelta
        url = self.minio.client.presigned_get_object(
            self.minio.bucket_name,
            task.file_path,
            expires=timedelta(hours=24)
        )
        return url
    
    def delete_export_task(self, task_id: int, user_id: int) -> bool:
        """删除导出任务（软删除+硬删除同时执行）
        
        1. 先执行软删除：标记 is_deleted = True
        2. 删除MinIO中的文件（如果存在）
        3. 执行硬删除：从数据库中真正删除记录
        
        Returns:
            bool: 删除是否成功
        """
        try:
            logger.info("开始删除导出任务: task_id=%s, user_id=%s", task_id, user_id)
            # 获取任务（包括已软删除的）
            task = self.db.query(ExportTask).filter(
                ExportTask.id == task_id,
                ExportTask.user_id == user_id
            ).first()
            
            if not task:
                logger.warning("删除导出任务失败，任务不存在: task_id=%s, user_id=%s", task_id, user_id)
                return False
            
            # 1. 软删除：标记为已删除
            task.is_deleted = True
            self.db.commit()
            logger.info("导出任务软删除完成: task_id=%s, user_id=%s", task_id, user_id)
            
            # 2. 删除MinIO中的文件（如果存在）
            if task.file_path:
                try:
                    from minio.error import S3Error
                    self.minio.client.remove_object(
                        self.minio.bucket_name,
                        task.file_path
                    )
                    logger.info(f"已删除MinIO文件: {task.file_path}")
                except S3Error as e:
                    logger.warning(f"删除MinIO文件失败（可能文件不存在）: {task.file_path}, 错误: {e}")
                except Exception as e:
                    logger.warning(f"删除MinIO文件时发生错误: {task.file_path}, 错误: {e}")
            
            # 3. 硬删除：从数据库中真正删除记录
            self.db.delete(task)
            self.db.commit()
            
            logger.info(f"已删除导出任务: task_id={task_id}, user_id={user_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除导出任务失败: task_id={task_id}, user_id={user_id}, 错误: {e}", exc_info=True)
            return False
