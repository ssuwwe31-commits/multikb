/**
 * 统一问答 API
 * 支持文档+代码的上下文问答
 */

import request from '../utils/request'

// =============================================
// 类型定义
// =============================================

export interface UnifiedQARequest {
  question: string
  knowledge_base_id?: number
  search_scope?: ('documents' | 'code')[]
  max_context_items?: number
  include_code_context?: boolean
}

export interface QASource {
  type: 'document' | 'code_file' | 'code_symbol'
  id: number
  title?: string
  file_path?: string
  symbol_name?: string
  symbol_type?: string
  language?: string
  score: number
}

export interface UnifiedQAResponse {
  question: string
  answer: string
  sources: QASource[]
  context_items: number
  search_scope: string[]
  knowledge_base_id?: number
}

export interface CodeExample {
  symbol_id: number
  symbol_name: string
  symbol_type: string
  signature: string
  docstring?: string
  code_content: string
  file_path: string
  score: number
}

// =============================================
// API 接口
// =============================================

/**
 * 统一问答（文档 + 代码）
 */
export function unifiedQA(data: UnifiedQARequest) {
  return request<UnifiedQAResponse>({
    url: '/unified-qa',
    method: 'post',
    data
  })
}

/**
 * 向知识库提问
 */
export function askKnowledgeBase(kbId: number, params: {
  question: string
  include_code?: boolean
  max_sources?: number
}) {
  return request<UnifiedQAResponse>({
    url: `/unified-qa/knowledge-bases/${kbId}/ask`,
    method: 'post',
    params
  })
}

/**
 * 获取代码示例
 */
export function getCodeExamples(data: {
  concept: string
  knowledge_base_id?: number
  language?: string
  limit?: number
}) {
  return request<{
    concept: string
    total: number
    examples: CodeExample[]
  }>({
    url: '/unified-qa/code-examples',
    method: 'post',
    data
  })
}

/**
 * 解释代码仓库
 */
export function explainRepository(repoId: number, question?: string) {
  return request({
    url: `/unified-qa/repositories/${repoId}/explain`,
    method: 'get',
    params: { question }
  })
}
