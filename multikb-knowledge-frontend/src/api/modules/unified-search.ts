/**
 * 统一搜索 API
 * 支持文档+代码的混合搜索
 */

import request from '../utils/request'

// =============================================
// 类型定义
// =============================================

export interface UnifiedSearchRequest {
  query: string
  knowledge_base_id?: number
  search_scope?: ('documents' | 'code')[]
  search_mode?: 'hybrid' | 'vector' | 'keyword'
  top_k?: number
  filters?: Record<string, any>
}

export interface SearchResult {
  type: 'document' | 'code_file' | 'code_symbol'
  id: number
  score: number
  // 文档结果
  title?: string
  content?: string
  // 代码文件结果
  file_path?: string
  file_name?: string
  language?: string
  lines_of_code?: number
  complexity_score?: number
  // 代码符号结果
  symbol_name?: string
  symbol_type?: string
  qualified_name?: string
  signature?: string
  docstring?: string
  // 共有字段
  repository_id?: number
  knowledge_base_id?: number
}

export interface UnifiedSearchResponse {
  query: string
  total: number
  results: SearchResult[]
  search_mode: string
  search_scope: string[]
}

// =============================================
// API 接口
// =============================================

/**
 * 统一搜索（文档 + 代码）
 */
export function unifiedSearch(data: UnifiedSearchRequest) {
  return request<UnifiedSearchResponse>({
    url: '/unified-search',
    method: 'post',
    data
  })
}

/**
 * 在知识库中搜索
 */
export function searchInKnowledgeBase(kbId: number, params: {
  query: string
  search_scope?: 'all' | 'documents' | 'code'
  search_mode?: 'hybrid' | 'vector' | 'keyword'
  top_k?: number
}) {
  return request<UnifiedSearchResponse>({
    url: `/unified-search/knowledge-bases/${kbId}`,
    method: 'get',
    params
  })
}

/**
 * 搜索代码文件
 */
export function searchCodeFiles(params: {
  query: string
  repository_id?: number
  language?: string
  top_k?: number
}) {
  return request({
    url: '/unified-search/code/files',
    method: 'get',
    params
  })
}

/**
 * 搜索代码符号
 */
export function searchCodeSymbols(params: {
  query: string
  repository_id?: number
  symbol_type?: string
  top_k?: number
}) {
  return request({
    url: '/unified-search/code/symbols',
    method: 'get',
    params
  })
}
