import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { search } from '@/api/modules/search'

export const useSearchStore = defineStore('search', () => {
  const query = ref('')
  const searchType = ref<'vector' | 'keyword' | 'hybrid' | 'exact' | 'fuzzy'>('hybrid')
  const results = ref<any[]>([])
  const documents = ref<any[]>([])
  const images = ref<any[]>([])
  const total = ref(0)
  const page = ref(1)
  const size = ref(20)
  const loading = ref(false)

  const hasResults = computed(() => results.value.length > 0)
  const hasMore = computed(() => (page.value * size.value) < total.value)
  const documentCount = computed(() => documents.value.length)
  const imageCount = computed(() => images.value.length)

  const performSearch = async (params?: {
    knowledge_base_id?: number
    category_id?: number
    similarity_threshold?: number
  }) => {
    if (!query.value.trim()) {
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

      const payload: any = (res && res.data !== undefined) ? res.data : res
      const list: any[] = Array.isArray(payload) ? payload : (payload?.results || [])
      const totalCount: number = Array.isArray(payload) ? payload.length : (payload?.total || 0)

      results.value = list
      documents.value = list.filter(item => item.type === 'document')
      images.value = list.filter(item => item.type === 'image')
      total.value = totalCount
    } catch (error) {
      console.error('Search error:', error)
      results.value = []
      documents.value = []
      images.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  const reset = () => {
    query.value = ''
    searchType.value = 'hybrid'
    results.value = []
    documents.value = []
    images.value = []
    total.value = 0
    page.value = 1
  }

  const nextPage = () => {
    if (hasMore.value) {
      page.value++
      performSearch()
    }
  }

  const setQuery = (text: string) => {
    query.value = text
  }

  const setSearchType = (type: 'vector' | 'keyword' | 'hybrid' | 'exact' | 'fuzzy') => {
    searchType.value = type
  }

  return {
    query,
    searchType,
    results,
    documents,
    images,
    total,
    page,
    size,
    loading,
    hasResults,
    hasMore,
    documentCount,
    imageCount,
    performSearch,
    reset,
    nextPage,
    setQuery,
    setSearchType
  }
})
