/**
 * 代码库分析 API
 * MVP 版本 - 8 个核心接口
 */

import request from '../utils/request'

// =============================================
// 类型定义
// =============================================

export interface CodeRepository {
  id: number
  repo_url: string
  repo_name: string
  repo_type: string
  default_branch: string
  last_commit_hash?: string
  last_commit_date?: string
  local_path?: string
  clone_status: 'pending' | 'cloning' | 'completed' | 'failed'
  clone_progress: number
  parse_status: 'pending' | 'parsing' | 'completed' | 'failed'
  parse_progress: number
  total_files: number
  total_lines: number
  language_stats: Record<string, number>
  created_at: string
  updated_at: string
}

export interface CodeStructure {
  files: Array<{
    file_path: string
    language: string
    symbols: Array<{
      type: string
      name: string
      line: number
      parameters?: string[]
      docstring?: string
    }>
    imports: Array<{
      type: string
      module: string
      line: number
    }>
    complexity: {
      cyclomatic: number
      branches: number
    }
    lines: number
  }>
  statistics: {
    total_files: number
    total_lines: number
    total_functions: number
    total_classes: number
    languages: Record<string, number>
    complexity: {
      total: number
      average: number
      max: number
    }
  }
}

export interface DependencyGraph {
  nodes: Array<{
    id: string
    name: string
    type: string
    language: string
    symbols_count: number
    lines: number
  }>
  edges: Array<{
    source: string
    target: string
    type: string
  }>
}

export interface QAResult {
  answer: string
  sources: string[]
  question: string
}

export interface ProjectSummary {
  summary: string
  statistics: {
    total_files: number
    total_lines: number
    total_functions: number
    total_classes: number
    languages: Record<string, number>
  }
}

export interface WikiContent {
  project_overview: string
  what_is_project: string
  core_components: Array<{
    name: string
    purpose: string
  }>
  value_propositions: Array<{
    feature: string
    description: string
  }>
  key_features: Array<{
    name: string
    description: string
  }>
  system_architecture?: {
    three_tier_architecture: string
    functional_subsystems_table: Array<{
      subsystem_name: string
      frontend_path: string
      backend_route: string
      service_files: string[]
      key_responsibilities: string
    }>
    architectural_patterns: string
    storage_systems_table: Array<{
      storage_system: string
      data_types: string
      access_pattern: string
      key_use_cases: string
    }>
    key_architectural_decisions: Array<{
      decision: string
      rationale: string
      impact: string
    }>
    api_architecture: string
    scalability_considerations: string
    mermaid_architecture_diagram?: string
    mermaid_data_flow_diagram?: string
    mermaid_api_diagram?: string
  }
  technology_stack?: {
    core_technologies: string
    key_dependencies_table: Array<{
      name: string
      purpose: string
      category: string
    }>
    technology_choices: string
  }
  component_relationships?: {
    service_dependencies: string
    component_relationships: string
    data_flow: string
  }
  deployment_models?: {
    standalone_server: string
    docker_deployment: string
    build_features: string
    deployment_steps: Array<{
      step: string
      description: string
    }>
  }
  getting_started?: {
    prerequisites: Array<{
      item: string
      description: string
    }>
    installation_steps: Array<{
      step: string
      description: string
    }>
    key_endpoints: Array<{
      endpoint: string
      method: string
      description: string
    }>
    quick_start_summary: string
    run_project_command?: string
  }
  key_files?: Array<{
    path: string
    type: string
    importance: number
  }>
  architecture_recommendations?: {
    patterns_detected: Array<{
      pattern: string
      confidence: string
      description: string
    }>
    potential_issues: Array<{
      type: string
      severity: string
      description: string
      details?: any[]
    }>
    improvement_suggestions: Array<{
      suggestion: string
      priority: string
      impact: string
      implementation: string
    }>
  }
  code_quality_recommendations?: {
    code_smells: Array<{
      type: string
      severity: string
      file: string
      symbol?: string
      line?: number
      description: string
    }>
    refactoring_suggestions: Array<{
      suggestion: string
      priority: string
      affected_files: string[]
      steps: string
    }>
    test_suggestions: Array<{
      type: string
      severity: string
      description: string
      files?: string[]
    }>
  }
}

// =============================================
// API 接口
// =============================================

/**
 * 获取仓库列表
 */
export function getRepositories(params?: {
  page?: number
  page_size?: number
  search?: string
  clone_status?: string
  parse_status?: string
}) {
  return request({
    url: '/code-analysis/repositories',
    method: 'get',
    params
  })
}

/**
 * 1. 导入代码仓库
 */
export function createRepository(data: {
  repo_url: string
  branch?: string
}) {
  return request({
    url: '/code-analysis/repositories',
    method: 'post',
    params: data
  })
}

