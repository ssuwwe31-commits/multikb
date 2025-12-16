"""
Image Search Service
根据文档处理流程设计实现图片搜索功能
"""

import os
import re
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.models.image import DocumentImage
from app.schemas.image import ImageSearchRequest, ImageSearchResponse
# 图片向量化使用ImageVectorizationService，不需要VectorService
from app.services.opensearch_service import OpenSearchService
from app.services.rerank_service import RerankService
from app.core.logging import logger
from app.config.settings import settings
from app.core.exceptions import CustomException, ErrorCode
from app.services.ollama_service import OllamaService

class ImageSearchService:
    """图片搜索服务 - 严格按照设计文档实现"""
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        # 使用ImageVectorizationService进行图片向量化（不需要db）
        from app.services.image_vectorization_service import ImageVectorizationService
        self.image_vectorizer = ImageVectorizationService()
        self.opensearch_service = OpenSearchService()
        # ✅ 新增：Rerank服务（用于以文搜图的精排）
        self.rerank_service = RerankService()
    
    async def search_by_image(
        self,
        file: UploadFile,
        similarity_threshold: float = settings.SEARCH_VECTOR_THRESHOLD,
        limit: int = settings.QA_DEFAULT_MAX_RESULTS,
        knowledge_base_id: Optional[List[int]] = None
    ) -> List[ImageSearchResponse]:
        """以图找图搜索 - 根据设计文档实现"""
        try:
            logger.info(f"开始以图找图搜索: {file.filename}")
            
            # 根据设计文档的以图找图流程：
            # 用户上传图片 → 图片验证 → 图片预处理 → 特征提取 → 向量生成 → 向量搜索 → 相似度计算 → 结果排序 → 结果过滤 → 结果返回
            
            # 1. 图片验证和预处理
            logger.info("步骤1: 图片验证和预处理")
            processed_image = await self._preprocess_image(file)
            
            # 2. 特征提取和向量生成
            logger.info("步骤2: 特征提取和向量生成")
            # 使用ImageVectorizationService生成图片向量（CLIP，512维）
            image_vector = self.image_vectorizer.generate_clip_embedding(processed_image["path"])
            
            if not image_vector:
                logger.error("图片向量生成失败")
                raise CustomException(
                    code=ErrorCode.VECTOR_GENERATION_FAILED,
                    message="图片向量生成失败"
                )
            
            # 3. 向量搜索
            logger.info("步骤3: 向量搜索")
            search_results = await self.opensearch_service.search_image_vectors(
                query_vector=image_vector,
                similarity_threshold=similarity_threshold,
                limit=limit,
                knowledge_base_id=knowledge_base_id
            )
            
            # 4. 结果处理和排序
            logger.info("步骤4: 结果处理和排序")
            results = []
            for result in search_results:
                # 处理 image_type：如果为 None，使用默认值 "unknown"
                image_type = result.get("image_type") or "unknown"
                if not isinstance(image_type, str):
                    image_type = str(image_type) if image_type is not None else "unknown"
                
                # 处理 source_document：转换为字符串
                source_doc = result.get("source_document", "")
                if source_doc is None:
                    source_doc = ""
                elif isinstance(source_doc, int):
                    # 如果是 document_id，转换为字符串
                    source_doc = str(source_doc)
                elif not isinstance(source_doc, str):
                    source_doc = str(source_doc)
                
                # 处理图片路径：转换为代理 URL
                image_path = result["image_path"]
                if image_path and not (image_path.startswith('http://') or image_path.startswith('https://') or image_path.startswith('/api/images/file')):
                    from urllib.parse import quote
                    image_path = f"/api/images/file?object={quote(image_path, safe='')}"
                
                image_response = ImageSearchResponse(
                    image_id=result["image_id"],
                    document_id=result["document_id"],
                    knowledge_base_id=result["knowledge_base_id"],
                    image_path=image_path,
                    similarity_score=result["similarity_score"],
                    image_type=image_type,
                    page_number=result.get("page_number"),
                    coordinates=result.get("coordinates"),
                    ocr_text=result.get("ocr_text") or "",
                    description=result.get("description") or "",
                    source_document=source_doc
                )
                results.append(image_response)
            
            # 按相似度排序
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            
            logger.info(f"以图找图搜索完成，找到 {len(results)} 个结果")
            return results
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"以图找图搜索错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.SEARCH_FAILED,
                message=f"以图找图搜索失败: {str(e)}"
            )
    
    async def search_by_text(
        self,
        search_request: ImageSearchRequest
    ) -> List[ImageSearchResponse]:
        """以文找图搜索 - 使用CLIP文本编码器"""
        try:
            # 记录前端传入的所有参数
            logger.info(
                f"[以文搜图] 开始搜索，前端参数: "
                f"query_text='{search_request.query_text}', "
                f"similarity_threshold={search_request.similarity_threshold}, "
                f"limit={search_request.limit}, "
                f"knowledge_base_id={search_request.knowledge_base_id}"
            )
            
            # 1. 文本处理和意图识别
            logger.info("[以文搜图] 步骤1: 文本处理和意图识别")
            processed_text = await self._process_search_text(search_request.query_text)
            logger.info(f"[以文搜图] 文本处理完成: 原始='{search_request.query_text}', 处理后='{processed_text}'")
            
            # 2. 使用CLIP文本编码器生成512维向量（替代Ollama）
            logger.info("[以文搜图] 步骤2: CLIP文本向量化（512维）")
            from app.services.image_vectorization_service import ImageVectorizationService
            
            text_vector = None
            try:
                image_vectorizer = ImageVectorizationService()
                text_vector = image_vectorizer.generate_clip_text_embedding(processed_text)
                
                if not text_vector or len(text_vector) != 512:
                    logger.error(f"[以文搜图] CLIP文本向量生成失败或维度不正确: 维度={len(text_vector) if text_vector else 0}, 期望=512")
                    text_vector = None  # 标记为失败，将降级到关键词搜索
                else:
                    logger.info(f"[以文搜图] CLIP文本向量生成成功: 维度={len(text_vector)}, 前5个值={text_vector[:5] if text_vector else []}")
            except Exception as e:
                logger.warning(f"[以文搜图] CLIP文本向量生成失败，将降级到关键词搜索: {e}", exc_info=True)
                text_vector = None  # 降级到关键词搜索
            
            # 3. 多路搜索（向量搜索 + 关键词搜索）
            logger.info("[以文搜图] 步骤3: 多路搜索（向量搜索 + 关键词搜索）")
            
            vector_results = []
            keyword_results = []
            
            # 向量搜索：使用512维向量搜索512维的image_vector字段
            # 召回更多候选（limit * 3），以便后续融合和rerank有足够候选
            search_limit = (search_request.limit or settings.QA_DEFAULT_MAX_RESULTS) * 3
            similarity_threshold = search_request.similarity_threshold or settings.SEARCH_VECTOR_THRESHOLD
            
            logger.info(
                f"[以文搜图] 向量搜索参数: "
                f"similarity_threshold={similarity_threshold}, "
                f"search_limit={search_limit}, "
                f"knowledge_base_id={search_request.knowledge_base_id}"
            )
            
            if text_vector:
                try:
                    vector_results = await self.opensearch_service.search_image_vectors(
                        query_vector=text_vector,  # 512维
                        similarity_threshold=similarity_threshold,
                        limit=search_limit,  # 召回更多候选
                        knowledge_base_id=search_request.knowledge_base_id
                    )
                    logger.info(f"[以文搜图] 向量搜索完成: 找到 {len(vector_results)} 个结果")
                    if vector_results:
                        logger.info(
                            f"[以文搜图] 向量搜索结果分数范围: "
                            f"最高={max(r.get('similarity_score', 0) for r in vector_results):.4f}, "
                            f"最低={min(r.get('similarity_score', 0) for r in vector_results):.4f}, "
                            f"平均={sum(r.get('similarity_score', 0) for r in vector_results) / len(vector_results):.4f}"
                        )
                except Exception as e:
                    logger.warning(f"[以文搜图] 向量搜索失败: {e}", exc_info=True)
                    vector_results = []
            else:
                logger.info("[以文搜图] CLIP向量生成失败，跳过向量搜索")
            
            # 关键词搜索（作为补充，用于有OCR文本的图片）
            logger.info(
                f"[以文搜图] 关键词搜索参数: "
                f"query_text='{processed_text}', "
                f"search_limit={search_limit}, "
                f"knowledge_base_id={search_request.knowledge_base_id}"
            )
            try:
                keyword_results = await self.opensearch_service.search_image_keywords(
                    query_text=processed_text,
                    limit=search_limit,  # 召回更多候选
                    knowledge_base_id=search_request.knowledge_base_id
                )
                logger.info(f"[以文搜图] 关键词搜索完成: 找到 {len(keyword_results)} 个结果")
                if keyword_results:
                    logger.info(
                        f"[以文搜图] 关键词搜索结果分数范围: "
                        f"最高={max(r.get('keyword_score', 0) for r in keyword_results):.4f}, "
                        f"最低={min(r.get('keyword_score', 0) for r in keyword_results):.4f}, "
                        f"平均={sum(r.get('keyword_score', 0) for r in keyword_results) / len(keyword_results):.4f}"
                    )
            except Exception as e:
                logger.warning(f"[以文搜图] 关键词搜索失败: {e}", exc_info=True)
                keyword_results = []
            
            # 如果两种搜索都失败，返回空结果
            if not vector_results and not keyword_results:
                logger.warning("[以文搜图] 向量搜索和关键词搜索都失败，返回空结果")
                return []
            
            # 4. 结果融合和相关性评分
            logger.info("[以文搜图] 步骤4: 结果融合和相关性评分")
            merged_results = await self._merge_search_results(
                vector_results, keyword_results, processed_text
            )
            logger.info(
                f"[以文搜图] 结果融合完成: 融合后 {len(merged_results)} 个结果, "
                f"向量结果={len(vector_results)}, 关键词结果={len(keyword_results)}"
            )
            if merged_results:
                logger.info(
                    f"[以文搜图] 融合后分数范围: "
                    f"最高={max(r.get('relevance_score', 0) for r in merged_results):.4f}, "
                    f"最低={min(r.get('relevance_score', 0) for r in merged_results):.4f}, "
                    f"平均={sum(r.get('relevance_score', 0) for r in merged_results) / len(merged_results):.4f}"
                )
            
            # 5. ✅ Rerank精排（使用rerank模型对融合后的结果重新排序）
            logger.info("[以文搜图] 步骤5: Rerank精排")
            # 为rerank准备候选数据（构建content字段：OCR文本 + 描述）
            rerank_candidates = []
            for result in merged_results:
                # 构建用于rerank的content：OCR文本 + 描述
                ocr_text = result.get("ocr_text", "")
                description = result.get("description", "")
                content_parts = []
                if ocr_text:
                    content_parts.append(f"[OCR文本]: {ocr_text}")
                if description:
                    content_parts.append(f"[图片描述]: {description}")
                # 如果都没有，使用默认描述
                content = " ".join(content_parts) if content_parts else "图片"
                
                rerank_candidates.append({
                    "image_id": result["image_id"],
                    "document_id": result["document_id"],
                    "knowledge_base_id": result["knowledge_base_id"],
                    "image_path": result["image_path"],
                    "image_type": result.get("image_type", "unknown"),
                    "page_number": result.get("page_number"),
                    "coordinates": result.get("coordinates"),
                    "ocr_text": result.get("ocr_text", ""),
                    "description": result.get("description", ""),
                    "source_document": result.get("source_document", ""),
                    "relevance_score": result["relevance_score"],  # 原始分数
                    "content": content,  # 用于rerank的文本内容
                    "score": result["relevance_score"]  # rerank需要的score字段
                })
            
            # 使用rerank模型重新排序
            top_k = search_request.limit if search_request.limit > 0 else settings.RERANK_TOP_K
            rerank_top_k = top_k * 2  # 召回更多候选，后续会按阈值过滤
            
            logger.info(
                f"[以文搜图] Rerank参数: "
                f"query='{processed_text}', "
                f"候选数量={len(rerank_candidates)}, "
                f"top_k={rerank_top_k}, "
                f"RERANK_TOP_K={settings.RERANK_TOP_K}"
            )
            
            reranked_results = self.rerank_service.rerank(
                query=processed_text,
                candidates=rerank_candidates,
                top_k=rerank_top_k  # 召回更多候选，后续会按阈值过滤
            )
            
            logger.info(
                f"[以文搜图] Rerank精排完成: "
                f"输入候选={len(rerank_candidates)}, "
                f"精排后数量={len(reranked_results)}"
            )
            if reranked_results:
                logger.info(
                    f"[以文搜图] Rerank后分数范围: "
                    f"最高={max(r.get('rerank_score', r.get('relevance_score', 0)) for r in reranked_results):.4f}, "
                    f"最低={min(r.get('rerank_score', r.get('relevance_score', 0)) for r in reranked_results):.4f}, "
                    f"平均={sum(r.get('rerank_score', r.get('relevance_score', 0)) for r in reranked_results) / len(reranked_results):.4f}"
                )
            
            # 6. 结果过滤和转换
            logger.info("[以文搜图] 步骤6: 结果过滤和转换")
            results = []
            # 向量召回阶段使用 similarity_threshold；
            # Rerank 阶段使用单独的最小精排分（与文本检索一致），默认 settings.RERANK_MIN_SCORE
            try:
                min_rerank_score = float(getattr(settings, 'RERANK_MIN_SCORE', 0.2))
            except Exception:
                min_rerank_score = 0.2
            
            logger.info(
                f"[以文搜图] 结果过滤参数: "
                f"min_rerank_score={min_rerank_score}, "
                f"RERANK_MIN_SCORE={settings.RERANK_MIN_SCORE}"
            )
            
            filtered_by_rerank_score = 0
            for result in reranked_results:
                # 使用rerank_score作为最终分数（如果存在），否则使用原始relevance_score
                final_score = result.get("rerank_score") or result.get("relevance_score", 0.0)
                
                # 按最小精排分过滤（不要使用 similarity_threshold 以免误伤关键词候选）
                if final_score >= min_rerank_score:
                    # 处理 image_type：如果为 None，使用默认值 "unknown"
                    image_type = result.get("image_type") or "unknown"
                    if not isinstance(image_type, str):
                        image_type = str(image_type) if image_type is not None else "unknown"
                    
                    # 处理 source_document：转换为字符串
                    source_doc = result.get("source_document", "")
                    if source_doc is None:
                        source_doc = ""
                    elif isinstance(source_doc, int):
                        # 如果是 document_id，转换为字符串
                        source_doc = str(source_doc)
                    elif not isinstance(source_doc, str):
                        source_doc = str(source_doc)
                    
                    # 处理图片路径：转换为代理 URL
                    image_path = result.get("image_path", "")
                    if image_path and not (image_path.startswith('http://') or image_path.startswith('https://') or image_path.startswith('/api/images/file')):
                        from urllib.parse import quote
                        image_path = f"/api/images/file?object={quote(image_path, safe='')}"
                    
                    image_response = ImageSearchResponse(
                        image_id=result["image_id"],
                        document_id=result["document_id"],
                        knowledge_base_id=result["knowledge_base_id"],
                        image_path=image_path,
                        similarity_score=final_score,  # 使用rerank分数
                        image_type=image_type,
                        page_number=result.get("page_number"),
                        coordinates=result.get("coordinates"),
                        ocr_text=result.get("ocr_text") or "",
                        description=result.get("description") or "",
                        source_document=source_doc
                    )
                    results.append(image_response)
                else:
                    filtered_by_rerank_score += 1
            
            # 限制返回数量（不超过 limit）
            original_limit = search_request.limit or settings.QA_DEFAULT_MAX_RESULTS
            if original_limit and len(results) > original_limit:
                logger.info(f"[以文搜图] 结果数量超过limit，截断: {len(results)} -> {original_limit}")
                results = results[:original_limit]
            
            # 按最终分数排序（rerank已经排序，但这里再次确保）
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            
            logger.info(
                f"[以文搜图] 搜索完成: "
                f"Rerank后候选={len(reranked_results)}, "
                f"最小精排分过滤（>={min_rerank_score}）过滤掉={filtered_by_rerank_score}, "
                f"最终返回={len(results)}, "
                f"limit={original_limit}"
            )
            if results:
                logger.info(
                    f"[以文搜图] 最终结果分数范围: "
                    f"最高={max(r.similarity_score for r in results):.4f}, "
                    f"最低={min(r.similarity_score for r in results):.4f}, "
                    f"平均={sum(r.similarity_score for r in results) / len(results):.4f}"
                )
            return results
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"[以文搜图] 搜索错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.SEARCH_FAILED,
                message=f"以文找图搜索失败: {str(e)}"
            )
    
    async def get_similar_images(
        self,
        image_id: int,
        similarity_threshold: float = settings.SEARCH_VECTOR_THRESHOLD,
        limit: int = settings.QA_DEFAULT_MAX_RESULTS,
        knowledge_base_id: Optional[int] = None
    ) -> List[ImageSearchResponse]:
        """获取相似图片 - 根据设计文档实现"""
        try:
            logger.info(f"开始获取相似图片: {image_id}")
            
            # 1. 获取图片信息（需要db）
            if not self.db:
                raise CustomException(
                    code=ErrorCode.IMAGE_NOT_FOUND,
                    message="数据库连接不可用"
                )
            image = self.db.query(DocumentImage).filter(DocumentImage.id == image_id).first()
            if not image:
                raise CustomException(
                    code=ErrorCode.IMAGE_NOT_FOUND,
                    message=f"图片 {image_id} 不存在"
                )
            
            # 2. 获取图片向量
            image_vector = await self.opensearch_service.get_image_vector(image_id)
            if not image_vector:
                logger.error(f"图片 {image_id} 的向量不存在")
                raise CustomException(
                    code=ErrorCode.VECTOR_NOT_FOUND,
                    message=f"图片 {image_id} 的向量不存在"
                )
            
            # 3. 搜索相似图片
            search_results = await self.opensearch_service.search_image_vectors(
                query_vector=image_vector,
                similarity_threshold=similarity_threshold,
                limit=limit + 1,  # +1 因为会包含自己
                knowledge_base_id=knowledge_base_id,
                exclude_image_id=image_id  # 排除自己
            )
            
            # 4. 构建结果
            results = []
            for result in search_results:
                image_response = ImageSearchResponse(
                    image_id=result["image_id"],
                    document_id=result["document_id"],
                    knowledge_base_id=result["knowledge_base_id"],
                    image_path=result["image_path"],
                    similarity_score=result["similarity_score"],
                    image_type=result.get("image_type", "unknown"),
                    page_number=result.get("page_number"),
                    coordinates=result.get("coordinates"),
                    ocr_text=result.get("ocr_text", ""),
                    description=result.get("description", ""),
                    source_document=result.get("source_document", "")
                )
                results.append(image_response)
            
            logger.info(f"获取相似图片完成，找到 {len(results)} 个相似图片")
            return results
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"获取相似图片错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.SEARCH_FAILED,
                message=f"获取相似图片失败: {str(e)}"
            )
    
    async def extract_ocr_text(self, file: UploadFile) -> str:
        """提取OCR文字 - 根据设计文档实现"""
        try:
            logger.info(f"开始OCR文字识别: {file.filename}")
            content = await file.read()
            if not content:
                return ""
            mime = file.content_type or "image/png"
            ollama = OllamaService(self.db)
            text = ollama.extract_text_from_image(content, image_mime=mime)
            logger.info(f"OCR文字识别完成: {file.filename}, 长度: {len(text)}")
            return text
        except Exception as e:
            logger.error(f"OCR文字识别错误: {e}", exc_info=True)
            return ""
    
    async def get_image_vectors(self, image_id: int) -> Dict[str, Any]:
        """获取图片向量信息 - 根据设计文档实现"""
        try:
            logger.info(f"开始获取图片向量信息: {image_id}")
            
            # 1. 获取图片基本信息
            image = self.db.query(DocumentImage).filter(DocumentImage.id == image_id).first()
            if not image:
                raise CustomException(
                    code=ErrorCode.IMAGE_NOT_FOUND,
                    message=f"图片 {image_id} 不存在"
                )
            
            # 2. 获取向量信息
            vector_info = await self.opensearch_service.get_image_vector_info(image_id)
            
            result = {
                "image_id": image_id,
                "document_id": image.document_id,
                "image_path": image.image_path,
                "image_type": image.image_type,
                "vector_dimension": vector_info.get("dimension", settings.IMAGE_EMBEDDING_DIMENSION),
                "vector_model": vector_info.get("model", "CLIP"),
                "vector_version": vector_info.get("version", "1.0"),
                "created_at": vector_info.get("created_at"),
                "updated_at": vector_info.get("updated_at")
            }
            
            logger.info(f"获取图片向量信息完成: {image_id}")
            return result
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"获取图片向量信息错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.SEARCH_FAILED,
                message=f"获取图片向量信息失败: {str(e)}"
            )
    
    async def _preprocess_image(self, file: UploadFile) -> Dict[str, Any]:
        """图片预处理 - 保存到临时文件，不进行尺寸调整
        
        重要：尺寸调整由 CLIP 的 transform 统一处理（与索引时一致），
        确保搜索和索引使用相同的预处理流程，避免向量不匹配问题。
        """
        try:
            logger.info(f"开始图片预处理: {file.filename}")
            
            import tempfile
            import shutil
            from PIL import Image
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_path = temp_file.name
            
            # 保存上传的图片到临时文件
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # 只做基本格式检查和转换，不进行尺寸调整
            # 尺寸调整由 ImageVectorizationService.generate_clip_embedding 内部的 CLIP transform 统一处理
            with Image.open(temp_path) as img:
                # 转换为RGB格式（CLIP要求RGB格式）
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    # 保存转换后的格式
                    img.save(temp_path, 'JPEG', quality=95)
                
                original_width = img.width
                original_height = img.height
                
                result = {
                    "path": temp_path,
                    "format": "JPEG",
                    "width": original_width,
                    "height": original_height,
                    "quality": 95,
                    "file_size": os.path.getsize(temp_path)
                }
            
            logger.info(
                f"图片预处理完成: {file.filename}, "
                f"原始尺寸: {result['width']}x{result['height']}, "
                f"尺寸调整将由CLIP transform统一处理（224x224）"
            )
            return result
            
        except Exception as e:
            logger.error(f"图片预处理错误: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.IMAGE_PROCESSING_FAILED,
                message=f"图片预处理失败: {str(e)}"
            )
    
    async def _process_search_text(self, text: str) -> str:
        """文本处理 - 根据设计文档实现
        
        处理流程：
        1. 文本清洗（去除特殊字符、空白）
        2. 文本长度检查（CLIP限制为77个token）
        3. 文本截断（如果超过限制）
        """
        try:
            logger.info(f"开始文本处理: {text[:50]}...")
            
            # 1. 文本清洗
            processed_text = text.strip()
            
            # 移除多余空白
            processed_text = re.sub(r'\s+', ' ', processed_text)
            
            # 2. CLIP文本编码器限制：77个token
            # 注意：
            # - Token不是字符，一个字符可能对应多个token（特别是中文）
            # - open_clip.tokenize()会自动截断超过77 token的文本，不会报错
            # - 我们使用100字符限制作为保守估计，提供用户友好的警告
            # - 实际token数量可能少于字符数量（取决于tokenizer的分词方式）
            MAX_LENGTH = 100  # 保守估计，避免超过77 token
            
            if len(processed_text) > MAX_LENGTH:
                logger.warning(
                    f"查询文本过长 ({len(processed_text)} 字符)，截断到 {MAX_LENGTH} 字符。"
                    f"注意：CLIP文本编码器限制为77个token，open_clip.tokenize()会自动处理超过限制的文本。"
                )
                processed_text = processed_text[:MAX_LENGTH].rstrip()
            
            # 转换为小写（英文搜索优化）
            processed_text = processed_text.lower()
            
            # 3. 验证文本不为空
            if not processed_text:
                logger.warning("处理后的文本为空，使用原始文本")
                processed_text = text.strip()
            
            logger.info(f"文本处理完成: {processed_text[:50]}... (长度: {len(processed_text)})")
            return processed_text
            
        except Exception as e:
            logger.error(f"文本处理错误: {e}", exc_info=True)
            # 降级：返回原始文本（去除首尾空白）
            return text.strip() if text else ""
    
    async def _merge_search_results(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        query_text: str
    ) -> List[Dict[str, Any]]:
        """结果融合 - 根据设计文档实现
        
        融合策略：
        1. 向量搜索结果优先（CLIP语义理解，更准确）
        2. 关键词搜索结果作为补充（精确匹配OCR文本）
        3. 权重计算：向量搜索权重0.7，关键词搜索权重0.3
        4. 去重处理：相同图片ID的结果合并，取最高分
        """
        try:
            logger.info("开始结果融合")
            
            # 构建结果字典，key为image_id，value为结果信息
            results_dict = {}
            
            # 1. 添加向量搜索结果（权重0.7）
            VECTOR_WEIGHT = 0.7
            for result in vector_results:
                image_id = result["image_id"]
                if image_id not in results_dict:
                    results_dict[image_id] = {
                        "image_id": image_id,
                        "document_id": result["document_id"],
                        "knowledge_base_id": result["knowledge_base_id"],
                        "image_path": result["image_path"],
                        "image_type": result.get("image_type", "unknown"),
                        "page_number": result.get("page_number"),
                        "coordinates": result.get("coordinates"),
                        "ocr_text": result.get("ocr_text", ""),
                        "description": result.get("description", ""),
                        "source_document": result.get("source_document", ""),
                        "vector_score": result.get("similarity_score", 0.0),
                        "keyword_score": 0.0,
                        "relevance_score": 0.0,
                        "search_types": []
                    }
                # 更新向量分数
                results_dict[image_id]["vector_score"] = max(
                    results_dict[image_id]["vector_score"],
                    result.get("similarity_score", 0.0)
                )
                results_dict[image_id]["search_types"].append("vector")
            
            # 2. 添加关键词搜索结果（权重0.3）
            KEYWORD_WEIGHT = 0.3
            for result in keyword_results:
                image_id = result["image_id"]
                keyword_score = result.get("keyword_score", 0.0)
                
                if image_id not in results_dict:
                    # 新建结果
                    results_dict[image_id] = {
                        "image_id": image_id,
                        "document_id": result["document_id"],
                        "knowledge_base_id": result["knowledge_base_id"],
                        "image_path": result["image_path"],
                        "image_type": result.get("image_type", "unknown"),
                        "page_number": result.get("page_number"),
                        "coordinates": result.get("coordinates"),
                        "ocr_text": result.get("ocr_text", ""),
                        "description": result.get("description", ""),
                        "source_document": result.get("source_document", ""),
                        "vector_score": 0.0,
                        "keyword_score": keyword_score,
                        "relevance_score": 0.0,
                        "search_types": []
                    }
                else:
                    # 更新关键词分数（取最高分）
                    results_dict[image_id]["keyword_score"] = max(
                        results_dict[image_id]["keyword_score"],
                        keyword_score
                    )
                results_dict[image_id]["search_types"].append("keyword")
            
            # 3. 计算综合相关性分数
            # 如果只有向量搜索，使用向量分数
            # 如果只有关键词搜索，使用关键词分数
            # 如果两者都有，使用加权平均
            merged_results = []
            for image_id, result in results_dict.items():
                vector_score = result["vector_score"]
                keyword_score = result["keyword_score"]
                
                if vector_score > 0 and keyword_score > 0:
                    # 两者都有：加权平均
                    result["relevance_score"] = (
                        vector_score * VECTOR_WEIGHT + 
                        keyword_score * KEYWORD_WEIGHT
                    )
                elif vector_score > 0:
                    # 只有向量搜索
                    result["relevance_score"] = vector_score
                elif keyword_score > 0:
                    # 只有关键词搜索
                    result["relevance_score"] = keyword_score
                else:
                    # 都不应该有，但为了安全
                    result["relevance_score"] = 0.0
                
                merged_results.append(result)
            
            # 4. 按相关性分数排序
            merged_results.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            logger.info(f"结果融合完成，合并后 {len(merged_results)} 个结果")
            return merged_results
            
        except Exception as e:
            logger.error(f"结果融合错误: {e}", exc_info=True)
            # 降级：返回向量搜索结果（如果存在）
            if vector_results:
                return vector_results
            # 否则返回关键词搜索结果
            return keyword_results
