"""
Entity Type Schemas
实体类型相关Schema
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class EntityTypeBase(BaseModel):
    """实体类型基础Schema"""
    code: str = Field(..., description="类型代码（唯一标识）")
    name: str = Field(..., description="类型名称（中文标签）")
    description: Optional[str] = Field(None, description="类型描述")
    icon: Optional[str] = Field(None, description="图标名称或URL")
    color: Optional[str] = Field(None, description="颜色代码")
    tag_type: Optional[str] = Field(None, description="标签类型")
    sort_order: int = Field(0, description="排序顺序")
    is_enabled: bool = Field(True, description="是否启用")
    parent_id: Optional[int] = Field(None, description="父类型ID（支持最多3级分类）")
    level: int = Field(1, description="层级深度（1=一级分类，2=二级分类，3=三级分类，最大3级，自动计算）")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="扩展元数据", alias="metadata")


class EntityTypeCreate(EntityTypeBase):
    """创建实体类型Schema"""
    pass


class EntityTypeUpdate(BaseModel):
    """更新实体类型Schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    tag_type: Optional[str] = None
    sort_order: Optional[int] = None
    is_enabled: Optional[bool] = None
    parent_id: Optional[int] = None
    level: Optional[int] = None
    meta_data: Optional[Dict[str, Any]] = Field(None, alias="metadata")


class EntityTypeResponse(EntityTypeBase):
    """实体类型响应Schema"""
    id: int
    is_system: bool
    user_id: Optional[int] = Field(None, description="创建用户ID（系统类型为NULL）")
    parent_id: Optional[int] = None
    level: int = 1
    created_at: datetime
    updated_at: datetime
    children: Optional[List["EntityTypeResponse"]] = Field(None, description="子类型列表")
    
    class Config:
        from_attributes = True
        populate_by_name = True  # 允许同时使用字段名和别名


class KnowledgeBaseEntityTypeConfig(BaseModel):
    """知识库实体类型配置Schema"""
    knowledge_base_id: int
    entity_type_id: int
    is_enabled: bool = True
    sort_order: int = 0


class KnowledgeBaseEntityTypeConfigUpdate(BaseModel):
    """更新知识库实体类型配置Schema"""
    is_enabled: Optional[bool] = None
    sort_order: Optional[int] = None


class KnowledgeBaseEntityTypeConfigRequest(BaseModel):
    """知识库实体类型配置请求Schema"""
    entity_type_ids: List[int] = Field(..., description="实体类型ID列表")
    configs: Optional[List[KnowledgeBaseEntityTypeConfig]] = Field(None, description="详细配置（可选）")


class IndustryTemplateResponse(BaseModel):
    """行业模板响应Schema"""
    code: str = Field(..., description="模板代码")
    name: str = Field(..., description="模板名称")
    description: str = Field(..., description="模板描述")
    entity_type_count: int = Field(..., description="包含的实体类型数量")
    
    class Config:
        from_attributes = True


class ApplyTemplateRequest(BaseModel):
    """应用模板请求Schema"""
    template_code: str = Field(..., description="模板代码")

