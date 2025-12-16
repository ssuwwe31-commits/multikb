import request from '../utils/request'

// 搜索接口
export const search = (params: {
  query: string
  search_type?: 'vector' | 'keyword' | 'hybrid' | 'exact' | 'fuzzy'
  knowledge_base_id?: number
  category_id?: number
  similarity_threshold?: number
  min_rerank_score?: number
  page?: number
  size?: number
}) => {
  return request({
    url: '/search',
    method: 'post',
    data: params
  })
}

// 向量搜索
export const vectorSearch = (params: {
  query: string
  knowledge_base_id?: number
  similarity_threshold?: number
  min_rerank_score?: number
  page?: number
  size?: number
}) => {
  return request({
    url: '/search/vector',
    method: 'post',
    data: params
  })
}

// 混合搜索
export const hybridSearch = (params: {
  query: string
  knowledge_base_id?: number
  category_id?: number
  similarity_threshold?: number
  page?: number
  size?: number
}) => {
  return request({
    url: '/search/hybrid',
    method: 'post',
    data: params
  })
}

// 高级搜索
export const advancedSearch = (params: {
  query: string
  filters?: any
  sort?: any
  page?: number
  size?: number
}) => {
  return request({
    url: '/search/advanced',
    method: 'post',
    data: params
  })
}

// 搜索建议
export const getSearchSuggestions = (query: string, limit: number = 5) => {
  return request({
    url: '/search/suggestions',
    method: 'get',
    params: { query, limit }
  })
}

// 搜索历史
export const getSearchHistory = (params?: { user_id?: number; limit?: number }) => {
  return request({
    url: '/search/history',
    method: 'get',
    params
  })
}

// 保存搜索
export const saveSearch = (data: { query: string; search_type: string; name?: string; description?: string }) => {
  return request({
    url: '/search/save',
    method: 'post',
    data
  })
}

// 删除搜索历史
export const deleteSearchHistory = (historyId: number) => {
  return request({
    url: `/search/history/${historyId}`,
    method: 'delete'
  })
}

// 清空搜索历史
export const clearSearchHistory = () => {
  return request({
    url: '/search/history',
    method: 'delete'
  })
}

// 搜索分面
export const getSearchFacets = (query: string, knowledge_base_id?: number) => {
  return request({
    url: '/search/facets',
    method: 'get',
    params: { query, knowledge_base_id }
  })
}

// 相似搜索
export const similarSearch = (data: { document_id: number; chunk_id?: number; similarity_threshold?: number; limit?: number }) => {
  return request({
    url: '/search/similar',
    method: 'post',
    data
  })
}

// 图片搜索 - 以图搜图
export const searchByImage = (file: File, params?: {
  similarity_threshold?: number
  limit?: number
  knowledge_base_id?: number
}) => {
  const formData = new FormData()
  formData.append('file', file)
  
  // 构建查询参数（URL查询参数）
  const queryParams = new URLSearchParams()
  if (params?.similarity_threshold !== undefined && params.similarity_threshold !== null) {
    queryParams.append('similarity_threshold', params.similarity_threshold.toString())
  }
  if (params?.limit !== undefined && params.limit !== null) {
    queryParams.append('limit', params.limit.toString())
  }
  if (params?.knowledge_base_id !== undefined && params.knowledge_base_id !== null) {
    queryParams.append('knowledge_base_id', params.knowledge_base_id.toString())
  }
  
  const url = queryParams.toString() 
    ? `/images/search-by-image?${queryParams.toString()}`
    : '/images/search-by-image'
  
  return request({
    url,
    method: 'post',
    data: formData
    // 注意：不要手动设置 Content-Type，让浏览器自动设置（包括 boundary）
  })
}

// 图片搜索 - 以文搜图
export const searchByTextForImages = (params: {
  query_text: string
  similarity_threshold?: number
  limit?: number
  knowledge_base_id?: number
}) => {
  return request({
    url: '/images/search-by-text',
    method: 'post',
    data: params
  })
}
