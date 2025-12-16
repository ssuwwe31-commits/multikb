"""
Image Service
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.image import DocumentImage
from app.models.document import Document
from app.services.minio_storage_service import MinioStorageService
from app.services.base import BaseService
from app.services.ollama_service import OllamaService
from app.services.vector_service import VectorService
from app.services.opensearch_service import OpenSearchService
from app.utils.image_utils import get_image_info as util_get_image_info
from app.config.settings import settings
from datetime import datetime
import os
import io
import hashlib
import mimetypes
import time
from PIL import Image
from app.core.logging import logger


class ImageService(BaseService[DocumentImage]):
    """图片服务（同步方法，适配 Celery 同步任务）"""
    
    def __init__(self, db: Session):
        super().__init__(db, DocumentImage)
        self._ollama_service: Optional[OllamaService] = None
    
    def _get_ollama_service(self) -> OllamaService:
        if self._ollama_service is None:
            self._ollama_service = OllamaService(self.db)
        return self._ollama_service
    
    def _detect_mime_from_path(self, path: str) -> str:
        mime = mimetypes.guess_type(path)[0]
        return mime or "image/png"
    
    def _load_image_bytes(self, image_path: str) -> bytes:
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as fp:
                return fp.read()
        storage = MinioStorageService()
        return storage.download_file(image_path)
    
    def _validate_image_bytes(self, image_bytes: bytes, image_mime: str) -> Tuple[bool, Optional[str]]:
        """验证图片字节是否有效"""
        if not image_bytes:
            return False, "图片数据为空"
        
        # 检查图片大小（太小可能是损坏的）
        min_size = 100  # 最小 100 bytes
        if len(image_bytes) < min_size:
            return False, f"图片文件过小（{len(image_bytes)} bytes），可能是损坏的文件"
        
        # 尝试用 PIL 验证图片
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()  # 验证图片完整性
            # 重新打开（verify 后需要重新打开）
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
            if width == 0 or height == 0:
                return False, f"图片尺寸无效: {width}x{height}"
            return True, None
        except Exception as e:
            return False, f"图片验证失败: {str(e)}"
    
    def _preprocess_image_for_ocr(self, image_bytes: bytes, image_mime: str) -> bytes:
        """预处理图片用于OCR：缩放、格式转换等"""
        if not settings.OCR_PREPROCESS_ENABLED:
            return image_bytes
        
        try:
            img = Image.open(io.BytesIO(image_bytes))
            original_width, original_height = img.size
            
            # 如果图片尺寸小于等于最大尺寸，不需要缩放
            max_size = settings.OCR_PREPROCESS_MAX_SIZE
            if original_width <= max_size and original_height <= max_size:
                logger.debug(f"图片尺寸 {original_width}x{original_height} 无需缩放")
                return image_bytes
            
            # 计算缩放比例，保持宽高比
            ratio = min(max_size / original_width, max_size / original_height)
            new_width = int(original_width * ratio)
            new_height = int(original_height * ratio)
            
            logger.debug(f"图片预处理: {original_width}x{original_height} -> {new_width}x{new_height}")
            
            # 转换为RGB格式（OCR模型通常需要RGB）
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 使用高质量重采样算法缩放
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 保存为JPEG格式（压缩比高，文件小）
            output = io.BytesIO()
            img_resized.save(output, format='JPEG', quality=85, optimize=True)
            processed_bytes = output.getvalue()
            
            logger.debug(f"图片预处理完成: 原始大小={len(image_bytes)} bytes, 处理后={len(processed_bytes)} bytes")
            return processed_bytes
            
        except Exception as e:
            logger.warning(f"图片预处理失败，使用原始图片: {e}")
            return image_bytes
    
    def _perform_qwen_ocr(self, image_bytes: bytes, image_mime: str) -> str:
        # 先验证图片
        is_valid, error_msg = self._validate_image_bytes(image_bytes, image_mime)
        if not is_valid:
            logger.warning(f"图片验证失败，跳过 OCR: {error_msg}")
            return ""  # 返回空字符串而不是抛出异常，允许继续处理
        
        # 预处理图片（缩放、格式转换等）
        processed_bytes = self._preprocess_image_for_ocr(image_bytes, image_mime)
        # 如果预处理成功且改变了图片，使用JPEG格式；否则保持原始MIME类型
        processed_mime = "image/jpeg" if (settings.OCR_PREPROCESS_ENABLED and processed_bytes != image_bytes) else image_mime
        
        service = self._get_ollama_service()
        return service.extract_text_from_image(
            image_bytes=processed_bytes,
            image_mime=processed_mime,
        )
    
    def _mark_status(
        self,
        image: DocumentImage,
        status: str,
        *,
        error: Optional[str] = None,
        retry_count: Optional[int] = None,
    ) -> None:
        image.status = status
        if error is not None:
            image.error_message = error
        if retry_count is not None:
            image.retry_count = retry_count
        image.last_processed_at = datetime.utcnow()
        self.db.commit()
    
    def _index_image_in_opensearch(
        self,
        image: DocumentImage,
        image_vector: List[float],
    ) -> None:
        os_service = OpenSearchService()
        document = self.db.query(Document).filter(Document.id == image.document_id).first()
        metadata = {}
        if image.meta:
            try:
                import json
                metadata = json.loads(image.meta) if isinstance(image.meta, str) else image.meta
            except Exception:
                metadata = {}
        os_service.index_image_sync(
            {
                "image_id": image.id,
                "document_id": image.document_id,
                "knowledge_base_id": getattr(document, "knowledge_base_id", None),
                "category_id": getattr(document, "category_id", None),
                "image_path": image.image_path,
                "page_number": metadata.get("page_number"),
                "coordinates": metadata.get("coordinates"),
                "width": image.width,
                "height": image.height,
                "image_type": image.image_type,
                "ocr_text": image.ocr_text or "",
                "description": metadata.get("description", ""),
                "feature_tags": metadata.get("feature_tags", []),
                "image_vector": image_vector,
                "created_at": getattr(image, "created_at", None).isoformat()
                if getattr(image, "created_at", None)
                else None,
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
                "processing_status": image.status,
                "model_version": "1.0",
            }
        )
    
    # =============== 基础工具 ===============
    def compute_sha256(self, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def generate_thumbnail(self, src_path: str, max_size: int = 512) -> Optional[str]:
        try:
            thumb_dir = os.path.join(os.path.dirname(src_path), 'thumb')
            os.makedirs(thumb_dir, exist_ok=True)
            base = os.path.basename(src_path)
            name, ext = os.path.splitext(base)
            thumb_path = os.path.join(thumb_dir, f"{name}_thumb.jpg")
            with Image.open(src_path) as im:
                im = im.convert('RGB')
                im.thumbnail((max_size, max_size))
                im.save(thumb_path, format='JPEG', quality=85)
            return thumb_path
        except Exception:
            return None
    
    # =============== 信息/识别 ===============
    def get_image_info(self, image_path: str) -> Optional[dict]:
        return util_get_image_info(image_path)
    
    def extract_ocr_text(self, image_path: str) -> str:
        """兼容旧调用：直接对指定路径执行 Qwen OCR"""
        try:
            data = self._load_image_bytes(image_path)
            mime = self._detect_mime_from_path(image_path)
            return self._perform_qwen_ocr(data, mime)
        except Exception as exc:
            logger.warning(f"extract_ocr_text 调用失败: {exc}")
            return ""
    
    def _normalize_ext(self, image_ext: Optional[str]) -> str:
        ext = (image_ext or ".png").lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        return ext
    
    def _infer_image_type(self, image_ext: str, explicit_type: Optional[str] = None, info_format: Optional[str] = None) -> str:
        candidates = [
            explicit_type,
            image_ext.lstrip(".") if image_ext else None,
            info_format.lower() if info_format else None,
        ]
        for candidate in candidates:
            if candidate:
                return candidate.replace(".", "").lower()
        return "unknown"
    
    def ensure_image_type_from_storage(self, image: DocumentImage, minio: Optional[MinioStorageService] = None) -> Optional[str]:
        """确保图片类型存在；如缺失则根据路径或 MinIO 内容推断并回写数据库。"""
        current = (getattr(image, "image_type", None) or "").strip().lower()
        if current and current != "unknown":
            return current
        
        path = getattr(image, "image_path", "") or ""
        inferred = None
        if path:
            ext = os.path.splitext(path)[1]
            if ext:
                inferred = self._infer_image_type(self._normalize_ext(ext))
        
        if (not inferred or inferred == "unknown") and path:
            storage = minio or MinioStorageService()
            try:
                obj = storage.client.get_object(storage.bucket_name, path)
                data = obj.read()
                obj.close()
                obj.release_conn()
                with Image.open(io.BytesIO(data)) as im:
                    fmt = (im.format or "").lower()
                    if fmt:
                        inferred = fmt
            except Exception as exc:
                logger.warning(f"无法从 MinIO 推断图片类型: image_id={image.id}, path={path}, error={exc}")
        
        if inferred:
            image.image_type = inferred
            self.db.commit()
            return inferred
        return None
    
    def backfill_missing_image_types(self, batch_size: int = 200) -> int:
        """回填缺失的 image_type 字段"""
        query = self.db.query(DocumentImage).filter(
            DocumentImage.is_deleted == False,
            or_(
                DocumentImage.image_type == None,  # noqa: E711
                DocumentImage.image_type == "",
                DocumentImage.image_type == "unknown"
            )
        )
        total = query.count()
        if total == 0:
            logger.info("没有需要回填的图片类型记录")
            return 0
        
        logger.info(f"开始回填 image_type, 待处理: {total} 条")
        updated = 0
        minio = MinioStorageService()
        for image in query.yield_per(batch_size):
            inferred = self.ensure_image_type_from_storage(image, minio=minio)
            if inferred:
                updated += 1
        logger.info(f"回填图片类型完成，更新 {updated}/{total} 条记录")
        return updated
    
    # =============== 入口：保存并去重 ===============
    def create_image_from_bytes(self, document_id: int, data: bytes, image_ext: str = ".png", image_type: Optional[str] = None) -> DocumentImage:
        """从二进制创建图片：上传 MinIO，记录 MySQL，返回实体。"""
        sha = hashlib.sha256(data).hexdigest()
        norm_ext = self._normalize_ext(image_ext)
        inferred_type = self._infer_image_type(norm_ext, explicit_type=image_type)
        existing = self.db.query(DocumentImage).filter(DocumentImage.sha256_hash == sha, DocumentImage.is_deleted == False).first()
        if existing:
            if not existing.image_type and inferred_type != "unknown":
                existing.image_type = inferred_type
                self.db.commit()
            return existing
        # 上传原图至 MinIO
        minio = MinioStorageService()
        object_name = f"documents/{document_id}/images/{sha}{norm_ext}"
        content_type = mimetypes.types_map.get(norm_ext, f"image/{inferred_type}" if inferred_type != "unknown" else "application/octet-stream")
        minio.upload_bytes(object_name, data, content_type=content_type)
        # 生成缩略图（内存）
        thumb_object = None
        width = None
        height = None
        try:
            from io import BytesIO
            with Image.open(BytesIO(data)) as im:
                width, height = im.size
                im = im.convert('RGB')
                im.thumbnail((256, 256))
                buf = BytesIO()
                im.save(buf, format='JPEG', quality=85)
                thumb_object = f"documents/{document_id}/images/thumb/{sha}_thumb.jpg"
                minio.upload_bytes(thumb_object, buf.getvalue(), content_type="image/jpeg")
        except Exception:
            pass
        # OCR（Qwen VL）
        ocr_text = ""
        status = "pending"
        error_message = None
        try:
            mime = f"image/{inferred_type}" if inferred_type and inferred_type != "unknown" else "image/png"
            ocr_text = self._perform_qwen_ocr(data, mime)
            status = "completed"
        except Exception as exc:
            error_message = str(exc)
            status = "failed"
            logger.warning(f"Qwen OCR 失败（image sha={sha[:8]}...）：{exc}")
        image = DocumentImage(
            document_id=document_id,
            image_path=object_name,
            thumbnail_path=thumb_object,
            image_type=inferred_type,
            file_size=len(data),
            width=width,
            height=height,
            sha256_hash=sha,
            ocr_text=ocr_text,
            status=status,
            error_message=error_message,
            retry_count=0,
            last_processed_at=datetime.utcnow()
        )
        self.db.add(image)
        self.db.commit()
        self.db.refresh(image)
        return image
    def create_or_get_image(self, document_id: int, image_path: str, image_type: Optional[str] = None) -> DocumentImage:
        sha = self.compute_sha256(image_path)
        _, ext = os.path.splitext(image_path)
        norm_ext = self._normalize_ext(ext if ext else ".png")
        info = self.get_image_info(image_path) or {}
        inferred_type = self._infer_image_type(norm_ext, explicit_type=image_type, info_format=info.get("format"))
        # 去重：已存在则直接返回
        existing = self.db.query(DocumentImage).filter(DocumentImage.sha256_hash == sha, DocumentImage.is_deleted == False).first()
        if existing:
            if not existing.image_type and inferred_type != "unknown":
                existing.image_type = inferred_type
                self.db.commit()
            return existing
        thumb = self.generate_thumbnail(image_path)
        size = os.path.getsize(image_path) if os.path.exists(image_path) else None
        image_data = {
            "document_id": document_id,
            "image_path": image_path,
            "thumbnail_path": thumb,
            "image_type": inferred_type,
            "file_size": size,
            "width": info.get("width"),
            "height": info.get("height"),
            "sha256_hash": sha,
            "status": "extracted"
        }
        return self.create(image_data)  # BaseService 同步 create
    
    # =============== 处理流水（供任务调用） ===============
    def process_image_sync(self, image_id: int) -> bool:
        image = self.db.query(DocumentImage).filter(
            DocumentImage.id == image_id,
            DocumentImage.is_deleted == False
        ).first()
        if not image:
            return False
        try:
            self._mark_status(image, "processing", retry_count=0, error=None)
            image_bytes = self._load_image_bytes(image.image_path)
            mime = self._detect_mime_from_path(image.image_path)
            
            # 验证图片有效性
            is_valid, validation_error = self._validate_image_bytes(image_bytes, mime)
            if not is_valid:
                logger.warning(f"图片 {image_id} 验证失败: {validation_error}, 跳过 OCR 处理")
                image.ocr_text = ""
                image.error_message = f"图片验证失败: {validation_error}"
                # 即使图片无效，也尝试生成向量（可能可以处理）
                try:
                    vector_service = VectorService(self.db)
                    image_vector = vector_service.generate_image_embedding_prefer_memory(image_bytes)
                    image.vector_model = settings.CLIP_MODEL_NAME
                    image.vector_dim = len(image_vector)
                    self.db.commit()
                    self._index_image_in_opensearch(image, image_vector)
                    self._mark_status(image, "completed", error=validation_error, retry_count=0)
                    return True
                except Exception as vec_exc:
                    logger.error(f"图片 {image_id} 向量生成失败: {vec_exc}")
                    self._mark_status(image, "failed", error=f"图片验证失败且向量生成失败: {validation_error}", retry_count=0)
                    return False
            
            # 图片有效，执行 OCR
            retries = max(0, settings.OCR_MAX_RETRIES)
            last_error: Optional[str] = None
            ocr_text = ""
            for attempt in range(retries + 1):
                try:
                    ocr_text = self._perform_qwen_ocr(image_bytes, mime)
                    image.retry_count = attempt
                    self.db.commit()
                    break
                except Exception as exc:
                    last_error = str(exc)
                    image.retry_count = attempt + 1
                    image.error_message = last_error
                    self.db.commit()
                    if attempt < retries and settings.OCR_RETRY_DELAY_SECONDS > 0:
                        time.sleep(settings.OCR_RETRY_DELAY_SECONDS)
            else:
                # OCR 失败，但图片有效，记录错误但继续处理向量
                logger.warning(f"图片 {image_id} OCR 失败: {last_error}, 继续处理向量")
                image.ocr_text = ""
            
            image.ocr_text = ocr_text
            vector_service = VectorService(self.db)
            image_vector = vector_service.generate_image_embedding_prefer_memory(image_bytes)
            image.vector_model = settings.CLIP_MODEL_NAME
            image.vector_dim = len(image_vector)
            self.db.commit()
            self._index_image_in_opensearch(image, image_vector)
            self._mark_status(image, "completed", error=None, retry_count=image.retry_count)
            return True
        except Exception as exc:
            logger.error(f"图片处理失败 image_id={image_id}: {exc}", exc_info=True)
            self._mark_status(image, "failed", error=str(exc), retry_count=image.retry_count)
            return False

    # =============== API 适配：异步包装 ===============
    async def get_images(self, skip: int = 0, limit: int = 24, document_id: Optional[int] = None) -> List[DocumentImage]:
        """获取图片列表（支持按文档过滤，分页）。
        为兼容路由中的 await，这里声明为 async，但内部为同步 ORM 调用。
        """
        query = self.db.query(DocumentImage).filter(DocumentImage.is_deleted == False)
        if document_id is not None:
            query = query.filter(DocumentImage.document_id == document_id)
        # 按创建时间倒序（BaseModel 通常含 created_at）
        try:
            from app.models.base import BaseModel as _BaseModel  # 仅用于类型上的 created_at 引用
            created_col = getattr(DocumentImage, 'created_at', None)
        except Exception:
            created_col = None
        if created_col is not None:
            query = query.order_by(created_col.desc())
        else:
            query = query.order_by(DocumentImage.id.desc())
        return query.offset(skip).limit(limit).all()

    async def get_image(self, image_id: int) -> Optional[DocumentImage]:
        """获取单张图片详情（异步包装）。"""
        return self.db.query(DocumentImage).filter(DocumentImage.id == image_id, DocumentImage.is_deleted == False).first()

    async def upload_image(self, file, document_id: int) -> DocumentImage:
        """上传图片文件并入库（支持 FastAPI UploadFile）。"""
        # 读取文件二进制
        if hasattr(file, 'read'):
            # UploadFile: 需要 await
            try:
                data = await file.read()  # type: ignore
            except TypeError:
                # 同步 file-like
                data = file.read()
        else:
            raise ValueError("无效的文件对象")

        # 推断扩展名
        filename = getattr(file, 'filename', None) or 'upload.png'
        _, ext = os.path.splitext(filename)
        ext = ext.lower() if ext else '.png'
        if ext not in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']:
            ext = '.png'

        image_type = ext.lstrip('.')

        return self.create_image_from_bytes(document_id=document_id, data=data, image_ext=ext, image_type=image_type)
