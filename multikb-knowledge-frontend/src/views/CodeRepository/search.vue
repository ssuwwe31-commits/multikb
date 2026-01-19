<template>
  <div class="code-search-page">
    <!-- 快速开始提示 -->
    <el-alert
      v-if="!hasSearched"
      type="info"
      :closable="false"
      style="margin-bottom: 20px"
    >
      <template #title>
        <div class="quick-start-guide">
          <div style="font-weight: bold; margin-bottom: 8px;">📚 快速开始：</div>
          <div style="line-height: 1.8;">
            <div>1️⃣ <strong>文件搜索</strong>：输入文件名或路径，快速找到代码文件（如：输入 "api" 查找所有 API 相关文件）</div>
            <div>2️⃣ <strong>符号搜索</strong>：输入函数名或类名，查找具体的代码符号（如：输入 "login" 查找登录相关函数）</div>
            <div>3️⃣ <strong>调用链查询</strong>：查找函数之间的调用关系，需要填写"源"和"目标"（如：从 "handleClick" 到 "submitForm"）</div>
            <div>4️⃣ <strong>依赖路径查询</strong>：查找文件之间的依赖关系，需要填写"源文件"和"目标文件"</div>
          </div>
        </div>
      </template>
    </el-alert>

    <el-card class="search-card">
      <template #header>
        <div class="card-header">
          <span>代码查询</span>
          <el-button type="primary" :icon="Refresh" @click="handleRefresh" :loading="refreshing">
            刷新
          </el-button>
        </div>
      </template>

      <!-- 搜索表单 -->
      <el-form :model="searchForm" class="search-form" @submit.prevent="handleSearch">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="仓库">
              <el-select
                v-model="searchForm.repository_id"
                placeholder="选择仓库（建议选择，可提高搜索准确性）"
                clearable
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="repo in repositories"
                  :key="repo.id"
                  :label="repo.repo_name"
                  :value="repo.id"
                />
              </el-select>
              <div class="form-item-tip">💡 提示：选择一个仓库可以缩小搜索范围，提高准确性</div>
            </el-form-item>
          </el-col>
          
          <el-col :span="8">
            <el-form-item label="查询类型">
              <el-select v-model="searchForm.search_type" style="width: 100%">
                <el-option label="文件搜索 - 按文件名或路径搜索代码文件" value="file" />
                <el-option label="符号搜索 - 搜索函数、类、方法等代码符号" value="symbol" />
                <el-option label="调用链查询 - 查找函数之间的调用关系" value="call_chain" />
                <el-option label="依赖路径查询 - 查找文件之间的依赖关系" value="dependency_path" />
              </el-select>
              <div class="form-item-tip">
                <template v-if="searchForm.search_type === 'file'">
                  💡 文件搜索：输入文件名或路径，如 "utils.py" 或 "src/components"
                </template>
                <template v-else-if="searchForm.search_type === 'symbol'">
                  💡 符号搜索：输入函数名、类名等，如 "getUserInfo" 或 "UserService"
                </template>
                <template v-else-if="searchForm.search_type === 'call_chain'">
                  💡 调用链查询：查找从源函数到目标函数的调用路径，需要填写"目标"字段
                </template>
                <template v-else-if="searchForm.search_type === 'dependency_path'">
                  💡 依赖路径查询：查找从源文件到目标文件的依赖路径，需要填写"目标"字段
                </template>
              </div>
            </el-form-item>
          </el-col>
          
          <el-col :span="8">
            <el-form-item label="关键词">
              <el-input
                v-model="searchForm.keyword"
                :placeholder="getKeywordPlaceholder()"
                clearable
                @keyup.enter="handleSearch"
              >
                <template #append>
                  <el-button type="primary" @click="handleSearch" :loading="searching">
                    搜索
                  </el-button>
                </template>
              </el-input>
              <div class="form-item-tip">
                <template v-if="searchForm.search_type === 'file'">
                  💡 示例：输入 "api" 查找所有包含 api 的文件，或输入完整路径 "src/api/user.ts"
                </template>
                <template v-else-if="searchForm.search_type === 'symbol'">
                  💡 示例：输入 "login" 查找所有包含 login 的函数或类
                </template>
                <template v-else>
                  💡 输入源文件路径或符号名称作为起点
                </template>
              </div>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 高级筛选（根据查询类型显示） -->
        <el-collapse v-model="advancedCollapse">
          <el-collapse-item name="advanced" title="高级筛选（可选）">
            <el-alert
              type="info"
              :closable="false"
              style="margin-bottom: 16px"
            >
              <template #title>
                <span>💡 提示：高级筛选可以帮助您更精确地找到目标代码。如果不确定，可以留空使用默认值。</span>
              </template>
            </el-alert>
            
            <el-row :gutter="20">
              <el-col :span="8" v-if="searchForm.search_type === 'file'">
                <el-form-item label="编程语言">
                  <el-select v-model="searchForm.language" placeholder="全部语言（不限制）" clearable style="width: 100%">
                    <el-option label="Python" value="python" />
                    <el-option label="JavaScript" value="javascript" />
                    <el-option label="TypeScript" value="typescript" />
                    <el-option label="Java" value="java" />
                    <el-option label="Go" value="go" />
                    <el-option label="C++" value="cpp" />
                    <el-option label="其他" value="other" />
                  </el-select>
                  <div class="form-item-tip">💡 筛选特定编程语言的文件，留空则搜索所有语言</div>
                </el-form-item>
              </el-col>
              
              <el-col :span="8" v-if="searchForm.search_type === 'symbol'">
                <el-form-item label="符号类型">
                  <el-select v-model="searchForm.symbol_type" placeholder="全部类型（不限制）" clearable style="width: 100%">
                    <el-option label="函数 - 独立的函数定义" value="function" />
                    <el-option label="类 - 类定义" value="class" />
                    <el-option label="方法 - 类中的方法" value="method" />
                    <el-option label="变量 - 变量定义" value="variable" />
                  </el-select>
                  <div class="form-item-tip">💡 筛选特定类型的符号，留空则搜索所有类型</div>
                </el-form-item>
              </el-col>
              
              <el-col :span="8" v-if="searchForm.search_type === 'call_chain' || searchForm.search_type === 'dependency_path'">
                <el-form-item label="目标" required>
                  <el-input
                    v-model="searchForm.target"
                    :placeholder="searchForm.search_type === 'call_chain' ? '目标函数/方法名称，如：handleSubmit' : '目标文件路径，如：src/api/user.ts'"
                    clearable
                  />
                  <div class="form-item-tip">
                    <template v-if="searchForm.search_type === 'call_chain'">
                      ⚠️ 必填：输入目标函数或方法的名称，系统将查找从"关键词"到"目标"的调用路径
                    </template>
                    <template v-else>
                      ⚠️ 必填：输入目标文件的路径，系统将查找从"关键词"到"目标"的依赖路径
                    </template>
                  </div>
                </el-form-item>
              </el-col>
              
              <el-col :span="8" v-if="searchForm.search_type === 'call_chain' || searchForm.search_type === 'dependency_path'">
                <el-form-item label="最大跳数">
                  <el-input-number
                    v-model="searchForm.max_hops"
                    :min="1"
                    :max="10"
                    :step="1"
                    style="width: 100%"
                  />
                  <div class="form-item-tip">💡 限制搜索的最大跳数（默认3），值越大可能找到更多路径但速度更慢</div>
                </el-form-item>
              </el-col>
            </el-row>
          </el-collapse-item>
        </el-collapse>
      </el-form>
    </el-card>

    <!-- 搜索结果 -->
    <el-card v-if="searchResults.length > 0 || searching" class="results-card">
      <template #header>
        <span>搜索结果 ({{ searchResults.length }})</span>
      </template>

      <!-- 文件搜索结果 -->
      <div v-if="searchForm.search_type === 'file'">
        <el-table :data="searchResults" v-loading="searching" stripe>
          <el-table-column prop="file_path" label="文件路径" min-width="300">
            <template #default="{ row }">
              <el-link
                type="primary"
                @click="viewFile(row)"
                :underline="false"
              >
                {{ row.file_path }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column prop="language" label="语言" width="100" />
          <el-table-column prop="lines_of_code" label="代码行数" width="100" />
          <el-table-column prop="symbols_count" label="符号数" width="100" />
          <el-table-column prop="complexity_score" label="复杂度" width="100">
            <template #default="{ row }">
              <el-tag :type="getComplexityType(row.complexity_score)" size="small">
                {{ row.complexity_score?.toFixed(2) || '0.00' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="viewFile(row)">
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 符号搜索结果 -->
      <div v-if="searchForm.search_type === 'symbol'">
        <el-table :data="searchResults" v-loading="searching" stripe>
          <el-table-column prop="symbol_name" label="符号名称" min-width="200">
            <template #default="{ row }">
              <el-link
                type="primary"
                @click="viewSymbol(row)"
                :underline="false"
              >
                {{ row.symbol_name }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column prop="qualified_name" label="限定名" min-width="300" />
          <el-table-column prop="symbol_type" label="类型" width="100">
            <template #default="{ row }">
              <el-tag :type="getSymbolTypeTag(row.symbol_type)" size="small">
                {{ getSymbolTypeLabel(row.symbol_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="file_path" label="文件路径" min-width="250" />
          <el-table-column prop="start_line" label="行号" width="80" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="viewSymbol(row)">
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 调用链查询结果 -->
      <div v-if="searchForm.search_type === 'call_chain'">
        <div v-if="callChainResult" class="call-chain-result">
          <el-alert
            v-if="callChainResult.paths && callChainResult.paths.length === 0"
            type="info"
            :closable="false"
            style="margin-bottom: 20px"
          >
            未找到调用链路径
          </el-alert>
          
          <div v-else>
            <div v-for="(path, index) in callChainResult.paths" :key="index" class="call-chain-path">
              <el-card shadow="hover" style="margin-bottom: 16px">
                <template #header>
                  <span>路径 {{ index + 1 }} ({{ path.length }} 步)</span>
                </template>
                <div class="path-nodes">
                  <div
                    v-for="(node, nodeIndex) in path"
                    :key="nodeIndex"
                    class="path-node"
                  >
                    <el-tag type="primary" size="large">{{ node.name || node.symbol_name || node.file_path }}</el-tag>
                    <el-icon v-if="nodeIndex < path.length - 1" class="path-arrow">
                      <ArrowRight />
                    </el-icon>
                  </div>
                </div>
              </el-card>
            </div>
          </div>
        </div>
      </div>

      <!-- 依赖路径查询结果 -->
      <div v-if="searchForm.search_type === 'dependency_path'">
        <div v-if="dependencyPathResult" class="dependency-path-result">
          <el-alert
            v-if="dependencyPathResult.paths && dependencyPathResult.paths.length === 0"
            type="info"
            :closable="false"
            style="margin-bottom: 20px"
          >
            未找到依赖路径
          </el-alert>
          
          <div v-else>
            <div v-for="(path, index) in dependencyPathResult.paths" :key="index" class="dependency-path">
              <el-card shadow="hover" style="margin-bottom: 16px">
                <template #header>
                  <span>路径 {{ index + 1 }} ({{ path.length }} 步)</span>
                </template>
                <div class="path-nodes">
                  <div
                    v-for="(node, nodeIndex) in path"
                    :key="nodeIndex"
                    class="path-node"
                  >
                    <el-tag type="success" size="large">{{ node.name || node.file_path }}</el-tag>
                    <el-icon v-if="nodeIndex < path.length - 1" class="path-arrow">
                      <ArrowRight />
                    </el-icon>
                  </div>
                </div>
              </el-card>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 空状态 -->
    <el-empty
      v-if="!searching && searchResults.length === 0 && !callChainResult && !dependencyPathResult && hasSearched"
      description="暂无搜索结果"
      :image-size="120"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, ArrowRight } from '@element-plus/icons-vue'
import * as codeRepositoryApi from '@/api/modules/code-repository'
import { searchCodeFiles, searchCodeSymbols } from '@/api/modules/unified-search'
import type { CodeRepository } from '@/api/modules/code-repository'

const router = useRouter()

// 搜索表单
const searchForm = ref({
  repository_id: undefined as number | undefined,
  search_type: 'file' as 'file' | 'symbol' | 'call_chain' | 'dependency_path',
  keyword: '',
  language: undefined as string | undefined,
  symbol_type: undefined as string | undefined,
  target: '',
  max_hops: 3
})

const advancedCollapse = ref<string[]>([])
const searching = ref(false)
const refreshing = ref(false)
const hasSearched = ref(false)

// 仓库列表
const repositories = ref<CodeRepository[]>([])

// 搜索结果
const searchResults = ref<any[]>([])
const callChainResult = ref<any>(null)
const dependencyPathResult = ref<any>(null)

// 加载仓库列表
const loadRepositories = async () => {
  try {
    const res = await codeRepositoryApi.getRepositories({ page: 1, size: 100 })
    repositories.value = res.data?.list || res.data?.items || res.data || []
  } catch (error: any) {
    ElMessage.error('加载仓库列表失败: ' + (error.message || '未知错误'))
  }
}

// 执行搜索
const handleSearch = async () => {
  if (!searchForm.value.keyword.trim() && searchForm.value.search_type !== 'call_chain' && searchForm.value.search_type !== 'dependency_path') {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  if ((searchForm.value.search_type === 'call_chain' || searchForm.value.search_type === 'dependency_path') && !searchForm.value.target.trim()) {
    ElMessage.warning('调用链/依赖路径查询需要指定目标')
    return
  }

  searching.value = true
  hasSearched.value = true
  searchResults.value = []
  callChainResult.value = null
  dependencyPathResult.value = null

  try {
    if (searchForm.value.search_type === 'file') {
      // 文件搜索
      const res = await searchCodeFiles({
        query: searchForm.value.keyword,
        repository_id: searchForm.value.repository_id,
        language: searchForm.value.language,
        top_k: 50
      })
      searchResults.value = res.data?.results || res.data?.items || []
    } else if (searchForm.value.search_type === 'symbol') {
      // 符号搜索
      const res = await searchCodeSymbols({
        query: searchForm.value.keyword,
        repository_id: searchForm.value.repository_id,
        symbol_type: searchForm.value.symbol_type,
        top_k: 50
      })
      searchResults.value = res.data?.results || res.data?.items || []
    } else if (searchForm.value.search_type === 'call_chain') {
      // 调用链查询
      const res = await codeRepositoryApi.queryCallChain({
        repository_id: searchForm.value.repository_id!,
        source: searchForm.value.keyword,
        target: searchForm.value.target,
        max_hops: searchForm.value.max_hops
      })
      callChainResult.value = res.data
    } else if (searchForm.value.search_type === 'dependency_path') {
      // 依赖路径查询
      const res = await codeRepositoryApi.queryDependencyPath({
        repository_id: searchForm.value.repository_id!,
        source: searchForm.value.keyword,
        target: searchForm.value.target,
        max_hops: searchForm.value.max_hops
      })
      dependencyPathResult.value = res.data
    }

    if (searchResults.value.length === 0 && !callChainResult.value && !dependencyPathResult.value) {
      ElMessage.info('未找到相关结果')
    }
  } catch (error: any) {
    console.error('搜索失败:', error)
    ElMessage.error('搜索失败: ' + (error.message || '未知错误'))
  } finally {
    searching.value = false
  }
}

// 刷新
const handleRefresh = async () => {
  refreshing.value = true
  await loadRepositories()
  refreshing.value = false
  ElMessage.success('已刷新')
}

// 查看文件
const viewFile = (file: any) => {
  if (file.repository_id) {
    router.push(`/code-repository/${file.repository_id}?file=${encodeURIComponent(file.file_path)}`)
  } else {
    ElMessage.warning('文件信息不完整，无法查看')
  }
}

// 查看符号
const viewSymbol = (symbol: any) => {
  if (symbol.repository_id) {
    router.push(`/code-repository/${symbol.repository_id}?symbol=${encodeURIComponent(symbol.qualified_name || symbol.symbol_name)}`)
  } else {
    ElMessage.warning('符号信息不完整，无法查看')
  }
}

// 获取复杂度标签类型
const getComplexityType = (score: number) => {
  if (score < 5) return 'success'
  if (score < 10) return 'warning'
  return 'danger'
}

// 获取符号类型标签
const getSymbolTypeTag = (type: string) => {
  const typeMap: Record<string, string> = {
    function: 'primary',
    class: 'success',
    method: 'info',
    variable: 'warning'
  }
  return typeMap[type] || 'info'
}

// 获取符号类型标签文本
const getSymbolTypeLabel = (type: string) => {
  const labelMap: Record<string, string> = {
    function: '函数',
    class: '类',
    method: '方法',
    variable: '变量'
  }
  return labelMap[type] || type
}

// 获取关键词占位符
const getKeywordPlaceholder = () => {
  switch (searchForm.value.search_type) {
    case 'file':
      return '输入文件名或路径，如：utils.py 或 src/components'
    case 'symbol':
      return '输入函数名、类名等，如：getUserInfo 或 UserService'
    case 'call_chain':
      return '输入源函数/方法名称，如：handleClick'
    case 'dependency_path':
      return '输入源文件路径，如：src/api/auth.ts'
    default:
      return '输入搜索关键词...'
  }
}

// 监听查询类型变化，自动展开高级筛选（如果是调用链或依赖路径查询）
watch(() => searchForm.value.search_type, (newType) => {
  if (newType === 'call_chain' || newType === 'dependency_path') {
    // 如果是调用链或依赖路径查询，自动展开高级筛选
    if (!advancedCollapse.value.includes('advanced')) {
      advancedCollapse.value = ['advanced']
    }
  }
})

// 初始化
onMounted(() => {
  loadRepositories()
  // 加载完成后，如果有仓库，默认选择第一个
  setTimeout(() => {
    if (repositories.value.length > 0 && !searchForm.value.repository_id) {
      searchForm.value.repository_id = repositories.value[0].id
    }
  }, 500)
})
</script>

<style scoped lang="scss">
.code-search-page {
  padding: 20px;
  
  .search-card {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .search-form {
      .el-form-item {
        margin-bottom: 16px;
      }
      
      .form-item-tip {
        font-size: 12px;
        color: #909399;
        margin-top: 4px;
        line-height: 1.5;
      }
    }
  }
  
  .results-card {
    .call-chain-result,
    .dependency-path-result {
      .path-nodes {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        
        .path-node {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        
        .path-arrow {
          color: #409eff;
          font-size: 18px;
        }
      }
    }
  }
  
  .quick-start-guide {
    font-size: 13px;
  }
}
</style>
