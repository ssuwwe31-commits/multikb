import request from '../utils/request'

// 获取个人统计数据
export const getPersonalStatistics = (period: string = 'all') => {
  return request({
    url: '/statistics/personal',
    method: 'get',
    params: { period }
  })
}

// 获取数据趋势
export const getTrends = (params: {
  metric: string
  period?: string
  start_date?: string
  end_date?: string
}) => {
  return request({
    url: '/statistics/trends',
    method: 'get',
    params
  })
}

// 获取知识库使用热力图
export const getKnowledgeBasesHeatmap = () => {
  return request({
    url: '/statistics/knowledge-bases/heatmap',
    method: 'get'
  })
}

// 获取搜索热词
export const getSearchHotwords = (params?: {
  limit?: number
  period?: string
}) => {
  return request({
    url: '/statistics/search/hotwords',
    method: 'get',
    params
  })
}
