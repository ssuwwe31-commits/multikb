"""
Knowledge Graph Schemas
知识图谱相关Schema
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================
# 实体相关Schema
# ============================================

class EntityBase(BaseModel):
    """实体基础Schema"""
    name: str = Field(..., description="实体名称")
    type: str = Field(..., description="实体类型")
    description: Optional[str] = Field(None, description="实体描述")
    aliases: Optional[List[str]] = Field(None, description="实体别名列表")
    confidence: Optional[float] = Field(0.7, ge=0.0, le=1.0, description="置信度分数")
    metadata: Optional[Dict[str, Any]] = Field(None, description="扩展元数据")


class EntityCreate(EntityBase):
    """创建实体Schema"""
    knowledge_base_id: int = Field(..., description="知识库ID")


class EntityUpdate(BaseModel):
    """更新实体Schema"""
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    aliases: Optional[List[str]] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None


class EntityResponse(EntityBase):
    """实体响应Schema"""
    id: int
    knowledge_base_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    nebula_synced: bool
    nebula_synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EntityListResponse(BaseModel):
    """实体列表响应Schema"""
    id: int
    name: str
    type: str
    description: Optional[str] = None
    aliases: Optional[List[str]] = None
    confidence: float
    related_documents_count: Optional[int] = 0
    related_entities_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


# ============================================
# 关系相关Schema
# ============================================

class RelationshipBase(BaseModel):
    """关系基础Schema"""
    source_entity_id: int = Field(..., description="源实体ID")
    target_entity_id: int = Field(..., description="目标实体ID")
    relation_type: str = Field(..., description="关系类型")
    description: Optional[str] = Field(None, description="关系描述")
    weight: Optional[float] = Field(0.5, ge=0.0, le=1.0, description="关系权重")
    confidence: Optional[float] = Field(0.7, ge=0.0, le=1.0, description="置信度分数")
    metadata: Optional[Dict[str, Any]] = Field(None, description="扩展元数据")


class RelationshipCreate(RelationshipBase):
    """创建关系Schema"""
    knowledge_base_id: int = Field(..., description="知识库ID")


class RelationshipUpdate(BaseModel):
    """更新关系Schema"""
    relation_type: Optional[str] = None
    description: Optional[str] = None
    weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None


class RelationshipResponse(RelationshipBase):
    """关系响应Schema"""
    id: int
    knowledge_base_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    nebula_synced: bool
    nebula_synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class RelationshipDetailResponse(RelationshipResponse):
    """关系详情响应Schema"""
    source_entity: Optional[EntityResponse] = None
    target_entity: Optional[EntityResponse] = None


# ============================================
# 查询相关Schema
# ============================================

class PathQueryRequest(BaseModel):
    """路径查询请求Schema"""
    source_entity_id: int = Field(..., description="源实体ID")
    target_entity_id: int = Field(..., description="目标实体ID")
    max_hops: Optional[int] = Field(3, ge=1, le=10, description="最大跳数")
    relation_types: Optional[List[str]] = Field(None, description="限制关系类型")


class PathResponse(BaseModel):
    """路径响应Schema"""
    entities: List[int] = Field(..., description="实体ID列表")
    relationships: List[Dict[str, Any]] = Field(..., description="关系列表")
    total_weight: float = Field(..., description="总权重")
    path_length: int = Field(..., description="路径长度")


class NeighborQueryRequest(BaseModel):
    """邻居查询请求Schema"""
    relation_type: Optional[str] = Field(None, description="关系类型")
    max_depth: Optional[int] = Field(1, ge=1, le=5, description="最大深度")
    limit: Optional[int] = Field(50, ge=1, le=200, description="返回数量限制")


class EntityDetailResponse(EntityResponse):
    """实体详情响应Schema"""
    relationships: List[RelationshipDetailResponse] = []
    related_documents: List[Dict[str, Any]] = []


# ============================================
# 提取相关Schema
# ============================================

class ExtractionTaskCreate(BaseModel):
    """创建提取任务Schema"""
    knowledge_base_id: int = Field(..., description="知识库ID")
    document_ids: Optional[List[int]] = Field(None, description="文档ID列表（可选，为空表示批量提取）")


class ExtractionTaskResponse(BaseModel):
    """提取任务响应Schema"""
    id: int
    knowledge_base_id: int
    document_id: Optional[int] = None
    status: str
    total_entities: int
    total_relationships: int
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================
# 可视化相关Schema
# ============================================

class VisualizationRequest(BaseModel):
    """可视化请求Schema"""
    knowledge_base_id: int = Field(..., description="知识库ID")
    entity_ids: Optional[List[int]] = Field(None, description="指定要展示的实体ID列表")
    relation_types: Optional[List[str]] = Field(None, description="限制关系类型")
    max_nodes: Optional[int] = Field(100, ge=1, le=1000, description="最大节点数")
    layout: Optional[str] = Field("force", description="布局类型: force/hierarchical/circular")


class VisualizationNode(BaseModel):
    """可视化节点Schema"""
    id: int
    label: str
    type: str
    group: str
    value: int
    title: str


class VisualizationEdge(BaseModel):
    """可视化边Schema"""
    from: int
    to: int
    label: str
    value: float
    title: str


class VisualizationResponse(BaseModel):
    """可视化响应Schema"""
    nodes: List[VisualizationNode]
    edges: List[VisualizationEdge]
    layout: str


# ============================================
# 统计相关Schema
# ============================================

class GraphStatsResponse(BaseModel):
    """图谱统计响应Schema"""
    total_entities: int
    total_relationships: int
    entity_type_distribution: Dict[str, int]
    relation_type_distribution: Dict[str, int]
    graph_density: float
    average_degree: float
    largest_component_size: int


# ============================================
# 批量操作Schema
# ============================================

class EntityBatchCreate(BaseModel):
    """批量创建实体Schema"""
    entities: List[EntityCreate]


class EntityBatchUpdate(BaseModel):
    """批量更新实体Schema"""
    entities: List[Dict[str, Any]]  # 包含id和更新字段


class EntityBatchDelete(BaseModel):
    """批量删除实体Schema"""
    entity_ids: List[int]


class EntityMergeRequest(BaseModel):
    """实体合并请求Schema"""
    entity_ids: List[int] = Field(..., description="要合并的实体ID列表")
    target_entity_id: int = Field(..., description="目标实体ID")

