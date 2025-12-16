import request from '../utils/request'
import type { PaginationResult, PaginationParams } from '@/types'

// ============================================
// 类型定义
// ============================================

export interface KnowledgeGraphEntity {
  id: number
  knowledge_base_id: number
  user_id: number
  name: string
  type: string
  description?: string
  aliases?: string[]
  confidence: number
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
  related_documents_count?: number
  related_entities_count?: number
}

export interface KnowledgeGraphRelationship {
  id: number
  knowledge_base_id: number
  user_id: number
  source_entity_id: number
  target_entity_id: number
  relation_type: string
  description?: string
  weight: number
  confidence: number
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
  source_entity?: KnowledgeGraphEntity
  target_entity?: KnowledgeGraphEntity
}

export interface EntityCreate {
  knowledge_base_id: number
  name: string
  type: string
  description?: string
  aliases?: string[]
  confidence?: number
  metadata?: Record<string, any>
}

export interface EntityUpdate {
  name?: string
  type?: string
  description?: string
  aliases?: string[]
  confidence?: number
  metadata?: Record<string, any>
}

export interface RelationshipCreate {
  knowledge_base_id: number
  source_entity_id: number
  target_entity_id: number
  relation_type: string
  description?: string
  weight?: number
  confidence?: number
  metadata?: Record<string, any>
}

export interface RelationshipUpdate {
  relation_type?: string
  description?: string
  weight?: number
  confidence?: number
  metadata?: Record<string, any>
}

export interface PathQuery {
  source_entity_id: number
  target_entity_id: number
  max_hops?: number
  relation_types?: string[]
}

export interface VisualizationData {
  nodes: Array<{
    id: number
    label: string
    type: string
    group: string
    value: number
    title: string
  }>
  edges: Array<{
    from: number
    to: number
    label: string
    value: number
    title: string
  }>
  layout: string
}

export interface GraphStats {
  total_entities: number
  total_relationships: number
  entity_type_distribution: Record<string, number>
  relation_type_distribution: Record<string, number>
  graph_density: number
  average_degree: number
  largest_component_size: number
}

// ============================================
// 实体相关API
// ============================================

// 获取实体列表
export const getEntities = (params: PaginationParams & {
  knowledge_base_id: number
  type?: string
  keyword?: string
}) => {
  return request<PaginationResult<KnowledgeGraphEntity>>({
    url: '/knowledge-graph/entities',
    method: 'get',
    params
  })
}

// 创建实体
export const createEntity = (data: EntityCreate) => {
  return request<KnowledgeGraphEntity>({
    url: '/knowledge-graph/entities',
    method: 'post',
    data
  })
}

// 获取实体详情
export const getEntityDetail = (id: number) => {
  return request<{
    code: number
    message: string
    data: {
      entity: KnowledgeGraphEntity
      relationships: KnowledgeGraphRelationship[]
      related_documents: Array<{
        document_id: number
        title: string
        mentions_count: number
      }>
    }
  }>({
    url: `/knowledge-graph/entities/${id}`,
    method: 'get'
  })
}

// 更新实体
export const updateEntity = (id: number, data: EntityUpdate) => {
  return request<KnowledgeGraphEntity>({
    url: `/knowledge-graph/entities/${id}`,
    method: 'put',
    data
  })
}

// 删除实体
export const deleteEntity = (id: number) => {
  return request({
    url: `/knowledge-graph/entities/${id}`,
    method: 'delete'
  })
}

// 批量创建实体
export const batchCreateEntities = (data: { entities: EntityCreate[] }) => {
  return request<{
    code: number
    message: string
    data: {
      created: number
      failed: number
      entities: KnowledgeGraphEntity[]
    }
  }>({
    url: '/knowledge-graph/entities/batch',
    method: 'post',
    data
  })
}

// 批量更新实体
export const batchUpdateEntities = (data: { entities: Array<{ id: number } & EntityUpdate> }) => {
  return request({
    url: '/knowledge-graph/entities/batch',
    method: 'put',
    data
  })
}