/**
 * 2. 获取仓库信息
 */
export function getRepository(repoId: number) {
  return request<CodeRepository>({
    url: `/code-analysis/repositories/${repoId}`,
    method: 'get'
  })
}

/**
 * 3. 删除仓库
 */
export function deleteRepository(repoId: number) {
  return request({
    url: `/code-analysis/repositories/${repoId}`,
    method: 'delete'
  })
}

/**
 * 4. 获取代码结构（仅从缓存读取）
 */
export function getCodeStructure(repoId: number) {
  return request<CodeStructure | {
    status: string
    message: string
  }>({
    url: `/code-analysis/repositories/${repoId}/structure`,
    method: 'get'
  })
}

/**
 * 4.1 触发代码结构异步解析（刷新时调用）
 */
export function analyzeCodeStructure(repoId: number) {
  return request<{
    task_id: string
    repository_id: number
    status: string
    message: string
  }>({
    url: `/code-analysis/repositories/${repoId}/structure/analyze`,
    method: 'post'
  })
}

/**
 * 5. 获取依赖关系图（仅从缓存读取）
 */
export function getDependencies(repoId: number) {
  return request<DependencyGraph | {
    status: string
    message: string
  }>({
    url: `/code-analysis/repositories/${repoId}/dependencies`,
    method: 'get'
  })
}

/**
 * 获取 API 调用链（前端接口 → 后端接口 → 后端服务）
 */

/**
 * 6. 分析单个文件
 */
export function analyzeFile(filePath: string, repositoryId: number) {
  return request({
    url: `/code-analysis/files/${filePath}/analysis`,
    method: 'get',
    params: { repository_id: repositoryId }
  })
}

export function getFileContent(filePath: string, repositoryId: number) {
  return request({
    url: `/code-analysis/files/${encodeURIComponent(filePath)}/content`,
    method: 'get',
    params: { repository_id: repositoryId }
  })
}

/**
 * 7. 代码问答
 */
export function codeQA(data: {
  repository_id: number
  question: string
  context_files?: string[]
  session_id?: string  // 可选，会话ID
}) {
  const { repository_id, session_id, ...requestData } = data
  return request<QAResult>({
    url: `/code-analysis/repositories/${repository_id}/qa`,
    method: 'post',
    data: requestData,
    params: session_id ? { session_id } : undefined
  })
}

/**
 * 8. 生成项目摘要
 */
export function generateSummary(repoId: number, useCache: boolean = true) {
  return request<ProjectSummary>({
    url: `/code-analysis/repositories/${repoId}/summary`,
    method: 'post',
    params: { use_cache: useCache }
  })
}

/**
 * 9. 获取 Wiki 内容（优先从缓存获取，如果没有则触发异步生成）
 */
export function getWikiContent(repoId: number, forceRefresh: boolean = false) {
  return request<WikiContent | {
    task_id: string
    repository_id: number
    status: string
    message: string
  }>({
    url: `/code-analysis/repositories/${repoId}/wiki-content`,
    method: 'get',
    params: { force_refresh: forceRefresh }
  })
}

// =============================================
// 深度集成 API（2026-01-12 新增）
// =============================================

/**
 * 获取代码文件列表
 */
export function getCodeFiles(params: {
  repo_id: number
  language?: string
  page?: number
  page_size?: number
}) {
  return request({
    url: `/code-analysis/repositories/${params.repo_id}/files`,
    method: 'get',
    params
  })
}

/**
 * 获取文件符号列表
 */
export function getFileSymbols(fileId: number, params?: {
  symbol_type?: string
  page?: number
  page_size?: number
}) {
  return request({
    url: `/code-analysis/files/${fileId}/symbols`,
    method: 'get',
    params
  })
}

/**
 * 提取文件符号
 */
export function extractFileSymbols(fileId: number) {
  return request({
    url: `/code-analysis/files/${fileId}/extract-symbols`,
    method: 'post'
  })
}

/**
 * 同步文件到图谱
 */
export function syncFileToGraph(fileId: number) {
  return request({
    url: `/code-analysis/files/${fileId}/sync-graph`,
    method: 'post'
  })
}

/**
 * 同步符号到图谱
 */
export function syncSymbolToGraph(symbolId: number) {
  return request({
    url: `/code-analysis/symbols/${symbolId}/sync-graph`,
    method: 'post'
  })
}

/**
 * 获取符号统计
 */
export function getSymbolStats(repoId: number) {
  return request({
    url: `/code-analysis/repositories/${repoId}/symbols/stats`,
    method: 'get'
  })
}

/**
 * 搜索代码符号
 */
