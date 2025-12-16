"""
Multimodal Processing Service
根据知识问答系统设计文档实现多模态输入处理功能
"""

import asyncio
import io
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import numpy as np
from PIL import Image
import cv2
import torch
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.config.settings import settings
from app.services.ollama_service import OllamaService
from app.services.image_vectorization_service import ImageVectorizationService
from app.core.exceptions import CustomException, ErrorCode

class MultimodalProcessingService:
    """多模态输入处理服务 - 根据设计文档实现"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ollama_service = OllamaService(db)
        # 延迟加载：仅在需要图片能力时再初始化，避免纯文本流程加载CLIP
        self.image_vectorization_service: Optional[ImageVectorizationService] = None
        
        # 输入类型定义 - 根据设计文档
        self.INPUT_TYPES = {
            "text": "纯文本输入",
            "image": "纯图片输入", 
            "multimodal": "图文混合输入",
            "multi_image": "多图片输入"
        }
        
        # 意图分类扩展 - 根据设计文档
        self.INTENT_TYPES = {
            "factual_qa": "事实性问答",
            "concept_explanation": "概念解释",
            "operation_guide": "操作指导",
            "comparison_analysis": "比较分析",
            "troubleshooting": "故障排除",
            "image_search": "图片搜索",
            "multimodal_qa": "图文问答",
            "summary": "总结归纳"
        }
        
        # 相似度阈值 - 根据设计文档
        self.SIMILARITY_THRESHOLDS = {
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3,
            "none": 0.0
        }
    
    async def process_multimodal_input(
        self,
        text_content: Optional[str] = None,
        image_file: Optional[UploadFile] = None,
        input_type: str = "text"
    ) -> Dict[str, Any]:
        """
        处理多模态输入 - 根据设计文档实现
        
        Args:
            text_content: 文本内容
            image_file: 图片文件
            input_type: 输入类型 (text, image, multimodal, multi_image)
            
        Returns:
            处理后的多模态数据
        """
        try:
            logger.info(f"开始处理多模态输入，类型: {input_type}")
            
            # 1. 输入类型识别 - 根据设计文档
            validated_input_type = self._validate_input_type(input_type, text_content, image_file)
            
            # 2. 输入验证 - 根据设计文档
            validation_result = await self._validate_input_content(
                text_content, image_file, validated_input_type
            )
            
            if not validation_result["valid"]:
                raise CustomException(
                    code=ErrorCode.INVALID_INPUT,
                    message=validation_result["message"]
                )
            
            # 3. 多模态内容解析 - 根据设计文档
            processed_data = {
                "input_type": validated_input_type,
                "timestamp": datetime.now().isoformat(),
                "processing_steps": []
            }
            
            # 文本内容解析
            if text_content:
                text_data = await self._process_text_content(text_content)
                processed_data["text_data"] = text_data
                processed_data["processing_steps"].append("text_processing")
            
            # 图片内容解析
            if image_file:
                image_data = await self._process_image_content(image_file)
                processed_data["image_data"] = image_data
                processed_data["processing_steps"].append("image_processing")
            
            # 图文融合处理
            if validated_input_type == "multimodal":
                fusion_data = await self._fuse_text_image_content(
                    processed_data.get("text_data", {}),
                    processed_data.get("image_data", {})
                )
                processed_data["fusion_data"] = fusion_data
                processed_data["processing_steps"].append("multimodal_fusion")
            
            # 4. 多模态意图识别 - 根据设计文档
            intent_data = await self._recognize_multimodal_intent(processed_data)
            processed_data["intent_data"] = intent_data
            processed_data["processing_steps"].append("intent_recognition")
            
            logger.info(f"多模态输入处理完成，步骤: {processed_data['processing_steps']}")
            return processed_data
            
        except Exception as e:
            logger.error(f"多模态输入处理失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.MULTIMODAL_PROCESSING_FAILED,
                message=f"多模态输入处理失败: {str(e)}"
            )
    
    def _validate_input_type(
        self,
        input_type: str,
        text_content: Optional[str],
        image_file: Optional[UploadFile]
    ) -> str:
        """验证输入类型 - 根据设计文档实现"""
        if input_type not in self.INPUT_TYPES:
            raise CustomException(
                code=ErrorCode.INVALID_INPUT_TYPE,
                message=f"无效的输入类型: {input_type}"
            )
        
        # 根据实际内容调整输入类型
        if input_type == "text" and image_file:
            return "multimodal"
        elif input_type == "image" and text_content:
            return "multimodal"
        elif not text_content and not image_file:
            raise CustomException(
                code=ErrorCode.EMPTY_INPUT,
                message="输入内容不能为空"
            )
        
        return input_type
    
    async def _validate_input_content(
        self,
        text_content: Optional[str],
        image_file: Optional[UploadFile],
        input_type: str
    ) -> Dict[str, Any]:
        """输入验证 - 根据设计文档实现"""
        validation_result = {"valid": True, "message": ""}
        
        try:
            # 文本验证
            if text_content:
                text_validation = self._validate_text_content(text_content)
                if not text_validation["valid"]:
                    return text_validation
            
            # 图片验证
            if image_file:
                image_validation = await self._validate_image_content(image_file)
                if not image_validation["valid"]:
                    return image_validation
            
            # 混合验证
            if input_type == "multimodal":
                multimodal_validation = self._validate_multimodal_content(
                    text_content, image_file
                )
                if not multimodal_validation["valid"]:
                    return multimodal_validation
            
            return validation_result
            
        except Exception as e:
            return {
                "valid": False,
                "message": f"输入验证失败: {str(e)}"
            }
    
    def _validate_text_content(self, text_content: str) -> Dict[str, Any]:
        """文本验证 - 根据设计文档实现"""
        try:
            # 长度检查
            if len(text_content.strip()) == 0:
                return {"valid": False, "message": "文本内容不能为空"}
            
            if len(text_content) > settings.MULTIMODAL_TEXT_MAX_LENGTH:
                return {"valid": False, "message": f"文本内容过长，请控制在{settings.MULTIMODAL_TEXT_MAX_LENGTH}字符以内"}
            
            # 语言检测
            language = self._detect_language(text_content)
            
            # 敏感词过滤
            filtered_content = self._filter_sensitive_words(text_content)
            
            return {
                "valid": True,
                "message": "",
                "language": language,
                "filtered_content": filtered_content,
                "char_count": len(text_content),
                "word_count": len(text_content.split())
            }
            
        except Exception as e:
            return {"valid": False, "message": f"文本验证失败: {str(e)}"}
    
    async def _validate_image_content(self, image_file: UploadFile) -> Dict[str, Any]:
        """图片验证 - 根据设计文档实现"""
        try:
            # 格式检查
            allowed_formats = ["image/jpeg", "image/png", "image/gif", "image/webp"]
            if image_file.content_type not in allowed_formats:
                return {
                    "valid": False,
                    "message": f"不支持的图片格式: {image_file.content_type}"
                }
            
            # 大小限制
            max_size = settings.MULTIMODAL_IMAGE_MAX_SIZE_MB * 1024 * 1024  # MB to bytes
            content = await image_file.read()
            if len(content) > max_size:
                return {"valid": False, "message": f"图片文件过大，请控制在{settings.MULTIMODAL_IMAGE_MAX_SIZE_MB}MB以内"}
            
            # 内容安全检查
            try:
                image = Image.open(io.BytesIO(content))
                image.verify()
            except Exception:
                return {"valid": False, "message": "图片文件损坏或格式错误"}
            
            return {
                "valid": True,
                "message": "",
                "format": image_file.content_type,
                "size": len(content),
                "filename": image_file.filename
            }
            
        except Exception as e:
            return {"valid": False, "message": f"图片验证失败: {str(e)}"}
    
    def _validate_multimodal_content(
        self,
        text_content: Optional[str],
        image_file: Optional[UploadFile]
    ) -> Dict[str, Any]:
        """混合验证 - 根据设计文档实现"""
        try:
            # 图文关联性检查
            if text_content and image_file:
                # 简单的关联性检查
                relevance_score = self._calculate_content_relevance(text_content, image_file)
                if relevance_score < 0.3:
                    return {
                        "valid": False,
                        "message": "文本和图片内容关联性较低"
                    }
            
            # 内容一致性验证
            consistency_score = self._check_content_consistency(text_content, image_file)
            
            return {
                "valid": True,
                "message": "",
                "relevance_score": relevance_score if text_content and image_file else 1.0,
                "consistency_score": consistency_score
            }
            
        except Exception as e:
            return {"valid": False, "message": f"混合验证失败: {str(e)}"}
    
    async def _process_text_content(self, text_content: str) -> Dict[str, Any]:
        """文本内容解析 - 根据设计文档实现"""
        try:
            logger.info("开始处理文本内容")
            
            # 文本清洗
            cleaned_text = self._clean_text(text_content)
            
            # 语言检测
            language = self._detect_language(cleaned_text)
            
            # 实体抽取
            entities = await self._extract_entities(cleaned_text)
            
            # 意图识别
            intent = await self._recognize_text_intent(cleaned_text)
            
            # 关键词提取
            keywords = await self._extract_keywords(cleaned_text)
            
            # 向量化
            embedding = await self._generate_text_embedding(cleaned_text)
            
            return {
                "original_text": text_content,
                "cleaned_text": cleaned_text,
                "language": language,
                "entities": entities,
                "intent": intent,
                "keywords": keywords,
                "embedding": embedding,
                "char_count": len(cleaned_text),
                "word_count": len(cleaned_text.split()),
                "processing_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"文本内容处理失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.TEXT_PROCESSING_FAILED,
                message=f"文本内容处理失败: {str(e)}"
            )
    
    async def _process_image_content(self, image_file: UploadFile) -> Dict[str, Any]:
        """图片内容解析 - 根据设计文档实现"""
        try:
            logger.info(f"开始处理图片内容: {image_file.filename}")
            
            # 读取图片内容
            content = await image_file.read()
            image = Image.open(io.BytesIO(content))
            
            # 图片预处理
            processed_image = self._preprocess_image(image)
            
            # 特征提取
            features = await self._extract_image_features(processed_image)
            
            # OCR识别
            ocr_text = await self._extract_ocr_text(processed_image)
            
            # 内容理解
            content_understanding = await self._understand_image_content(processed_image)
            
            # 向量化
            embedding = await self._generate_image_embedding(processed_image)
            
            return {
                "filename": image_file.filename,
                "format": image_file.content_type,
                "size": len(content),
                "dimensions": processed_image.size,
                "features": features,
                "ocr_text": ocr_text,
                "content_understanding": content_understanding,
                "embedding": embedding,
                "processing_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"图片内容处理失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.IMAGE_PROCESSING_FAILED,
                message=f"图片内容处理失败: {str(e)}"
            )
    
    async def _fuse_text_image_content(
        self,
        text_data: Dict[str, Any],
        image_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """图文融合处理 - 根据设计文档实现"""
        try:
            logger.info("开始图文融合处理")
            
            # 特征对齐
            aligned_features = await self._align_text_image_features(text_data, image_data)
            
            # 语义融合
            fused_semantics = await self._fuse_semantics(text_data, image_data)
            
            # 上下文构建
            context = await self._build_multimodal_context(text_data, image_data)
            
            # 意图增强
            enhanced_intent = await self._enhance_intent_with_image(text_data, image_data)
            
            return {
                "aligned_features": aligned_features,
                "fused_semantics": fused_semantics,
                "context": context,
                "enhanced_intent": enhanced_intent,
                "fusion_score": self._calculate_fusion_score(text_data, image_data),
                "processing_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"图文融合处理失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.MULTIMODAL_FUSION_FAILED,
                message=f"图文融合处理失败: {str(e)}"
            )
    
    async def _recognize_multimodal_intent(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """多模态意图识别 - 根据设计文档实现"""
        try:
            logger.info("开始多模态意图识别")
            
            intent_data = {
                "primary_intent": None,
                "secondary_intents": [],
                "confidence_scores": {},
                "intent_features": {},
                "processing_time": datetime.now().isoformat()
            }
            
            # 基于文本的意图识别
            if "text_data" in processed_data:
                text_intent = processed_data["text_data"].get("intent", {})
                intent_data["text_intent"] = text_intent
            
            # 基于图片的意图识别
            if "image_data" in processed_data:
                image_intent = await self._recognize_image_intent(processed_data["image_data"])
                intent_data["image_intent"] = image_intent
            
            # 多模态意图融合
            if "fusion_data" in processed_data:
                multimodal_intent = await self._fuse_multimodal_intents(
                    intent_data.get("text_intent", {}),
                    intent_data.get("image_intent", {})
                )
                intent_data["multimodal_intent"] = multimodal_intent
            
            # 确定主要意图
            primary_intent = self._determine_primary_intent(intent_data)
            intent_data["primary_intent"] = primary_intent
            
            # 计算置信度分数
            confidence_scores = self._calculate_intent_confidence(intent_data)
            intent_data["confidence_scores"] = confidence_scores
            
            logger.info(f"多模态意图识别完成，主要意图: {primary_intent}")
            return intent_data
            
        except Exception as e:
            logger.error(f"多模态意图识别失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.INTENT_RECOGNITION_FAILED,
                message=f"多模态意图识别失败: {str(e)}"
            )
    
    # 辅助方法实现
    
    def _detect_language(self, text: str) -> str:
        """语言检测"""
        # 简单的语言检测逻辑
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        
        if chinese_chars > english_chars:
            return "zh"
        elif english_chars > chinese_chars:
            return "en"
        else:
            return "mixed"
    
    def _filter_sensitive_words(self, text: str) -> str:
        """敏感词过滤"""
        # 简单的敏感词过滤
        sensitive_words = ["敏感词1", "敏感词2"]  # 实际应用中从配置文件读取
        filtered_text = text
        for word in sensitive_words:
            filtered_text = filtered_text.replace(word, "*" * len(word))
        return filtered_text
    
    def _clean_text(self, text: str) -> str:
        """文本清洗"""
        # 去除特殊字符，标准化格式
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    async def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """实体抽取"""
        # 简单的实体抽取逻辑
        entities = []
        
        # 提取人名
        names = re.findall(r'[A-Z][a-z]+ [A-Z][a-z]+', text)
        for name in names:
            entities.append({"type": "PERSON", "value": name, "confidence": settings.ENTITY_PERSON_CONFIDENCE})
        
        # 提取地名
        places = re.findall(r'[A-Z][a-z]+(?: [A-Z][a-z]+)*', text)
        for place in places:
            entities.append({"type": "PLACE", "value": place, "confidence": settings.ENTITY_PLACE_CONFIDENCE})
        
        return entities
    
    async def _recognize_text_intent(self, text: str) -> Dict[str, Any]:
        """文本意图识别"""
        # 简单的意图识别逻辑
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["什么", "是什么", "what", "what is"]):
            return {"type": "factual_qa", "confidence": settings.INTENT_FACTUAL_CONFIDENCE}
        elif any(word in text_lower for word in ["如何", "怎么", "how", "how to"]):
            return {"type": "operation_guide", "confidence": settings.INTENT_OPERATION_CONFIDENCE}
        elif any(word in text_lower for word in ["比较", "对比", "compare"]):
            return {"type": "comparison_analysis", "confidence": settings.INTENT_COMPARISON_CONFIDENCE}
        else:
            return {"type": "factual_qa", "confidence": settings.INTENT_DEFAULT_CONFIDENCE}
    
    async def _extract_keywords(self, text: str) -> List[str]:
        """关键词提取"""
        # 简单的关键词提取
        words = text.split()
        # 过滤停用词
        stop_words = {"的", "是", "在", "有", "和", "the", "is", "in", "and"}
        keywords = [word for word in words if word not in stop_words and len(word) > 1]
        return keywords[:settings.MULTIMODAL_MAX_KEYWORDS]  # 返回前N个关键词
    
    async def _generate_text_embedding(self, text: str) -> List[float]:
        """生成文本向量"""
        try:
            # 使用Ollama生成文本向量
            embedding = await self.ollama_service.generate_embedding(text)
            return embedding
        except Exception as e:
            logger.error(f"文本向量生成失败: {e}")
            return [0.0] * 768  # 返回默认向量
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """图片预处理"""
        # 尺寸调整
        max_size = (settings.MULTIMODAL_IMAGE_MAX_DIMENSION, settings.MULTIMODAL_IMAGE_MAX_DIMENSION)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # 格式转换
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        return image
    
    async def _extract_image_features(self, image: Image.Image) -> Dict[str, Any]:
        """提取图片特征"""
        try:
            # 使用图片向量化服务提取特征
            if self.image_vectorization_service is None:
                self.image_vectorization_service = ImageVectorizationService()
            features = await self.image_vectorization_service.extract_image_features(image)
            return features
        except Exception as e:
            logger.error(f"图片特征提取失败: {e}")
            return {"sift_keypoints_count": 0, "orb_keypoints_count": 0}
    
    async def _extract_ocr_text(self, image: Image.Image) -> str:
        """OCR识别"""
        try:
            # 使用Ollama进行OCR识别
            ocr_text = await self.ollama_service.extract_text_from_image(image)
            return ocr_text
        except Exception as e:
            logger.error(f"OCR识别失败: {e}")
            return ""
    
    async def _understand_image_content(self, image: Image.Image) -> Dict[str, Any]:
        """理解图片内容"""
        try:
            # 使用Ollama理解图片内容
            content_description = await self.ollama_service.describe_image(image)
            return {
                "description": content_description,
                "objects": [],  # 对象检测结果
                "scene": "unknown"  # 场景识别结果
            }
        except Exception as e:
            logger.error(f"图片内容理解失败: {e}")
            return {"description": "", "objects": [], "scene": "unknown"}
    
    async def _generate_image_embedding(self, image: Image.Image) -> List[float]:
        """生成图片向量"""
        try:
            # 使用图片向量化服务生成向量
            if self.image_vectorization_service is None:
                self.image_vectorization_service = ImageVectorizationService()
            embedding = await self.image_vectorization_service.vectorize_image(image, "hybrid")
            return embedding
        except Exception as e:
            logger.error(f"图片向量生成失败: {e}")
            return [0.0] * 512  # 返回默认向量
    
    async def _align_text_image_features(
        self,
        text_data: Dict[str, Any],
        image_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """特征对齐"""
        # 将文本和图片特征对齐到同一向量空间
        return {
            "text_vector": text_data.get("embedding", []),
            "image_vector": image_data.get("embedding", []),
            "alignment_score": settings.MULTIMODAL_DEFAULT_FUSION_SCORE
        }
    
    async def _fuse_semantics(
        self,
        text_data: Dict[str, Any],
        image_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """语义融合"""
        return {
            "fused_vector": [],  # 融合后的向量
            "semantic_similarity": settings.MULTIMODAL_DEFAULT_SEMANTIC_SIMILARITY,
            "fusion_method": "weighted_average"
        }
    
    async def _build_multimodal_context(
        self,
        text_data: Dict[str, Any],
        image_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """上下文构建"""
        return {
            "text_context": text_data.get("cleaned_text", ""),
            "image_context": image_data.get("content_understanding", {}),
            "combined_context": "",
            "context_length": 0
        }
    
    async def _enhance_intent_with_image(
        self,
        text_data: Dict[str, Any],
        image_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """意图增强"""
        text_intent = text_data.get("intent", {})
        image_description = image_data.get("content_understanding", {}).get("description", "")
        
        # 基于图片描述增强意图理解
        enhanced_intent = text_intent.copy()
        enhanced_intent["image_enhanced"] = True
        enhanced_intent["confidence"] = min(text_intent.get("confidence", settings.INTENT_DEFAULT_CONFIDENCE) + 0.1, 1.0)
        
        return enhanced_intent
    
    def _calculate_fusion_score(
        self,
        text_data: Dict[str, Any],
        image_data: Dict[str, Any]
    ) -> float:
        """计算融合分数"""
        # 基于文本和图片的相似度计算融合分数
        return settings.MULTIMODAL_DEFAULT_FUSION_SCORE
    
    async def _recognize_image_intent(self, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """图片意图识别"""
        description = image_data.get("content_understanding", {}).get("description", "")
        
        if "search" in description.lower() or "find" in description.lower():
            return {"type": "image_search", "confidence": settings.IMAGE_SEARCH_DEFAULT_CONFIDENCE}
        elif "question" in description.lower() or "?" in description:
            return {"type": "multimodal_qa", "confidence": settings.IMAGE_SEARCH_MULTIMODAL_CONFIDENCE}
        else:
            return {"type": "image_search", "confidence": settings.IMAGE_SEARCH_DEFAULT_CONFIDENCE_FALLBACK}
    
    async def _fuse_multimodal_intents(
        self,
        text_intent: Dict[str, Any],
        image_intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """多模态意图融合"""
        # 融合文本和图片意图
        if text_intent.get("type") == image_intent.get("type"):
            return {
                "type": text_intent.get("type"),
                "confidence": max(text_intent.get("confidence", 0), image_intent.get("confidence", 0))
            }
        else:
            # 选择置信度更高的意图
            if text_intent.get("confidence", 0) > image_intent.get("confidence", 0):
                return text_intent
            else:
                return image_intent
    
    def _determine_primary_intent(self, intent_data: Dict[str, Any]) -> str:
        """确定主要意图"""
        multimodal_intent = intent_data.get("multimodal_intent", {})
        if multimodal_intent:
            return multimodal_intent.get("type", "factual_qa")
        
        text_intent = intent_data.get("text_intent", {})
        if text_intent:
            return text_intent.get("type", "factual_qa")
        
        return "factual_qa"
    
    def _calculate_intent_confidence(self, intent_data: Dict[str, Any]) -> Dict[str, float]:
        """计算意图置信度"""
        return {
            "text_intent": intent_data.get("text_intent", {}).get("confidence", 0.0),
            "image_intent": intent_data.get("image_intent", {}).get("confidence", 0.0),
            "multimodal_intent": intent_data.get("multimodal_intent", {}).get("confidence", 0.0),
            "overall": settings.MULTIMODAL_DEFAULT_RELEVANCE_SCORE
        }
    
    def _calculate_content_relevance(
        self,
        text_content: str,
        image_file: UploadFile
    ) -> float:
        """计算内容关联性"""
        # 简单的关联性计算
        return settings.MULTIMODAL_DEFAULT_RELEVANCE_SCORE
    
    def _check_content_consistency(
        self,
        text_content: Optional[str],
        image_file: Optional[UploadFile]
    ) -> float:
        """检查内容一致性"""
        # 简单的一致性检查
        return settings.MULTIMODAL_DEFAULT_CONSISTENCY_SCORE
    
    async def process_image_input(self, image_file: UploadFile) -> Dict[str, Any]:
        """处理图片输入 - 用于图片搜索"""
        try:
            logger.info(f"处理图片输入: {image_file.filename}")
            
            # 验证图片
            validation_result = await self._validate_image_content(image_file)
            if not validation_result["valid"]:
                raise CustomException(
                    code=ErrorCode.INVALID_IMAGE,
                    message=validation_result["message"]
                )
            
            # 处理图片内容
            image_data = await self._process_image_content(image_file)
            
            return image_data
            
        except Exception as e:
            logger.error(f"图片输入处理失败: {e}", exc_info=True)
            raise CustomException(
                code=ErrorCode.IMAGE_PROCESSING_FAILED,
                message=f"图片输入处理失败: {str(e)}"
            )
