/**
 * 错误处理工具
 */

import { ElMessage, ElMessageBox } from 'element-plus'

export enum ErrorCode {
  // 内容验证错误
  VALIDATION_LENGTH_ERROR = 7001,
  VALIDATION_FORMAT_ERROR = 7002,
  VALIDATION_ENCODING_ERROR = 7003,
  
  // 修改处理错误
  CHUNK_NOT_FOUND = 7004,
  PERMISSION_DENIED = 7005,
  VERSION_CONFLICT = 7006,
  
  // 向量化错误
  VECTORIZATION_FAILED = 7007,
  MODEL_UNAVAILABLE = 7008,
  
  // 索引更新错误
  INDEX_UPDATE_FAILED = 7009,
  CACHE_UPDATE_FAILED = 7010,
  
  // 网络错误
  NETWORK_ERROR = 8001,
  TIMEOUT_ERROR = 8002,
  SERVER_ERROR = 8003
}

export interface ErrorInfo {
  code: ErrorCode
  message: string
  details?: any
  retryable?: boolean
}

const errorMessages: Record<ErrorCode, string> = {
  [ErrorCode.VALIDATION_LENGTH_ERROR]: '内容长度超过限制',
  [ErrorCode.VALIDATION_FORMAT_ERROR]: '内容格式不正确',
  [ErrorCode.VALIDATION_ENCODING_ERROR]: '字符编码错误',
  [ErrorCode.CHUNK_NOT_FOUND]: '块不存在或已被删除',
  [ErrorCode.PERMISSION_DENIED]: '没有修改权限',
  [ErrorCode.VERSION_CONFLICT]: '版本冲突，请刷新后重试',
  [ErrorCode.VECTORIZATION_FAILED]: '向量化失败，请检查Ollama服务',
  [ErrorCode.MODEL_UNAVAILABLE]: '向量化模型不可用',
  [ErrorCode.INDEX_UPDATE_FAILED]: '索引更新失败，请检查OpenSearch服务',
  [ErrorCode.CACHE_UPDATE_FAILED]: '缓存更新失败，请检查Redis服务',
  [ErrorCode.NETWORK_ERROR]: '网络连接错误',
  [ErrorCode.TIMEOUT_ERROR]: '请求超时',
  [ErrorCode.SERVER_ERROR]: '服务器错误'
}

/**
 * 解析错误
 */
export const parseError = (error: any): ErrorInfo => {
  if (error.response) {
    const code = error.response.data?.error_code || ErrorCode.SERVER_ERROR
    const message = error.response.data?.message || errorMessages[code] || '未知错误'
    
    return {
      code,
      message,
      details: error.response.data,
      retryable: isRetryable(code)
    }
  }
  
  if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
    return {
      code: ErrorCode.TIMEOUT_ERROR,
      message: errorMessages[ErrorCode.TIMEOUT_ERROR],
      retryable: true
    }
  }
  
  if (error.code === 'ERR_NETWORK') {
    return {
      code: ErrorCode.NETWORK_ERROR,
      message: errorMessages[ErrorCode.NETWORK_ERROR],
      retryable: true
    }
  }
  
  return {
    code: ErrorCode.SERVER_ERROR,
    message: error.message || '未知错误',
    retryable: false
  }
}

/**
 * 判断错误是否可重试
 */
const isRetryable = (code: ErrorCode): boolean => {
  const retryableCodes = [
    ErrorCode.NETWORK_ERROR,
    ErrorCode.TIMEOUT_ERROR,
    ErrorCode.VECTORIZATION_FAILED,
    ErrorCode.MODEL_UNAVAILABLE,
    ErrorCode.INDEX_UPDATE_FAILED,
    ErrorCode.CACHE_UPDATE_FAILED
  ]
  return retryableCodes.includes(code)
}

/**
 * 显示错误消息
 */
export const showError = (error: any) => {
  const errorInfo = parseError(error)
  
  ElMessage({
    message: errorInfo.message,
    type: 'error',
    duration: 5000
  })
}

/**
 * 重试机制
 */
export const retryOperation = async <T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  delay: number = 1000
): Promise<T> => {
  let lastError: any
  
  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await operation()
    } catch (error) {
      lastError = error
      
      if (i < maxRetries) {
        const errorInfo = parseError(error)
        
        if (errorInfo.retryable) {
          console.log(`重试 ${i + 1}/${maxRetries}...`)
          await new Promise(resolve => setTimeout(resolve, delay * (i + 1)))
          continue
        } else {
          throw error
        }
      }
    }
  }
  
  throw lastError
}

/**
 * 确认重试对话框
 */
export const showRetryDialog = async (error: any): Promise<boolean> => {
  const errorInfo = parseError(error)
  
  if (!errorInfo.retryable) {
    showError(error)
    return false
  }
  
  try {
    await ElMessageBox.confirm(
      `${errorInfo.message}\n\n是否重试？`,
      '操作失败',
      {
        confirmButtonText: '重试',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    return true
  } catch {
    return false
  }
}

/**
 * 错误分类
 */
export const categorizeError = (error: any): string => {
  const errorInfo = parseError(error)
  
  if ([ErrorCode.VALIDATION_LENGTH_ERROR, ErrorCode.VALIDATION_FORMAT_ERROR, ErrorCode.VALIDATION_ENCODING_ERROR].includes(errorInfo.code)) {
    return 'validation'
  }
  
  if ([ErrorCode.CHUNK_NOT_FOUND, ErrorCode.PERMISSION_DENIED, ErrorCode.VERSION_CONFLICT].includes(errorInfo.code)) {
    return 'processing'
  }
  
  if ([ErrorCode.VECTORIZATION_FAILED, ErrorCode.MODEL_UNAVAILABLE].includes(errorInfo.code)) {
    return 'vectorization'
  }
  
  if ([ErrorCode.INDEX_UPDATE_FAILED, ErrorCode.CACHE_UPDATE_FAILED].includes(errorInfo.code)) {
    return 'indexing'
  }
  
  if ([ErrorCode.NETWORK_ERROR, ErrorCode.TIMEOUT_ERROR].includes(errorInfo.code)) {
    return 'network'
  }
  
  return 'unknown'
}

/**
 * 错误日志
 */
export const logError = (error: any, context: string) => {
  const errorInfo = parseError(error)
  const category = categorizeError(error)
  
  console.error(`[${category}] ${context}:`, {
    code: errorInfo.code,
    message: errorInfo.message,
    details: errorInfo.details,
    timestamp: new Date().toISOString()
  })
}
