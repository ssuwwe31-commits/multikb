/**
 * 本地存储工具
 */

const PREFIX = 'spx_knowledge_'

// LocalStorage
export const localStorage = {
  set(key: string, value: any): void {
    try {
      window.localStorage.setItem(PREFIX + key, JSON.stringify(value))
    } catch (error) {
      console.error('LocalStorage set error:', error)
    }
  },

  get<T = any>(key: string): T | null {
    try {
      const item = window.localStorage.getItem(PREFIX + key)
      return item ? JSON.parse(item) : null
    } catch (error) {
      console.error('LocalStorage get error:', error)
      return null
    }
  },

  remove(key: string): void {
    try {
      window.localStorage.removeItem(PREFIX + key)
    } catch (error) {
      console.error('LocalStorage remove error:', error)
    }
  },

  clear(): void {
    try {
      const keys = Object.keys(window.localStorage)
      keys.forEach(key => {
        if (key.startsWith(PREFIX)) {
          window.localStorage.removeItem(key)
        }
      })
    } catch (error) {
      console.error('LocalStorage clear error:', error)
    }
  }
}

// SessionStorage
export const sessionStorage = {
  set(key: string, value: any): void {
    try {
      window.sessionStorage.setItem(PREFIX + key, JSON.stringify(value))
    } catch (error) {
      console.error('SessionStorage set error:', error)
    }
  },

  get<T = any>(key: string): T | null {
    try {
      const item = window.sessionStorage.getItem(PREFIX + key)
      return item ? JSON.parse(item) : null
    } catch (error) {
      console.error('SessionStorage get error:', error)
      return null
    }
  },

  remove(key: string): void {
    try {
      window.sessionStorage.removeItem(PREFIX + key)
    } catch (error) {
      console.error('SessionStorage remove error:', error)
    }
  },

  clear(): void {
    try {
      const keys = Object.keys(window.sessionStorage)
      keys.forEach(key => {
        if (key.startsWith(PREFIX)) {
          window.sessionStorage.removeItem(key)
        }
      })
    } catch (error) {
      console.error('SessionStorage clear error:', error)
    }
  }
}
