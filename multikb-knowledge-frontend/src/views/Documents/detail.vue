<template>
  <div class="document-detail-page" v-loading="loading">
    <el-card v-if="document">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-button 
              circle 
              @click="handleBack"
              class="back-button"
              title="返回"
            >
              <el-icon><ArrowLeft /></el-icon>
            </el-button>
            <span>文档详情</span>
          </div>
          <div>
            <el-button @click="handleEdit">编辑</el-button>
            <el-button type="danger" @click="handleDelete">删除</el-button>
          </div>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="标题">{{ document.title }}</el-descriptions-item>
        <el-descriptions-item label="文件名">{{ document.file_name }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ document.file_type }}</el-descriptions-item>
        <el-descriptions-item label="大小">{{ formatFileSize(document.file_size) }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(document.status)">
            {{ getStatusText(document.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDateTime(document.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDateTime(document.updated_at) }}</el-descriptions-item>
      <el-descriptions-item label="安全扫描状态">
        <el-tag :type="getSecurityScanStatusType(document.security_scan_status || 'pending')" size="small">
          {{ getSecurityScanStatusText(document.security_scan_status || 'pending') }}
        </el-tag>
        <span v-if="document.security_scan_method" style="margin-left: 8px; color: #909399; font-size: 12px;">
          ({{ getSecurityScanMethodText(document.security_scan_method) }})
        </span>
      </el-descriptions-item>
      <el-descriptions-item v-if="document.security_scan_timestamp" label="扫描时间">
        {{ formatDateTime(document.security_scan_timestamp) }}
      </el-descriptions-item>
      </el-descriptions>

      <!-- 安全扫描详情 -->
      <el-card v-if="document.security_scan_result" style="margin-top: 16px;">
        <template #header>
          <span>安全扫描详情</span>
        </template>
        <el-descriptions :column="1" size="small" border>
          <el-descriptions-item label="扫描方法">
            {{ getSecurityScanMethodText(document.security_scan_method) }}
          </el-descriptions-item>
          <el-descriptions-item v-if="document.security_scan_result?.virus_scan" label="ClamAV 扫描">
            <el-tag :type="getVirusScanStatusType(document.security_scan_result.virus_scan?.status)" size="small">
              {{ getVirusScanStatusText(document.security_scan_result.virus_scan?.status) }}
            </el-tag>
            <span v-if="document.security_scan_result.virus_scan?.message" style="margin-left: 8px; color: #909399; font-size: 12px;">
              {{ document.security_scan_result.virus_scan.message }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item v-if="document.security_scan_result?.script_scan" label="脚本检测">
            <el-tag :type="document.security_scan_result.script_scan?.safe ? 'success' : 'warning'" size="small">
              {{ document.security_scan_result.script_scan?.safe ? '安全' : '可疑' }}
            </el-tag>
            <span v-if="document.security_scan_result.script_scan?.found_keywords?.length" style="margin-left: 8px; color: #E6A23C; font-size: 12px;">
              发现关键词: {{ document.security_scan_result.script_scan.found_keywords.join(', ') }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item v-if="document.security_scan_result?.threats_found?.length" label="威胁列表">
            <el-tag type="danger" size="small" v-for="threat in document.security_scan_result.threats_found" :key="threat" style="margin-right: 4px;">
              {{ threat }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-divider>文档内容</el-divider>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="内容预览" name="preview">
          <!-- 预览加载中 -->
          <div v-if="previewLoading || (!previewReady && isOffice && document?.status !== 'completed')" class="preview-loading-container" v-loading="true" element-loading-text="预览生成中，请稍候...">
            <div style="height: 400px;"></div>
          </div>
          <!-- 预览已准备好 -->
          <template v-else-if="previewUrl && previewReady">
            <div class="preview-switch" v-if="htmlPreviewUrl && isPdf">
              <span>预览模式：</span>
              <el-radio-group v-model="previewMode" size="small">
                <el-radio-button label="pdf">PDF</el-radio-button>
                <el-radio-button label="html">原始样式</el-radio-button>
              </el-radio-group>
            </div>
            <!-- PDF 直接内嵌展示（优先显示PDF预览） -->
            <iframe
              v-if="isPdf && previewMode === 'pdf'"
              class="preview-frame"
              :src="previewUrl"
              frameborder="0"
              referrerpolicy="no-referrer"
            />
            <!-- HTML 预览 -->
            <iframe
              v-else-if="isPdf && previewMode === 'html' && htmlPreviewUrl"
              class="preview-frame"
              :src="htmlPreviewUrl"
              frameborder="0"
              referrerpolicy="no-referrer"
            />
            <!-- Office 文档：如果有PDF预览就显示PDF，否则显示下载提示 -->
            <div v-else-if="isOffice && !isPdf" class="preview-download">
              <el-alert type="info" :closable="false" show-icon>
                <template #title>
                  <span>预览生成中或生成失败</span>
                </template>
                <template #default>
                  <div style="margin-top: 8px;">
                    <p>PDF预览尚未生成，您可以：</p>
                    <el-button type="primary" :href="previewUrl" target="_blank" style="margin-top: 8px;">下载原始文件</el-button>
                  </div>
                </template>
              </el-alert>
            </div>
            <!-- 图片原样展示 -->
            <img v-else-if="isImage" class="image-inline" :src="previewUrl" />
            <!-- Markdown 文件渲染 -->
            <div v-else-if="isMarkdown" class="markdown-preview-container" v-loading="textLoading">
              <div class="markdown-content" v-html="renderedMarkdown"></div>
            </div>
            <!-- HTML 文档原样展示 -->
            <iframe
              v-else-if="isHtml"
              class="preview-frame"
              :src="previewUrl"
              frameborder="0"
              referrerpolicy="no-referrer"
            />
            <!-- 文本文件在线预览 -->
            <div v-else-if="isText" class="text-preview-container" v-loading="textLoading">
              <pre class="text-preview-content">{{ textContent || contentPreview }}</pre>
            </div>
            <!-- 其他类型：提供打开原文件按钮 -->
            <div v-else class="preview-download">
              <el-alert type="info" :closable="false" show-icon title="该文件类型暂不支持内嵌预览，已提供原文件直链。" />
              <el-button type="primary" :href="previewUrl" target="_blank">打开原文件</el-button>
            </div>
          </template>
          <!-- 无预览URL时显示内容预览 -->
          <div class="content-preview" v-else v-html="contentPreview"></div>
        </el-tab-pane>

        <el-tab-pane label="分块列表" name="chunks">
          <el-table :data="chunks" v-loading="chunksLoading" class="chunk-table">
            <el-table-column prop="chunk_index" label="序号" width="80" />
            <el-table-column label="类型" width="120">
              <template #default="{ row }">
                <el-tag :type="getChunkTypeTagType(row.chunk_type)" size="small">
                  {{ getChunkTypeLabel(row.chunk_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="char_count" label="字符数" width="120" />
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-tag size="small" type="info" @click="showChunk(row)" style="cursor:pointer">查看内容</el-tag>
              </template>
            </el-table-column>
          </el-table>

          <el-dialog
            v-model="chunkDialogVisible"
            title="分块内容"
            width="60%"
            class="chunk-dialog"
          >
            <template #default>
              <!-- 图片分块 -->
              <div v-if="currentChunk && currentChunk.chunk_type === 'image'">
                <img
                  v-if="currentChunk.image_url"
                  class="chunk-image"
                  :src="currentChunk.image_url"
                  alt="分块图片"
                />
                <div class="chunk-meta" v-if="currentChunk.meta">
                  <el-descriptions :column="1" size="small" border>
                    <el-descriptions-item label="图片路径">{{ currentChunk.image_path || '—' }}</el-descriptions-item>
                    <el-descriptions-item label="图片ID">{{ currentChunk.image_id || '—' }}</el-descriptions-item>
                  </el-descriptions>
                </div>
              </div>
              
              <!-- 代码块分块 -->
              <div v-else-if="currentChunk && currentChunk.chunk_type === 'code_block'">
                <div class="chunk-meta" v-if="currentChunk.meta">
                  <el-descriptions :column="1" size="small" border>
                    <el-descriptions-item label="代码语言">
                      {{ getChunkMeta(currentChunk, 'code_language') || '未知' }}
                    </el-descriptions-item>
                  </el-descriptions>
                </div>
                <div class="chunk-code-content" v-html="highlightCode(currentChunk?.content || '', getChunkMeta(currentChunk, 'code_language'))"></div>
              </div>
              
              <!-- HTML 特有分块（标题章节、语义块、列表、段落） -->
              <div v-else-if="currentChunk && isHtmlChunk(currentChunk)">
                <div class="chunk-meta" v-if="currentChunk.meta">
                  <el-descriptions :column="1" size="small" border>
                    <el-descriptions-item label="分块类型">
                      {{ getChunkTypeLabel(currentChunk.chunk_type) }}
                    </el-descriptions-item>
                    <el-descriptions-item v-if="getChunkMeta(currentChunk, 'heading_level')" label="标题层级">
                      H{{ getChunkMeta(currentChunk, 'heading_level') }}
                    </el-descriptions-item>
                    <el-descriptions-item v-if="getChunkMeta(currentChunk, 'heading_path')?.length" label="标题路径">
                      {{ getChunkMeta(currentChunk, 'heading_path')?.join(' > ') || '—' }}
                    </el-descriptions-item>
                    <el-descriptions-item v-if="getChunkMeta(currentChunk, 'semantic_tag')" label="语义标签">
                      {{ getChunkMeta(currentChunk, 'semantic_tag') }}
                    </el-descriptions-item>
                    <el-descriptions-item v-if="getChunkMeta(currentChunk, 'list_type')" label="列表类型">
                      {{ getChunkMeta(currentChunk, 'list_type') }}
                    </el-descriptions-item>
                  </el-descriptions>
                </div>
                <pre class="chunk-content">{{ currentChunk?.content || '' }}</pre>
              </div>
              
              <!-- 其他分块 -->
              <pre v-else class="chunk-content">{{ currentChunk?.content || '' }}</pre>
            </template>
          </el-dialog>
        </el-tab-pane>

        <el-tab-pane label="目录导航" name="toc">
          <div v-loading="tocLoading" class="toc-container">
            <template v-if="tocItems.length > 0">
              <el-tree
                :data="tocTree"
                :props="{ children: 'children', label: 'title' }"
                default-expand-all
                @node-click="handleTocClick"
              >
                <template #default="{ node, data }">
                  <div class="toc-node">
                    <span class="toc-title">{{ data.title }}</span>
                    <span class="toc-page" v-if="data.page_number">第 {{ data.page_number }} 页</span>
                  </div>
                </template>
              </el-tree>
            </template>
            <el-empty v-else description="该文档暂无目录信息" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="版本历史" name="versions">
          <template v-if="versionsCount > 0">
            <el-timeline>
              <el-timeline-item
                v-for="version in versions"
                :key="version.id"
                :timestamp="formatDateTime(version.created_at)"
              >
                <div :class="['version-line', getVersionType(version)]">
                  <el-tag class="ver-tag" size="large">{{ version.version_number }}</el-tag>
                  <span class="version-desc" :title="version.description || '—'">{{ version.description || '—' }}</span>
                </div>
              </el-timeline-item>
            </el-timeline>
          </template>
          <el-empty v-else description="暂无版本（0）" />
        </el-tab-pane>

        <el-tab-pane label="图片列表" name="images">
          <el-empty v-if="images.length === 0" description="图片列表为空" />
          <div v-else class="image-gallery">
            <div
              v-for="image in images"
              :key="image.id"
              class="image-item"
              @click="viewImage(image)"
            >
              <img :src="image.url || image.image_path" :alt="image.description" />
              <div class="image-info">{{ image.description }}</div>
            </div>
          </div>
        </el-tab-pane>
        
        <!-- 结构化预览（JSON/XML/CSV） -->
        <el-tab-pane v-if="isStructuredType" label="结构化预览" name="structured">
          <StructuredPreview :document-id="documentId" />
        </el-tab-pane>
      </el-tabs>
      
      <!-- AI标签和摘要 -->
      <el-card style="margin-top: 16px;">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span>AI 标签与摘要</span>
            <el-button 
              size="small" 
              type="primary"
              :loading="regenerating"
              @click="handleRegenerateSummary"
            >
              {{ document?.metadata?.auto_keywords || document?.metadata?.auto_summary ? '重新生成' : '生成摘要' }}
            </el-button>
          </div>
        </template>
        <div v-if="document?.metadata?.auto_keywords && document.metadata.auto_keywords.length > 0" class="ai-keywords-section">
          <div style="margin-bottom: 16px;">
            <strong class="section-label">关键词：</strong>
            <el-tag
              v-for="keyword in document.metadata.auto_keywords"
              :key="keyword"
              class="keyword-tag"
            >
              {{ keyword }}
            </el-tag>
          </div>
        </div>
        <div v-else-if="!regenerating" class="ai-empty-text">
          <span>暂无关键词</span>
        </div>
        <div v-if="document?.metadata?.auto_summary" class="ai-summary-section">
          <strong class="section-label">摘要：</strong>
          <p class="summary-text">{{ document.metadata.auto_summary }}</p>
        </div>
        <div v-else-if="!regenerating" class="ai-empty-text">
          <span>暂无摘要</span>
        </div>
        <div v-if="regenerating" style="text-align: center; padding: 20px; color: #909399;">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span style="margin-left: 8px;">正在生成中...</span>
        </div>
      </el-card>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Loading, ArrowLeft } from '@element-plus/icons-vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import {
  getDocumentDetail,
  deleteDocument,
  reprocessDocument,
  getDocumentChunks,
  getDocumentImages,
  getDocumentVersions,
  getDocumentPreview,
  getChunkContentFromOS,
  getDocumentTOC,
  getStructuredPreview,
  regenerateSummary
} from '@/api/modules/documents'
import { formatFileSize, formatDateTime } from '@/utils/format'
import StructuredPreview from '@/components/business/StructuredPreview.vue'
import type { Document } from '@/types'

const route = useRoute()
const router = useRouter()
const documentId = Number(route.params.id)

const document = ref<Document | null>(null)
const loading = ref(false)
const chunks = ref<any[]>([])
const chunksLoading = ref(false)
const versions = ref<any[]>([])
const images = ref<any[]>([])
const tocItems = ref<any[]>([])
const tocLoading = ref(false)
const activeTab = ref('preview')
const contentPreview = ref('')
const previewUrl = ref('')
const previewType = ref('')
const htmlPreviewUrl = ref('')
const previewMode = ref<'pdf' | 'html'>('pdf')
const previewLoading = ref(false)
const previewReady = ref(false)  // 预览是否已准备好
let previewRetryCount = 0  // 预览重试次数
const MAX_PREVIEW_RETRIES = 30  // 最多重试30次（90秒）
const isPdf = computed(() => /pdf/i.test(previewType.value) || /\.pdf(\?|$)/i.test(previewUrl.value))
const isImage = computed(() => /^(image\/)\w+/i.test(previewType.value) || /\.(png|jpg|jpeg|gif|webp|bmp)(\?|$)/i.test(previewUrl.value))
const isOffice = computed(() => {
  // 支持常见 Office 类型：doc/docx/xls/xlsx/ppt/pptx
  if (/msword|officedocument|vnd\.ms-|vnd\.openxmlformats/i.test(previewType.value)) return true
  if (document.value?.file_type) {
    const fileType = document.value.file_type.toLowerCase()
    if (['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'].includes(fileType)) return true
  }
  return /\.(doc|docx|xls|xlsx|ppt|pptx)(\?|$)/i.test(previewUrl.value || document.value?.file_name || '')
})
const isHtml = computed(() => {
  if (/text\/html/i.test(previewType.value)) return true
  const fileType = document.value?.file_type?.toLowerCase()
  if (fileType && ['html', 'htm'].includes(fileType)) return true
  return /\.(html|htm)(\?|$)/i.test(previewUrl.value || document.value?.file_name || '')
})

const isText = computed(() => {
  // 支持文本文件类型：txt, json, xml, csv, log, etc. (不包括 md/html，md 单独处理)
  if (isHtml.value) return false
  if (/text\/html/i.test(previewType.value)) return false
  if (/text\/|plain/i.test(previewType.value) && !/markdown/i.test(previewType.value)) return true
  const fileType = document.value?.file_type?.toLowerCase()
  if (fileType && ['txt', 'json', 'xml', 'csv', 'log', 'conf', 'ini', 'yaml', 'yml', 'sh', 'bat', 'py', 'js', 'ts', 'css'].includes(fileType)) {
    return true
  }
  return /\.(txt|json|xml|csv|log|conf|ini|yaml|yml|sh|bat|py|js|ts|css)(\?|$)/i.test(previewUrl.value || document.value?.file_name || '')
})

const isMarkdown = computed(() => {
  // 判断是否为 Markdown 文件
  if (/text\/markdown|markdown/i.test(previewType.value)) return true
  if (document.value?.file_type?.toLowerCase() === 'md' || document.value?.file_type?.toLowerCase() === 'markdown') return true
  return /\.(md|markdown|mkd)(\?|$)/i.test(previewUrl.value || document.value?.file_name || '')
})

const isStructuredType = computed(() => {
  // 判断是否为结构化文件类型（JSON/XML/CSV）
  const fileType = document.value?.file_type?.toLowerCase()
  const metadata = document.value?.metadata || {}
  if (metadata.structured_type) return true
  if (fileType && ['json', 'xml', 'csv'].includes(fileType)) return true
  const fileName = document.value?.file_name || ''
  return /\.(json|xml|csv)(\?|$)/i.test(fileName)
})
// Office Web Viewer 已移除，因为无法访问MinIO签名URL，改为使用PDF预览
const textContent = ref('')
const textLoading = ref(false)

// 配置 marked 和 highlight.js
marked.setOptions({
  highlight: (code: string, lang: string) => {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch (err) {
        console.warn('代码高亮失败:', err)
      }
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true, // GitHub Flavored Markdown
})

// Markdown 渲染结果
const renderedMarkdown = computed(() => {
  if (!isMarkdown.value || !textContent.value) {
    return ''
  }
  try {
    const html = marked.parse(textContent.value)
    // 为标题添加锚点 ID，用于目录导航
    return addHeadingIds(html)
  } catch (error) {
    console.error('Markdown 渲染失败:', error)
    return '<pre>' + escapeHtml(textContent.value) + '</pre>'
  }
})

// 为标题添加 ID 锚点
function addHeadingIds(html: string): string {
  return html.replace(/<h([1-6])>(.*?)<\/h\1>/gi, (match, level, content) => {
    const text = content.replace(/<[^>]+>/g, '').trim()
    const id = text.toLowerCase()
      .replace(/[^\w\s-]/g, '') // 移除特殊字符
      .replace(/\s+/g, '-') // 空格替换为连字符
      .replace(/-+/g, '-') // 多个连字符合并为一个
      .substring(0, 50) // 限制长度
    return `<h${level} id="${id}">${content}</h${level}>`
  })
}

// HTML 转义
function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

const chunkDialogVisible = ref(false)
const currentChunk = ref<any>(null)
const versionsCount = computed(() => versions.value?.length || 0)
const showChunk = async (row: any) => {
  try {
    const resp = await getChunkContentFromOS(documentId, row.id)
    const data = (resp as any)?.data
    currentChunk.value = data || null
  } catch (e) {
    currentChunk.value = null
  } finally {
    chunkDialogVisible.value = true
  }
}

const loadDetail = async () => {
  loading.value = true
  previewRetryCount = 0  // 重置预览重试计数器
  previewReady.value = false  // 重置预览就绪状态
  try {
    const res = await getDocumentDetail(documentId)
    document.value = res.data
    // 先加载文档信息，再加载预览URL（因为isText需要document.value）
    await loadPreviewUrl()
    // 并行加载其他数据
    await Promise.all([loadChunks(), loadImages(), loadVersions(), loadTOC()])
    // chunks加载完成后，构建预览（对于文本文件，会使用chunks内容）
    await buildPreview()
    // 如果是文本文件或 Markdown 文件且textContent还是空的，尝试再次加载
    if ((isText.value || isMarkdown.value) && !textContent.value && previewUrl.value) {
      await loadTextContent()
    }
  } catch (error) {
    ElMessage.error('加载详情失败')
    router.back()
  } finally {
    loading.value = false
  }
}

const loadChunks = async () => {
  chunksLoading.value = true
  try {
    // 简单加载前 200 条分块用于列表与预览构建
    const resp = await getDocumentChunks(documentId, { page: 1, size: 200 })
    const data = (resp as any)?.data
    // 后端分页统一 { list, total } 或直接数组，做兼容
    chunks.value = Array.isArray(data) ? data : (data?.list ?? [])
  } catch (error) {
    ElMessage.error('加载分块失败')
  } finally {
    chunksLoading.value = false
  }
}

const buildPreview = async () => {
  try {
    // 若 chunks 已加载，直接构建；否则先拉取少量块
    if (chunks.value.length === 0) {
      const resp = await getDocumentChunks(documentId, { page: 1, size: 50, include_content: true } as any)
      const data = (resp as any)?.data
      const list = Array.isArray(data) ? data : (data?.list ?? [])
      contentPreview.value = list.map((c: any) => c.content).filter(Boolean).join('\n\n')
    } else {
      contentPreview.value = chunks.value.map((c: any) => c.content).filter(Boolean).slice(0, 50).join('\n\n')
    }
    
    // 如果是文本文件，更新文本内容
    if (isText.value && contentPreview.value) {
      textContent.value = contentPreview.value
    }
  } catch (e) {
    contentPreview.value = ''
  }
}

const loadImages = async () => {
  try {
    const resp = await getDocumentImages(documentId)
    const data = (resp as any)?.data
    images.value = Array.isArray(data) ? data : (data?.list ?? [])
  } catch (error) {
    // 图片为空不报错
    images.value = []
  }
}

const loadVersions = async () => {
  try {
    const resp = await getDocumentVersions(documentId, { page: 1, size: 50 })
    const data = (resp as any)?.data
    versions.value = Array.isArray(data) ? data : (data?.list ?? [])
  } catch (error) {
    versions.value = []
  }
}

const loadPreviewUrl = async () => {
  previewLoading.value = true
  try {
    const resp = await getDocumentPreview(documentId)
    const data = (resp as any)?.data
    previewUrl.value = data?.preview_url || ''
    previewType.value = data?.content_type || ''
    htmlPreviewUrl.value = data?.html_preview_url || ''
    
    // 判断预览是否已准备好
    // Office文档：如果有PDF预览（content_type是application/pdf）或HTML预览，说明已准备好
    if (isOffice.value) {
      const hasPdfPreview = previewType.value === 'application/pdf'
      const hasHtmlPreview = !!htmlPreviewUrl.value
      
      if (hasPdfPreview || hasHtmlPreview) {
        // 预览已生成
        previewReady.value = true
        previewRetryCount = 0  // 重置计数器
      } else {
        // 预览未生成
        previewReady.value = false
        // 如果文档正在处理中，设置轮询
        const docStatus = document.value?.status
        if (docStatus === 'processing' || docStatus === 'parsing' || docStatus === 'vectorizing' || docStatus === 'chunking' || docStatus === 'indexing') {
          if (previewRetryCount < MAX_PREVIEW_RETRIES) {
            previewRetryCount++
            setTimeout(() => {
              loadPreviewUrl()  // 3秒后重试
            }, 3000)
            return
          } else {
            // 超时后停止轮询，显示下载提示
            previewReady.value = true
            previewRetryCount = 0  // 重置计数器
          }
        } else if (docStatus === 'completed') {
          // 文档已完成但预览未生成，可能是生成失败，显示下载提示
          previewReady.value = true
          previewRetryCount = 0  // 重置计数器
        } else {
          // 其他状态，也显示下载提示
          previewReady.value = true
        }
      }
    } else {
      // 非Office文档，有URL就算准备好
      previewReady.value = !!previewUrl.value
    }
    
    if (htmlPreviewUrl.value) {
      previewMode.value = 'html'
    } else {
      previewMode.value = 'pdf'
    }
    
    // 如果是文本文件且有预览URL，加载文本内容
    if (isText.value && previewUrl.value) {
      await loadTextContent()
    }
  } catch (e) {
    // 不显示错误，保持加载状态
    console.error('加载预览失败:', e)
    // 如果是Office文档且正在处理中，继续等待
    if (isOffice.value && (document.value?.status === 'processing' || document.value?.status === 'parsing' || document.value?.status === 'vectorizing' || document.value?.status === 'chunking' || document.value?.status === 'indexing')) {
      previewReady.value = false
      setTimeout(() => {
        loadPreviewUrl()  // 3秒后重试
      }, 3000)
    } else {
      // 文档已完成或非Office文档，停止等待
      previewReady.value = true
    }
  } finally {
    previewLoading.value = false
  }
}

const loadTextContent = async () => {
  if ((!isText.value && !isMarkdown.value) || !previewUrl.value) return
  
  textLoading.value = true
  try {
    // 如果已经有从chunks构建的内容预览，优先使用
    if (contentPreview.value) {
      textContent.value = contentPreview.value
      return
    }
    
    // 否则从预览URL加载原始文件内容
    const response = await fetch(previewUrl.value)
    if (response.ok) {
      textContent.value = await response.text()
    } else {
      // 如果fetch失败，尝试使用chunks构建预览
      if (chunks.value.length > 0) {
        textContent.value = chunks.value.map((c: any) => c.content).filter(Boolean).join('\n\n')
      }
    }
  } catch (error) {
    console.error('加载文本内容失败:', error)
    // 失败时使用chunks构建预览
    if (chunks.value.length > 0) {
      textContent.value = chunks.value.map((c: any) => c.content).filter(Boolean).join('\n\n')
    }
  } finally {
    textLoading.value = false
  }
}

const loadTOC = async () => {
  tocLoading.value = true
  try {
    const resp = await getDocumentTOC(documentId)
    const data = (resp as any)?.data
    tocItems.value = data?.toc || []
  } catch (error) {
    // 目录为空不报错
    tocItems.value = []
  } finally {
    tocLoading.value = false
  }
}

const tocTree = computed(() => {
  return tocItems.value
})

const handleTocClick = (data: any) => {
  // 简化功能：仅支持PDF文档的页码跳转
  if (data.page_number && isPdf.value && previewUrl.value) {
    // PDF预览URL添加页码参数
    const url = new URL(previewUrl.value)
    url.searchParams.set('page', String(data.page_number))
    // 刷新iframe
    const iframe = document.querySelector('.preview-frame') as HTMLIFrameElement
    if (iframe) {
      iframe.src = url.toString()
    }
    // 切换到预览标签页
    activeTab.value = 'preview'
  } else {
    // 非PDF文档或没有页码信息，仅显示提示
    ElMessage.info('该目录项暂无跳转功能，请使用文档预览查看内容')
  }
}

const handleBack = () => {
  router.back()
}

const handleEdit = () => {
  router.push(`/documents/${documentId}/edit`)
}

const regenerating = ref(false)

const handleRegenerateSummary = async () => {
  try {
    const hasSummary = document.value?.metadata?.auto_keywords || document.value?.metadata?.auto_summary
    const message = hasSummary ? '确定要重新生成标签和摘要吗？' : '确定要生成标签和摘要吗？'
    
    await ElMessageBox.confirm(message, '提示', {
      type: 'warning'
    })
    
    regenerating.value = true
    try {
      const res = await regenerateSummary(documentId)
      ElMessage.success(hasSummary ? '重新生成成功' : '生成成功')
      // 重新加载文档详情（只重新获取文档信息，不重新加载所有数据）
      loading.value = true
      try {
        const res = await getDocumentDetail(documentId)
        document.value = res.data
      } catch (error) {
        console.error('重新加载文档详情失败:', error)
      } finally {
        loading.value = false
      }
    } finally {
      regenerating.value = false
    }
  } catch (error: any) {
    regenerating.value = false
    if (error !== 'cancel') {
      // 处理403权限错误
      if (error?.response?.status === 403) {
        ElMessage.error(error?.response?.data?.detail || '权限不足，无法生成摘要')
      } else {
        ElMessage.error(error?.response?.data?.detail || error?.response?.data?.message || error?.message || '生成失败')
      }
    }
  }
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm('确定要删除该文档吗？', '提示')
    await deleteDocument(documentId)
    ElMessage.success('删除成功')
    router.push('/documents')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const viewImage = (image: any) => {
  // TODO: 查看图片
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    'completed': 'success',
    'processing': 'warning',
    'failed': 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    'completed': '已完成',
    'processing': '处理中',
    'failed': '失败'
  }
  return map[status] || status
}

// HTML 分块类型标签映射
const getChunkTypeLabel = (chunkType: string): string => {
  const map: Record<string, string> = {
    'text': '文本',
    'table': '表格',
    'image': '图片',
    'heading_section': '标题章节',
    'code_block': '代码块',
    'semantic_block': '语义块',
    'list': '列表',
    'paragraph': '段落'
  }
  return map[chunkType] || chunkType
}

// HTML 分块类型标签颜色映射
const getChunkTypeTagType = (chunkType: string): string => {
  const map: Record<string, string> = {
    'text': 'info',
    'table': 'warning',
    'image': 'success',
    'heading_section': 'primary',
    'code_block': 'danger',
    'semantic_block': '',
    'list': 'info',
    'paragraph': ''
  }
  return map[chunkType] || 'info'
}

// 获取分块元数据
const getChunkMeta = (chunk: any, key: string): any => {
  if (!chunk?.meta) return null
  try {
    const meta = typeof chunk.meta === 'string' ? JSON.parse(chunk.meta) : chunk.meta
    return meta[key]
  } catch {
    return null
  }
}

// 判断是否为 HTML 特有分块
const isHtmlChunk = (chunk: any): boolean => {
  const htmlChunkTypes = ['heading_section', 'code_block', 'semantic_block', 'list', 'paragraph']
  return htmlChunkTypes.includes(chunk?.chunk_type)
}

// 代码高亮
const highlightCode = (code: string, language?: string): string => {
  if (!code) return ''
  try {
    if (language && hljs.getLanguage(language)) {
      return hljs.highlight(code, { language }).value
    }
    return hljs.highlightAuto(code).value
  } catch {
    return escapeHtml(code)
  }
}

// 版本类型：用于颜色标注
const getVersionType = (v: any): string => {
  const desc = String(v?.description || '')
  if (/回退|恢复|revert/i.test(desc)) return 'revert'
  if (/编辑|修改|变更|edit|update/i.test(desc)) return 'edit'
  return 'init'
}

// 安全扫描状态类型
const getSecurityScanStatusType = (status: string) => {
  const map: Record<string, string> = {
    'safe': 'success',
    'infected': 'danger',
    'error': 'warning',
    'skipped': 'info',
    'scanning': 'warning',
    'pending': ''
  }
  return map[status] || 'info'
}

// 安全扫描状态文本
const getSecurityScanStatusText = (status: string) => {
  const map: Record<string, string> = {
    'safe': '安全',
    'infected': '感染',
    'error': '错误',
    'skipped': '跳过',
    'scanning': '扫描中',
    'pending': '待扫描'
  }
  return map[status] || status || '未知'
}

// 安全扫描方法文本
const getSecurityScanMethodText = (method: string) => {
  const map: Record<string, string> = {
    'clamav': 'ClamAV 扫描',
    'pattern_only': '模式匹配',
    'none': '未扫描'
  }
  return map[method] || method || '未知'
}

// ClamAV 扫描状态类型
const getVirusScanStatusType = (status: string) => {
  const map: Record<string, string> = {
    'safe': 'success',
    'infected': 'danger',
    'error': 'warning',
    'warning': 'warning',
    'skipped': 'info'
  }
  return map[status] || 'info'
}

// ClamAV 扫描状态文本
const getVirusScanStatusText = (status: string) => {
  const map: Record<string, string> = {
    'safe': '安全',
    'infected': '感染',
    'error': '错误',
    'warning': '警告',
    'skipped': '跳过'
  }
  return map[status] || status || '未知'
}

onMounted(() => {
  loadDetail()
})
</script>

<style lang="scss" scoped>
.document-detail-page {
  /* 提升标签页可读性 */
  :deep(.el-tabs__item) {
    color: rgba(255, 255, 255, 0.75);
    font-weight: 500;
  }
  :deep(.el-tabs__item.is-active) {
    color: #ffffff;
  }
  :deep(.el-tabs__item:hover) {
    color: #ffffff;
  }
  :deep(.el-tabs__active-bar) {
    background-color: #409eff; /* 高亮下划线颜色 */
  }

  .content-preview {
    padding: 20px;
    background: #f9f9f9;
    border-radius: 4px;
    min-height: 300px;
  }

  .markdown-preview-container {
    background: #ffffff;
    border-radius: 8px;
    border: 1px solid rgba(15, 23, 42, 0.1);
    padding: 24px;
    max-width: 100%;
    overflow-x: auto;
    
    .markdown-content {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB',
        'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
      line-height: 1.8;
      color: #24292f;
      
      // 标题样式
      :deep(h1),
      :deep(h2),
      :deep(h3),
      :deep(h4),
      :deep(h5),
      :deep(h6) {
        margin-top: 24px;
        margin-bottom: 16px;
        font-weight: 600;
        line-height: 1.25;
        scroll-margin-top: 80px; // 用于锚点跳转时留出导航栏空间
        
        &:first-child {
          margin-top: 0;
        }
      }
      
      :deep(h1) {
        font-size: 2em;
        border-bottom: 1px solid #d0d7de;
        padding-bottom: 0.3em;
      }
      
      :deep(h2) {
        font-size: 1.5em;
        border-bottom: 1px solid #d0d7de;
        padding-bottom: 0.3em;
      }
      
      :deep(h3) {
        font-size: 1.25em;
      }
      
      :deep(h4) {
        font-size: 1em;
      }
      
      :deep(h5) {
        font-size: 0.875em;
      }
      
      :deep(h6) {
        font-size: 0.85em;
        color: #57606a;
      }
      
      // 目录高亮效果
      :deep(h1.toc-highlight),
      :deep(h2.toc-highlight),
      :deep(h3.toc-highlight),
      :deep(h4.toc-highlight),
      :deep(h5.toc-highlight),
      :deep(h6.toc-highlight) {
        background-color: #fff8c5;
        transition: background-color 2s ease-out;
      }
      
      // 段落
      :deep(p) {
        margin-bottom: 16px;
      }
      
      // 代码块
      :deep(pre) {
        background-color: #f6f8fa;
        border: 1px solid #d0d7de;
        border-radius: 6px;
        padding: 16px;
        overflow-x: auto;
        margin-bottom: 16px;
        
        code {
          background-color: transparent;
          padding: 0;
          font-size: 85%;
          color: #24292f;
        }
      }
      
      // 行内代码
      :deep(code:not(pre code)) {
        background-color: rgba(175, 184, 193, 0.2);
        padding: 0.2em 0.4em;
        border-radius: 3px;
        font-size: 85%;
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
      }
      
      // 链接
      :deep(a) {
        color: #0969da;
        text-decoration: none;
        
        &:hover {
          text-decoration: underline;
        }
      }
      
      // 列表
      :deep(ul),
      :deep(ol) {
        margin-bottom: 16px;
        padding-left: 2em;
      }
      
      :deep(li) {
        margin-bottom: 0.25em;
      }
      
      // 表格
      :deep(table) {
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 16px;
        
        th,
        td {
          border: 1px solid #d0d7de;
          padding: 6px 13px;
        }
        
        th {
          background-color: #f6f8fa;
          font-weight: 600;
        }
        
        tr:nth-child(2n) {
          background-color: #f6f8fa;
        }
      }
      
      // 引用块
      :deep(blockquote) {
        padding: 0 1em;
        color: #57606a;
        border-left: 0.25em solid #d0d7de;
        margin-bottom: 16px;
      }
      
      // 水平线
      :deep(hr) {
        height: 0.25em;
        padding: 0;
        margin: 24px 0;
        background-color: #d0d7de;
        border: 0;
      }
      
      // 图片
      :deep(img) {
        max-width: 100%;
        height: auto;
        border-radius: 4px;
      }
    }
  }

  .text-preview-container {
    background: #ffffff;
    border-radius: 8px;
    border: 1px solid rgba(15, 23, 42, 0.1);
    overflow: hidden;
    min-height: 400px;
    max-height: 72vh;
  }

  .text-preview-content {
    margin: 0;
    padding: 24px;
    background: #ffffff;
    color: #1f2937;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 14px;
    line-height: 1.8;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-x: auto;
    overflow-y: auto;
    max-height: 72vh;
    border: none;
    box-shadow: none;
  }

  /* 版本历史时间轴可读性增强 */
  :deep(.el-timeline-item__timestamp) {
    color: #cbd5e1;
    font-size: 13px;
  }
  .version-line {
    display: flex;
    align-items: center;
    gap: 14px;
    .version-desc {
      color: #e2e8f0;
      font-size: 16px;
      font-weight: 500;
      letter-spacing: .2px;
    }
    :deep(.ver-tag) {
      font-size: 14px;
      padding: 6px 12px;
    }
  }

  /* ===== 科技感增强样式（时间轴） ===== */
  :deep(.el-timeline) {
    padding-left: 8px;
  }
  /* 竖线：渐变+微弱发光 */
  :deep(.el-timeline-item__tail) {
    border-left: none !important;
    width: 3px;
    background: linear-gradient(180deg, rgba(64,158,255,0.85), rgba(56,189,248,0.65));
    box-shadow: 0 0 8px rgba(64,158,255,0.45);
  }
  /* 节点：霓虹点 */
  :deep(.el-timeline-item__node) {
    background: radial-gradient(circle at 30% 30%, #4a90e2, #2563eb);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2), 0 0 12px rgba(56,189,248,0.5);
    border: none;
  }
  /* 版本号标签：渐变胶囊 + 轻微发光 */
  .version-line :deep(.ver-tag) {
    background: linear-gradient(135deg, #3b82f6, #06b6d4) !important;
    color: #eaf6ff !important;
    border: none !important;
    box-shadow: 0 2px 10px rgba(59,130,246,0.35) !important;
    border-radius: 999px !important;
  }
  /* 颜色区分：回退=红橙、编辑=蓝青、初始=紫蓝 */
  .version-line.revert :deep(.ver-tag) {
    background: linear-gradient(135deg, #ef4444, #f59e0b) !important;
    box-shadow: 0 2px 10px rgba(239,68,68,0.35) !important;
  }
  .version-line.edit :deep(.ver-tag) {
    background: linear-gradient(135deg, #3b82f6, #06b6d4) !important;
  }
  .version-line.init :deep(.ver-tag) {
    background: linear-gradient(135deg, #8b5cf6, #3b82f6) !important;
  }
  /* 文本悬浮高亮 */
  .version-line {
    transition: transform .15s ease, filter .15s ease;
  }
  .version-line:hover {
    transform: translateX(2px);
    filter: brightness(1.05);
  }

  .preview-loading-container {
    min-height: 400px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .preview-frame {
    width: 100%;
    height: 72vh;
    background: #fff;
  }

  .preview-switch {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
    color: rgba(255, 255, 255, 0.85);
  }

  .image-inline {
    max-width: 100%;
    height: auto;
    background: #fff;
  }

  .image-gallery {
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

      .image-info {
        padding: 8px;
        font-size: 12px;
        color: #666;
      }
    }
  }

  /* 降低表格 hover 亮度，适配深色背景 */
  :deep(.chunk-table .el-table__row:hover>td) {
    background-color: rgba(255, 255, 255, 0.06) !important;
  }

  .chunk-content {
    background: #ffffff;
    color: #1f2933;
    font-size: 16px;
    line-height: 1.8;
    padding: 20px 24px;
    border-radius: 10px;
    border: 1px solid rgba(15, 23, 42, 0.08);
    box-shadow: 0 16px 40px rgba(15, 23, 42, 0.12);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 60vh;
    overflow: auto;
  }

  :deep(.chunk-content strong) {
    color: #0f172a;
  }

  :deep(.chunk-content em) {
    color: #2563eb;
  }

  :deep(.chunk-content mark) {
    background: rgba(250, 204, 21, 0.35);
    color: #92400e;
    padding: 0 2px;
    border-radius: 2px;
  }

  :deep(.chunk-content table) {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    background: #fff;
  }

  :deep(.chunk-content table th),
  :deep(.chunk-content table td) {
    border: 1px solid rgba(148, 163, 184, 0.35);
    padding: 12px 14px;
    text-align: left;
    color: #1f2933;
  }

  :deep(.chunk-content table th) {
    background: rgba(37, 99, 235, 0.12);
    color: #0f172a;
    font-weight: 600;
  }

  /* AI标签与摘要样式优化 */
  :deep(.el-card) {
    background: rgba(6, 12, 24, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.9);
    
    .el-card__header {
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      color: rgba(255, 255, 255, 0.95);
      font-size: 16px;
      font-weight: 600;
    }
    
    .el-card__body {
      color: rgba(255, 255, 255, 0.85);
    }
  }
  
  /* 卡片头部样式 */
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: rgba(255, 255, 255, 0.95);
    
    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
      
      .back-button {
        background: rgba(255, 255, 255, 0.08);
        border-color: rgba(255, 255, 255, 0.2);
        color: rgba(255, 255, 255, 0.9);
        width: 36px;
        height: 36px;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
        
        &:hover {
          background: rgba(64, 158, 255, 0.2);
          border-color: #409eff;
          color: #409eff;
          transform: translateX(-2px);
        }
        
        .el-icon {
          font-size: 18px;
        }
      }
      
      span {
        font-size: 18px;
        font-weight: 600;
      }
    }
  }
  
  .ai-keywords-section {
    margin-bottom: 16px;
    
    .section-label {
      font-size: 15px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.95);
      margin-right: 8px;
      display: inline-block;
    }
    
    .keyword-tag {
      margin-left: 8px;
      margin-bottom: 6px;
      font-size: 14px;
      font-weight: 500;
      padding: 6px 12px;
      border-radius: 4px;
    }
  }
  
  .ai-summary-section {
    margin-top: 16px;
    
    .section-label {
      font-size: 15px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.95);
      display: block;
      margin-bottom: 10px;
    }
    
    .summary-text {
      margin-top: 8px;
      color: rgba(255, 255, 255, 0.9);
      font-size: 15px;
      line-height: 1.8;
      font-weight: 400;
      letter-spacing: 0.3px;
    }
  }
  
  .ai-empty-text {
    color: rgba(255, 255, 255, 0.65);
    font-size: 14px;
    margin-bottom: 12px;
  }

  .toc-container {
    padding: 20px;
    min-height: 200px;
    background: rgba(6, 12, 24, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    box-shadow: 0 8px 30px rgba(2, 6, 23, 0.45);
    backdrop-filter: blur(8px);
  }

  :deep(.el-tree) {
    background: transparent;
    color: rgba(255, 255, 255, 0.85);
  }

  :deep(.el-tree-node) {
    margin-bottom: 4px;
  }

  :deep(.el-tree-node__content) {
    height: auto;
    padding: 6px 10px;
    border-radius: 8px;
    transition: background 0.2s ease;

    &:hover {
      background: rgba(64, 158, 255, 0.15);
    }
  }

  .toc-node {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    padding: 4px 0;
    cursor: pointer;

    .toc-title {
      flex: 1;
      color: #e8eef7;
      font-size: 14px;
    }

    .toc-page {
      color: #9aa5b1;
      font-size: 12px;
      margin-left: 12px;
    }

    &:hover {
      .toc-title {
        color: #409eff;
      }
    }
  }

  :deep(.el-tree-node__label) {
    width: 100%;
  }

  :deep(.chunk-content table tr:nth-child(even)) {
    background: rgba(148, 163, 184, 0.08);
  }

  .chunk-dialog :deep(.el-dialog__body) {
    background: #f8fafc;
  }

  .chunk-dialog :deep(.el-dialog__header) {
    background: linear-gradient(135deg, #1d4ed8, #9333ea);
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    padding: 16px 24px;
  }

  .chunk-dialog :deep(.el-dialog__title) {
    color: #ffffff;
    font-weight: 600;
    letter-spacing: 0.02em;
  }

  .chunk-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
    color: rgba(255, 255, 255, 0.85);
  }

  .chunk-dialog :deep(.el-descriptions__cell) {
    color: #1f2933;
    font-size: 14px;
  }

  .chunk-dialog :deep(.el-descriptions__label) {
    color: #475569;
    font-weight: 600;
  }

  .chunk-image {
    max-width: 100%;
    max-height: 60vh;
    display: block;
    margin: 0 auto 16px;
    border-radius: 6px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  }

  .chunk-code-content {
    padding: 16px;
    background: #f5f5f5;
    border-radius: 4px;
    overflow-x: auto;
    margin-top: 16px;
    
    :deep(pre) {
      margin: 0;
      padding: 0;
      background: transparent;
    }
    
    :deep(code) {
      font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
      font-size: 14px;
      line-height: 1.6;
      display: block;
      white-space: pre;
    }
  }

  .chunk-meta {
    margin-top: 8px;
    margin-bottom: 16px;
  }
}
</style>
