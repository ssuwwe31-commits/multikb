import request from '../utils/request'
import type { Document, PaginationParams, PaginationResult } from '@/types'

// 文档列表
export const getDocuments = (params: PaginationParams & { knowledge_base_id?: number }) => {
  return request<PaginationResult<Document>>({
    url: '/documents',
    method: 'get',
    params
  })
}

// 文档详情
export const getDocumentDetail = (id: number) => {
  return request<Document>({
    url: `/documents/${id}`,
    method: 'get'
  })
}

// 文档上传
export const uploadDocument = (data: FormData) => {
  return request({
    url: '/documents/upload',
    method: 'post',
    data,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 从URL导入文档
export const uploadDocumentFromUrl = (data: FormData) => {
  return request({
    url: '/documents/upload-from-url',
    method: 'post',
    data,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 文档状态查询
export const getDocumentStatus = (id: number) => {
  return request({
    url: `/documents/${id}/status`,
    method: 'get'
  })
}

// 文档进度
export const getDocumentProgress = (id: number) => {
  return request({
    url: `/documents/${id}/progress`,
    method: 'get'
  })
}

// 删除文档
export const deleteDocument = (id: number) => {
  return request({
    url: `/documents/${id}`,
    method: 'delete'
  })
}

// 批量删除文档
export const batchDeleteDocuments = (documentIds: number[]) => {
  return request({
    url: '/documents/batch/delete',
    method: 'post',
    data: { document_ids: documentIds }
  })
}

// 批量移动文档
export const batchMoveDocuments = (data: {
  document_ids: number[]
  target_knowledge_base_id: number
  target_category_id?: number
}) => {
  return request({
    url: '/documents/batch/move',
    method: 'post',
    data
  })
}

// 批量添加标签
export const batchAddTags = (data: {
  document_ids: number[]
  tags: string[]
}) => {
  return request({
    url: '/documents/batch/tags/add',
    method: 'post',
    data
  })
}

// 批量删除标签
export const batchRemoveTags = (data: {
  document_ids: number[]
  tags: string[]
}) => {
  return request({
    url: '/documents/batch/tags/remove',
    method: 'post',
    data
  })
}

// 批量替换标签
export const batchReplaceTags = (data: {
  document_ids: number[]
  tags: string[]
}) => {
  return request({
    url: '/documents/batch/tags/replace',
    method: 'post',
    data
  })
}

// 获取文档目录
export const getDocumentTOC = (documentId: number) => {
  return request({
    url: `/documents/${documentId}/toc`,
    method: 'get'
  })
}

// 文档内搜索
export const searchInDocument = (documentId: number, params: {
  query: string
  page?: number
}) => {
  return request({
    url: `/documents/${documentId}/search`,
    method: 'get',
    params
  })
}

// 重新处理文档
export const reprocessDocument = (id: number) => {
  return request({
    url: `/documents/${id}/reprocess`,
    method: 'post'
  })
}

// 批量上传
export const batchUploadDocuments = (data: FormData) => {
  return request({
    url: '/documents/batch-upload',
    method: 'post',
    data,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 获取批次状态
export const getBatchStatus = (batchId: number) => {
  return request({
    url: `/documents/batch/${batchId}/status`,
    method: 'get'
  })
}

// 获取结构化预览
export const getStructuredPreview = (documentId: number) => {
  return request({
    url: `/documents/${documentId}/structured-preview`,
    method: 'get'
  })
}

// 重新生成标签和摘要
export const regenerateSummary = (documentId: number) => {
  return request({
    url: `/documents/${documentId}/regenerate-summary`,
    method: 'post'
  })
}

// 获取文档图片列表
export const getDocumentImages = (documentId: number) => {
  return request({
    url: `/documents/${documentId}/images`,
    method: 'get'
  })
}

// 获取图片详情
export const getImageDetail = (documentId: number, imageId: number) => {
  return request({
    url: `/documents/${documentId}/images/${imageId}`,
    method: 'get'
  })
}

// 搜索图片内容
export const searchImageContent = (documentId: number, params: any) => {
  return request({
    url: `/documents/${documentId}/images/search`,
    method: 'post',
    data: params
  })
}

// ============ 块级管理接口 ============

// 获取文档的所有块列表
export const getDocumentChunks = (documentId: number, params?: {
  page?: number
  size?: number
  chunk_type?: string
}) => {
  return request({
    url: `/documents/${documentId}/chunks`,
    method: 'get',
    params
  })
}

// 获取单个块的内容
export const getChunkDetail = (documentId: number, chunkId: number) => {
  return request({
    url: `/documents/${documentId}/chunks/${chunkId}`,
    method: 'get'
  })
}

// 获取文本/表格命中的上下文
export const getChunkContext = (
  documentId: number,
  chunkId: number,
  params?: { neighbor_pre?: number; neighbor_next?: number; parent_group_max_chars?: number }
) => {
  return request({
    url: `/query/documents/${documentId}/chunks/${chunkId}/context`,
    method: 'get',
    params
  })
}

// 获取图片的上下文（位置与关联文本）
export const getImageContext = (
  documentId: number,
  imageId: number,
  params?: { neighbor_pre?: number; neighbor_next?: number; min_confidence?: number }
) => {
  return request({
    url: `/query/documents/${documentId}/images/${imageId}/context`,
    method: 'get',
    params
  })
}

// 更新块内容（块级修改）
export const updateChunk = (documentId: number, chunkId: number, data: {
  content: string
  metadata?: any
  version_comment?: string
}) => {
  return request({
    url: `/documents/${documentId}/chunks/${chunkId}`,
    method: 'put',
    data
  })
}

// 验证块内容
export const validateChunk = (documentId: number, chunkId: number, data: {
  content: string
  metadata?: any
}) => {
  return request({
    url: `/documents/${documentId}/chunks/${chunkId}/validate`,
    method: 'post',
    data
  })
}

// ============ 一致性检查接口 ============

// 检查文档数据一致性
export const checkDocumentConsistency = (documentId: number) => {
  return request({
    url: `/documents/${documentId}/consistency-check`,
    method: 'get'
  })
}

// 检查块数据一致性
export const checkChunkConsistency = (documentId: number, chunkId: number) => {
  return request({
    url: `/documents/${documentId}/chunks/${chunkId}/consistency-check`,
    method: 'get'
  })
}

// 修复数据不一致问题
export const repairConsistency = (documentId: number, data?: any) => {
  return request({
    url: `/documents/${documentId}/consistency-repair`,
    method: 'post',
    data
  })
}

// 文档版本列表（文档级）
export const getDocumentVersions = (documentId: number, params?: { page?: number; size?: number }) => {
  return request({
    url: `/versions`,
    method: 'get',
    params: { document_id: documentId, ...(params || {}) }
  })
}

// 文档原文预览（PDF优先，失败则原文件直链）
export const getDocumentPreview = (documentId: number) => {
  return request({
    url: `/documents/${documentId}/preview`,
    method: 'get'
  })
}

// 从 OpenSearch 获取指定块内容
export const getChunkContentFromOS = (documentId: number, chunkId: number) => {
  return request({
    url: `/documents/${documentId}/chunks/${chunkId}/content-opensearch`,
    method: 'get'
  })
}

// ============ 版本管理接口 ============

// 获取块的版本列表
export const getChunkVersions = (documentId: number, chunkId: number, params?: {
  page?: number
  size?: number
}) => {
  return request({
    url: `/documents/${documentId}/chunks/${chunkId}/versions`,
    method: 'get',
    params
  })
}

// 获取特定版本
export const getChunkVersion = (documentId: number, chunkId: number, version: number) => {
  return request({
    url: `/documents/${documentId}/chunks/${chunkId}/versions/${version}`,
    method: 'get'
  })
}

// 回滚到特定版本
export const restoreChunkVersion = (documentId: number, chunkId: number, version: number, revertComment?: string) => {
  return request({
    url: `/documents/${documentId}/chunks/${chunkId}/versions/${version}/restore`,
    method: 'post',
    data: {
      target_version: version,
      revert_comment: revertComment || `回退到版本 V${version}`
    }
  })
}

// 快速回退到上一个版本
export const revertToPreviousVersion = (documentId: number, chunkId: number) => {
  return request({
    url: `/documents/${documentId}/chunks/${chunkId}/revert-to-previous`,
    method: 'post'
  })
}

// 获取回退预览
export const getRevertPreview = (documentId: number, chunkId: number) => {
  return request({
    url: `/documents/${documentId}/chunks/${chunkId}/revert-preview`,
    method: 'get'
  })
}

// 批量回退到上一个版本
export const batchRevertToPrevious = (documentId: number, chunkIds: number[]) => {
  return request({
    url: `/documents/${documentId}/chunks/batch-revert-previous`,
    method: 'post',
    data: { chunk_ids: chunkIds }
  })
}

// ============ 文档级修改接口 ============

// 更新文档（现有接口增强）
export const updateDocument = (id: number, data: any) => {
  return request({
    url: `/documents/${id}`,
    method: 'put',
    data
  })
}

// 更新文档块内容（块级修改）
export const updateDocumentContent = (documentId: number, chunkId: number, data: any) => {
  return updateChunk(documentId, chunkId, data)
}
