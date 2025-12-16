<template>
  <div class="upload-page">
    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">文档上传</span>
          <span class="card-subtitle">选择知识库、上传文件并添加标签</span>
        </div>
      </template>

      <!-- 上传方式切换 -->
      <div class="upload-tabs">
        <el-radio-group v-model="uploadMode" size="default" @change="handleModeChange">
          <el-radio-button label="file">本地上传</el-radio-button>
          <el-radio-button label="batch">批量上传</el-radio-button>
          <el-radio-button label="url">URL导入</el-radio-button>
        </el-radio-group>
      </div>

      <el-form :model="form" label-width="120px">
        <el-form-item label="选择知识库" :required="true">
          <el-select 
            v-model="form.knowledge_base_id" 
            placeholder="请先选择知识库"
            class="kb-select"
            :disabled="uploading"
          >
            <el-option
              v-for="kb in knowledgeBases"
              :key="kb.id"
              :label="kb.name"
              :value="kb.id"
            />
          </el-select>
          <el-alert 
            v-if="!form.knowledge_base_id" 
            title="请先选择知识库后再上传文件" 
            type="warning" 
            :closable="false"
            style="margin-top: 10px"
          />
        </el-form-item>

        <!-- 本地上传模式 -->
        <template v-if="uploadMode === 'file'">
          <el-form-item label="选择文件">
            <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :limit="1"
              accept=".docx,.pdf,.pptx,.txt,.log,.md,.markdown,.mkd,.xlsx,.xls,.csv"
              drag
            >
            <template #default>
              <el-icon class="el-icon--upload"><Upload /></el-icon>
              <div class="el-upload__text">
                将文件拖到此处，或<em>点击上传</em>
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item v-if="file">
          <div class="file-info">
            <span>文件名: {{ file.name }}</span>
            <span>大小: {{ formatFileSize(file.size) }}</span>
            <el-button size="small" type="primary" @click="handlePreviewFile" style="margin-left: 10px">
              预览
            </el-button>
          </div>
        </el-form-item>
        </template>

        <!-- 批量上传模式 -->
        <template v-if="uploadMode === 'batch'">
          <el-form-item label="选择文件">
            <el-upload
              ref="batchUploadRef"
              :auto-upload="false"
              :on-change="handleBatchFileChange"
              :on-remove="handleBatchFileRemove"
              :limit="100"
              multiple
              accept=".docx,.pdf,.pptx,.txt,.log,.md,.markdown,.mkd,.xlsx,.xls,.csv,.zip"
              drag
            >
            <template #default>
              <el-icon class="el-icon--upload"><Upload /></el-icon>
              <div class="el-upload__text">
                将文件拖到此处，或<em>点击上传</em>
                <div style="margin-top: 10px; font-size: 12px; color: #999">
                  支持多文件上传或ZIP压缩包（自动解包）
                </div>
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <!-- 批量上传进度 -->
        <el-form-item v-if="batchFiles.length > 0">
          <div class="batch-progress">
            <div class="progress-header">
              <span>已选择 {{ batchFiles.length }} 个文件</span>
              <el-button size="small" @click="clearBatchFiles">清空</el-button>
            </div>
            <el-progress 
              v-if="batchProgress.total > 0"
              :percentage="Math.round((batchProgress.processed / batchProgress.total) * 100)"
              :status="batchProgress.status"
            />
            <div v-if="batchProgress.total > 0" class="progress-stats">
              <span>总进度: {{ batchProgress.processed }}/{{ batchProgress.total }}</span>
              <span>成功: {{ batchProgress.success }}</span>
              <span>失败: {{ batchProgress.failed }}</span>
            </div>
            <el-table 
              v-if="batchFiles.length > 0 && batchProgress.files.length > 0"
              :data="batchProgress.files"
              style="margin-top: 10px"
              max-height="300"
            >
              <el-table-column prop="filename" label="文件名" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="getStatusTagType(row.status)">
                    {{ getStatusText(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="processing_progress" label="进度" width="120">
                <template #default="{ row }">
                  <el-progress 
                    :percentage="Math.round(row.processing_progress || 0)"
                    :status="row.status === 'failed' ? 'exception' : undefined"
                  />
                </template>
              </el-table-column>
              <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip />
            </el-table>
          </div>
        </el-form-item>
        </template>

        <!-- URL导入模式 -->
        <template v-if="uploadMode === 'url'">
          <el-form-item label="文档URL" :required="true">
            <el-input
              v-model="form.url"
              placeholder="请输入文档的下载链接，例如：https://example.com/document.pdf"
              :disabled="uploading"
              clearable
            >
              <template #prepend>
                <el-icon><Link /></el-icon>
              </template>
            </el-input>
            <div class="url-tips">
              <el-alert
                title="提示"
                type="info"
                :closable="false"
                style="margin-top: 10px"
              >
                <template #default>
                  <div>
                    <p>• 支持直接下载的文档链接（PDF、Word、Excel、PPT等）</p>
                    <p>• 系统会自动下载文件并进行安全检测</p>
                    <p>• 文件大小限制：{{ formatFileSize(maxFileSize) }}</p>
                  </div>
                </template>
              </el-alert>
            </div>
          </el-form-item>

          <el-form-item label="自定义文件名" v-if="form.url">
            <el-input
              v-model="form.filename"
              placeholder="可选，留空则使用URL中的文件名"
              :disabled="uploading"
              clearable
            />
          </el-form-item>

          <el-form-item v-if="urlFileInfo">
            <div class="file-info">
              <span>检测到文件: {{ urlFileInfo.filename }}</span>
              <span v-if="urlFileInfo.size">大小: {{ formatFileSize(urlFileInfo.size) }}</span>
            </div>
          </el-form-item>
        </template>

        <!-- 标签选择 -->
        <el-form-item label="标签">
          <TagSelector
            v-model="form.tags"
            :recommended-tags="recommendedTags"
            :max-tags="10"
          />
        </el-form-item>

        <el-form-item>
          <el-button 
            type="primary" 
            size="large" 
            @click="handleSubmit" 
            :loading="uploading"
            :disabled="uploadMode === 'batch' && batchFiles.length === 0"
          >
            {{ uploadMode === 'file' ? '上传' : uploadMode === 'batch' ? '批量上传' : '导入' }}
          </el-button>
          <el-button size="large" @click="$router.back()">取消</el-button>
        </el-form-item>

        <el-form-item v-if="uploadResult">
          <el-result 
            icon="success" 
            :title="uploadMode === 'file' ? '上传成功' : '导入成功'" 
            sub-title="文档已添加到知识库"
          >
            <template #extra>
              <el-button type="primary" @click="$router.push(`/documents/${uploadResult.document_id}`)">
                查看文档
              </el-button>
            </template>
          </el-result>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 文件预览 -->
    <FilePreview
      v-model="showPreview"
      :file="previewFile"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Link } from '@element-plus/icons-vue'
import { getKnowledgeBases } from '@/api/modules/knowledge-bases'
import { uploadDocument, uploadDocumentFromUrl, batchUploadDocuments, getBatchStatus } from '@/api/modules/documents'
import { formatFileSize } from '@/utils/format'
import TagSelector from '@/components/business/TagSelector.vue'
import FilePreview from '@/components/business/FilePreview.vue'
import type { KnowledgeBase } from '@/types'

const knowledgeBases = ref<KnowledgeBase[]>([])
const loading = ref(false)
const uploading = ref(false)
const file = ref<File | null>(null)
const uploadResult = ref<any>(null)
const uploadMode = ref<'file' | 'batch' | 'url'>('file')
const urlFileInfo = ref<{ filename?: string; size?: number } | null>(null)
const maxFileSize = 100 * 1024 * 1024 // 100MB

// 批量上传相关
const batchFiles = ref<File[]>([])
const batchUploadRef = ref()
const batchProgress = ref({
  total: 0,
  processed: 0,
  success: 0,
  failed: 0,
  status: 'success' as 'success' | 'exception' | 'warning',
  files: [] as any[]
})
const batchId = ref<number | null>(null)
const batchStatusTimer = ref<any>(null)

const form = ref({
  knowledge_base_id: undefined as number | undefined,
  tags: [] as string[],
  url: '',
  filename: ''
})

const uploadRef = ref()
const showPreview = ref(false)
const previewFile = ref<any>(null)
const recommendedTags = ref<string[]>(['技术文档', '用户手册', 'API文档', '产品介绍'])

const loadKnowledgeBases = async () => {
  loading.value = true
  try {
    // 只加载有文档上传权限的知识库（后端过滤）
    const res = await getKnowledgeBases({ 
      page: 1, 
      size: 100,
      require_permission: 'doc:upload'
    })
    const data = res?.data ?? {}
    let kbList = data.list ?? data.items ?? []
    
    // 前端二次过滤：确保只显示有上传权限的知识库（role 不是 viewer）
    // 双重保险，即使后端过滤失效，前端也能过滤掉 viewer 角色
    knowledgeBases.value = kbList.filter((kb: KnowledgeBase) => {
      const role = kb.role
      // 只有 owner、admin、editor 有上传权限，viewer 没有
      return role && role !== 'viewer'
    })
  } catch (error) {
    ElMessage.error('加载知识库列表失败')
  } finally {
    loading.value = false
  }
}

const handleFileChange = (uploadFile: any) => {
  if (uploadFile.raw) {
    file.value = uploadFile.raw
  }
}

const handleFileRemove = () => {
  file.value = null
}

const handleModeChange = () => {
  // 切换模式时清空数据
  file.value = null
  batchFiles.value = []
  form.value.url = ''
  form.value.filename = ''
  urlFileInfo.value = null
  uploadResult.value = null
  batchId.value = null
  batchProgress.value = {
    total: 0,
    processed: 0,
    success: 0,
    failed: 0,
    status: 'success',
    files: []
  }
  if (batchStatusTimer.value) {
    clearInterval(batchStatusTimer.value)
    batchStatusTimer.value = null
  }
}

const handleBatchFileChange = (uploadFile: any) => {
  if (uploadFile.raw) {
    batchFiles.value.push(uploadFile.raw)
  }
}

const handleBatchFileRemove = (uploadFile: any) => {
  if (uploadFile.raw) {
    const index = batchFiles.value.findIndex(f => f.name === uploadFile.raw.name)
    if (index > -1) {
      batchFiles.value.splice(index, 1)
    }
  }
}

const clearBatchFiles = () => {
  batchFiles.value = []
  if (batchUploadRef.value) {
    batchUploadRef.value.clearFiles()
  }
}

const getStatusTagType = (status: string) => {
  const statusMap: Record<string, string> = {
    'completed': 'success',
    'failed': 'danger',
    'processing': 'warning',
    'pending': 'info'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'completed': '完成',
    'failed': '失败',
    'processing': '处理中',
    'pending': '待处理',
    'uploaded': '已上传',
    'parsing': '解析中',
    'chunking': '分块中',
    'vectorizing': '向量化中',
    'indexing': '索引中'
  }
  return statusMap[status] || status
}

const handleSubmit = async () => {
  if (!form.value.knowledge_base_id) {
    ElMessage.warning('请选择知识库')
    return
  }

  if (uploadMode.value === 'file') {
    // 本地上传
    if (!file.value) {
      ElMessage.warning('请选择文件')
      return
    }

    uploading.value = true
    try {
      const formData = new FormData()
      formData.append('file', file.value)
      formData.append('knowledge_base_id', String(form.value.knowledge_base_id))
      if (form.value.tags && form.value.tags.length > 0) {
        formData.append('tags', JSON.stringify(form.value.tags))
      }

      const res = await uploadDocument(formData)
      uploadResult.value = res.data || res
      ElMessage.success('上传成功')
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.message || error?.message || '上传失败')
    } finally {
      uploading.value = false
    }
  } else if (uploadMode.value === 'batch') {
    // 批量上传
    if (batchFiles.value.length === 0) {
      ElMessage.warning('请选择文件')
      return
    }

    uploading.value = true
    try {
      const formData = new FormData()
      batchFiles.value.forEach(file => {
        formData.append('files', file)
      })
      formData.append('knowledge_base_id', String(form.value.knowledge_base_id))
      if (form.value.tags && form.value.tags.length > 0) {
        formData.append('tags', JSON.stringify(form.value.tags))
      }

      const res = await batchUploadDocuments(formData)
      const data = res.data || res
      batchId.value = data.batch_id
      batchProgress.value = {
        total: data.total || batchFiles.value.length,
        processed: 0,
        success: data.success_count || 0,
        failed: data.fail_count || 0,
        status: 'success',
        files: []
      }
      
      // 开始轮询批次状态
      startBatchStatusPolling()
      
      ElMessage.success(`批量上传已开始，共 ${batchFiles.value.length} 个文件`)
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.message || error?.message || '批量上传失败')
    } finally {
      uploading.value = false
    }
  } else {
    // URL导入
    if (!form.value.url) {
      ElMessage.warning('请输入文档URL')
      return
    }

    // 验证URL格式
    try {
      new URL(form.value.url)
    } catch {
      ElMessage.warning('请输入有效的URL地址')
      return
    }

    uploading.value = true
    try {
      const formData = new FormData()
      formData.append('url', form.value.url)
      formData.append('knowledge_base_id', String(form.value.knowledge_base_id))
      if (form.value.tags && form.value.tags.length > 0) {
        formData.append('tags', JSON.stringify(form.value.tags))
      }
      if (form.value.filename) {
        formData.append('filename', form.value.filename)
      }

      const res = await uploadDocumentFromUrl(formData)
      uploadResult.value = res.data || res
      ElMessage.success('导入成功')
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.message || error?.message || '导入失败')
    } finally {
      uploading.value = false
    }
  }
}

