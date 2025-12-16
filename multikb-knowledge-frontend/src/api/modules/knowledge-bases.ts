import request from '../utils/request'
import type { KnowledgeBase, PaginationResult, PaginationParams } from '@/types'

// 获取知识库列表
export const getKnowledgeBases = (params: PaginationParams & { 
  category_id?: number; 
  status?: string;
  require_permission?: string; // 要求用户对该知识库有指定权限（如 'doc:upload'）
}) => {
  return request<PaginationResult<KnowledgeBase>>({
    url: '/knowledge-bases',
    method: 'get',
    params
  })
}

// 创建知识库
export const createKnowledgeBase = (data: Partial<KnowledgeBase>) => {
  return request<KnowledgeBase>({
    url: '/knowledge-bases',
    method: 'post',
    data
  })
}

// 获取知识库详情
export const getKnowledgeBaseDetail = (id: number) => {
  return request<{
    code: number
    message: string
    data: KnowledgeBase & { visibility?: string; role?: string }
  }>({
    url: `/knowledge-bases/${id}`,
    method: 'get'
  })
}

// 更新知识库
export const updateKnowledgeBase = (id: number, data: Partial<KnowledgeBase>) => {
  return request<KnowledgeBase>({
    url: `/knowledge-bases/${id}`,
    method: 'put',
    data
  })
}

// 知识库成员管理

export interface KnowledgeBaseMember {
  user_id: number
  username?: string
  nickname?: string
  role: string
  invited_by?: number
  invited_at?: string
}

// 获取成员列表
export const getKnowledgeBaseMembers = (kbId: number) => {
  return request<{
    code: number
    message: string
    data: KnowledgeBaseMember[]
  }>({
    url: `/knowledge-bases/${kbId}/members`,
    method: 'get'
  })
}

// 添加/邀请成员
export const addKnowledgeBaseMember = (kbId: number, data: { user_id: number; role: string }) => {
  return request({
    url: `/knowledge-bases/${kbId}/members`,
    method: 'post',
    data
  })
}

// 更新成员角色
export const updateKnowledgeBaseMember = (kbId: number, userId: number, data: { role: string }) => {
  return request({
    url: `/knowledge-bases/${kbId}/members/${userId}`,
    method: 'put',
    data
  })
}

// 移除成员
export const removeKnowledgeBaseMember = (kbId: number, userId: number) => {
  return request({
    url: `/knowledge-bases/${kbId}/members/${userId}`,
    method: 'delete'
  })
}

// 删除知识库
export const deleteKnowledgeBase = (id: number) => {
  return request({
    url: `/knowledge-bases/${id}`,
    method: 'delete'
  })
}

// 获取分类树
export const getCategories = () => {
  return request({
    url: '/knowledge-bases/categories',
    method: 'get'
  })
}

// 创建分类
export const createCategory = (data: any) => {
  return request({
    url: '/knowledge-bases/categories',
    method: 'post',
    data
  })
}

// 更新分类
export const updateCategory = (id: number, data: any) => {
  return request({
    url: `/knowledge-bases/categories/${id}`,
    method: 'put',
    data
  })
}

// 删除分类
export const deleteCategory = (id: number) => {
  return request({
    url: `/knowledge-bases/categories/${id}`,
    method: 'delete'
  })
}

// 获取标签列表
export const getTags = () => {
  return request({
    url: '/knowledge-bases/tags',
    method: 'get'
  })
}

// 创建标签
export const createTag = (data: any) => {
  return request({
    url: '/knowledge-bases/tags',
    method: 'post',
    data
  })
}

// 更新标签
export const updateTag = (id: number, data: any) => {
  return request({
    url: `/knowledge-bases/tags/${id}`,
    method: 'put',
    data
  })
}

// 删除标签
export const deleteTag = (id: number) => {
  return request({
    url: `/knowledge-bases/tags/${id}`,
    method: 'delete'
  })
}

// 获取热门标签
export const getPopularTags = () => {
  return request({
    url: '/knowledge-bases/tags/popular',
    method: 'get'
  })
}

// 推荐分类
export const suggestCategory = (documentId: number) => {
  return request({
    url: `/documents/${documentId}/suggest-category`,
    method: 'post'
  })
}

// 推荐标签
export const suggestTags = (documentId: number) => {
  return request({
    url: `/documents/${documentId}/suggest-tags`,
    method: 'post'
  })
}

// 批量推荐
export const batchSuggest = (documentIds: number[]) => {
  return request({
    url: '/documents/batch-suggest',
    method: 'post',
    data: { document_ids: documentIds }
  })
}
