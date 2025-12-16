import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadDocument } from '@/api/modules/documents'

export const useUpload = () => {
  const uploading = ref(false)
  const progress = ref(0)
  const uploadResult = ref<any>(null)

  const upload = async (file: File, knowledgeBaseId: number, categoryId?: number, tags?: string[]) => {
    uploading.value = true
    progress.value = 0

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('knowledge_base_id', String(knowledgeBaseId))
      if (categoryId) formData.append('category_id', String(categoryId))
      if (tags) formData.append('tags', JSON.stringify(tags))

      // 监听上传进度
      const config = {
        onUploadProgress: (progressEvent: any) => {
          if (progressEvent.total) {
            progress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
          }
        }
      }

      uploadResult.value = await uploadDocument(formData)
      ElMessage.success('上传成功')
      return uploadResult.value
    } catch (error: any) {
      ElMessage.error(error.message || '上传失败')
      throw error
    } finally {
      uploading.value = false
      progress.value = 0
    }
  }

  const reset = () => {
    progress.value = 0
    uploadResult.value = null
  }

  return {
    uploading,
    progress,
    uploadResult,
    upload,
    reset
  }
}