// 批量删除实体
export const batchDeleteEntities = (data: { entity_ids: number[] }) => {
  return request({
    url: '/knowledge-graph/entities/batch',
    method: 'delete',
    data
  })
}

// 合并实体
export const mergeEntities = (data: {
  entity_ids: number[]
  target_entity_id: number
}) => {
  return request<KnowledgeGraphEntity>({
    url: '/knowledge-graph/entities/merge',
    method: 'post',
    data
  })
}

// 搜索实体
export const searchEntities = (params: {
  q: string
  knowledge_base_id?: number
  type?: string
}) => {
  return request<{
    code: number
    message: string
    data: {
      entities: Array<KnowledgeGraphEntity & { score: number; matched_field: string }>
    }
  }>({
    url: '/knowledge-graph/search',
    method: 'get',
    params
  })
}

// ============================================
// 关系相关API
// ============================================

// 获取关系列表
export const getRelationships = (params: PaginationParams & {
  knowledge_base_id: number
  source_entity_id?: number
  target_entity_id?: number
  relation_type?: string
}) => {
  return request<PaginationResult<KnowledgeGraphRelationship>>({
    url: '/knowledge-graph/relationships',
    method: 'get',
    params
  })
}

// 创建关系
export const createRelationship = (data: RelationshipCreate) => {
  return request<KnowledgeGraphRelationship>({
    url: '/knowledge-graph/relationships',
    method: 'post',
    data
  })
}

// 获取关系详情
export const getRelationshipDetail = (id: number) => {
  return request<{
    code: number
    message: string
    data: KnowledgeGraphRelationship
  }>({
    url: `/knowledge-graph/relationships/${id}`,
    method: 'get'
  })
}

// 更新关系
export const updateRelationship = (id: number, data: RelationshipUpdate) => {
  return request<KnowledgeGraphRelationship>({
    url: `/knowledge-graph/relationships/${id}`,
    method: 'put',
    data
  })
}

// 删除关系
export const deleteRelationship = (id: number) => {
  return request({
    url: `/knowledge-graph/relationships/${id}`,
    method: 'delete'
  })
}

// ============================================
// 查询相关API
// ============================================

// 路径查询
export const findPaths = (data: PathQuery) => {
  return request<{
    code: number
    message: string
    data: {
      paths: Array<{
        entities: number[]
        relationships: Array<{
          source: number
          target: number
          type: string
        }>
        total_weight: number
        path_length: number
      }>
    }
  }>({
    url: '/knowledge-graph/paths',
    method: 'post',
    data
  })
}

// 获取实体邻居
export const getEntityNeighbors = (entityId: number, params?: {
  relation_type?: string
  max_depth?: number
  limit?: number
}) => {
  return request<{
    code: number
    message: string
    data: {
      neighbors: Array<{
        entity: KnowledgeGraphEntity
        relationship: KnowledgeGraphRelationship
        depth: number
      }>
    }
  }>({
    url: `/knowledge-graph/entities/${entityId}/neighbors`,
    method: 'get',
    params
  })
}

// 获取可视化数据
export const getVisualizationData = (params: {
  knowledge_base_id: number
  entity_ids?: number[]
  relation_types?: string[]
  entity_type?: string
  max_nodes?: number
  layout?: string
}) => {
  return request<{
    code: number
    message: string
    data: VisualizationData
  }>({
    url: '/knowledge-graph/visualization',
    method: 'get',
    params
  })
}

// ============================================
// 提取相关API
// ============================================

// 批量提取实体
export const extractEntities = (data: {
  knowledge_base_id: number
  document_ids?: number[]
  entity_type_mode?: 'system' | 'user' | 'model'
  entity_type_codes?: string[]
}) => {
  return request<{
    code: number
    message: string
    data: {
      task_id: number
      status: string
    }
  }>({
    url: '/knowledge-graph/extract',
    method: 'post',
    data
  })
}