// 监听URL变化，尝试获取文件信息
watch(() => form.value.url, async (newUrl) => {
  if (!newUrl || uploadMode.value !== 'url') {
    urlFileInfo.value = null
    return
  }

  // 验证URL格式
  try {
    new URL(newUrl)
    // 可以从URL中提取文件名
    const urlObj = new URL(newUrl)
    const pathname = urlObj.pathname
    const filename = pathname.split('/').pop() || 'document'
    if (filename && filename !== 'document') {
      urlFileInfo.value = { filename }
    }
  } catch {
    urlFileInfo.value = null
  }
})

const handlePreviewFile = () => {
  if (file.value) {
    previewFile.value = {
      name: file.value.name,
      size: file.value.size,
      url: URL.createObjectURL(file.value)
    }
    showPreview.value = true
  }
}

// 批量上传状态轮询
const startBatchStatusPolling = () => {
  if (!batchId.value) return
  
  batchStatusTimer.value = setInterval(async () => {
    try {
      const res = await getBatchStatus(batchId.value!)
      const data = res.data || res
      
      batchProgress.value = {
        total: data.total_files || 0,
        processed: data.processed_files || 0,
        success: data.success_files || 0,
        failed: data.failed_files || 0,
        status: data.status === 'completed' ? 'success' : 
                data.status === 'failed' ? 'exception' : 
                data.status === 'completed_with_errors' ? 'warning' : 'success',
        files: data.files || []
      }
      
      // 如果批次处理完成，停止轮询
      if (['completed', 'failed', 'completed_with_errors'].includes(data.status)) {
        if (batchStatusTimer.value) {
          clearInterval(batchStatusTimer.value)
          batchStatusTimer.value = null
        }
        if (data.status === 'completed') {
          ElMessage.success('批量上传完成')
        } else if (data.status === 'completed_with_errors') {
          ElMessage.warning(`批量上传完成，但有 ${data.failed_files} 个文件失败`)
        } else {
          ElMessage.error('批量上传失败')
        }
      }
    } catch (error) {
      console.error('获取批次状态失败:', error)
    }
  }, 2000) // 每2秒轮询一次
}

