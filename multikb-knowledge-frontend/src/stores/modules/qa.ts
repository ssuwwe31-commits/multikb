import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getQASessions, createQASession, deleteQASession, getSearchTypes, getAvailableModels } from '@/api/modules/qa'

// 查询方式类型定义
export type QueryMethod = 'vector' | 'keyword' | 'hybrid' | 'exact' | 'fuzzy' | 'multimodal'

// 输入类型定义
export type InputType = 'text' | 'image' | 'multimodal'

export const useQAStore = defineStore('qa', () => {
  const sessions = ref<any[]>([])
  const currentSession = ref<any>(null)
  const messages = ref<any[]>([])
  const selectedKnowledgeBaseId = ref<number | null>(null)
  const queryMethod = ref<QueryMethod>('hybrid')
  const inputType = ref<InputType>('text')
  const loading = ref(false)
  const streaming = ref(false)
  const searchTypes = ref<any[]>([])
  const availableModels = ref<any[]>([])
  const citations = ref<any[]>([])
  const fallbackLevel = ref<'knowledge_base' | 'llm' | 'no_info'>('knowledge_base')

  const hasSessions = computed(() => sessions.value.length > 0)
  const currentSessionId = computed(() => currentSession.value?.id)
  const isStreaming = computed(() => streaming.value)

  const loadSessions = async () => {
    loading.value = true
    try {
      const res = await getQASessions({ page: 1, size: 100 })
      sessions.value = res.data.results || []
    } catch (error) {
      console.error('Load sessions error:', error)
    } finally {
      loading.value = false
    }
  }

  const createSession = async (knowledgeBaseId: number) => {
    loading.value = true
    try {
      const res = await createQASession({
        knowledge_base_id: knowledgeBaseId
      })
      const newSession = res.data
      sessions.value.unshift(newSession)
      currentSession.value = newSession
      messages.value = []
      selectedKnowledgeBaseId.value = knowledgeBaseId
      return newSession
    } catch (error) {
      console.error('Create session error:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  const selectSession = (session: any) => {
    currentSession.value = session
    selectedKnowledgeBaseId.value = session.knowledge_base_id
  }

  const deleteSession = async (sessionId: number) => {
    loading.value = true
    try {
      await deleteQASession(sessionId)
      sessions.value = sessions.value.filter(s => s.id !== sessionId)
      if (currentSession.value?.id === sessionId) {
        currentSession.value = null
        messages.value = []
      }
    } catch (error) {
      console.error('Delete session error:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  const addMessage = (message: any) => {
    messages.value.push(message)
  }

  const setQueryMethod = (method: QueryMethod) => {
    queryMethod.value = method
  }

  const setInputType = (type: InputType) => {
    inputType.value = type
  }

  const setFallbackLevel = (level: 'knowledge_base' | 'llm' | 'no_info') => {
    fallbackLevel.value = level
  }

  const loadSearchTypes = async () => {
    try {
      const res = await getSearchTypes()
      searchTypes.value = res.data || []
    } catch (error) {
      console.error('Load search types error:', error)
    }
  }

  const loadAvailableModels = async () => {
    try {
      const res = await getAvailableModels()
      availableModels.value = res.data || []
    } catch (error) {
      console.error('Load models error:', error)
    }
  }

  const addCitation = (citation: any) => {
    citations.value.push(citation)
  }

  const clearCitations = () => {
    citations.value = []
  }

  const setStreaming = (value: boolean) => {
    streaming.value = value
  }

  const reset = () => {
    currentSession.value = null
    messages.value = []
    selectedKnowledgeBaseId.value = null
    streaming.value = false
    citations.value = []
    fallbackLevel.value = 'knowledge_base'
  }

  return {
    sessions,
    currentSession,
    messages,
    selectedKnowledgeBaseId,
    queryMethod,
    inputType,
    loading,
    streaming,
    searchTypes,
    availableModels,
    citations,
    fallbackLevel,
    hasSessions,
    currentSessionId,
    isStreaming,
    loadSessions,
    createSession,
    selectSession,
    deleteSession,
    addMessage,
    setQueryMethod,
    setInputType,
    setFallbackLevel,
    loadSearchTypes,
    loadAvailableModels,
    addCitation,
    clearCitations,
    setStreaming,
    reset
  }
})
