import request from '../utils/request'
import { API_BASE_URL } from '@/config/api'

// 用户信息类型
export interface UserInfo {
  id: number
  username: string
  email: string
  nickname?: string
  avatar_url?: string
  phone?: string
  status: string
  email_verified: boolean
  last_login_at?: string
  created_at: string
}

// 注册请求
export interface RegisterRequest {
  username: string
  email: string
  password: string
  nickname?: string
}

// 注册响应
export interface RegisterResponse {
  user_id: number
  username: string
  email: string
  email_verified: boolean
  created_at: string
}

// 登录请求
export interface LoginRequest {
  username: string
  password: string
}

// 登录响应
export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: UserInfo
}

// Token刷新请求
export interface TokenRefreshRequest {
  refresh_token: string
}

// Token刷新响应
export interface TokenRefreshResponse {
  access_token: string
  refresh_token: string
  expires_in: number
}

// 用户注册
export const register = (data: RegisterRequest) => {
  return request<RegisterResponse>({
    url: '/auth/register',
    method: 'post',
    data
  })
}

// 用户登录
export const login = (data: LoginRequest) => {
  return request<LoginResponse>({
    url: '/auth/login',
    method: 'post',
    data
  })
}

// 刷新Token
export const refreshToken = (data: TokenRefreshRequest) => {
  return request<TokenRefreshResponse>({
    url: '/auth/refresh',
    method: 'post',
    data
  })
}

// 用户登出
export const logout = (refresh_token?: string) => {
  return request({
    url: '/auth/logout',
    method: 'post',
    data: refresh_token ? { refresh_token } : {}
  })
}

// 获取当前用户信息
export const getCurrentUser = () => {
  return request<UserInfo>({
    url: '/auth/me',
    method: 'get'
  })
}

// 获取Token刷新URL（用于WebSocket）
export const getRefreshURL = () => {
  return `${API_BASE_URL}/auth/refresh`
}