onUnmounted(() => {
  if (batchStatusTimer.value) {
    clearInterval(batchStatusTimer.value)
  }
})

loadKnowledgeBases()
</script>

<style lang="scss" scoped>
.upload-page {
  display: flex;
  justify-content: center;
  padding: 24px;
  position: relative;
}

/* 科技感动态网格背景 */
.upload-page::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(1200px 600px at 80% -20%, rgba(99,102,241,0.18), transparent 60%),
    radial-gradient(800px 400px at 10% 110%, rgba(59,130,246,0.15), transparent 55%),
    repeating-linear-gradient(
      90deg,
      rgba(255,255,255,0.06) 0,
      rgba(255,255,255,0.06) 1px,
      transparent 1px,
      transparent 28px
    ),
    repeating-linear-gradient(
      0deg,
      rgba(255,255,255,0.05) 0,
      rgba(255,255,255,0.05) 1px,
      transparent 1px,
      transparent 28px
    );
  mask-image: radial-gradient(closest-side, rgba(0,0,0,0.9), rgba(0,0,0,0.4));
}

.upload-card {
  width: 100%;
  max-width: 920px;
  background: linear-gradient(180deg, rgba(17,24,39,0.65), rgba(17,24,39,0.35));
  border: 1px solid rgba(99, 102, 241, 0.35);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35), inset 0 0 60px rgba(99,102,241,0.08);
  backdrop-filter: blur(6px);
  border-radius: 12px;
}

