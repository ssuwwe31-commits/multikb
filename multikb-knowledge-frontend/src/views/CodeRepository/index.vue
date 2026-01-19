<template>
  <div class="code-repository-container">
    <!-- 顶部操作栏 -->
    <el-card class="header-card">
      <div class="header-content">
        <h2>代码库分析</h2>
        <el-button type="primary" :icon="Plus" @click="showImportDialog = true">
          导入代码仓库
        </el-button>
      </div>
    </el-card>

    <!-- 仓库列表 -->
    <el-card class="list-card">
      <el-table
        :data="repositories"
        v-loading="loading"
        style="width: 100%"
        :cell-style="{ padding: '16px 12px' }"
        :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600' }"
      >
        <el-table-column prop="repo_name" label="仓库名称" min-width="200">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px;">
              <el-link 
                :href="row.repo_url" 
                target="_blank" 
                type="primary"
                :disabled="row.is_deleted || deletingRepoIds.has(row.id)"
              >
                {{ row.repo_name }}
              </el-link>
              <el-tag v-if="row.is_deleted || deletingRepoIds.has(row.id)" type="info" size="small">
                删除中
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="default_branch" label="分支" width="100" />

        <el-table-column label="克隆状态" width="130">
          <template #default="{ row }">
            <div class="status-cell">
              <el-tag :type="getStatusType(row.clone_status)" class="status-tag">
                {{ getStatusText(row.clone_status) }}
              </el-tag>
              <el-progress
                v-if="row.clone_status === 'cloning'"
                :percentage="Math.round(row.clone_progress * 100)"
                :show-text="false"
                class="status-progress"
              />
            </div>
          </template>
        </el-table-column>

        <el-table-column label="解析状态" width="130">
          <template #default="{ row }">
            <div class="status-cell">
              <el-tag :type="getStatusType(row.parse_status)" class="status-tag">
                {{ getStatusText(row.parse_status) }}
              </el-tag>
              <el-progress
                v-if="row.parse_status === 'parsing'"
                :percentage="Math.round(row.parse_progress * 100)"
                :show-text="false"
                class="status-progress"
              />
            </div>
          </template>
        </el-table-column>

        <el-table-column label="统计信息" min-width="240">
          <template #default="{ row }">
            <div class="stats">
              <div class="stats-summary">
                <span class="stat-item">
                  <span class="stat-label">文件:</span>
                  <span class="stat-value">{{ row.total_files || 0 }}</span>
                </span>
                <span class="stat-item">
                  <span class="stat-label">代码行:</span>
                  <span class="stat-value">{{ row.total_lines || 0 }}</span>
                </span>
              </div>
              <div class="languages" v-if="row.language_stats && Object.keys(row.language_stats).length > 0">
                <el-tag
                  v-for="(count, lang) in row.language_stats"
                  :key="lang"
                  size="small"
                  class="language-tag"
                >
                  {{ lang }}: {{ count }}
                </el-tag>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button
                v-if="row.clone_status === 'completed' && row.parse_status === 'completed'"
                type="primary"
                size="small"
                class="action-btn"
                @click="viewRepository(row)"
                :disabled="row.is_deleted || deletingRepoIds.has(row.id)"
              >
                查看分析
              </el-button>
              <el-button
                type="danger"
                size="small"
                class="action-btn"
                @click="handleDelete(row)"
                :disabled="row.is_deleted || deletingRepoIds.has(row.id)"
                :loading="deletingRepoIds.has(row.id)"
              >
                {{ deletingRepoIds.has(row.id) ? '删除中...' : '删除' }}
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 导入对话框 -->
    <el-dialog
      v-model="showImportDialog"
      title="导入代码仓库"
      width="600px"
    >
      <el-form :model="importForm" :rules="importRules" ref="importFormRef" label-width="100px">
        <el-form-item label="仓库 URL" prop="repo_url">
          <el-input
            v-model="importForm.repo_url"
            placeholder="https://github.com/owner/repo"
          />
        </el-form-item>

        <el-form-item label="分支" prop="branch">
          <el-input
            v-model="importForm.branch"
            placeholder="main"
          />
        </el-form-item>

        <el-alert
          title="说明"
          type="info"
          :closable="false"
          style="margin-bottom: 20px"
        >
          <p>1. 支持 GitHub 公开仓库</p>
          <p>2. 克隆和分析将在后台自动进行</p>
          <p>3. 大型仓库可能需要几分钟时间</p>
        </el-alert>
      </el-form>

      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="handleImport" :loading="importing">
          开始导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import * as codeRepositoryApi from '@/api/modules/code-repository'

