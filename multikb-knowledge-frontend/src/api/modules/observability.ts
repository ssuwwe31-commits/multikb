import request from '../utils/request'
import type {
  ApiResponse,
  PaginationParams,
  ClusterListResult,
  ClusterConfig,
  ClusterConnectivityResult,
  ResourceSnapshot,
  ResourceSyncResult,
  MetricsQueryResult,
  LogQueryResult,
  DiagnosisRecord,
  DiagnosisIteration,
  DiagnosisIterationList,
  DiagnosisMemoryList,
  SubmitDiagnosisFeedbackPayload
} from '@/types'

// 集群管理
export const fetchClusters = (params: PaginationParams) => {
  return request<ApiResponse<ClusterListResult>>({
    url: '/observability/clusters',
    method: 'get',
    params
  })
}

export const createCluster = (data: Partial<ClusterConfig>) => {
  return request<ApiResponse<ClusterConfig>>({
    url: '/observability/clusters',
    method: 'post',
    data
  })
}

export const updateCluster = (id: number, data: Partial<ClusterConfig>) => {
  return request<ApiResponse<ClusterConfig>>({
    url: `/observability/clusters/${id}`,
    method: 'put',
    data
  })
}

export const deleteCluster = (id: number, hard: boolean = true) => {
  return request<ApiResponse>({
    url: `/observability/clusters/${id}`,
    method: 'delete',
    params: { hard }
  })
}

export const testClusterConnectivity = (id: number, overrides?: Record<string, any>) => {
  return request<ApiResponse<ClusterConnectivityResult>>({
    url: `/observability/clusters/${id}/test`,
    method: 'post',
    data: overrides
  })
}

export const runClusterHealthCheck = (id: number) => {
  return request<ApiResponse<ClusterConnectivityResult>>({
    url: `/observability/clusters/${id}/health-check`,
    method: 'post'
  })
}

export const syncClusterResources = (
  id: number,
  data: { namespace?: string; resource_types: string[]; limit?: number }
) => {
  return request<ApiResponse<Record<string, ResourceSyncResult>>>({
    url: `/observability/clusters/${id}/sync`,
    method: 'post',
    data
  })
}

export const fetchResourceSnapshots = (
  id: number,
  params: PaginationParams & {
    resource_type?: string
    namespace?: string
    resource_name?: string
  }
) => {
  return request<ApiResponse<{
    list: ResourceSnapshot[]
    total: number
    page: number
    size: number
  }>>({
    url: `/observability/clusters/${id}/resources`,
    method: 'get',
    params
  })
}

export const fetchClusterNamespaces = (id: number) => {
  return request<ApiResponse<string[]>>({
    url: `/observability/clusters/${id}/namespaces`,
    method: 'get'
  })
}

export const fetchClusterPods = (id: number, namespace?: string) => {
  return request<ApiResponse<string[]>>({
    url: `/observability/clusters/${id}/pods`,
    method: 'get',
    params: namespace ? { namespace } : {}
  })
}

// 指标与日志
export const queryMetrics = (payload: {
  cluster_id: number
  promql?: string
  template_id?: string
  context?: Record<string, any>
  start?: string
  end?: string
  step_seconds?: number
}) => {
  return request<ApiResponse<MetricsQueryResult>>({
    url: '/observability/metrics/query',
    method: 'post',
    data: payload
  })
}

export const queryLogs = (payload: {
  cluster_id: number
  query: string
  start?: string
  end?: string
  limit?: number
  page?: number
  page_size?: number
  highlight?: boolean
  stats?: boolean
}) => {
  return request<ApiResponse<LogQueryResult>>({
    url: '/observability/logs/query',
    method: 'post',
    data: payload
  })
}

// 诊断
export const listDiagnosisRecords = (params: PaginationParams) => {
  return request<ApiResponse<{
    list: DiagnosisRecord[]
    total: number
    page: number
    size: number
  }>>({
    url: '/observability/diagnosis',
    method: 'get',
    params
  })
}

export const getDiagnosisRecord = (recordId: number) => {
  return request<ApiResponse<DiagnosisRecord>>({
    url: `/observability/diagnosis/${recordId}`,
    method: 'get'
  })
}

export const runDiagnosis = (payload: {
  cluster_id: number
  namespace?: string
  resource_type?: string
  resource_name: string
  trigger_source?: string
  trigger_payload?: Record<string, any>
  time_range_hours?: number
}) => {
  return request<ApiResponse<DiagnosisRecord>>({
    url: '/observability/diagnosis/run',
    method: 'post',
    data: payload
  })
}

export const submitDiagnosisFeedback = (
  recordId: number,
  feedback: SubmitDiagnosisFeedbackPayload
) => {
  return request<ApiResponse<DiagnosisRecord>>({
    url: `/observability/diagnosis/${recordId}/feedback`,
    method: 'post',
    data: feedback
  })
}

export const listDiagnosisIterations = (recordId: number) => {
  return request<ApiResponse<DiagnosisIterationList>>({
    url: `/observability/diagnosis/${recordId}/iterations`,
    method: 'get'
  })
}

export const listDiagnosisMemories = (
  recordId: number,
  params?: { memory_type?: string }
) => {
  return request<ApiResponse<DiagnosisMemoryList>>({
    url: `/observability/diagnosis/${recordId}/memories`,
    method: 'get',
    params
  })
}

export const getDiagnosisReport = (recordId: number) => {
  return request<ApiResponse<{ has_report: boolean; report?: any; message?: string; status?: string }>>({
    url: `/observability/diagnosis/${recordId}/report`,
    method: 'get'
  })
}

export const deleteDiagnosisRecord = (recordId: number) => {
  return request<ApiResponse>({
    url: `/observability/diagnosis/${recordId}`,
    method: 'delete'
  })
}
