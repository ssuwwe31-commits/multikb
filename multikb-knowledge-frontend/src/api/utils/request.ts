import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAppStore } from '@/stores/modules/app'
import { API_BASE_URL } from '@/config/api'

const service = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000 // 2 分钟，避免 rerank 等长耗时请求超时
})

// 请求拦截器
service.interceptors.request.use(
  (config) => {
    const appStore = useAppStore()
    
    // 添加loading
    appStore.setLoading(true)
    
    // 添加token（如果有）
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // 如果是 FormData，让浏览器自动设置 Content-Type（包括 boundary）
    // 不要手动设置，否则会丢失 boundary 信息
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    
    return config
  },
  (error) => {
    appStore.setLoading(false)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  (response) => {
    const appStore = useAppStore()
    appStore.setLoading(false)
    
    const res = response.data
    
    // 检查响应格式：如果有 code 字段，需要验证
    if (res && typeof res === 'object' && 'code' in res) {
      if (res.code !== 200 && res.code !== 0 && res.code !== 201) {
        if (res.code === 401) {
          // 401 未授权，清除认证信息并跳转登录
          // 使用 Promise 异步处理，避免在响应拦截器中直接使用 async
          Promise.resolve().then(async () => {
            const { useUserStore } = await import('@/stores/modules/user')
            const userStore = useUserStore()
            userStore.clearAuth()
            
            // 避免在登录页面重复跳转
            if (window.location.pathname !== '/login') {
              const { default: router } = await import('@/router')
              router.push('/login')
              ElMessage.warning('登录已过期，请重新登录')
            }
          })
          
          const authError = new Error(res.message || 'Not authenticated')
          Object.assign(authError, { isAuthError: true, code: 401 })
          return Promise.reject(authError)
        }
        ElMessage.error(res.message || 'Error')
        return Promise.reject(new Error(res.message || 'Error'))
      }
    }
    // 兼容 success 字段的响应格式（后端使用 SuccessResponse）
    if (res && typeof res === 'object' && 'success' in res && !('code' in res)) {
      if (res.success === false) {
        ElMessage.error(res.message || 'Error')
        return Promise.reject(new Error(res.message || 'Error'))
      }
      // success 为 true 时，正常返回响应
    }
    // 如果没有 code 或 success 字段，直接返回响应（兼容直接返回数据的格式）
    return res
  },
  async (error) => {
    const appStore = useAppStore()
    appStore.setLoading(false)
    
    // 处理401错误：尝试刷新Token
    // 跳过刷新请求本身（/auth/refresh），避免循环刷新
    const isRefreshRequest = error.config?.url?.includes('/auth/refresh')
    if (error.response?.status === 401 && !isRefreshRequest) {
      const refreshTokenValue = localStorage.getItem('refresh_token')
      if (refreshTokenValue && !error.config._retry) {
        error.config._retry = true
        
        try {
          // 尝试刷新Token
          const { useUserStore } = await import('@/stores/modules/user')
          const userStore = useUserStore()
          const refreshed = await userStore.tryRefreshToken()
          
          if (refreshed) {
            // 刷新成功，更新请求头并重试
            const newToken = localStorage.getItem('access_token')
            if (newToken) {
              error.config.headers.Authorization = `Bearer ${newToken}`
              return service.request(error.config)
            }
          }
        } catch (refreshError) {
          // 刷新失败，清除认证信息并跳转登录
          // 静默处理，避免产生过多错误提示
          const { useUserStore } = await import('@/stores/modules/user')
          const userStore = useUserStore()
          userStore.clearAuth()
          
          // 避免在登录页面重复跳转
          if (window.location.pathname !== '/login') {
            const { default: router } = await import('@/router')
            router.push('/login')
            ElMessage.warning('登录已过期，请重新登录')
          }
        }
      } else {
        // 没有 refresh_token 或已经重试过，直接跳转登录
        const { useUserStore } = await import('@/stores/modules/user')
        const userStore = useUserStore()
        userStore.clearAuth()
        
        // 避免在登录页面重复跳转
        if (window.location.pathname !== '/login') {
          const { default: router } = await import('@/router')
          router.push('/login')
          ElMessage.warning('登录已过期，请重新登录')
        }
      }
    }
    
    let message = '请求失败'
    if (error.response) {
      // FastAPI HTTPException 返回格式: {detail: "..."}
      const detail = error.response.data?.detail
      if (detail) {
        message = typeof detail === 'string' ? detail : JSON.stringify(detail)
      } else {
        message = error.response.data?.message || error.message
      }
      // 只在非 404 错误时显示错误消息（404 可能是正常的业务逻辑）
      if (error.response.status !== 404 && error.response.status !== 401) {
        ElMessage.error(message)
      }
    }
    
    return Promise.reject(error)
  }
)

export default service