const router = useRouter()

// 状态
const loading = ref(false)
const repositories = ref<any[]>([])
const showImportDialog = ref(false)
const importing = ref(false)
const deletingRepoIds = ref<Set<number>>(new Set())  // 正在删除的仓库ID集合

// 导入表单
const importForm = ref({
  repo_url: '',
  branch: 'main'
})

const importFormRef = ref<FormInstance>()

const importRules: FormRules = {
  repo_url: [
    { required: true, message: '请输入仓库 URL', trigger: 'blur' },
    { pattern: /^https:\/\/github\.com\/[\w-]+\/[\w-]+/, message: '请输入有效的 GitHub URL', trigger: 'blur' }
  ],
  branch: [
    { required: true, message: '请输入分支名称', trigger: 'blur' }
  ]
}

// 加载仓库列表
const loadRepositories = async () => {
  loading.value = true
  try {
    const res = await codeRepositoryApi.getRepositories()
    repositories.value = res.data.items || []
    
    // 只在有数据时不显示提示，空数据静默处理
    // 用户可以看到"暂无数据"的表格提示
  } catch (error: any) {
    console.error('加载仓库列表失败:', error)
    
    // 区分错误类型
    if (error.response) {
      // 后端返回了错误响应
      const status = error.response.status
      if (status === 404) {
        // 接口不存在，可能是后端版本问题
        console.warn('API 接口未找到，可能需要更新后端')
      } else if (status >= 500) {
        // 服务器错误
        ElMessage.error('服务器错误，请检查后端服务是否正常运行')
      } else {
        ElMessage.error('加载失败：' + (error.response.data?.message || '未知错误'))
      }
    } else if (error.request) {
      // 请求发出但没有响应
      ElMessage.warning('无法连接到服务器，请检查后端服务是否启动')
    } else {
      // 其他错误
      ElMessage.error('加载失败：' + error.message)
    }
  } finally {
    loading.value = false
  }
}

// 导入仓库
const handleImport = async () => {
  if (!importFormRef.value) return

  await importFormRef.value.validate(async (valid) => {
    if (!valid) return

    importing.value = true
    try {
      const res = await codeRepositoryApi.createRepository({
        repo_url: importForm.value.repo_url,
        branch: importForm.value.branch
      })

      ElMessage.success('导入任务已创建，后台正在克隆和分析...')
      showImportDialog.value = false
      importForm.value = { repo_url: '', branch: 'main' }

      // 刷新列表
      setTimeout(() => {
        loadRepositories()
      }, 1000)
    } catch (error: any) {
      console.error('导入失败:', error)
      ElMessage.error(error.message || '导入失败')
    } finally {
      importing.value = false
    }
  })
}

