import request from '../utils/request'
import { WS_BASE_URL } from '@/config/api'

// 获取知识库列表（用于问答）
export const getKnowledgeBases = () => {
  return request({
    url: '/qa/knowledge-bases',
    method: 'get'
  })
}

// 获取知识库详情
export const getKnowledgeBaseDetail = (kbId: number) => {
  return request({
    url: `/qa/knowledge-bases/${kbId}`,
    method: 'get'
  })
}

// 创建问答会话
export const createQASession = (data: { knowledge_base_id: number; session_name: string }) => {
  return request({
    url: '/qa/sessions',
    method: 'post',
    data
  })
}

// 获取问答会话列表
export const getQASessions = () => {
  return request({
    url: '/qa/sessions',
    method: 'get'
  })
}

// 获取会话详情
export const getQASessionDetail = (sessionId: string) => {
  return request({
    url: `/qa/sessions/${sessionId}`,
    method: 'get'
  })
}

// 多模态问答
export const askQuestion = (sessionId: string, data: {
  text_content?: string
  image_file?: File
  input_type: 'text' | 'image' | 'multimodal'
  search_type?: string
  similarity_threshold?: number
  max_sources?: number
}) => {
  const formData = new FormData()
  if (data.image_file) {
    formData.append('image_file', data.image_file)
  }
  if (data.text_content !== undefined) {
    formData.append('text_content', data.text_content)
  }
  formData.append('input_type', data.input_type)
  if (data.search_type) formData.append('search_type', data.search_type)
  if (data.similarity_threshold !== undefined && data.similarity_threshold !== null) {
    formData.append('similarity_threshold', data.similarity_threshold.toString())
  }
  if (data.max_sources !== undefined && data.max_sources !== null) {
    formData.append('max_sources', data.max_sources.toString())
  }
  
  return request({
    url: `/qa/sessions/${sessionId}/multimodal-questions`,
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 图片搜索
export const searchImage = (sessionId: string, data: FormData, params?: {
  search_type?: string
  similarity_threshold?: number
  max_results?: number
  knowledge_base_id?: number
}) => {
  return request({
    url: `/qa/sessions/${sessionId}/image-search`,
    method: 'post',
    data,
    params,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 删除会话
export const deleteQASession = (sessionId: string) => {
  return request({
    url: `/qa/sessions/${sessionId}`,
    method: 'delete'
  })
}

// 获取问答历史
export const getQAHistory = (params?: { skip?: number; limit?: number; session_id?: string }) => {
  return request({
    url: '/qa/history',
    method: 'get',
    params
  })
}

// 搜索问答历史
export const searchQAHistory = (data: any) => {
  return request({
    url: '/qa/history/search',
    method: 'post',
    data
  })
}

// ============ 新增API接口 ============

// 获取查询方式列表
export const getSearchTypes = () => {
  return request({
    url: '/qa/search-types',
    method: 'get'
  })
}

// 获取可用模型列表
export const getAvailableModels = () => {
  return request({
    url: '/qa/models',
    method: 'get'
  })
}

// 更新会话配置
export const updateSessionConfig = (sessionId: string, data: {
  search_config?: any
  llm_config?: any
}) => {
  return request({
    url: `/qa/sessions/${sessionId}/config`,
    method: 'put',
    data
  })
}

// 获取问答详情
export const getQAHistoryDetail = (questionId: string) => {
  return request({
    url: `/qa/history/${questionId}`,
    method: 'get'
  })
}

// 删除历史记录
export const deleteQAHistory = (questionId: string) => {
  return request({
    url: `/qa/history/${questionId}`,
    method: 'delete'
  })
}

// 流式问答（WebSocket地址）
export const getStreamURL = (sessionId: string) => {
  return `${WS_BASE_URL}/api/qa/sessions/${sessionId}/stream`
}

// 外部联网搜索
export const externalSearch = (data: {
  question: string
  context?: string
  conversation_id?: string
  knowledge_base_hits?: number
  top_score?: number
  answer_confidence?: number
  limit?: number
}) => {
  return request({
    url: '/qa/external-search',
    method: 'post',
    data
  })
}
