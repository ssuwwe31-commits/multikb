import request from '../utils/request'
import type { UserInfo } from './auth'

// 更新用户信息请求
export interface UserUpdateRequest {
  nickname?: string
  avatar_url?: string
  phone?: string
  preferences?: Record<string, any>
}

// 修改密码请求
export interface PasswordChangeRequest {
  old_password: string
  new_password: string
}

// 邮箱验证请求
export interface EmailVerifyRequest {
  email: string
}

// 邮箱验证响应
export interface EmailVerifyResponse {
  email: string
  expires_in: number
}

// 邮箱确认请求
export interface EmailConfirmRequest {
  email: string
  verification_code: string
}

// 邮箱确认响应
export interface EmailConfirmResponse {
  email: string
  email_verified: boolean
}

// 更新用户信息
export const updateUserInfo = (data: UserUpdateRequest) => {
  return request<UserInfo>({
    url: '/users/me',
    method: 'put',
    data
  })
}

// 修改密码
export const changePassword = (data: PasswordChangeRequest) => {
  return request({
    url: '/users/me/password',
    method: 'post',
    data
  })
}

// 发送邮箱验证码
export const sendEmailVerification = (data: EmailVerifyRequest) => {
  return request<EmailVerifyResponse>({
    url: '/users/me/email/verify',
    method: 'post',
    data
  })
}

// 验证邮箱
export const confirmEmail = (data: EmailConfirmRequest) => {
  return request<EmailConfirmResponse>({
    url: '/users/me/email/confirm',
    method: 'post',
    data
  })
}
