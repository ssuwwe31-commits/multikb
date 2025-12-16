import request from '../utils/request'

// ⚠️ 注意：以下接口已弃用，请使用QA模块的图片搜索接口
// 新接口路径：POST /qa/sessions/{session_id}/image-search
// 使用方式：先创建QA会话，然后通过QA模块进行图片搜索

// 以图找图搜索 (已弃用 - 使用QA模块)
export const searchByImage = (data: FormData, params?: { similarity_threshold?: number; limit?: number; knowledge_base_id?: number }) => {
  console.warn('searchByImage: 此接口已弃用，请使用QA模块的图片搜索接口')
  return request({
    url: '/images/search-by-image',
    method: 'post',
    data,
    params,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 以文找图搜索 (已弃用 - 使用QA模块)
export const searchByText = (data: { text: string; search_type?: string; similarity_threshold?: number; limit?: number }) => {
  console.warn('searchByText: 此接口已弃用，请使用QA模块的图片搜索接口')
  return request({
    url: '/images/search-by-text',
    method: 'post',
    data
  })
}

// 获取相似图片 (已弃用 - 使用QA模块)
export const getSimilarImages = (imageId: number, params?: { threshold?: number; limit?: number }) => {
  console.warn('getSimilarImages: 此接口已弃用，请使用QA模块的图片搜索接口')
  return request({
    url: `/images/similar/${imageId}`,
    method: 'get',
    params
  })
}

// 上传图片并搜索 (已弃用 - 使用QA模块)
export const uploadAndSearch = (data: FormData, params?: { search_type?: string; threshold?: number }) => {
  console.warn('uploadAndSearch: 此接口已弃用，请使用QA模块的图片搜索接口')
  return request({
    url: '/images/upload-and-search',
    method: 'post',
    data,
    params,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 获取图片向量信息
export const getImageVectors = (imageId: number) => {
  return request({
    url: `/images/vectors/${imageId}`,
    method: 'get'
  })
}

// ✅ 新的QA模块图片搜索接口
export const searchImageViaQA = (sessionId: string, data: FormData, params?: {
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

// 获取图片详情
export const getImageDetail = (imageId: number) => {
  return request({
    url: `/images/${imageId}`,
    method: 'get'
  })
}

// 获取图片列表
export const getImageList = (params?: {
  page?: number
  size?: number
  knowledge_base_id?: number
  document_id?: number
  mime_type?: string
}) => {
  return request({
    url: '/images',
    method: 'get',
    params
  })
}

export const retryImageOcr = (imageId: number) => {
  return request({
    url: `/images/${imageId}/retry-ocr`,
    method: 'post'
  })
}

// 图片上传（补齐后端接口）
export const uploadImage = (data: FormData) => {
  return request({
    url: '/images/upload',
    method: 'post',
    data,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