export function searchSymbols(params: {
  keyword: string
  repository_id?: number
  symbol_type?: string
  limit?: number
}) {
  return request({
    url: '/code-analysis/symbols/search',
    method: 'get',
    params
  })
}

/**
 * 查询调用链
 */
export function queryCallChain(params: {
  repository_id: number
  source: string
  target: string
  max_hops?: number
}) {
  return request({
    url: '/code-analysis/query/call-chain',
    method: 'get',
    params
  })
}

/**
 * 查询依赖路径
 */
export function queryDependencyPath(params: {
  repository_id: number
  source: string
  target: string
  max_hops?: number
}) {
  return request({
    url: '/code-analysis/query/dependency-path',
    method: 'get',
    params
  })
}

/**
 * 关联代码仓库到知识库
 */
export function linkRepositoryToKB(repoId: number, knowledgeBaseId: number) {
  return request({
    url: `/code-analysis/repositories/${repoId}/link-kb`,
    method: 'post',
    params: { knowledge_base_id: knowledgeBaseId }
  })
}

/**
 * 取消代码仓库与知识库的关联
 */
export function unlinkRepositoryFromKB(repoId: number) {
  return request({
    url: `/code-analysis/repositories/${repoId}/unlink-kb`,
    method: 'delete'
  })
}

/**
 * 获取知识库关联的代码仓库
 */
export function getKBRepositories(kbId: number) {
  return request({
    url: `/code-analysis/knowledge-bases/${kbId}/repositories`,
    method: 'get'
  })
}

// =============================================
// 代码导航 API（类似 LSP）
// =============================================

/**
 * 代码导航位置信息
 */
export interface NavigationLocation {
  file_path: string
  line: number
  column: number
  symbol_name?: string
  qualified_name?: string
  symbol_type?: string
  signature?: string
  context?: string
  type?: 'definition' | 'reference' | 'call'
}

/**
 * 悬停信息
 */
export interface HoverInfo {
  symbol_name: string
  qualified_name: string
  symbol_type: string
  signature: string
  docstring?: string
  file_path?: string
  line?: number
}

/**
 * Go to Definition - 跳转到定义
 */
export function getDefinition(params: {
  repository_id: number
  file_path: string
  line: number
  column?: number
}) {
  return request<NavigationLocation>({
    url: '/code-analysis/navigation/definition',
    method: 'get',
    params
  })
}

/**
 * Find References - 查找所有引用
 */
export function getReferences(params: {
  repository_id: number
  file_path: string
  line: number
  column?: number
  include_definition?: boolean
}) {
  return request<{
    total: number
    references: NavigationLocation[]
  }>({
    url: '/code-analysis/navigation/references',
    method: 'get',
    params
  })
}

/**
 * Hover Info - 获取悬停信息
 */
export function getHoverInfo(params: {
  repository_id: number
  file_path: string
  line: number
  column?: number
}) {
  return request<HoverInfo>({
    url: '/code-analysis/navigation/hover',
    method: 'get',
    params
  })
}

// =============================================
// 代码问答会话 API
// =============================================

/**
 * 创建代码问答会话
 */
export function createQASession(repositoryId: number, data?: {
  session_name?: string
}) {
  return request<{
    session_id: string
  }>({
    url: `/code-analysis/repositories/${repositoryId}/qa/sessions`,
    method: 'post',
    data
  })
}

/**
 * 获取代码问答会话列表
 */
export function getQASessions(repositoryId: number, params?: {
  page?: number
  page_size?: number
}) {
  return request<{
    total: number
    sessions: Array<{
      session_id: string
      session_name: string
      question_count: number
      last_question: string
      last_activity_time: string
      created_at: string
    }>
  }>({
    url: `/code-analysis/repositories/${repositoryId}/qa/sessions`,
    method: 'get',
    params
  })
}

/**
 * 获取问答记录列表
 */
export function getQARecords(sessionId: string, params?: {
  page?: number
  page_size?: number
}) {
  return request<{
    total: number
    records: Array<{
      record_id: string
      question: string
      answer: string
      sources: string[]
      created_at: string
    }>
  }>({
    url: `/code-analysis/qa/sessions/${sessionId}/records`,
    method: 'get',
    params
  })
}

// =============================================
// 代码解释
// =============================================

export interface CodeExplanationRequest {
  code: string
  file_path?: string
  language?: string
}

export interface CodeExplanationResponse {
  explanation: string
  code: string
  file_path?: string
  language?: string
  model: string
}

export function explainCode(repositoryId: number, data: CodeExplanationRequest) {
  return request<CodeExplanationResponse>({
    url: `/code-analysis/repositories/${repositoryId}/explain-code`,
    method: 'post',
    data
  })
}