.card-header {
  display: flex;
  flex-direction: column;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #e9eef5;
  text-shadow: 0 0 12px rgba(99,102,241,0.55);
}

.card-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #c8d3e6;
  opacity: 0.95;
}

.upload-tabs {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  
  :deep(.el-radio-button__inner) {
    background: rgba(30, 41, 59, 0.6) !important;
    border-color: rgba(148, 163, 184, 0.3) !important;
    color: #cbd5e1 !important;
  }
  
  :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
    background: rgba(99, 102, 241, 0.4) !important;
    border-color: rgba(99, 102, 241, 0.6) !important;
    color: #e2e8f0 !important;
    box-shadow: 0 0 8px rgba(99, 102, 241, 0.3) !important;
  }
}

.kb-select {
  width: 360px;
}

.url-tips {
  :deep(.el-alert) {
    background: rgba(30, 41, 59, 0.7) !important;
    border: 1px solid rgba(99, 102, 241, 0.3) !important;
    border-radius: 8px;
  }
  
  :deep(.el-alert__title) {
    color: #e9eef5 !important;
    font-weight: 600;
    font-size: 14px;
  }
  
  :deep(.el-alert__content) {
    p {
      margin: 4px 0;
      color: #cbd5e1 !important;
      font-size: 12px;
      line-height: 1.6;
    }
  }
  
  :deep(.el-alert__icon) {
    color: #93c5fd !important;
  }
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 18px;
  border-radius: 12px;
  background: rgba(30, 41, 59, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.35);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.32);
}

