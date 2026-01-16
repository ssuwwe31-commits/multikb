<template>
  <div class="unified-search">
    <el-card class="search-card">
      <template #header>
        <div class="card-header">
          <span>🔍 统一搜索</span>
          <el-tag size="small" type="info">文档 + 代码</el-tag>
        </div>
      </template>

      <!-- 搜索框 -->
      <el-input
        v-model="searchQuery"
        placeholder="搜索文档或代码..."
        class="search-input"
        size="large"
        clearable
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
        <template #append>
          <el-button type="primary" @click="handleSearch" :loading="loading">
            搜索
          </el-button>
        </template>
      </el-input>

      <!-- 搜索选项 -->
      <div class="search-options">
        <el-radio-group v-model="searchScope" size="small">
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="documents">仅文档</el-radio-button>
          <el-radio-button label="code">仅代码</el-radio-button>
        </el-radio-group>

        <el-radio-group v-model="searchMode" size="small">
          <el-radio-button label="hybrid">混合搜索</el-radio-button>
          <el-radio-button label="vector">向量搜索</el-radio-button>
          <el-radio-button label="keyword">关键词</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 搜索结果 -->
      <div v-if="searchResults.length > 0" class="search-results">
        <el-divider>搜索结果（{{ searchResults.length }}）</el-divider>

        <el-scrollbar max-height="600px">
          <div
            v-for="(result, index) in searchResults"
            :key="`result-${index}`"
            class="result-item"
          >
            <!-- 文档结果 -->
            <div v-if="result.type === 'document'" class="result-document">
              <div class="result-header">
                <el-icon color="#409EFF"><Document /></el-icon>
                <span class="result-title">{{ result.title }}</span>
                <el-tag size="small" type="primary">文档</el-tag>
                <span class="result-score">{{ (result.score * 100).toFixed(1) }}%</span>
              </div>
              <div class="result-content">{{ result.content }}</div>
            </div>

            <!-- 代码文件结果 -->
            <div v-if="result.type === 'code_file'" class="result-code-file">
              <div class="result-header">
                <el-icon color="#67C23A"><Folder /></el-icon>
                <span class="result-title">{{ result.file_path }}</span>
                <el-tag size="small" type="success">{{ result.language }}</el-tag>
                <span class="result-score">{{ (result.score * 100).toFixed(1) }}%</span>
              </div>
              <div class="result-meta">
                行数: {{ result.lines_of_code }} | 
                复杂度: {{ result.complexity_score?.toFixed(2) }}
              </div>
            </div>

            <!-- 代码符号结果 -->
            <div v-if="result.type === 'code_symbol'" class="result-code-symbol">
              <div class="result-header">
                <el-icon color="#E6A23C"><Promotion /></el-icon>
                <span class="result-title">{{ result.qualified_name || result.symbol_name }}</span>
                <el-tag size="small" type="warning">{{ result.symbol_type }}</el-tag>
                <span class="result-score">{{ (result.score * 100).toFixed(1) }}%</span>
              </div>
              <div class="result-signature" v-if="result.signature">
                <code>{{ result.signature }}</code>
              </div>
              <div class="result-content" v-if="result.docstring">
                {{ result.docstring }}
              </div>
            </div>
          </div>
        </el-scrollbar>
      </div>

      <!-- 空状态 -->
      <el-empty
        v-else-if="searched && !loading"
        description="未找到相关结果"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Search, Document, Folder, Promotion } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as unifiedSearchApi from '@/api/modules/unified-search'

// =============================================
// Props
// =============================================

const props = defineProps<{
  knowledgeBaseId?: number
}>()

// =============================================
// 状态
// =============================================

const searchQuery = ref('')
const searchScope = ref('all')
const searchMode = ref('hybrid')
const loading = ref(false)
const searched = ref(false)
const searchResults = ref<any[]>([])

// =============================================
// 方法
// =============================================

const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  loading.value = true
  searched.value = true

  try {
    // 转换搜索范围
    const scopeMap: Record<string, any> = {
      'all': ['documents', 'code'],
      'documents': ['documents'],
      'code': ['code']
    }

    const response = await unifiedSearchApi.unifiedSearch({
      query: searchQuery.value,
      knowledge_base_id: props.knowledgeBaseId,
      search_scope: scopeMap[searchScope.value],
      search_mode: searchMode.value as any,
      top_k: 20
    })

    if (response.code === 200) {
      searchResults.value = response.data.results
      ElMessage.success(`找到 ${response.data.total} 个结果`)
    } else {
      ElMessage.error(response.message || '搜索失败')
      searchResults.value = []
    }
  } catch (error: any) {
    console.error('搜索失败:', error)
    ElMessage.error('搜索失败: ' + (error.message || '未知错误'))
    searchResults.value = []
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.unified-search {
  .search-card {
    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
    }

    .search-input {
      margin-bottom: 16px;
    }

    .search-options {
      display: flex;
      gap: 16px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }

    .search-results {
      margin-top: 16px;

      .result-item {
        padding: 12px;
        border: 1px solid #ebeef5;
        border-radius: 4px;
        margin-bottom: 12px;
        transition: all 0.3s;

        &:hover {
          box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
          border-color: #409EFF;
        }

        .result-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;

          .result-title {
            flex: 1;
            font-weight: 500;
            font-size: 14px;
          }

          .result-score {
            color: #909399;
            font-size: 12px;
          }
        }

        .result-content {
          color: #606266;
          font-size: 13px;
          line-height: 1.6;
          margin-top: 8px;
        }

        .result-signature {
          background: #f5f7fa;
          padding: 8px;
          border-radius: 4px;
          font-family: 'Consolas', 'Monaco', monospace;
          font-size: 12px;
          margin-top: 8px;
          overflow-x: auto;
        }

        .result-meta {
          color: #909399;
          font-size: 12px;
          margin-top: 8px;
        }
      }
    }
  }
}
</style>
