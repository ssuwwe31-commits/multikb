import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getDocuments } from '@/api/modules/documents'
import type { Document, PaginationResult } from '@/types'

export const useDocumentsStore = defineStore('documents', () => {
  // 状态
  const list = ref<Document[]>([])
  const current = ref<Document | null>(null)
  const loading = ref(false)
  const total = ref(0)

  // Actions
  const fetchList = async (params?: { 
    knowledge_base_id?: number
    page?: number
    size?: number
  }) => {
    loading.value = true
    try {
      const res = await getDocuments(params || {})
      // 后端返回格式: { code: 0, message: "ok", data: { list: [], total: 0 } }
      // 响应拦截器已经返回了 response.data，所以 res 就是响应数据本身
      if (res && typeof res === 'object') {
        if (res.code === 0 && res.data) {
          list.value = res.data.list || res.data.items || []
          total.value = res.data.total || 0
        } else if (res.data) {
          // 兼容没有 code 字段的格式
          list.value = res.data.list || res.data.items || []
          total.value = res.data.total || 0
        } else if (Array.isArray(res)) {
          // 兼容直接返回数组的格式
          list.value = res
          total.value = res.length
        } else {
          list.value = []
          total.value = 0
        }
      } else {
        list.value = []
        total.value = 0
      }
    } catch (error: any) {
      // 发生错误时，设置为空数组，不报错
      list.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  const setCurrent = (doc: Document) => {
    current.value = doc
  }

  const clear = () => {
    list.value = []
    current.value = null
    total.value = 0
  }

  return {
    list,
    current,
    loading,
    total,
    fetchList,
    setCurrent,
    clear
  }
})
