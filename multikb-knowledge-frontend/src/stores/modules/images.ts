import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { searchByImage, searchByText, getImageList, searchImageViaQA } from '@/api/modules/images'
import { useQAStore } from './qa'

export const useImagesStore = defineStore('images', () => {
  const images = ref<any[]>([])
  const currentImage = ref<any>(null)
  const searchResults = ref<any[]>([])
  const loading = ref(false)
  const page = ref(1)
  const size = ref(20)
  const total = ref(0)

  const hasImages = computed(() => images.value.length > 0)
  const hasMore = computed(() => (page.value * size.value) < total.value)
  const hasResults = computed(() => searchResults.value.length > 0)

  const loadImages = async (params?: {
    knowledge_base_id?: number
    document_id?: number
  }) => {
    loading.value = true
    try {
      const res = await getImageList({
        page: page.value,
        size: size.value,
        ...params
      })
      images.value = res.data.results || []
      total.value = res.data.total || 0
    } catch (error) {
      console.error('Load images error:', error)
      images.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  const searchImagesByImage = async (imageFile: File, params?: {
    similarity_threshold?: number
    max_results?: number
  }) => {
    loading.value = true
    try {
      // 使用新的QA模块图片搜索接口
      const qaStore = useQAStore()
      
      // 确保有一个QA会话
      if (!qaStore.currentSessionId) {
        // 创建默认会话
        await qaStore.createSession({
          knowledge_base_id: 1,
          title: '图片搜索会话'
        })
      }
      
      if (!qaStore.currentSessionId) {
        throw new Error('无法创建QA会话')
      }
      
      const formData = new FormData()
      formData.append('image_file', imageFile)
      
      const res = await searchImageViaQA(qaStore.currentSessionId, formData, {
        search_type: 'image-to-image',
        similarity_threshold: params?.similarity_threshold || 0.7,
        max_results: params?.max_results || 20
      })
      
      searchResults.value = res.data.results || []
      return searchResults.value
    } catch (error) {
      console.error('Search by image error:', error)
      searchResults.value = []
      return []
    } finally {
      loading.value = false
    }
  }

  const searchImagesByText = async (query: string, params?: {
    similarity_threshold?: number
    max_results?: number
  }) => {
    loading.value = true
    try {
      // 使用新的QA模块图片搜索接口
      const qaStore = useQAStore()
      
      // 确保有一个QA会话
      if (!qaStore.currentSessionId) {
        // 创建默认会话
        await qaStore.createSession({
          knowledge_base_id: 1,
          title: '图片搜索会话'
        })
      }
      
      if (!qaStore.currentSessionId) {
        throw new Error('无法创建QA会话')
      }
      
      const formData = new FormData()
      formData.append('search_text', query)
      
      const res = await searchImageViaQA(qaStore.currentSessionId, formData, {
        search_type: 'text-to-image',
        similarity_threshold: params?.similarity_threshold || 0.7,
        max_results: params?.max_results || 20
      })
      
      searchResults.value = res.data.results || []
      return searchResults.value
    } catch (error) {
      console.error('Search by text error:', error)
      searchResults.value = []
      return []
    } finally {
      loading.value = false
    }
  }

  const selectImage = (image: any) => {
    currentImage.value = image
  }

  const nextPage = () => {
    if (hasMore.value) {
      page.value++
      loadImages()
    }
  }

  const reset = () => {
    images.value = []
    currentImage.value = null
    searchResults.value = []
    page.value = 1
  }

  const resetSearch = () => {
    searchResults.value = []
  }

  return {
    images,
    currentImage,
    searchResults,
    loading,
    page,
    size,
    total,
    hasImages,
    hasMore,
    hasResults,
    loadImages,
    searchImagesByImage,
    searchImagesByText,
    selectImage,
    nextPage,
    reset,
    resetSearch
  }
})
