// 通用类型
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface PaginationParams {
  page: number
  size: number
}

export interface PaginationResult<T> {
  total: number
  items: T[]
  page: number
  size: number
}

// 知识库类型
export interface KnowledgeBase {
  id: number
  name: string
  description: string
  category_id: number
  category_name: string
  is_active?: boolean
  // 共享相关字段
  visibility?: 'private' | 'shared' | 'public' | string
  role?: 'owner' | 'admin' | 'editor' | 'viewer' | string
  // 统计字段
  document_count?: number
  created_at: string
  updated_at: string
}

// 文档类型
export interface Document {
  id: number
  knowledge_base_id: number
  title: string
  file_name: string
  file_type: string
  file_size: number
  status: string
  created_at: string
  updated_at: string
}

// 用户类型
export interface User {
  id: string
  username: string
  email: string
  role: string
}

// 观测运维
export interface ClusterConfig {
  id: number
  name: string
  description?: string
  api_server: string
  auth_type: string
  auth_token?: string
  kubeconfig?: string
  client_cert?: string
  client_key?: string
  ca_cert?: string
  verify_ssl: boolean
  prometheus_url?: string
  prometheus_auth_type?: string
  prometheus_username?: string
  prometheus_password?: string
  log_system?: string
  log_endpoint?: string
  log_auth_type?: string
  log_username?: string
  log_password?: string
  is_active: boolean
  last_health_status?: string
  last_health_message?: string
  last_health_checked_at?: string
  created_at: string
  updated_at: string
}

export interface ClusterListResult {
  list: ClusterConfig[]
  total: number
  page: number
  size: number
}

export interface HealthStatus {
  name: string
  status: string
  message?: string
}

export interface ClusterConnectivityResult {
  api_server: HealthStatus
  prometheus?: HealthStatus | null
  logging?: HealthStatus | null
}

export interface ResourceSyncEvent {
  uid: string
  type: string
  diff?: Record<string, any>
}

export interface ResourceSyncResult {
  status: string
  count: number
  resource_version?: string
  events: ResourceSyncEvent[]
}

export interface ResourceSnapshot {
  id: number
  cluster_id: number
  resource_type: string
  namespace?: string
  resource_uid: string
  resource_name: string
  labels?: Record<string, string>
  annotations?: Record<string, string>
  spec?: Record<string, any>
  status?: Record<string, any>
  resource_version?: string
  snapshot: Record<string, any>
  collected_at?: string
  updated_at: string
}

export interface MetricsQueryResult {
  status: string
  data: Record<string, any>
}

export interface LogEntry {
  timestamp?: string
  message?: string
  severity?: string
  labels?: Record<string, any>
  highlight?: string | string[]
  raw?: Record<string, any>
}

export interface LogPagination {
  total?: number
  page: number
  page_size: number
}

export interface LogQueryResult {
  backend: string
  results: LogEntry[]
  pagination: LogPagination
  stats?: Record<string, any>
  raw: Record<string, any>
}

export interface DiagnosisEvent {
  timestamp?: string
  stage?: string
  status?: string
  message?: string
}

export type DiagnosisFeedbackType = 'confirmed' | 'continue_investigation' | 'custom'

export interface DiagnosisFeedbackEntry {
  feedback_type: DiagnosisFeedbackType
  feedback_notes?: string | null
  action_taken?: string | null
  iteration_no?: number | null
  continue_from_step?: number | null
  submitted_at?: string
}

export interface DiagnosisFeedbackState {
  last_feedback_type?: DiagnosisFeedbackType
  last_feedback_iteration?: number
  continue_from_step?: number
  min_steps_before_exit?: number
}

export interface DiagnosisFeedback {
  latest?: DiagnosisFeedbackEntry
  history?: DiagnosisFeedbackEntry[]
  state?: DiagnosisFeedbackState
}

export interface SubmitDiagnosisFeedbackPayload {
  feedback_type: DiagnosisFeedbackType
  feedback_notes?: string
  action_taken?: string
  iteration_no?: number
}

export interface DiagnosisRecord {
  id: number
  cluster_id: number
  namespace?: string
  resource_type?: string
  resource_name?: string
  trigger_source: string
  trigger_payload?: Record<string, any>
  symptoms?: Record<string, any>
  status: string
  summary?: string
  conclusion?: string
  confidence?: number
  metrics?: Record<string, any>
  logs?: Record<string, any>
  recommendations?: Record<string, any>
  events?: DiagnosisEvent[]
  feedback?: DiagnosisFeedback
  iterations?: DiagnosisIteration[]
  memories?: DiagnosisMemory[]
  knowledge_refs?: number[] | null
  knowledge_source?: string | null
  started_at: string
  completed_at?: string
  created_at: string
  updated_at: string
}

export interface DiagnosisIteration {
  id: number
  diagnosis_id: number
  iteration_no: number
  stage?: string
  status: string
  reasoning_prompt?: string
  reasoning_summary?: string
  reasoning_output?: Record<string, any>
  action_plan?: any
  action_result?: any
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface DiagnosisMemory {
  id: number
  diagnosis_id: number
  iteration_id?: number
  iteration_no?: number
  memory_type: string
  summary?: string
  content?: Record<string, any>
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface DiagnosisIterationList {
  list: DiagnosisIteration[]
  total: number
}

export interface DiagnosisMemoryList {
  list: DiagnosisMemory[]
  total: number
}
