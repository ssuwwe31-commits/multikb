import request from '../utils/request'
import { API_BASE_URL } from '@/config/api'

// 导出知识库
export const exportKnowledgeBase = (kbId: number, data: {
  format: string
  include_documents?: boolean
  include_chunks?: boolean
}) => {
  return request({
    url: `/exports/knowledge-bases/${kbId}/export`,
    method: 'post',
    data
  })
}

// 导出文档
export const exportDocument = (docId: number, data: {
  format: string
  include_chunks?: boolean
  include_images?: boolean
  export_original?: boolean
}) => {
  return request({
    url: `/exports/documents/${docId}/export`,
    method: 'post',
    data
  })
}

// 批量导出文档
export const batchExportDocuments = (data: {
  document_ids: number[]
  format: string
  include_chunks?: boolean
  include_images?: boolean
  export_original?: boolean
}) => {
  return request({
    url: '/exports/documents/batch/export',
    method: 'post',
    data
  })
}

// 导出问答历史
export const exportQAHistory = (data: {
  format: string
  session_id?: number
  start_date?: string
  end_date?: string
}) => {
  return request({
    url: '/exports/qa/history/export',
    method: 'post',
    data
  })
}

// 获取导出任务列表
export const getExportTasks = (params?: {
  status?: string
  limit?: number
  offset?: number
}) => {
  return request({
    url: '/exports',
    method: 'get',
    params
  })
}

// 查询导出任务状态
export const getExportTask = (taskId: number) => {
  return request({
    url: `/exports/${taskId}`,
    method: 'get'
  })
}

// 删除导出任务
export const deleteExportTask = (taskId: number) => {
  return request({
    url: `/exports/${taskId}`,
    method: 'delete'
  })
}

// 下载导出文件
export const downloadExportFile = async (taskId: number) => {
  const axios = (await import('axios')).default
  const token = localStorage.getItem('access_token')
  
  const response = await axios.get(
    `${API_BASE_URL}/exports/${taskId}/download`,
    {
      responseType: 'blob',
      headers: {
        Authorization: token ? `Bearer ${token}` : ''
      }
    }
  )
  
  return response.data
}
