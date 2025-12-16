import request from '../utils/request'

// 获取失败任务列表
export const getFailureTasks = (params: {
  task_type?: 'document' | 'image'
  knowledge_base_id?: number
  page?: number
  size?: number
}) => {
  return request({
    url: '/tasks/failures',
    method: 'get',
    params
  })
}

// 重试单个任务
export const retryTask = (taskId: number, taskType: 'document' | 'image') => {
  return request({
    url: `/tasks/failures/${taskId}/retry`,
    method: 'post',
    params: { task_type: taskType }
  })
}

// 批量重试任务
export const batchRetryTasks = (data: {
  task_ids: number[]
  task_type: 'document' | 'image'
}) => {
  return request({
    url: '/tasks/failures/batch-retry',
    method: 'post',
    data
  })
}
