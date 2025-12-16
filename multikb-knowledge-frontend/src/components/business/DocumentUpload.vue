<template>
  <div class="document-upload">
    <el-upload
      ref="uploadRef"
      class="upload-dragger"
      drag
      :action="uploadUrl"
      :data="uploadData"
      :on-success="handleSuccess"
      :on-error="handleError"
      :on-progress="handleProgress"
      :auto-upload="false"
      :show-file-list="false"
    >
      <el-icon class="el-icon--upload"><upload-filled /></el-icon>
      <div class="el-upload__text">
        将文件拖到此处，或<em>点击上传</em>
      </div>
      <template #tip>
        <div class="el-upload__tip">
          支持 PDF, DOCX, PPTX, TXT, MD 等格式，单个文件不超过100MB
        </div>
      </template>
    </el-upload>

    <div v-if="uploadedFiles.length > 0" class="uploaded-files">
      <div
        v-for="file in uploadedFiles"
        :key="file.id"
        class="file-item"
      >
        <el-icon><document /></el-icon>
        <span class="file-name">{{ file.name }}</span>
        <span class="file-size">{{ formatFileSize(file.size) }}</span>
        <el-progress :percentage="file.progress" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Document } from '@element-plus/icons-vue'
import { formatFileSize } from '@/utils/format'

const props = defineProps<{
  knowledgeBaseId: number
}>()

const emit = defineEmits(['success'])

const uploadRef = ref()
const uploadedFiles = ref<any[]>([])
const uploadUrl = '/api/v1/documents/upload'
const uploadData = ref({
  knowledge_base_id: props.knowledgeBaseId
})

const handleSuccess = (response: any) => {
  ElMessage.success('上传成功')
  emit('success', response)
}

const handleError = () => {
  ElMessage.error('上传失败')
}

const handleProgress = (event: any, file: any) => {
  const fileItem = uploadedFiles.value.find(f => f.uid === file.uid)
  if (fileItem) {
    fileItem.progress = Math.round((event.loaded / event.total) * 100)
  }
}

const submit = () => {
  uploadRef.value?.submit()
}
</script>

<style lang="scss" scoped>
.document-upload {
  .uploaded-files {
    margin-top: 20px;

    .file-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      border: 1px solid #e5e5e5;
      border-radius: 4px;
      margin-bottom: 12px;

      .file-name {
        flex: 1;
      }

      .file-size {
        color: #999;
        font-size: 12px;
      }
    }
  }
}
</style>