.file-info span {
  color: #e2e8f0;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.2px;
}

/* 强化左侧表单标签与辅助文字的可读性（深色背景下） */
:deep(.el-form-item__label) {
  color: #e9eef5 !important;
  opacity: 1 !important;
  font-weight: 600;
  font-size: 14px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.35);
}

/* 拖拽上传提示文字 */
:deep(.el-upload__text) {
  color: #eef4ff !important;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0,0,0,0.35);
}
:deep(.el-upload-dragger) {
  background: rgba(30,41,59,0.5);
  border: 1px dashed rgba(99,102,241,0.6);
  box-shadow: inset 0 0 30px rgba(99,102,241,0.08);
}
:deep(.el-upload-dragger .el-icon--upload) {
  color: #93c5fd;
}
:deep(.el-upload-dragger em) {
  color: #93c5fd !important;
}

/* 输入框占位符与文本颜色 */
:deep(.el-input__inner) {
  color: #e2e8f0 !important;
  background: rgba(30, 41, 59, 0.6) !important;
  border-color: rgba(148, 163, 184, 0.3) !important;
}

:deep(.el-input__inner::placeholder) {
  color: #94a3b8 !important;
  opacity: 1;
}

:deep(.el-input__inner:focus) {
  border-color: rgba(99, 102, 241, 0.6) !important;
  background: rgba(30, 41, 59, 0.8) !important;
}

