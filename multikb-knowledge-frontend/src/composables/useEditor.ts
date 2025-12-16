import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { updateDocumentContent } from '@/api/modules/documents'

export const useEditor = () => {
  const content = ref('')
  const originalContent = ref('')
  const loading = ref(false)
  const saving = ref(false)

  const hasChanges = computed(() => content.value !== originalContent.value)

  const loadContent = (text: string) => {
    content.value = text
    originalContent.value = text
  }

  const updateContent = (text: string) => {
    content.value = text
  }

  const saveContent = async (documentId: number, chunkId: number) => {
    if (!hasChanges.value) {
      ElMessage.info('没有修改')
      return false
    }

    saving.value = true
    try {
      await updateDocumentContent(documentId, chunkId, {
        content: content.value
      })
      originalContent.value = content.value
      ElMessage.success('保存成功')
      return true
    } catch (error) {
      ElMessage.error('保存失败')
      return false
    } finally {
      saving.value = false
    }
  }

  const reset = () => {
    content.value = originalContent.value
  }

  const undo = () => {
    content.value = originalContent.value
  }

  return {
    content,
    originalContent,
    loading,
    saving,
    hasChanges,
    loadContent,
    updateContent,
    saveContent,
    reset,
    undo
  }
}