// 单文档提取
export const extractDocumentEntities = (documentId: number, entity_type_mode?: 'system' | 'user' | 'model') => {
  return request<{
    code: number
    message: string
    data: {
      task_id: number
      status: string
    }
  }>({
    url: `/knowledge-graph/extract/document/${documentId}`,
    method: 'post',
    params: entity_type_mode ? { entity_type_mode } : undefined
  })
}

// 提取任务相关类型
export interface ExtractionTask {
  id: number
  knowledge_base_id: number
  document_id?: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  total_entities: number
  total_relationships: number
  error_message?: string
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
  completed_at?: string
}

// 获取提取任务列表
export const listExtractionTasks = (params: { knowledge_base_id: number; page?: number; size?: number }) => {
  return request<{
    code: number
    message: string
    data: {
      tasks: ExtractionTask[]
      total: number
      page: number
      size: number
    }
  }>({
    url: '/knowledge-graph/extract/tasks',
    method: 'get',
    params
  })
}

// 获取提取任务状态
export const getExtractionTask = (taskId: number) => {
  return request<{
    code: number
    message: string
    data: ExtractionTask
  }>({
    url: `/knowledge-graph/extract/tasks/${taskId}`,
    method: 'get'
  })
}

// 删除提取任务
export const deleteExtractionTask = (taskId: number) => {
  return request<{
    code: number
    message: string
  }>({
    url: `/knowledge-graph/extract/tasks/${taskId}`,
    method: 'delete'
  })
}

// 重新生成提取任务
export const regenerateExtractionTask = (taskId: number) => {
  return request<{
    code: number
    message: string
    data: {
      old_task_id: number
      new_task_id: string
      document_id: number
    }
  }>({
    url: `/knowledge-graph/extract/tasks/${taskId}/regenerate`,
    method: 'post'
  })
}

// ============================================
// 实体类型管理API
// ============================================