:deep(.el-input-group__prepend) {
  background: rgba(30, 41, 59, 0.6) !important;
  border-color: rgba(148, 163, 184, 0.3) !important;
  color: #93c5fd !important;
}

:deep(.el-select .el-input__inner) {
  color: #e2e8f0 !important;
}

:deep(.el-select-dropdown) {
  background: rgba(30, 41, 59, 0.95) !important;
  border: 1px solid rgba(99, 102, 241, 0.3) !important;
}

:deep(.el-select-dropdown__item) {
  color: #e2e8f0 !important;
}

:deep(.el-select-dropdown__item:hover) {
  background: rgba(99, 102, 241, 0.2) !important;
}

:deep(.el-select-dropdown__item.is-selected) {
  color: #93c5fd !important;
  background: rgba(99, 102, 241, 0.3) !important;
}

/* 警告条文字颜色（通用，针对知识库选择提示） */
:deep(.el-alert) {
  background: rgba(30, 41, 59, 0.7) !important;
  border: 1px solid rgba(251, 191, 36, 0.3) !important;
}

:deep(.el-alert__title) {
  color: #fbbf24 !important;
  font-weight: 600;
}

:deep(.el-alert--warning) {
  background: rgba(30, 41, 59, 0.7) !important;
  border-color: rgba(251, 191, 36, 0.3) !important;
}

/* 主操作按钮视觉增强 */
:deep(.el-button.el-button--primary) {
  box-shadow: 0 4px 16px rgba(59,130,246,0.35);
  background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
  border: none !important;
}

:deep(.el-button:not(.el-button--primary)) {
  background: rgba(30, 41, 59, 0.6) !important;
  border-color: rgba(148, 163, 184, 0.3) !important;
  color: #e2e8f0 !important;
}

:deep(.el-button:not(.el-button--primary):hover) {
  background: rgba(30, 41, 59, 0.8) !important;
  border-color: rgba(148, 163, 184, 0.5) !important;
  color: #f1f5f9 !important;
}

/* 上传成功提示的可读性增强 */
:deep(.el-result__title) {
  color: #e6f0ff !important;
  text-shadow: 0 1px 2px rgba(0,0,0,0.35);
  font-weight: 700;
}
:deep(.el-result__subtitle) {
  color: #cbd5e1 !important;
  opacity: 1;
}
:deep(.el-result .icon-success) {
  filter: drop-shadow(0 0 10px rgba(16,185,129,0.35));
}

/* 标签选择器样式优化 */
:deep(.tag-selector) {
  .el-tag {
    background: rgba(99, 102, 241, 0.2) !important;
    border-color: rgba(99, 102, 241, 0.4) !important;
    color: #cbd5e1 !important;
  }
  
  .el-input__inner {
    background: rgba(30, 41, 59, 0.6) !important;
    border-color: rgba(148, 163, 184, 0.3) !important;
    color: #e2e8f0 !important;
  }
}

/* 自定义文件名输入框 */
:deep(.el-form-item:has(.el-input input[placeholder*="可选"])) {
  .el-input__inner {
    background: rgba(30, 41, 59, 0.6) !important;
    border-color: rgba(148, 163, 184, 0.3) !important;
    color: #e2e8f0 !important;
  }
}
</style>
