"""
QA Schemas
根据知识问答系统设计文档实现数据模型定义
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Tuple
from datetime import datetime
from enum import Enum

class InputType(str, Enum):
    """输入类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    MULTIMODAL = "multimodal"
    MULTI_IMAGE = "multi_image"

class SearchType(str, Enum):
    """搜索类型枚举"""
    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    EXACT = "exact"
    FUZZY = "fuzzy"
    IMAGE = "image"

class IntentType(str, Enum):
    """意图类型枚举"""
    FACTUAL_QA = "factual_qa"
    CONCEPT_EXPLANATION = "concept_explanation"
    OPERATION_GUIDE = "operation_guide"
    COMPARISON_ANALYSIS = "comparison_analysis"
    TROUBLESHOOTING = "troubleshooting"
    IMAGE_SEARCH = "image_search"
    MULTIMODAL_QA = "multimodal_qa"
    SUMMARY = "summary"

class RelevanceLevel(str, Enum):
    """相关性等级枚举"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"

class AnswerType(str, Enum):
    """答案类型枚举"""
    KNOWLEDGE_BASE = "knowledge_base"
    LLM_ENHANCED = "llm_enhanced"
    LLM_ONLY = "llm_only"
    GENERAL = "general"
    NO_INFO = "no_info"
    ERROR = "error"
    CONVERSATION_CONTEXT = "conversation_context"  # 基于对话上下文的回答（不查询知识库）

# 1. 知识库相关Schema

class KnowledgeBaseInfo(BaseModel):
    """知识库信息"""
    id: int
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    document_count: int = 0
    storage_size: int = 0
    tags: List[str] = []
    status: str = "active"
    created_at: datetime

class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""
    knowledge_bases: List[KnowledgeBaseInfo]
    pagination: Dict[str, Any]

# 2. 会话管理相关Schema

class QASessionCreate(BaseModel):
    """创建问答会话请求"""
    knowledge_base_id: int
    # 必填：没有用户体系时，名称用于唯一标识
    session_name: str = Field(..., min_length=1)
    search_type: SearchType = SearchType.HYBRID
    max_sources: int = Field(default=10, ge=1, le=50)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    llm_model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)

class QASessionResponse(BaseModel):
    """问答会话响应"""
    session_id: str
    session_name: str
    knowledge_base_id: int
    knowledge_base_name: str
    search_type: SearchType = Field(default=SearchType.HYBRID)
    search_config: Dict[str, Any]
    llm_config: Dict[str, Any] = {}
    question_count: int = 0
    last_question: Optional[str] = None
    last_activity: Optional[datetime] = None
    created_at: datetime
    # ✅ 历史问答列表（用于会话详情）
    questions: Optional[List[Dict[str, Any]]] = None

class QASessionListResponse(BaseModel):
    """问答会话列表响应"""
    sessions: List[QASessionResponse]
    pagination: Dict[str, Any]

class QASessionConfigUpdate(BaseModel):
    """更新会话配置请求"""
    knowledge_base_id: Optional[int] = None
    search_type: Optional[SearchType] = None
    max_sources: Optional[int] = Field(None, ge=1, le=50)
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)

# 3. 多模态问答相关Schema

class QAMultimodalQuestionRequest(BaseModel):
    """多模态问答请求"""
    text_content: Optional[str] = None
    input_type: InputType = InputType.TEXT
    include_history: bool = True
    max_history: int = Field(default=5, ge=0, le=10)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    max_sources: int = Field(default=10, ge=1, le=50)
    search_type: SearchType = SearchType.HYBRID

class SourceInfo(BaseModel):
    """来源信息"""
    document_id: Optional[str] = None  # ✅ 允许 None（用于 LLM 生成的回答，无文档来源）
    document_title: str
    knowledge_base_name: str
    content_snippet: str
    similarity_score: float
    position_info: Dict[str, Any]
    # ✅ 新增：关联图片信息
    associated_images: Optional[List[Dict[str, Any]]] = None

class QAMultimodalQuestionResponse(BaseModel):
    """多模态问答响应"""
    question_id: str
    input_type: InputType
    answer_content: str
    answer_type: AnswerType
    confidence: float
    source_info: List[SourceInfo]
    processing_info: Dict[str, Any]
    image_info: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

# 4. 图片搜索相关Schema

class QAImageSearchRequest(BaseModel):
    """图片搜索请求"""
    search_type: str = "image-to-image"  # image-to-image, text-to-image
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    max_results: int = Field(default=10, ge=1, le=50)
    knowledge_base_id: Optional[int] = None

class ImageSearchResult(BaseModel):
    """图片搜索结果"""
    image_id: str
    image_path: str
    similarity_score: float
    image_info: Dict[str, Any]
    source_document: Dict[str, Any]
    # ✅ 上下文文本块信息（已存在字段，现在会填充内容）
    # context_info 结构: {"chunks": [...], "chunk_count": int, "document_id": int}
    context_info: Optional[Dict[str, Any]] = None

class QAImageSearchResponse(BaseModel):
    """图片搜索响应"""
    search_type: str
    results: List[ImageSearchResult]
    results_count: int
    search_time: float
    similarity_threshold: float

# 5. 历史记录相关Schema

class QAHistoryRecord(BaseModel):
    """问答历史记录"""
    question_id: str
    session_id: str
    user_id: str
    knowledge_base_id: int
    question_content: str
    answer_content: str
    answer_type: AnswerType
    confidence: float
    source_count: int
    created_at: datetime

class QAHistoryResponse(BaseModel):
    """问答历史响应"""
    history_records: List[QAHistoryRecord]
    pagination: Dict[str, Any]
    statistics: Dict[str, Any]

class QAHistorySearchRequest(BaseModel):
    """历史搜索请求"""
    search_keyword: str
    search_type: str = "hybrid"  # keyword, semantic, hybrid
    filter_conditions: Optional[Dict[str, Any]] = None
    sort_method: str = "relevance"  # time, relevance, quality
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

class QAHistorySearchResponse(BaseModel):
    """历史搜索响应"""
    search_results: List[Dict[str, Any]]
    search_statistics: Dict[str, Any]
    pagination: Dict[str, Any]

# 6. 模型配置相关Schema

class QAModelResponse(BaseModel):
    """模型响应"""
    name: str
    display_name: str
    description: str
    language: str
    size: Optional[str] = None
    dimension: Optional[int] = None
    status: str

class QAModelsResponse(BaseModel):
    """模型列表响应"""
    llm_models: List[QAModelResponse]
    embedding_models: List[QAModelResponse]

# 7. 流式问答相关Schema

class StreamChunk(BaseModel):
    """流式数据块"""
    type: str  # content_chunk, source_info, completion, error
    data: Dict[str, Any]
    timestamp: datetime

# 8. 多模态处理相关Schema

class ProcessedTextData(BaseModel):
    """处理后的文本数据"""
    original_text: str
    cleaned_text: str
    language: str
    entities: List[Dict[str, Any]]
    intent: Dict[str, Any]
    keywords: List[str]
    embedding: List[float]
    char_count: int
    word_count: int
    processing_time: str

class ProcessedImageData(BaseModel):
    """处理后的图片数据"""
    filename: str
    format: str
    size: int
    dimensions: Tuple[int, int]
    features: Dict[str, Any]
    ocr_text: str
    content_understanding: Dict[str, Any]
    embedding: List[float]
    processing_time: str

class FusionData(BaseModel):
    """融合数据"""
    aligned_features: Dict[str, Any]
    fused_semantics: Dict[str, Any]
    context: Dict[str, Any]
    enhanced_intent: Dict[str, Any]
    fusion_score: float
    processing_time: str

class IntentData(BaseModel):
    """意图数据"""
    primary_intent: str
    secondary_intents: List[str]
    confidence_scores: Dict[str, float]
    intent_features: Dict[str, Any]
    processing_time: str

class ProcessedMultimodalData(BaseModel):
    """处理后的多模态数据"""
    input_type: InputType
    timestamp: str
    processing_steps: List[str]
    text_data: Optional[ProcessedTextData] = None
    image_data: Optional[ProcessedImageData] = None
    fusion_data: Optional[FusionData] = None
    intent_data: IntentData

# 9. 降级策略相关Schema

class RelevanceAssessment(BaseModel):
    """相关性评估"""
    overall_score: float
    relevance_level: RelevanceLevel
    similarity_score: float
    match_score: float
    completeness_score: float
    accuracy_score: float
    high_quality_count: int
    total_count: int

class StrategyDecision(BaseModel):
    """策略决策"""
    strategy_type: str
    strategy_name: str
    description: str
    relevance_level: RelevanceLevel
    confidence: float
    decision_reason: str

class ProcessingResult(BaseModel):
    """处理结果"""
    answer: str
    answer_type: AnswerType
    confidence: float
    citations: List[SourceInfo]
    source_count: int
    strategy_details: Dict[str, Any]

class FallbackStrategyResult(BaseModel):
    """降级策略结果"""
    strategy: str
    strategy_type: str
    relevance_score: float
    relevance_level: RelevanceLevel
    evaluation_details: Dict[str, Any]
    processing_result: ProcessingResult
    decision_time: str

# 10. 错误处理相关Schema

class QAErrorResponse(BaseModel):
    """QA错误响应"""
    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    request_id: Optional[str] = None

# 11. 统计相关Schema

class QAStatistics(BaseModel):
    """问答统计"""
    total_questions: int
    answered_questions: int
    unanswered_questions: int
    average_response_time: float
    average_confidence: float
    popular_questions: List[Dict[str, Any]]
    search_type_stats: Dict[str, int]
    knowledge_base_stats: Dict[str, int]

class QAPerformanceMetrics(BaseModel):
    """问答性能指标"""
    response_time: float
    retrieval_time: float
    generation_time: float
    total_tokens: int
    similarity_scores: List[float]
    source_count: int
    processing_steps: List[str]

# 12. 外部搜索相关 Schema

class QAExternalSearchRequest(BaseModel):
    """外部搜索请求"""
    question: str = Field(..., min_length=1)
    context: Optional[str] = None
    conversation_id: Optional[str] = None
    knowledge_base_hits: Optional[int] = Field(default=None, ge=0)
    top_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    answer_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    limit: Optional[int] = Field(default=None, ge=1, le=10)
    force: bool = False

class QAExternalSearchResult(BaseModel):
    """外部搜索结果"""
    title: Optional[str] = None
    url: str
    snippet: Optional[str] = None
    source: Optional[str] = None
    engines: Optional[List[str]] = None

class QAExternalSearchResponse(BaseModel):
    """外部搜索响应"""
    triggered: bool = True
    from_cache: bool = False
    query: Optional[str] = None
    latency: Optional[float] = None
    results: List[QAExternalSearchResult]
    message: Optional[str] = None
    summary: Optional[str] = None
