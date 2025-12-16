import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { search } from '@/api/modules/search'
import { debounce } from '@/utils/common'

export const useSearch = () => {
  const query = ref('')
  const searchType = ref<'vector' | 'keyword' | 'hybrid' | 'exact' | 'fuzzy'>('hybrid')
  const results = ref<any[]>([])
  const loading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const size = ref(20)

  const hasResults = computed(() => results.value.length > 0)
  const hasMore = computed(() => (page.value * size.value) < total.value)

  const performSearch = async (params?: {
    knowledge_base_id?: number
    category_id?: number
    similarity_threshold?: number
  }) => {
    if (!query.value.trim()) {
      ElMessage.warning('请输入搜索关键词')
      return
    }

    loading.value = true
    try {
      const res = await search({
        query: query.value,
        search_type: searchType.value,
        page: page.value,
        size: size.value,
        ...params
      })
      const payload: any = (res && (res as any).data !== undefined) ? (res as any).data : res
      const list: any[] = Array.isArray(payload) ? payload : (payload?.results || [])
      const totalCount: number = Array.isArray(payload) ? payload.length : (payload?.total || 0)
      results.value = list
      total.value = totalCount
    } catch (error) {
      ElMessage.error('搜索失败')
      results.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  const debouncedSearch = debounce(performSearch, 300)

  const handleSearch = () => {
    page.value = 1
    performSearch()
  }

  const handleInputChange = () => {
    if (query.value.trim()) {
      debouncedSearch()
    }
  }

  const loadMore = () => {
    if (hasMore.value && !loading.value) {
      page.value++
      performSearch()
    }
  }

  const reset = () => {
    query.value = ''
    searchType.value = 'hybrid'
    results.value = []
    total.value = 0
    page.value = 1
  }

  return {
    query,
    searchType,
    results,
    loading,
    total,
    page,
    size,
    hasResults,
    hasMore,
    performSearch,
    handleSearch,
    handleInputChange,
    loadMore,
    reset
  }
}
