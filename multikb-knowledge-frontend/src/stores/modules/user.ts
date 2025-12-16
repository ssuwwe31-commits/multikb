import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login, logout, getCurrentUser, refreshToken, type UserInfo, type LoginRequest } from '@/api/modules/auth'
import { ElMessage } from 'element-plus'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  // 状态
  const user = ref<UserInfo | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshTokenValue = ref<string | null>(localStorage.getItem('refresh_token'))
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)

  // 初始化：从localStorage恢复token
  const initUser = () => {
    const token = localStorage.getItem('access_token')
    const refresh = localStorage.getItem('refresh_token')
    if (token) {
      accessToken.value = token
    }
    if (refresh) {
      refreshTokenValue.value = refresh
    }
    // 如果有token，尝试获取用户信息
    if (token) {
      fetchUserInfo().catch(() => {
        // 如果获取失败，清除token
        clearAuth()
      })
    }
  }

  // 登录
  const userLogin = async (loginData: LoginRequest) => {
    try {
      const res = await login(loginData)
      // 响应拦截器已经返回了 response.data，所以 res 就是响应数据本身
      const { access_token, refresh_token, user: userInfo } = res

      // 保存token和用户信息
      accessToken.value = access_token
      refreshTokenValue.value = refresh_token
      user.value = userInfo

      // 保存到localStorage
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)

      ElMessage.success('登录成功')
      return true
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || '登录失败'
      ElMessage.error(message)
      return false
    }
  }

  // 登出
  const userLogout = async () => {
    try {
      if (refreshTokenValue.value) {
        await logout(refreshTokenValue.value)
      }
    } catch (error) {
      console.error('登出错误:', error)
    } finally {
      clearAuth()
      ElMessage.success('已登出')
      router.push('/login')
    }
  }

  // 清除认证信息
  const clearAuth = () => {
    user.value = null
    accessToken.value = null
    refreshTokenValue.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  // 获取用户信息
  const fetchUserInfo = async () => {
    try {
      const res = await getCurrentUser()
      // 响应拦截器已经返回了 response.data，所以 res 就是响应数据本身
      user.value = res
      return user.value
    } catch (error: any) {
      // 如果401，可能是token过期，尝试刷新
      if (error.response?.status === 401) {
        const refreshed = await tryRefreshToken()
        if (refreshed) {
          // 刷新成功，重试获取用户信息
          return await fetchUserInfo()
        }
      }
      throw error
    }
  }

  // 刷新Token
  const tryRefreshToken = async (): Promise<boolean> => {
    if (!refreshTokenValue.value) {
      return false
    }

    try {
      const res = await refreshToken({ refresh_token: refreshTokenValue.value })
      // 响应拦截器已经返回了 response.data，所以 res 就是响应数据本身
      const { access_token, refresh_token: new_refresh_token } = res

      // 更新token
      accessToken.value = access_token
      refreshTokenValue.value = new_refresh_token
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', new_refresh_token)

      return true
    } catch (error) {
      // 刷新失败，清除认证信息
      clearAuth()
      return false
    }
  }

  // 更新用户信息（从外部更新后调用）
  const updateUser = (userInfo: UserInfo) => {
    user.value = userInfo
  }

  return {
    user,
    accessToken,
    refreshTokenValue,
    isAuthenticated,
    initUser,
    userLogin,
    userLogout,
    clearAuth,
    fetchUserInfo,
    tryRefreshToken,
    updateUser
  }
})
