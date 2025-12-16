<template>
  <el-dialog v-model="visible" :title="`预览: ${fileName}`" width="900px" top="5vh">
    <div class="file-preview">
      <!-- 图片预览 -->
      <div v-if="isImage" class="image-preview">
        <img :src="previewUrl" alt="preview" class="preview-image" />
      </div>

      <!-- 文本预览 -->
      <div v-else-if="isText" class="text-preview">
        <pre class="preview-content">{{ textContent }}</pre>
      </div>

      <!-- PDF预览 -->
      <div v-else-if="isPdf" class="pdf-preview">
        <iframe :src="previewUrl" class="pdf-iframe" />
      </div>

      <!-- 不支持预览 -->
      <div v-else class="unsupported-preview">
        <el-empty description="该文件类型暂不支持在线预览">
          <el-button type="primary" @click="downloadFile">
            下载文件
          </el-button>
        </el-empty>
      </div>

      <!-- 文件信息 -->
      <el-descriptions :column="2" border class="file-info">
        <el-descriptions-item label="文件名">{{ fileName }}</el-descriptions-item>
        <el-descriptions-item label="文件类型">{{ fileType }}</el-descriptions-item>
        <el-descriptions-item label="文件大小">{{ fileSize }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ createdTime }}</el-descriptions-item>
      </el-descriptions>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { formatFileSize } from '@/utils/format'

const props = defineProps<{
  modelValue: boolean
  file: any
}>()

const emit = defineEmits(['update:modelValue', 'download'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const fileName = computed(() => props.file?.name || props.file?.file_name || '未知文件')
const fileType = computed(() => {
  if (!props.file) return 'unknown'
  const name = props.file.name || props.file.file_name || ''
  const ext = name.split('.').pop()?.toLowerCase() || ''
  return ext
})

const isImage = computed(() => {
  const imageTypes = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg']
  return imageTypes.includes(fileType.value)
})

const isText = computed(() => {
  const textTypes = ['txt', 'md', 'json', 'xml', 'csv', 'log']
  return textTypes.includes(fileType.value)
})

const isPdf = computed(() => fileType.value === 'pdf')

const previewUrl = computed(() => props.file?.url || props.file?.preview_url)

const textContent = ref('')

// 加载文本内容
const loadTextContent = async () => {
  if (!isText.value) return
  
  try {
    // 如果是URL，需要fetch
    if (previewUrl.value) {
      const response = await fetch(previewUrl.value)
      textContent.value = await response.text()
    }
  } catch (error) {
    ElMessage.error('加载文件内容失败')
  }
}

// 下载文件
const downloadFile = () => {
  if (props.file) {
    emit('download', props.file)
    ElMessage.success('文件下载中...')
  }
}

// 监听visible变化，加载内容
watch(() => props.modelValue, (val) => {
  if (val && isText.value) {
    loadTextContent()
  }
})

const fileSize = computed(() => {
  if (!props.file?.size) return '未知'
  return formatFileSize(props.file.size)
})

const createdTime = computed(() => {
  if (!props.file?.created_at) return '未知'
  return new Date(props.file.created_at).toLocaleString('zh-CN')
})
</script>

<style lang="scss" scoped>
.file-preview {
  .image-preview {
    text-align: center;
    margin-bottom: 20px;
    max-height: 500px;
    overflow-y: auto;

    .preview-image {
      max-width: 100%;
      max-height: 500px;
      object-fit: contain;
    }
  }

  .text-preview {
    max-height: 400px;
    overflow-y: auto;
    background-color: #f5f5f5;
    border-radius: 4px;
    padding: 15px;
    margin-bottom: 20px;

    .preview-content {
      margin: 0;
      white-space: pre-wrap;
      word-wrap: break-word;
      font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
      font-size: 14px;
      line-height: 1.6;
    }
  }

  .pdf-preview {
    height: 500px;
    margin-bottom: 20px;

    .pdf-iframe {
      width: 100%;
      height: 100%;
      border: none;
    }
  }

  .unsupported-preview {
    text-align: center;
    padding: 40px 0;
  }

  .file-info {
    margin-top: 20px;
  }
}
</style>