// 删除仓库（硬删除 - 异步任务）
const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要永久删除仓库 "${row.repo_name}" 吗？\n\n⚠️ 这是硬删除操作，将清理以下所有数据：\n• 本地克隆的代码文件\n• MySQL 数据库记录\n• OpenSearch 向量索引\n• NebulaGraph 图数据库\n• 分析缓存数据\n\n删除后无法恢复！\n\n注意：删除操作在后台执行，可能需要一些时间。`,
      '⚠️ 确认硬删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'error',
        dangerouslyUseHTMLString: false,
        distinguishCancelAndClose: true
      }
    )

    // 标记为正在删除
    deletingRepoIds.value.add(row.id)
    
    try {
      // 发送异步删除任务
      const res = await codeRepositoryApi.deleteRepository(row.id)
      
      if (res.data && res.data.task_id) {
        ElMessage.success({
          message: `删除任务已提交（任务ID: ${res.data.task_id}），正在后台执行...`,
          duration: 5000
        })
        
        // 立即刷新列表（仓库状态会更新，is_deleted 会被设置为 true）
        await loadRepositories()
        
        // 轮询任务状态（每2秒检查一次，最多60秒）
        // 后端删除任务完成后会物理删除仓库记录，仓库会从列表中消失
        let pollCount = 0
        const maxPolls = 30  // 增加到30次，共60秒
        const pollInterval = setInterval(async () => {
          pollCount++
          await loadRepositories()
          
          // 检查仓库是否已从列表中消失（物理删除后不再出现在列表中）
          const repo = repositories.value.find(r => r.id === row.id)
          const stillExists = !!repo  // 只要仓库还在列表中，就认为还存在
          
          if (!stillExists) {
            // 仓库已从列表中消失，说明删除完成
            clearInterval(pollInterval)
            deletingRepoIds.value.delete(row.id)  // 移除删除标记
            ElMessage.success('仓库删除完成')
          } else if (pollCount >= maxPolls) {
            // 达到最大轮询次数，停止轮询
            clearInterval(pollInterval)
            deletingRepoIds.value.delete(row.id)  // 移除删除标记
            ElMessage.warning('删除任务可能需要更长时间，请稍后刷新页面查看最新状态')
          }
        }, 2000)
      } else {
        // 兼容旧版本（同步删除）
        ElMessage.success('删除成功，已清理所有相关数据')
        await loadRepositories()
        deletingRepoIds.value.delete(row.id)  // 移除删除标记
      }
    } catch (error: any) {
      // 删除失败，移除删除标记
      deletingRepoIds.value.delete(row.id)
      throw error  // 重新抛出错误，让外层 catch 处理
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error(error.message || '删除失败')
    }
  }
}

// 查看仓库分析
const viewRepository = (row: any) => {
  router.push(`/code-repository/${row.id}`)
}

// 获取状态类型
const getStatusType = (status: string) => {
  const typeMap: Record<string, any> = {
    pending: 'info',
    cloning: 'warning',
    parsing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const textMap: Record<string, string> = {
    pending: '等待中',
    cloning: '克隆中',
    parsing: '解析中',
    completed: '已完成',
    failed: '失败'
  }
  return textMap[status] || status
}

// 初始化
onMounted(() => {
  loadRepositories()
})
</script>

<style scoped lang="scss">
.code-repository-container {
  padding: 20px;

  .header-card {
    margin-bottom: 20px;

    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: center;

      h2 {
        margin: 0;
      }
    }
  }

  .list-card {
    :deep(.el-table) {
      .el-table__cell {
        padding: 16px 12px;
      }
    }

    .stats {
      display: flex;
      flex-direction: column;
      gap: 10px;
      font-size: 13px;
      line-height: 1.5;

      .stats-summary {
        display: flex;
        flex-direction: column;
        gap: 6px;
        margin-bottom: 2px;

        .stat-item {
          display: flex;
          align-items: center;
          gap: 6px;
          color: #606266;

          .stat-label {
            color: #909399;
            font-weight: 500;
            min-width: 50px;
          }

          .stat-value {
            color: #303133;
            font-weight: 600;
          }
        }
      }

      .languages {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 4px;
        padding-top: 8px;
        border-top: 1px solid #ebeef5;

        .language-tag {
          margin: 0;
          border-radius: 4px;
          font-size: 11px;
          padding: 2px 8px;
          height: 22px;
          line-height: 18px;
          transition: all 0.2s;

          &:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
          }
        }
      }
    }

    .status-cell {
      display: flex;
      flex-direction: column;
      gap: 6px;
      align-items: flex-start;

      .status-tag {
        border-radius: 4px;
        font-weight: 500;
        padding: 4px 10px;
        font-size: 12px;
      }

      .status-progress {
        width: 100%;
        margin-top: 4px;
      }
    }

    .action-buttons {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;

      .action-btn {
        border-radius: 4px;
        font-weight: 500;
        transition: all 0.2s;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);

        &:not(:disabled):hover {
          transform: translateY(-1px);
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
        }

        &:not(:disabled):active {
          transform: translateY(0);
        }
      }
    }
  }
}
</style>