export interface EntityType {
  id: number
  code: string
  name: string
  description?: string
  icon?: string
  color?: string
  tag_type?: string
  sort_order: number
  is_system: boolean
  is_enabled: boolean
  parent_id?: number | null
  level: number
  children?: EntityType[]
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface EntityTypeCreate {
  code: string
  name: string
  description?: string
  icon?: string
  color?: string
  tag_type?: string
  sort_order?: number
  is_enabled?: boolean
  parent_id?: number | null
  level?: number
  metadata?: Record<string, any>
}

export interface EntityTypeUpdate {
  name?: string
  description?: string
  icon?: string
  color?: string
  tag_type?: string
  sort_order?: number
  is_enabled?: boolean
  parent_id?: number | null
  level?: number
  metadata?: Record<string, any>
}

// 获取实体类型列表
export const getEntityTypes = (params?: {
  is_enabled?: boolean
  is_system?: boolean
  knowledge_base_id?: number
  level?: number
  parent_id?: number
  include_children?: boolean
  page?: number
  size?: number
  keyword?: string
}) => {
  return request<{
    code: number
    message: string
    data: {
      list?: EntityType[]
      items?: EntityType[]
      types?: EntityType[]  // 兼容旧格式
      total: number
      page?: number
      size?: number
      pages?: number
      has_next?: boolean
      has_prev?: boolean
    }
  }>({
    url: '/knowledge-graph/entity-types',
    method: 'get',
    params
  })
}

// 获取实体类型树
export const getEntityTypeTree = (params?: {
  root_id?: number
  knowledge_base_id?: number
}) => {
  return request<{
    code: number
    message: string
    data: {
      tree: EntityType[]
      total: number
    }
  }>({
    url: '/knowledge-graph/entity-types/tree',
    method: 'get',
    params
  })
}

// 获取指定类型的子类型
export const getEntityTypeChildren = (typeId: number) => {
  return request<{
    code: number
    message: string
    data: {
      types: EntityType[]
      total: number
    }
  }>({
    url: `/knowledge-graph/entity-types/${typeId}/children`,
    method: 'get'
  })
}

// 获取实体类型详情
export const getEntityType = (typeId: number) => {
  return request<{
    code: number
    message: string
    data: EntityType
  }>({
    url: `/knowledge-graph/entity-types/${typeId}`,
    method: 'get'
  })
}

// 创建实体类型
export const createEntityType = (data: EntityTypeCreate) => {
  return request<{
    code: number
    message: string
    data: EntityType
  }>({
    url: '/knowledge-graph/entity-types',
    method: 'post',
    data
  })
}

// 更新实体类型
export const updateEntityType = (typeId: number, data: EntityTypeUpdate) => {
  return request<{
    code: number
    message: string
    data: EntityType
  }>({
    url: `/knowledge-graph/entity-types/${typeId}`,
    method: 'put',
    data
  })
}

// 删除实体类型
export const deleteEntityType = (typeId: number) => {
  return request<{
    code: number
    message: string
  }>({
    url: `/knowledge-graph/entity-types/${typeId}`,
    method: 'delete'
  })
}

// 启用/禁用实体类型
export const toggleEntityType = (typeId: number, isEnabled: boolean) => {
  return request<{
    code: number
    message: string
    data: EntityType
  }>({
    url: `/knowledge-graph/entity-types/${typeId}/toggle`,
    method: 'patch',
    params: { is_enabled: isEnabled }
  })
}

// 获取知识库的实体类型配置
export const getKnowledgeBaseEntityTypes = (kbId: number) => {
  return request<{
    code: number
    message: string
    data: {
      types: EntityType[]
      total: number
    }
  }>({
    url: `/knowledge-graph/knowledge-bases/${kbId}/entity-types`,
    method: 'get'
  })
}

// 配置知识库的实体类型
export const configureKnowledgeBaseEntityTypes = (
  kbId: number,
  data: {
    entity_type_ids: number[]
    configs?: Array<{
      entity_type_id: number
      is_enabled: boolean
      sort_order: number
    }>
  }
) => {
  return request<{
    code: number
    message: string
    data: {
      count: number
    }
  }>({
    url: `/knowledge-graph/knowledge-bases/${kbId}/entity-types`,
    method: 'post',
    data
  })
}

// ============================================
// 行业模板API
// ============================================

export interface IndustryTemplate {
  code: string
  name: string
  description: string
  entity_type_count: number
}

export interface IndustryTemplateDetail {
  template: {
    code: string
    name: string
    description: string
  }
  entity_types: Array<EntityType & { sort_order?: number; exists?: boolean }>
}

// 获取所有行业模板列表
export const getIndustryTemplates = () => {
  return request<{
    code: number
    message: string
    data: {
      templates: IndustryTemplate[]
      total: number
    }
  }>({
    url: '/knowledge-graph/entity-type-templates',
    method: 'get'
  })
}

// 获取指定行业模板详情
export const getIndustryTemplate = (templateCode: string) => {
  return request<{
    code: number
    message: string
    data: IndustryTemplateDetail
  }>({
    url: `/knowledge-graph/entity-type-templates/${templateCode}`,
    method: 'get'
  })
}

// 应用行业模板到知识库
export const applyIndustryTemplate = (kbId: number, templateCode: string) => {
  return request<{
    code: number
    message: string
    data: {
      count: number
    }
  }>({
    url: `/knowledge-graph/knowledge-bases/${kbId}/apply-template`,
    method: 'post',
    data: {
      template_code: templateCode
    }
  })
}

// ============================================
// 统计相关API
// ============================================

// 获取统计信息
export const getGraphStats = (knowledgeBaseId: number) => {
  return request<{
    code: number
    message: string
    data: GraphStats
  }>({
    url: '/knowledge-graph/stats',
    method: 'get',
    params: { knowledge_base_id: knowledgeBaseId }
  })
}

