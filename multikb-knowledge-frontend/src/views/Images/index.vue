<template>
  <div class="images-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>图片管理</span>
          <el-radio-group v-model="viewType" size="small">
            <el-radio-button label="list">列表</el-radio-button>
            <el-radio-button label="grid">网格</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-form :inline="true" :model="filterForm">
          <el-form-item label="来源文档">
            <el-input
              v-model.number="filterForm.document_id"
              placeholder="请输入文档ID"
              clearable
              style="width: 200px"
              @clear="handleFilter"
            >
              <template #append>
                <el-button type="primary" @click="handleFilter">筛选</el-button>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item>
            <el-button class="reset-btn" @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <div v-loading="loading" class="images-container" :class="{ 'grid-view': viewType === 'grid' }">
        <el-empty v-if="images.length === 0" description="暂无图片" />

        <div v-else class="image-list">
          <div
            v-for="image in images"
            :key="image.id"
            class="image-item"
            @click="handleImageClick(image)"
          >
            <!-- 图片预览区域 -->
            <div class="image-preview">
              <img :src="image.image_path" :alt="image.description" />
              <div class="image-overlay">
                <el-icon class="preview-icon"><ZoomIn /></el-icon>
              </div>
            </div>
            
            <!-- 信息区域 -->
            <div class="image-info">
              <!-- 标题和基本信息 -->
              <div class="info-header">
                <div class="image-title" :title="image.description || `图片 #${image.id}`">
                  {{ image.description || `图片 #${image.id}` }}
                </div>
                <div class="image-badges">
                  <el-tag v-if="image.image_type" size="small" type="info" effect="plain">
                    {{ image.image_type }}
                  </el-tag>
                  <el-tag v-if="image.document_id" size="small" type="warning" effect="plain">
                    文档{{ image.document_id }}
                  </el-tag>
                </div>
              </div>

              <!-- 状态信息 -->
              <div class="status-section">
                <div class="status-tags">
                  <el-tag
                    v-if="image.status"
                    size="small"
                    :type="statusTagType(image.status)"
                  >
                    {{ statusLabel(image.status) }}
                  </el-tag>
                  <el-tag
                    size="small"
                    :type="image?.vector_model && image?.vector_dim ? 'success' : 'info'"
                    effect="plain"
                  >
                    {{ vectorStatusLabel(image) }}
                  </el-tag>
                </div>
                <div class="file-size">
                  <el-icon><Document /></el-icon>
                  <span>{{ formatFileSize(image.file_size || 0) }}</span>
                </div>
              </div>

              <!-- OCR文本预览 -->
              <div class="ocr-section">
                <div v-if="image.ocr_text" class="ocr-preview">
                  <el-icon class="ocr-icon"><DocumentCopy /></el-icon>
                  <span class="ocr-text">{{ truncateText(image.ocr_text, 50) }}</span>
                </div>
                <div v-else class="ocr-empty">
                  <el-icon class="ocr-icon"><DocumentDelete /></el-icon>
                  <span>未检测到文字</span>
                </div>
              </div>

              <!-- 底部信息 -->
              <div class="info-footer">
                <div v-if="image.last_processed_at" class="process-time">
                  <el-icon><Clock /></el-icon>
                  <span>{{ formatDateTime(image.last_processed_at) }}</span>
                </div>
                <div class="image-actions" @click.stop>
                  <el-button
                    size="small"
                    type="primary"
                    :loading="retryingId === image.id"
                    :disabled="(image.status || '').toLowerCase() === 'completed' || (image.status || '').toLowerCase() === 'processing'"
                    @click="handleRetry(image)"
                  >
                    <el-icon><Refresh /></el-icon>
                    <span>重新识别</span>
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        :total="total"
        :page-sizes="[12, 24, 48, 96]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
        class="pagination"
        :disabled="loading"
      />
    </el-card>

    <el-dialog v-model="imageDialogVisible" title="图片详情" width="900px">
      <div v-if="selectedImage" class="image-detail">
        <div class="detail-info">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="图片ID">{{ selectedImage.id }}</el-descriptions-item>
            <el-descriptions-item label="来源文档ID">{{ selectedImage.document_id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="图片类型">{{ selectedImage.image_type || '-' }}</el-descriptions-item>
            <el-descriptions-item label="文件大小">{{ formatFileSize(selectedImage.file_size || 0) }}</el-descriptions-item>
            <el-descriptions-item label="图片尺寸" v-if="selectedImage.width && selectedImage.height">
              {{ selectedImage.width }} × {{ selectedImage.height }} 像素
            </el-descriptions-item>
            <el-descriptions-item label="向量模型">{{ selectedImage.vector_model || '-' }}</el-descriptions-item>
            <el-descriptions-item label="向量维度">{{ selectedImage.vector_dim || '-' }}</el-descriptions-item>
            <el-descriptions-item label="处理状态">{{ selectedImage.status || '-' }}</el-descriptions-item>
            <el-descriptions-item label="重试次数">{{ selectedImage.retry_count ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="最近处理时间">
              {{ formatDateTime(selectedImage.last_processed_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间" v-if="selectedImage.created_at">
              {{ new Date(selectedImage.created_at).toLocaleString() }}
            </el-descriptions-item>
          </el-descriptions>
          
          <el-divider />
          
          <div v-if="selectedImage.description" class="info-section">
            <h4>描述</h4>
            <p>{{ selectedImage.description }}</p>
          </div>
          
          <div class="info-section">
            <h4>OCR识别文字</h4>
            <template v-if="selectedImage.ocr_text">
              <p class="ocr-text">{{ selectedImage.ocr_text }}</p>
            </template>
            <template v-else>
              <p class="ocr-empty">未检测到文字</p>
            </template>
          </div>

          <div v-if="selectedImage.error_message" class="info-section">
            <h4>错误信息</h4>
            <p class="error-text">{{ selectedImage.error_message }}</p>
          </div>
          
          <div v-if="selectedImage.meta" class="info-section">
            <h4>元数据</h4>
            <pre class="meta-data">{{ typeof selectedImage.meta === 'string' ? selectedImage.meta : JSON.stringify(selectedImage.meta, null, 2) }}</pre>
          </div>

          <div class="detail-actions">
            <el-button
              type="primary"
              :loading="retryingId === selectedImage.id"
              :disabled="(selectedImage.status || '').toLowerCase() === 'completed' || (selectedImage.status || '').toLowerCase() === 'processing'"
              @click="handleRetry(selectedImage)"
            >
              重新识别
            </el-button>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { ZoomIn, Document, DocumentCopy, DocumentDelete, Clock, Refresh } from '@element-plus/icons-vue'
import { getImageList, getImageDetail, retryImageOcr } from '@/api/modules/images'
import { formatFileSize, formatDateTime, truncateText } from '@/utils/format'

const loading = ref(false)
const images = ref<any[]>([])
const viewType = ref<'list' | 'grid'>('grid')
const page = ref(1)
const size = ref(24)
const total = ref(0)
const imageDialogVisible = ref(false)
const selectedImage = ref<any>(null)
const retryingId = ref<number | null>(null)
const isChangingSize = ref(false)

const filterForm = ref({
  document_id: undefined as number | undefined
})

const loadData = async () => {
  loading.value = true
  try {
    // 计算 skip（后端使用 skip/limit）
    const skip = (page.value - 1) * size.value
    
    const params: any = {
      skip,
      limit: size.value
    }
    
    // 如果有文档ID筛选，添加到参数
    if (filterForm.value.document_id) {
      params.document_id = filterForm.value.document_id
    }
    
    const res = await getImageList(params)
    
    // 处理返回数据 - 后端现在返回 { code: 0, message: "ok", data: { list: [], total: 0 } }
    let imageList: any[] = []
    let newTotal = 0
    
    if (res && typeof res === 'object') {
      // 检查是否是新的分页格式
      if (res.code === 0 && res.data && typeof res.data === 'object') {
        imageList = res.data.list || res.data.items || []
        newTotal = res.data.total || 0
      } 
      // 兼容旧格式：直接是数组
      else if (Array.isArray(res)) {
        imageList = res
        newTotal = res.length
      }
      // 兼容旧格式：{ data: [...] }
      else if (res.data) {
        if (Array.isArray(res.data)) {
          imageList = res.data
          newTotal = (res as any).total || res.data.length
        } else if (res.data.list || res.data.items) {
          imageList = res.data.list || res.data.items || []
          newTotal = res.data.total || imageList.length
        }
      }
    }
    
    // 更新总数（确保是数字类型）
    total.value = Number(newTotal) || 0
    
    // 数据加载后，检查当前页是否超出范围
    // 只有在非改变每页数量的情况下才调整页码，避免与 handleSizeChange 冲突
    if (!isChangingSize.value) {
      const totalPages = Math.ceil(total.value / size.value)
      if (totalPages > 0 && page.value > totalPages) {
        // 如果超出范围，调整到最后一页
        page.value = totalPages
      }
    }
    
    // 确保所有图片URL都包含token（用于认证）
    const token = localStorage.getItem('access_token')
    images.value = imageList.map((img: any) => {
      if (img.image_path && typeof img.image_path === 'string') {
        // 如果已经是完整URL或已包含token，不处理
        if (img.image_path.startsWith('http') || img.image_path.includes('token=')) {
          return img
        }
        
        // 确保路径以 /api 开头（如果后端返回的是 /images/file，需要改为 /api/images/file）
        let finalPath = img.image_path
        if (finalPath.startsWith('/images/file') && !finalPath.startsWith('/api/images/file')) {
          finalPath = finalPath.replace('/images/file', '/api/images/file')
        }
        
        // 添加token到URL
        const separator = finalPath.includes('?') ? '&' : '?'
        img.image_path = `${finalPath}${separator}token=${token || ''}`
      }
      return img
    })
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '加载图片列表失败')
    images.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const handlePageChange = (newPage: number) => {
  // 如果正在改变每页数量，忽略页码变化事件（避免冲突）
  if (isChangingSize.value) {
    return
  }
  // 确保页码变化时重新加载数据
  if (page.value !== newPage) {
    page.value = newPage
  }
  loadData()
}

const handleSizeChange = async (newSize: number) => {
  // 标记正在改变每页数量
  isChangingSize.value = true
  
  try {
    // 更新每页数量
    size.value = newSize
    // 改变每页数量时，重置到第1页
    page.value = 1
    
    // 等待 Vue 完成响应式更新
    await nextTick()
    
    // 再等待一个 tick，确保分页组件也更新完成
    await nextTick()
    
    // 重新加载数据
    await loadData()
  } finally {
    // 恢复标记（延迟一点，确保所有事件处理完成）
    await nextTick()
    isChangingSize.value = false
  }
}

const handleFilter = () => {
  page.value = 1
  loadData()
}

const handleReset = () => {
  filterForm.value.document_id = undefined
  page.value = 1
  loadData()
}

const handleImageClick = async (image: any) => {
  try {
    // 加载完整图片详情
    const detailRes = await getImageDetail(image.id)
    const detail = detailRes?.data || detailRes || image
    // 确保 image_path 可直接访问（后端应已处理，这里再次兜底）
    if (detail && typeof detail.image_path === 'string' && !/^https?:\/\//.test(detail.image_path)) {
      const enc = encodeURIComponent(detail.image_path)
      const token = localStorage.getItem('access_token')
      detail.image_path = `/api/images/file?object=${enc}${token ? `&token=${token}` : ''}`
    }
    selectedImage.value = detail
    imageDialogVisible.value = true
  } catch (error: any) {
    // 如果加载详情失败，使用列表中的基本信息
    selectedImage.value = image
    imageDialogVisible.value = true
  }
}

onMounted(() => {
  loadData()
})

const statusTagType = (status?: string) => {
  switch ((status || '').toLowerCase()) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'danger'
    case 'processing':
      return 'warning'
    default:
      return 'info'
  }
}

const statusLabel = (status?: string) => {
  switch ((status || '').toLowerCase()) {
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    case 'processing':
      return '处理中'
    case 'pending':
      return '待处理'
    default:
      return status || '未知'
  }
}

const vectorStatusLabel = (image: any) => {
  if (image?.vector_model && image?.vector_dim) return '已向量化'
  if (image?.status === 'failed') return '向量待重试'
  return '待向量化'
}

const canRetry = (image: any) => {
  const status = (image?.status || '').toLowerCase()
  return status !== 'completed' && status !== 'processing' && !retryingId.value
}

const handleRetry = async (image: any) => {
  if (!image || image.status === 'completed') return
  retryingId.value = image.id
  try {
    await retryImageOcr(image.id)
    ElMessage.success('已触发重新识别，请稍候刷新状态')
    await loadData()
    if (selectedImage.value?.id === image.id) {
      const detailRes = await getImageDetail(image.id)
      const detail = detailRes?.data || detailRes
      selectedImage.value = detail
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '重试失败')
  } finally {
    retryingId.value = null
  }
}
</script>

<style lang="scss" scoped>
.images-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .filter-bar {
    margin-bottom: 20px;
    padding: 16px;
    background: #f5f7fa;
    border-radius: 4px;
    :deep(.el-input-group__append) .el-button {
      font-weight: 600;
    }
    .reset-btn {
      background: #ffffff;
      border-color: #cbd5e1;
      color: #1f2937;
      font-weight: 600;
    }
  }

  .images-container {
    min-height: 400px;

    &.grid-view {
      .image-list {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 20px;

        @media (max-width: 768px) {
          grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
          gap: 16px;
        }

        @media (max-width: 480px) {
          grid-template-columns: 1fr;
          gap: 12px;
        }
      }
    }

    .image-item {
      border: 1px solid #e4e7ed;
      border-radius: 8px;
      overflow: hidden;
      cursor: pointer;
      transition: all 0.3s ease;
      background: #fff;
      display: flex;
      flex-direction: column;

      &:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        border-color: #409eff;
        transform: translateY(-2px);
      }

      .image-preview {
        position: relative;
        width: 100%;
        height: 200px;
        overflow: hidden;
        background: #f5f7fa;
        flex-shrink: 0;

        img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          transition: transform 0.3s ease;
        }

        .image-overlay {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0);
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;

          .preview-icon {
            font-size: 32px;
            color: #fff;
            opacity: 0;
            transition: opacity 0.3s ease;
          }
        }

        &:hover {
          img {
            transform: scale(1.05);
          }

          .image-overlay {
            background: rgba(0, 0, 0, 0.4);

            .preview-icon {
              opacity: 1;
            }
          }
        }
      }

      .image-info {
        padding: 16px;
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 12px;

        .info-header {
          .image-title {
            font-size: 14px;
            font-weight: 600;
            color: #303133;
            margin-bottom: 8px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            line-height: 1.4;
          }

          .image-badges {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
          }
        }

        .status-section {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 0;
          border-top: 1px solid #f0f0f0;
          border-bottom: 1px solid #f0f0f0;

          .status-tags {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
          }

          .file-size {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 12px;
            color: #909399;

            .el-icon {
              font-size: 14px;
            }
          }
        }

        .ocr-section {
          min-height: 40px;
          padding: 8px;
          background: #f5f7fa;
          border-radius: 4px;

          .ocr-preview {
            display: flex;
            align-items: flex-start;
            gap: 6px;
            font-size: 12px;
            color: #606266;
            line-height: 1.5;

            .ocr-icon {
              font-size: 14px;
              color: #409eff;
              margin-top: 2px;
              flex-shrink: 0;
            }

            .ocr-text {
              flex: 1;
              overflow: hidden;
              text-overflow: ellipsis;
              display: -webkit-box;
              -webkit-line-clamp: 2;
              -webkit-box-orient: vertical;
            }
          }

          .ocr-empty {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: #c0c4cc;

            .ocr-icon {
              font-size: 14px;
            }
          }
        }

        .info-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: auto;
          padding-top: 8px;
          border-top: 1px solid #f0f0f0;

          .process-time {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 12px;
            color: #909399;

            .el-icon {
              font-size: 14px;
            }
          }

          .image-actions {
            .el-button {
              padding: 4px 12px;
              font-size: 12px;

              .el-icon {
                margin-right: 4px;
              }
            }
          }
        }
      }
    }
  }

  .pagination {
    margin-top: 20px;
    text-align: right;
  }
  
  /* 优化分页组件样式 */
  :deep(.el-pagination) {
    color: rgba(255, 255, 255, 0.85);
    
    .el-pagination__total,
    .el-pagination__jump {
      color: rgba(255, 255, 255, 0.85);
    }
    
    .btn-prev,
    .btn-next {
      color: rgba(255, 255, 255, 0.85);
      
      &:hover {
        color: #409eff;
      }
      
      &.disabled {
        color: rgba(255, 255, 255, 0.3);
      }
    }
    
    .el-pager li {
      color: rgba(255, 255, 255, 0.85);
      background-color: transparent;
      
      &:hover {
        color: #409eff;
      }
      
      &.is-active {
        color: #409eff;
        background-color: rgba(64, 158, 255, 0.2);
      }
    }
    
    .el-pagination__editor {
      .el-input {
        .el-input__inner {
          background-color: rgba(255, 255, 255, 0.08) !important;
          border-color: rgba(255, 255, 255, 0.2) !important;
          color: rgba(255, 255, 255, 0.95) !important;
          font-size: 14px;
          width: 50px;
          height: 32px;
          text-align: center;
          
          &::placeholder {
            color: rgba(255, 255, 255, 0.5) !important;
          }
          
          &:focus {
            border-color: #409eff !important;
            background-color: rgba(255, 255, 255, 0.12) !important;
          }
        }
        
        .el-input__wrapper {
          background-color: rgba(255, 255, 255, 0.08) !important;
          border-color: rgba(255, 255, 255, 0.2) !important;
          box-shadow: none !important;
          
          &.is-focus {
            border-color: #409eff !important;
            box-shadow: 0 0 0 1px #409eff inset !important;
          }
        }
      }
    }
    
    .el-select {
      .el-input__inner {
        background-color: rgba(255, 255, 255, 0.08) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        color: rgba(255, 255, 255, 0.95) !important;
      }
    }
  }

    .image-detail {
    .detail-info {
      .info-section {
        margin-top: 16px;

        h4 {
          margin-bottom: 8px;
          color: #303133;
          font-size: 14px;
          font-weight: 600;
        }

        p {
          margin: 0;
          color: #606266;
          line-height: 1.6;
        }

        .ocr-text {
          background: #f5f7fa;
          padding: 12px;
          border-radius: 4px;
          white-space: pre-wrap;
          word-break: break-word;
        }

        .meta-data {
          background: #f5f7fa;
          padding: 12px;
          border-radius: 4px;
          overflow-x: auto;
          font-size: 12px;
          line-height: 1.5;
          max-height: 300px;
          overflow-y: auto;
        }

        .error-text {
          background: #fef2f2;
          color: #b91c1c;
          padding: 12px;
          border-radius: 4px;
          white-space: pre-wrap;
        }

        .ocr-empty {
          margin: 0;
          color: #94a3b8;
        }
      }
      .detail-actions {
        margin-top: 16px;
        text-align: right;
      }
    }
  }
}
</style>
