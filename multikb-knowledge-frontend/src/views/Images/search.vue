<template>
  <div class="image-search-page">
    <el-card>
      <template #header>
        <div class="search-header">
          <span>图片搜索</span>
          <el-button @click="$router.back()">返回</el-button>
        </div>
      </template>

      <el-tabs v-model="searchType">
        <el-tab-pane label="以图找图" name="image">
          <div class="search-box">
            <el-upload
              :auto-upload="false"
              :show-file-list="false"
              accept="image/*"
              @change="handleImageUpload"
            >
              <el-button type="primary">选择图片</el-button>
            </el-upload>

            <div v-if="uploadedImage" class="uploaded-image">
              <img :src="uploadedImageUrl" alt="上传的图片" />
              <el-button type="primary" @click="handleSearchByImage">开始搜索</el-button>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="以文找图" name="text">
          <div class="search-box">
            <el-input
              v-model="searchText"
              placeholder="输入图片描述、关键词等"
              clearable
            >
              <template #suffix>
                <el-button type="primary" @click="handleSearchByText">搜索</el-button>
              </template>
            </el-input>
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- 搜索结果 -->
      <div v-if="hasResults" class="search-results">
        <div class="results-header">
          <span>找到 {{ total }} 张相似图片</span>
        </div>

        <div class="image-grid">
          <div
            v-for="image in results"
            :key="image.id"
            class="image-item"
            @click="viewImage(image)"
          >
            <img :src="image.image_path" :alt="image.description" />
            <div class="image-info">
              <div class="similarity">相似度: {{ (image.similarity * 100).toFixed(1) }}%</div>
              <div class="description">{{ image.description }}</div>
            </div>
          </div>
        </div>
      </div>

      <BaseEmpty v-else description="暂无搜索结果" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useImagesStore } from '@/stores/modules/images'
import BaseEmpty from '@/components/common/BaseEmpty.vue'
import ImageViewer from '@/components/business/ImageViewer.vue'
import { uploadImage } from '@/utils/image'

const imagesStore = useImagesStore()

const searchType = ref<'image' | 'text'>('image')
const uploadedImage = ref<File | null>(null)
const uploadedImageUrl = ref<string>('')
const searchText = ref('')
const results = computed(() => imagesStore.searchResults)
const hasResults = computed(() => imagesStore.hasResults)
const total = computed(() => imagesStore.total)
const currentImage = ref<any>(null)
const showViewer = ref(false)

const handleImageUpload = async (file: File) => {
  uploadedImage.value = file
  uploadedImageUrl.value = await uploadImage(file)
}

const handleSearchByImage = async () => {
  if (!uploadedImage.value) {
    ElMessage.warning('请先选择图片')
    return
  }

  await imagesStore.searchImagesByImage(uploadedImage.value, {
    similarity_threshold: 0.7,
    max_results: 20
  })
}

const handleSearchByText = async () => {
  if (!searchText.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  await imagesStore.searchImagesByText(searchText.value, {
    similarity_threshold: 0.7,
    max_results: 20
  })
}

const viewImage = (image: any) => {
  currentImage.value = image
  showViewer.value = true
}
</script>

<style lang="scss" scoped>
.image-search-page {
  .search-box {
    padding: 20px;
    text-align: center;

    .uploaded-image {
      margin-top: 20px;

      img {
        max-width: 300px;
        max-height: 300px;
        margin-bottom: 20px;
        border-radius: 4px;
      }
    }
  }

  .search-results {
    margin-top: 30px;

    .results-header {
      margin-bottom: 20px;
      font-size: 14px;
      color: #666;
    }

    .image-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 16px;

      .image-item {
        border: 1px solid #e5e5e5;
        border-radius: 4px;
        overflow: hidden;
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          transform: translateY(-4px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        img {
          width: 100%;
          height: 200px;
          object-fit: cover;
        }

        .image-info {
          padding: 12px;

          .similarity {
            font-weight: 500;
            color: #409eff;
            margin-bottom: 4px;
          }

          .description {
            font-size: 12px;
            color: #666;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
        }
      }
    }
  }
}
</style>
