"""
Image Search Schemas
根据文档处理流程设计实现图片搜索相关的Pydantic模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ImageSearchRequest(BaseModel):
    """图片搜索请求模型"""
    query_text: str = Field(..., min_length=1, description="搜索查询文本")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="相似度阈值")
    limit: int = Field(10, ge=1, le=100, description="返回结果数量限制")
    knowledge_base_id: Optional[List[int]] = Field(None, description="知识库ID（支持多个）")
    search_type: str = Field("hybrid", description="搜索类型：vector, keyword, hybrid")

class ImageSearchResponse(BaseModel):
    """图片搜索响应模型"""
    image_id: int = Field(..., description="图片ID")
    document_id: int = Field(..., description="文档ID")
    knowledge_base_id: int = Field(..., description="知识库ID")
    image_path: str = Field(..., description="图片路径")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="相似度分数")
    image_type: str = Field("unknown", description="图片类型")
    page_number: Optional[int] = Field(None, description="页码")
    coordinates: Optional[Dict[str, Any]] = Field(None, description="坐标信息")
    ocr_text: str = Field("", description="OCR识别的文字")
    description: str = Field("", description="图片描述")
    source_document: str = Field("", description="来源文档")

    class Config:
        from_attributes = True

class ImageVectorInfo(BaseModel):
    """图片向量信息模型"""
    image_id: int = Field(..., description="图片ID")
    document_id: int = Field(..., description="文档ID")
    image_path: str = Field(..., description="图片路径")
    image_type: str = Field("unknown", description="图片类型")
    vector_dimension: int = Field(..., description="向量维度")
    vector_model: str = Field("CLIP", description="向量模型")
    vector_version: str = Field("1.0", description="模型版本")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True
