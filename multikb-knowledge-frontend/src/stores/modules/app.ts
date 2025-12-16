import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  // 状态
  const appTitle = ref<string>('MultiKB Knowledge Base')
  const sidebarCollapsed = ref<boolean>(false)
  const loading = ref<boolean>(false)

  // Actions
  const initApp = () => {
    console.log('App initialized')
  }

  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  const setLoading = (value: boolean) => {
    loading.value = value
  }

  return {
    appTitle,
    sidebarCollapsed,
    loading,
    initApp,
    toggleSidebar,
    setLoading
  }
})
