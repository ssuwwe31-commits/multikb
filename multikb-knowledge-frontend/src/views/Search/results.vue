<template>
  <div class="search-results-page">
    <el-card>
      <template #header>
        <div class="search-header">
          <SearchBox v-model="query" @search="handleSearch" />
          <el-select v-model="searchType" style="width: 200px; margin-left: 10px;" @change="handleSearchTypeChange">
            <el-option label="智能搜索" value="hybrid" />
            <el-option label="向量搜索" value="vector" />
            <el-option label="关键词搜索" value="keyword" />
            <el-option label="模糊搜索" value="fuzzy" />
            <el-option label="精确匹配" value="exact" />
          </el-select>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="全部" name="all">
          <div class="results-section">
            <div class="results-count">找到 {{ total }} 条结果</div>
            <DocumentCard
              v-for="doc in documents"
              :key="doc.id"
              :document="doc"
              @click="viewDocument(doc)"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="文档" name="documents">
          <div class="results-section">
            <DocumentCard
              v-for="doc in documents"
              :key="doc.id"
              :document="doc"
              @click="viewDocument(doc)"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="图片" name="images">
          <div class="image-grid">
            <div
              v-for="image in images"
              :key="image.id"
              class="image-item"
              @click="viewImage(image)"
            >
              <img :src="image.image_path" :alt="image.description" />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <BasePagination
        v-if="total > 0"
        v-model:page="page"
        v-model:size="size"
        :total="total"
        @change="handlePageChange"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { search } from '@/api/modules/search'
import SearchBox from '@/components/business/SearchBox.vue'
import DocumentCard from '@/components/business/DocumentCard.vue'
import BasePagination from '@/components/common/BasePagination.vue'

const route = useRoute()
const router = useRouter()

const query = ref((route.query.q as string) || '')
const searchType = ref<'vector' | 'keyword' | 'hybrid' | 'exact' | 'fuzzy'>(route.query.type as any || 'hybrid')
const activeTab = ref('all')

const documents = ref<any[]>([])
const images = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)

const handleSearch = async () => {
  await performSearch()
}

const handleSearchTypeChange = async () => {
  page.value = 1
  await performSearch()
}

const performSearch = async () => {
  if (!query.value.trim()) return

  loading.value = true
  try {
    const res = await search({
      query: query.value,
      search_type: searchType.value,
      page: page.value,
      size: size.value
    })

    const payload: any = (res && (res as any).data !== undefined) ? (res as any).data : res
    const list: any[] = Array.isArray(payload) ? payload : (payload?.results || [])
    documents.value = list.filter((item: any) => item.type === 'document')
    images.value = list.filter((item: any) => item.type === 'image')
    total.value = Array.isArray(payload) ? payload.length : (payload?.total || 0)
  } catch (error) {
    console.error('Search error:', error)
  } finally {
    loading.value = false
  }
}

const handlePageChange = (newPage: number, newSize: number) => {
  page.value = newPage
  size.value = newSize
  performSearch()
}

const viewDocument = (doc: any) => {
  router.push(`/documents/${doc.id}`)
}

const viewImage = (image: any) => {
  router.push(`/images/${image.id}`)
}

onMounted(() => {
  if (query.value) {
    performSearch()
  }
})
</script>

<style lang="scss" scoped>
.search-results-page {
  .search-header {
    display: flex;
    align-items: center;
  }

  .results-section {
    .results-count {
      margin-bottom: 20px;
      color: #909399;
      font-size: 14px;
    }
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

      img {
        width: 100%;
        height: 150px;
        object-fit: cover;
      }
    }
  }
}
</style>
