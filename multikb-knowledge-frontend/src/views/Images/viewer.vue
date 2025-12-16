<template>
  <div class="image-viewer-page" v-loading="loading">
    <el-card v-if="image">
      <template #header>
        <div class="card-header">
          <span>图片详情</span>
          <div>
            <el-button @click="handleDownload">下载</el-button>
            <el-button @click="$router.back()">返回</el-button>
          </div>
        </div>
      </template>

      <div class="viewer-container">
        <div class="image-preview">
          <img :src="imageUrl" :alt="image.description" />
        </div>

        <div class="image-details">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="描述">{{ image.description || '无' }}</el-descriptions-item>
            <el-descriptions-item label="文件大小">{{ formatFileSize(image.file_size) }}</el-descriptions-item>
            <el-descriptions-item label="尺寸">{{ image.width }} x {{ image.height }}</el-descriptions-item>
            <el-descriptions-item label="MIME类型">{{ image.mime_type }}</el-descriptions-item>
            <el-descriptions-item label="来源文档">{{ image.document_name }}</el-descriptions-item>
            <el-descriptions-item label="上传时间">{{ formatDateTime(image.created_at) }}</el-descriptions-item>
          </el-descriptions>

          <el-divider>相似图片</el-divider>

          <div class="similar-images">
            <div
              v-for="similar in similarImages"
              :key="similar.id"
              class="similar-item"
              @click="loadImage(similar.id)"
            >
              <img :src="similar.image_path" :alt="similar.description" />
              <div class="similarity">{{ (similar.similarity * 100).toFixed(1) }}%</div>
            </div>

            <BaseEmpty v-if="similarImages.length === 0" description="暂无相似图片" :image-size="100" />
          </div>

          <div class="actions">
            <el-button type="primary" @click="handleSearchSimilar">以图找图</el-button>
            <el-button @click="handleBackToDocument" v-if="image.document_id">
              返回文档
            </el-button>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getImageDetail } from '@/api/modules/images'
import { formatFileSize, formatDateTime } from '@/utils/format'
import BaseEmpty from '@/components/common/BaseEmpty.vue'

const route = useRoute()
const router = useRouter()
const imageId = Number(route.params.id)

const image = ref<any>(null)
const similarImages = ref<any[]>([])
const loading = ref(false)

const imageUrl = computed(() => {
  return image.value?.image_path || ''
})

const loadImage = async () => {
  loading.value = true
  try {
    const res = await getImageDetail(imageId)
    image.value = res.data
    // TODO: 加载相似图片
    similarImages.value = []
  } catch (error) {
    ElMessage.error('加载图片详情失败')
    router.back()
  } finally {
    loading.value = false
  }
}

const handleDownload = () => {
  if (image.value?.image_path) {
    const link = document.createElement('a')
    link.href = image.value.image_path
    link.download = image.value.file_name || 'image'
    link.click()
  }
}

const handleSearchSimilar = () => {
  router.push('/images/search')
}

const handleBackToDocument = () => {
  if (image.value?.document_id) {
    router.push(`/documents/${image.value.document_id}`)
  }
}

onMounted(() => {
  loadImage()
})
</script>

<style lang="scss" scoped>
.image-viewer-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .viewer-container {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 30px;

    .image-preview {
      img {
        width: 100%;
        max-height: 600px;
        object-fit: contain;
        border-radius: 4px;
      }
    }

    .image-details {
      .similar-images {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
        gap: 10px;

        .similar-item {
          border: 1px solid #e5e5e5;
          border-radius: 4px;
          overflow: hidden;
          cursor: pointer;
          position: relative;

          &:hover {
            border-color: #409eff;
          }

          img {
            width: 100%;
            height: 100px;
            object-fit: cover;
          }

          .similarity {
            position: absolute;
            top: 4px;
            right: 4px;
            background: rgba(64, 158, 255, 0.8);
            color: #fff;
            padding: 2px 6px;
            border-radius: 2px;
            font-size: 11px;
          }
        }
      }

      .actions {
        margin-top: 20px;
        display: flex;
        gap: 10px;
      }
    }
  }
}
</style>
