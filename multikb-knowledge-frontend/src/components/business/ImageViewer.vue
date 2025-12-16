<template>
  <el-dialog
    v-model="visible"
    :title="image?.description || '图片预览'"
    width="80%"
    :close-on-click-modal="false"
    @close="$emit('close')"
  >
    <div class="image-viewer">
      <img :src="imageUrl" :alt="image?.description" />
      
      <div class="image-info">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="描述">{{ image?.description || '无' }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">{{ formatFileSize(image?.file_size) || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="尺寸">{{ image?.width }} x {{ image?.height }}</el-descriptions-item>
          <el-descriptions-item label="MIME类型">{{ image?.mime_type }}</el-descriptions-item>
          <el-descriptions-item label="来源文档">{{ image?.document_name }}</el-descriptions-item>
          <el-descriptions-item label="上传时间">{{ formatDateTime(image?.created_at) }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="image-actions">
        <el-button @click="handleDownload">下载</el-button>
        <el-button type="primary" @click="handleSearchSimilar">以图找图</el-button>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('close')">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatFileSize, formatDateTime } from '@/utils/format'

defineProps<{
  image?: any
  visible?: boolean
}>()

defineEmits(['close', 'download', 'search-similar'])

const imageUrl = computed(() => {
  // TODO: 从MinIO获取图片URL
  return props.image?.image_path || ''
})

const handleDownload = () => {
  emit('download', props.image)
}

const handleSearchSimilar = () => {
  emit('search-similar', props.image)
}
</script>

<style lang="scss" scoped>
.image-viewer {
  display: flex;
  flex-direction: column;
  align-items: center;

  img {
    max-width: 100%;
    max-height: 400px;
    margin-bottom: 20px;
  }

  .image-info {
    width: 100%;
    margin-bottom: 20px;
  }

  .image-actions {
    display: flex;
    gap: 10px;
  }
}
</style>
