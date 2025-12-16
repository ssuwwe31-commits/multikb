/**
 * API配置
 * 统一管理后端API地址，方便切换环境
 * 
 * 使用方式：
 * 1. 开发环境：在项目根目录创建 .env 文件，设置环境变量
 * 2. 生产环境：在构建时通过环境变量设置
 * 
 * 环境变量：
 * - VITE_API_BASE_URL: API基础地址（包含 /api 后缀），例如: http://localhost:8000/api
 * - VITE_WS_BASE_URL: WebSocket基础地址（包含协议），例如: ws://localhost:8000
 */

// API基础地址（默认值：localhost:8000）
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

// WebSocket基础地址（默认值：localhost:8000）
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'

// 从API地址提取主机和端口（用于Vite代理配置）
export const getBackendHost = (): string => {
  try {
    const url = new URL(API_BASE_URL.replace('/api', ''))
    return `${url.protocol}//${url.host}`
  } catch {
    return 'http://localhost:8000'
  }
}
