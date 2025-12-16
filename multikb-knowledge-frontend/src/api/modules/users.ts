import request from '../utils/request'

export interface User {
  id: number
  username: string
  nickname?: string
  email: string
}

// 获取用户列表（用于下拉选择）
export const getUserList = () => {
  return request<{
    code: number
    message: string
    data: User[]
  }>({
    url: '/users/list',
    method: 'get'
  })
}
