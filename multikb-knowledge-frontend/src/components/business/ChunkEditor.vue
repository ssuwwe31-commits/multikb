<template>
  <div class="chunk-editor-page">
    <div class="chunk-editor">
    <!-- 左侧：块列表 -->
    <div class="chunk-list">
      <el-card class="chunk-list-card">
        <template #header>
          <div class="list-header">
            <span>文档块列表</span>
            <el-input
              v-model="searchKeyword"
              placeholder="搜索块..."
              clearable
              size="small"
              style="width: 150px"
            />
          </div>
        </template>
        
        <el-table
          :data="chunksTable"
          height="calc(100vh - 220px)"
          @row-click="onRowClick"
          highlight-current-row
          class="chunk-table"
        >
          <el-table-column prop="index" label="序号" width="70" align="center" />
          <el-table-column prop="chunk_type" label="类型" width="100" align="center">
            <template #default="scope">
              <span :class="['type-pill', scope.row.chunk_type]">{{ scope.row.chunk_type }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="char_count" label="字符数" width="90" align="center" />
        </el-table>
      </el-card>
    </div>

    <!-- 中间：编辑器 -->
    <div class="editor-main">
      <el-card v-if="currentChunk">
        <template #header>
          <div class="editor-header">
            <span>编辑块 #{{ currentChunk.chunk_index }}</span>
            <div>
              <el-button size="small" @click="handleCancel">取消</el-button>
              <el-button type="primary" size="small" @click="handleSave" :loading="saving">
                保存修改
              </el-button>
            </div>
          </div>
        </template>

        <div class="editor-content">
          <!-- 表格块：以表格方式编辑 -->
          <template v-if="isTableChunk">
            <el-tabs v-model="tableTab" type="border-card">
              <el-tab-pane label="原始预览" name="preview">
                <!-- ✅ 优先使用 cells 渲染（保存后能立即看到最新数据），HTML 作为兜底 -->
                <div v-if="tableData && tableData.length > 0 && !(tableData.length === 1 && tableData[0]?.length <= 1)" class="table-preview-from-cells">
                  <div class="table-hint">表格支持拖动横向滚动查看全部列</div>
                  <div class="table-scroll-wrapper" ref="tableScrollWrapper">
                    <div class="table-container">
                      <table class="preview-table" :style="{ minWidth: tableMinWidth }">
                      <thead v-if="tableData.length > 0">
                        <tr>
                          <th v-for="(cell, cellIdx) in tableData[0]" :key="cellIdx" 
                              class="table-header"
                              style="background: linear-gradient(to bottom, #4a90e2, #357abd); color: #ffffff; font-weight: 700; font-size: 16px; padding: 16px 20px; text-align: left; border-bottom: 3px solid #2c5f8a; border-right: 2px solid rgba(255, 255, 255, 0.2); white-space: nowrap;">
                            {{ cell }}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, rowIdx) in tableData.slice(1)" :key="rowIdx" 
                            :class="{ 'table-row-even': rowIdx % 2 === 0 }"
                            :style="{ backgroundColor: rowIdx % 2 === 0 ? '#f9fafb' : 'white' }">
                          <td v-for="(cell, cellIdx) in row" :key="cellIdx" 
                              class="table-cell"
                              :style="{
                                padding: '16px 20px',
                                borderBottom: '2px solid #d0d0d0',
                                borderRight: cellIdx < row.length - 1 ? '2px solid #d0d0d0' : 'none',
                                color: cellIdx === 0 ? '#34495e' : '#2c3e50',
                                fontWeight: cellIdx === 0 ? '600' : 'normal',
                                fontSize: '15px',
                                lineHeight: '1.8',
                                minHeight: '48px',
                                background: cellIdx === 0 ? (rowIdx % 2 === 0 ? 'linear-gradient(to right, #f0f2f5, #f9fafb)' : 'linear-gradient(to right, #f8f9fa, #ffffff)') : 'transparent'
                              }">
                            {{ cell }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                    </div>
                  </div>
                  <el-alert
                    type="warning"
                    :closable="false"
                    style="margin-top: 10px;"
                    description="✅ 当前使用结构化 cells 渲染。若需核对原始解析，可切换为 HTML 预览（当存在）。"
                  />
                </div>
                <!-- ✅ 如果 cells 不可用，再尝试 HTML 预览 -->
                <div v-else-if="debugTableHtml" class="table-html-wrapper">
                  <div class="table-html" v-html="debugTableHtml"></div>
                  <el-alert
                    type="info"
                    :closable="false"
                    style="margin-top: 10px;"
                    description="当前使用 HTML 兜底渲染。保存后的最新 cells 建议优先使用结构化渲染。"
                  />
                </div>
                <!-- ✅ 两者都没有时提示 -->
                <el-empty v-else description="无法显示表格预览：缺少表格结构数据（cells 或 HTML）。" />
              </el-tab-pane>
              <el-tab-pane label="网格编辑" name="grid">
                <div class="table-editor-tools">
                  <el-button size="small" @click="addRow">加一行</el-button>
                  <el-button size="small" @click="addCol">加一列</el-button>
                </div>
                <el-table :data="tableObjects" border class="table-editor">
                  <el-table-column v-for="(col, cIdx) in tableColumns" :key="cIdx" :label="col" :prop="col" align="center">
                    <template #default="scope">
                      <el-input v-model="tableData[scope.$index][cIdx]" size="small" />
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>
              <el-tab-pane label="结构化表格" name="sheet">
                <div class="luckysheet-wrapper">
                  <div
                    class="luckysheet-container"
                    :id="luckysheetContainerId"
                    ref="luckysheetContainer"
                  ></div>
                </div>
              </el-tab-pane>
            </el-tabs>
          </template>
          <!-- 文本块：富文本编辑器 -->
          <template v-else>
            <QuillEditor
              ref="editorRef"
              v-model:content="editorContent"
              content-type="html"
              theme="snow"
              :options="editorOptions"
              @ready="onEditorReady"
              class="editor"
            />
          </template>
        </div>

        <!-- 元数据信息 -->
        <el-divider>块元数据</el-divider>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="块ID">{{ currentChunk.id ?? currentChunk.chunk_id }}</el-descriptions-item>
          <el-descriptions-item label="块类型">{{ currentChunk.chunk_type }}</el-descriptions-item>
          <el-descriptions-item label="字符数">{{ currentChunk.char_count }}</el-descriptions-item>
          <el-descriptions-item label="版本号">{{ currentChunk.version || 1 }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(currentChunk.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="修改时间">{{ formatDateTime(currentChunk.last_modified_at) }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-empty v-else description="请从左侧选择块进行编辑" />
    </div>

    <!-- 右侧：版本历史 -->
    <div class="version-history">
      <el-card v-if="currentChunk">
        <template #header>
          <span>版本历史</span>
        </template>

        <el-scrollbar height="calc(100vh - 200px)">
          <el-timeline>
            <el-timeline-item
              v-for="version in chunkVersions"
              :key="version.id"
              :timestamp="formatDateTime(version.created_at)"
              :icon="(version.version_number ?? version.version) === currentChunk.version ? 'CaretRight' : ''"
            >
              <el-card>
                <div class="version-header">
                  <el-tag size="small" type="primary" effect="dark">V{{ version.version_number ?? version.version ?? '?' }}</el-tag>
                  <span class="version-comment" :title="version.version_comment || '无说明'">{{ version.version_comment || '无说明' }}</span>
                </div>
                <div class="version-actions">
                  <el-button size="small" @click="handleCompareVersion(version)">对比</el-button>
                  <el-button 
                    size="small" 
                    type="primary" 
                    :disabled="(version.version_number ?? version.version) === (currentChunk?.version ?? 0)"
                    @click="handleRestoreVersion(version)"
                  >
                    恢复
                  </el-button>
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-scrollbar>
      </el-card>

      <el-empty v-else description="选择块查看版本历史" />
    </div>
    </div>

    <!-- 版本对比对话框 -->
    <el-dialog v-model="compareDialogVisible" title="版本对比" width="90%">
      <div class="compare-legend">
        <span class="legend-ins">绿色 = 新增/修改</span>
        <span class="legend-del">红色删除线 = 被删除</span>
      </div>
      <div class="compare-content">
        <div class="compare-left">
          <div class="compare-header">
            <h4>当前版本</h4>
            <el-tag v-if="compareVersions.new?.version" size="small" type="primary">
              v{{ compareVersions.new.version }}
            </el-tag>
            <span v-if="compareVersions.new?.last_modified_at" class="version-time">
              {{ formatDateTime(compareVersions.new.last_modified_at) }}
            </span>
          </div>
          <pre v-html="compareHtmlNew || EMPTY_PLACEHOLDER" />
        </div>
        <div class="compare-right">
          <div class="compare-header">
            <h4>选择版本</h4>
            <el-tag v-if="compareVersions.old?.version_number" size="small" type="info">
              v{{ compareVersions.old.version_number }}
            </el-tag>
            <span v-if="compareVersions.old?.created_at" class="version-time">
              {{ formatDateTime(compareVersions.old.created_at) }}
            </span>
          </div>
          <pre v-html="compareHtmlOld || EMPTY_PLACEHOLDER" />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CaretRight } from '@element-plus/icons-vue'
import { 
  getDocumentChunks,
  getChunkDetail,
  updateChunk,
  getChunkVersions,
  getChunkVersion,
  restoreChunkVersion,
  revertToPreviousVersion
} from '@/api/modules/documents'
import { formatDateTime } from '@/utils/format'
import { QuillEditor } from '@vueup/vue-quill'
import '@vueup/vue-quill/dist/vue-quill.snow.css'
import { getTableByUid, getTableGroupByUid } from '@/api/modules/tables'
import 'luckysheet/dist/css/luckysheet.css'
import 'luckysheet/dist/plugins/css/pluginsCss.css'
import 'luckysheet/dist/plugins/plugins.css'

const props = defineProps<{
  documentId: number
}>()

const emit = defineEmits(['close'])

const chunks = ref<any[]>([])
const currentChunk = ref<any>(null)
const chunkVersions = ref<any[]>([])
const searchKeyword = ref('')
const saving = ref(false)
const compareDialogVisible = ref(false)
const compareVersions = ref<any>({})
const compareHtmlOld = ref('')
const compareHtmlNew = ref('')
const EMPTY_PLACEHOLDER = '<span style="color: #999;">(空内容)</span>'
const editorRef = ref<any>()
const editorContent = ref('')
const isTableChunk = computed(() => (currentChunk.value?.chunk_type === 'table'))
const tableData = ref<string[][]>([])
const tableHtml = ref<string>('')
const tableTab = ref<'preview' | 'grid' | 'sheet'>('preview')
// 统一内容清洗：去除不可见控制字符、零宽字符、非法代理对
const sanitizeContent = (raw: string): string => {
  if (!raw) return ''
  let s = String(raw)
  // 去除 C0 控制字符与 DEL（保留 \n、\t）
  s = s.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '')
  // 去除零宽字符（ZWSP/ZWNJ/ZWJ/ZWNBSP 等）
  s = s.replace(/[\u200B-\u200F\u202A-\u202E\u2060-\u206F\uFEFF]/g, '')
  // 规范化空白
  s = s.replace(/\u00A0/g, ' ')
  return s
}

// 将富文本 HTML 转为纯文本，避免后端过滤 <> 等特殊字符
const htmlToPlainText = (html: string): string => {
  if (!html) return ''
  const div = document.createElement('div')
  div.innerHTML = html
  const text = div.textContent || div.innerText || ''
  return text
}

// ✅ 调试用 computed，确保响应式更新
const debugTableHtml = computed(() => tableHtml.value)
const tableColumns = computed(() => {
  const cols = tableData.value[0]?.length || 0
  return Array.from({ length: cols }, (_, i) => `C${i + 1}`)
})
const tableObjects = computed(() => {
  // 将二维数组转换为 element-plus table 需要的对象数组
  return tableData.value.map(row => {
    const obj: Record<string, string> = {}
    row.forEach((val, idx) => { obj[`C${idx + 1}`] = val })
    return obj
  })
})
const tableScrollWrapper = ref<HTMLDivElement | null>(null)
const tableMinWidth = computed(() => {
  const cols = tableData.value[0]?.length || 1
  const base = 220 // 每列最小宽度
  return `${Math.max(cols * base, tableScrollWrapper.value?.clientWidth || 0)}px`
})
const luckysheetContainer = ref<HTMLDivElement | null>(null)
let luckysheetModule: any = null
const luckysheetContainerId = `luckysheet-preview-${Math.random().toString(36).slice(2, 8)}`

const editorOptions = {
  modules: {
    toolbar: [
      [{ 'header': [1, 2, 3, false] }],
      ['bold', 'italic', 'underline', 'strike'],
      [{ 'list': 'ordered'}, { 'list': 'bullet' }],
      [{ 'color': [] }, { 'background': [] }],
      ['link'],
      ['code-block']
    ]
  }
}

const chunksTable = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  const list = chunks.value || []
  const filtered = keyword
    ? list.filter((chunk: any) => {
        const idx = String(chunk?.chunk_index ?? '').toLowerCase()
        const type = String(chunk?.chunk_type ?? '').toLowerCase()
        const content = String(chunk?.content ?? '').toLowerCase()
        return idx.includes(keyword) || type.includes(keyword) || content.includes(keyword)
      })
    : list

  return filtered.map((chunk: any) => ({
    ...chunk,
    index: chunk.chunk_index,
  }))
})

const loadChunks = async () => {
  try {
    const res = await getDocumentChunks(props.documentId, { page: 1, size: 1000, include_content: true } as any)
    const data = (res as any)?.data
    const rawChunks = Array.isArray(data) ? data : (data?.list || data?.chunks || [])
    chunks.value = rawChunks.filter((chunk: any) => {
      const type = (chunk?.chunk_type || '').toLowerCase()
      return type !== 'image'
    })
    
    // ✅ 调试：检查表格块的数据
    const tableChunks = chunks.value.filter((c: any) => c.chunk_type === 'table')
  } catch (error) {
    ElMessage.error('加载块列表失败')
    
  }
}

// ✅ 辅助函数：初始化表格数据（优先通过 table_id 懒加载整表 JSON）
const initializeTableData = async (chunk: any) => {
  if (!chunk || chunk.chunk_type !== 'table') {
    tableData.value = []
    tableHtml.value = ''
    return
  }
  
  try {
    if (tableScrollWrapper.value) {
      tableScrollWrapper.value.scrollLeft = 0
    }
    // 解析 meta 字段
    const metaRaw = chunk.meta
    
    
    const meta = typeof metaRaw === 'string' ? JSON.parse(metaRaw || '{}') : (metaRaw || {})

    // ✅ 新策略：优先整表聚合（存在 table_group_uid 时）
    const tableGroupUid: string | undefined = meta?.table_group_uid
    if (tableGroupUid) {
      try {
        const res = await getTableGroupByUid(tableGroupUid)
        const t = (res as any)?.data || {}
        const cells = Array.isArray(t.cells) ? t.cells : []
        const headers = (t.headers && typeof t.headers === 'object') ? t.headers : {}
        if (cells.length > 0) {
          tableData.value = cells.map((r: any[]) => Array.isArray(r) ? r.map(v => String(v ?? '')) : [String(r ?? '')])
        } else if (headers?.content && Array.isArray(headers.content) && headers.content.length > 0) {
          tableData.value = headers.content.map((r: any[]) => Array.isArray(r) ? r.map(v => String(v ?? '')) : [String(r ?? '')])
        } else {
          tableData.value = []
        }
        tableHtml.value = ''
        
        return
      } catch (e: any) {
        
      }
    }

    // 其次：单片懒加载
    const tableUid: string | undefined = meta?.table_id
    if (tableUid) {
      try {
        const res = await getTableByUid(tableUid)
        const t = (res as any)?.data || {}
        // cells_json/headers_json/source_html 等字段由后端直接返回 JSON 字符串或对象
        const cells = typeof t.cells_json === 'string' ? JSON.parse(t.cells_json || '[]') : (t.cells_json || [])
        const headers = typeof t.headers_json === 'string' ? JSON.parse(t.headers_json || '{}') : (t.headers_json || {})
        const htmlFromSnapshot = t.source_html || ''

        // 优先 cells 渲染
        if (Array.isArray(cells) && cells.length > 0) {
          tableData.value = cells.map((r: any[]) => Array.isArray(r) ? r.map(v => String(v ?? '')) : [String(r ?? '')])
        } else if (headers?.content && Array.isArray(headers.content) && headers.content.length > 0) {
          // 若无 cells，仅表头也做兜底
          tableData.value = headers.content.map((r: any[]) => Array.isArray(r) ? r.map(v => String(v ?? '')) : [String(r ?? '')])
        } else {
          tableData.value = []
        }
        tableHtml.value = htmlFromSnapshot || ''
        
        return
      } catch (e: any) {
        
      }
    }
    
    // 兼容旧数据：使用 meta.table_data（如仍存在）
    const cells = meta?.table_data?.cells
    
    
    // ✅ 优先使用 cells 数组（最准确的结构化数据）
    if (Array.isArray(cells) && cells.length > 0) {
      const firstRow = cells[0]
      // 验证 cells 是否有效（至少2列或2行）
      const isValidCells = Array.isArray(firstRow) && (
        (firstRow.length >= 2) ||  // 至少2列
        (cells.length >= 2)         // 或至少2行
      )
      
      if (isValidCells) {
        // ✅ 直接使用 cells 数组（主要数据源）
        tableData.value = cells.map((r: any[]) => {
          if (Array.isArray(r)) {
            return r.map(v => String(v ?? ''))
          }
          return [String(r ?? '')]
        })
        
        
        // HTML 仅作为备份存储（不用于主要渲染）
        const htmlFromMeta = meta?.table_data?.html || ''
        tableHtml.value = htmlFromMeta
        
        
        // ✅ 使用 cells 后直接返回，不再处理 HTML
        return
      }
    }
    
    // ⚠️ 仅当 cells 不可用时，才使用 HTML（兜底方案）
    const htmlFromMeta = meta?.table_data?.html || ''
    tableHtml.value = htmlFromMeta
    
    
    // ✅ 如果 HTML 存在，尝试从中提取表格结构
    if (tableHtml.value) {
      // 如果 tableData 为空或无效，从 HTML 提取
      if (!tableData.value || tableData.value.length === 0 || 
          (tableData.value.length === 1 && tableData.value[0]?.length <= 1)) {
        try {
          // 创建一个临时 DOM 元素来解析 HTML
          const parser = new DOMParser()
          const doc = parser.parseFromString(tableHtml.value, 'text/html')
          const table = doc.querySelector('table')
          if (table) {
            const rows: string[][] = []
            const trs = table.querySelectorAll('tr')
            trs.forEach(tr => {
              const row: string[] = []
              const cells = tr.querySelectorAll('td, th')
              cells.forEach(cell => {
                row.push(cell.textContent?.trim() || '')
              })
              if (row.length > 0) {
                rows.push(row)
              }
            })
            if (rows.length > 0) {
              tableData.value = rows
            }
          }
        } catch (e) {
          
        }
      }
      // ⚠️ 重要：如果 tableHtml 存在，直接使用它渲染，不再继续执行兜底逻辑
      // 但保留 tableData 用于网格编辑
      return
    }
    
    // ⚠️ 最后兜底：从 content 解析（可能包含 OCR 错误，不推荐）
    const content = chunk.content || ''
    
    
    if (content) {
      // 尝试按制表符分隔（这是我们从结构化数据生成的格式）
      if (content.includes('\t')) {
        const lines = content.split('\n').filter(l => l.trim())
        if (lines.length > 0) {
          tableData.value = lines.map(l => l.split('\t').map(c => c.trim()))
          
          return
        }
      }
      // 尝试按管道符分隔（Markdown 表格格式）
      if (content.includes('|')) {
        const lines = content.split('\n').filter(l => l.trim() && !l.match(/^[\s|:\-]+$/))
        if (lines.length > 0) {
          tableData.value = lines.map(l => {
            const cols = l.split('|').map(c => c.trim()).filter(c => c && !c.match(/^[\-:]+$/))
            return cols.length > 0 ? cols : ['']
          }).filter(row => row.length > 0 && row.some(cell => cell))
          if (tableData.value.length > 0) {
            return
          }
        }
      }
      // 尝试按多个空格分隔（可能是 OCR 文本）
      const lines = content.split('\n').filter(l => l.trim())
      if (lines.length > 0) {
        const parsed = lines.map(l => l.split(/\s{2,}/).filter(c => c.trim()))
        if (parsed.length > 0 && parsed.some(row => row.length > 1)) {
          tableData.value = parsed
          return
        }
      }
      // 如果都不行，至少显示一个单元格，内容是整个 content
      tableData.value = [[content]]
    } else {
      tableData.value = [['']]
    }
  } catch (e) {
    
    const fallbackContent = chunk?.content || ''
    tableData.value = fallbackContent ? [[fallbackContent]] : [['无法加载表格数据']]
  }
  
  
}

const onRowClick = async (data: any) => {
  const type = (data?.chunk_type || '').toLowerCase()
  if (type === 'image') {
    return
  }
  // 同一个列表数据：直接使用左侧已加载的块数据，避免重复请求
  const chunkId = data.id || data.chunk_id
  if (!chunkId) return

  currentChunk.value = { ...data }
  editorContent.value = data.content || ''
  
  // ✅ 初始化表格数据（优先使用 meta.table_data）
  await initializeTableData(currentChunk.value)

  // 若内容为空（例如 DB 不存正文），再请求详情补全
  if (!editorContent.value) {
    try {
      const res = await getChunkDetail(props.documentId, chunkId)
      currentChunk.value = res.data
      editorContent.value = res.data?.content || ''
      
      // ✅ 重要：重新初始化表格数据（因为获取了新的数据，可能包含更完整的 meta）
      await initializeTableData(currentChunk.value)
    } catch (error) {
      // 保持已有数据
    }
  }

  try {
    await loadChunkVersions(chunkId)
  } catch (e) {}
}

const onEditorReady = () => {
  // 编辑器准备就绪
}

// ✅ 表格编辑功能：添加行
const addRow = () => {
  if (tableData.value.length === 0) {
    tableData.value = [['']]
  } else {
    const colCount = tableData.value[0]?.length || 1
    tableData.value.push(Array(colCount).fill(''))
  }
}

// ✅ 表格编辑功能：添加列
const addCol = () => {
  if (tableData.value.length === 0) {
    tableData.value = [['']]
  } else {
    tableData.value.forEach(row => {
      row.push('')
    })
  }
}

const destroyLuckysheet = () => {
  if (luckysheetModule && typeof luckysheetModule.destroy === 'function') {
    luckysheetModule.destroy()
  } else if ((window as any)?.luckysheet?.destroy) {
    (window as any).luckysheet.destroy()
  }
}

const renderLuckysheet = async () => {
  if (tableTab.value !== 'sheet') {
    destroyLuckysheet()
    return
  }
  if (!luckysheetContainer.value || !tableData.value.length) {
    destroyLuckysheet()
    return
  }
  if (!luckysheetModule) {
    const mod = await import('luckysheet')
    luckysheetModule = mod.default || mod
  }
  destroyLuckysheet()
  const sheetName = currentChunk.value?.metadata?.sheet_name || 'Sheet1'
  const luckysheetData = tableData.value.map(row => row.map(cell => ({ v: cell ?? '' })))
  luckysheetModule.create({
    container: luckysheetContainerId,
    data: [
      {
        name: sheetName,
        index: 0,
        order: 0,
        status: 1,
        data: luckysheetData
      }
    ],
    lang: 'zh',
    showtoolbar: false,
    sheetFormulaBar: false,
    showstatisticBar: false,
    allowEdit: false,
    enableAddRow: false,
    enableAddCol: false,
    forceCalculation: false,
    rowHeaderWidth: 60,
    columnHeaderHeight: 22,
    defaultColWidth: 120,
    defaultRowHeight: 24,
    cellRightClickConfig: {
      copy: true,
      copyAs: true,
      paste: false,
      insertRow: false,
      insertColumn: false,
      deleteRow: false,
      deleteColumn: false,
      deleteCell: false,
      hideRow: false,
      hideColumn: false,
      rowHeight: false,
      columnWidth: false,
      clear: false,
      matrix: false,
      sort: false,
      filter: false,
      chart: false,
      image: false,
      link: false,
      data: false
    }
  })
}

const loadChunkVersions = async (chunkId: number) => {
  try {
    const res = await getChunkVersions(props.documentId, chunkId)
    chunkVersions.value = res.data.versions || []
  } catch (error) {
    
  }
}

const handleSave = async () => {
  if (!currentChunk.value) return
  
  try {
    await ElMessageBox.confirm(
      '仅对当前分块重新向量化，不会影响其他分块。确定要保存吗？',
      '确认修改',
      { type: 'warning' }
    )
    
    saving.value = true
    // 兼容后端使用 id 或 chunk_id 的情况
    const chunkId = (currentChunk.value.id ?? currentChunk.value.chunk_id)
    if (!chunkId) {
      ElMessage.error('保存失败：未找到 chunkId')
      return
    }

    let content = editorContent.value || ''
    if (!content.trim() && !isTableChunk.value) {
      ElMessage.error('内容不能为空')
      return
    }
    let metadata: any = undefined
    if (isTableChunk.value) {
      // 将表格合并为文本（用于搜索），同时把结构写回 metadata
      content = tableData.value.map(r => r.join('\t')).join('\n')
      const metaRaw = (currentChunk.value as any).meta
      const metaObj = typeof metaRaw === 'string' ? (JSON.parse(metaRaw || '{}') || {}) : (metaRaw || {})
      metaObj.table_data = { cells: tableData.value, html: tableHtml.value }
      metadata = metaObj
    }
    else {
      // 普通文本块：把富文本 HTML 转成纯文本
      content = htmlToPlainText(content)
    }

    // 最后统一清洗文本内容
    content = sanitizeContent(content)
    

    await updateChunk(props.documentId, Number(chunkId), {
      content,
      metadata,
      version_comment: '块级修改'
    })
    
    ElMessage.success('保存成功，正在对当前分块重新向量化...')
    // ✅ 立即同步编辑态到当前选中块，避免界面仍显示旧内容
    try {
      // 更新 currentChunk 的内容与 meta，保证“分块内容”区域立刻显示新值
      (currentChunk.value as any).content = content
      if (metadata) {
        ;(currentChunk.value as any).meta = metadata
      }
      // 同步版本号与修改时间到前端（后端已写库，前端先行展示）
      const prevVer = Number((currentChunk.value as any).version || 0)
      ;(currentChunk.value as any).version = prevVer > 0 ? prevVer + 1 : 1
      ;(currentChunk.value as any).last_modified_at = new Date().toISOString()
    } catch (e) {}

    // ✅ 表格：保存后优先继续使用本地已编辑的 cells 渲染；
    // 服务器写回 document_tables 可能存在异步/缓存延迟，这里暂不立即强制刷新，避免覆盖你刚编辑的内容。
    // 如需立即拉取服务器数据，可改为 true。
    const REFRESH_TABLE_AFTER_SAVE = true
    if (isTableChunk.value && REFRESH_TABLE_AFTER_SAVE) {
      try {
        const metaRaw: any = metadata ?? (currentChunk.value as any).meta
        const metaObj = typeof metaRaw === 'string' ? (JSON.parse(metaRaw || '{}') || {}) : (metaRaw || {})
        const groupUid: string | undefined = metaObj.table_group_uid
        const tableUid: string | undefined = metaObj.table_id || metaObj.table_uid
        if (groupUid) {
          const res: any = await getTableGroupByUid(`${groupUid}?_=${Date.now()}`)
          const t = (res as any)?.data || {}
          const cells = Array.isArray(t.cells) ? t.cells : []
          if (cells.length > 0) {
            tableData.value = cells.map((r: any[]) => Array.isArray(r) ? r.map(v => String(v ?? '')) : [String(r ?? '')])
            tableHtml.value = ''
          }
        } else if (tableUid) {
          const res: any = await getTableByUid(`${tableUid}?_=${Date.now()}`)
          const t = (res as any)?.data || {}
          const cells = typeof t.cells_json === 'string' ? JSON.parse(t.cells_json || '[]') : (t.cells_json || [])
          if (Array.isArray(cells) && cells.length > 0) {
            tableData.value = cells.map((r: any[]) => Array.isArray(r) ? r.map(v => String(v ?? '')) : [String(r ?? '')])
            tableHtml.value = ''
          }
        }
      } catch (e) {
        
      }
    }

    await loadChunks()
    // 用最新列表项覆盖当前块的元数据（确保版本号/时间等与后端一致）
    try {
      const id = (currentChunk.value as any)?.id ?? (currentChunk.value as any)?.chunk_id
      const fresh = (chunks.value || []).find((c: any) => (c.id ?? c.chunk_id) === id)
      if (fresh) {
        currentChunk.value = { ...fresh, content: (currentChunk.value as any).content, meta: (currentChunk.value as any).meta }
      }
    } catch (e) {}
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}

const handleCancel = () => {
  emit('close')
}

const handleCompareVersion = async (version: any) => {
  try {
    const chunkId = (currentChunk.value?.id ?? currentChunk.value?.chunk_id)
    if (!chunkId) {
      ElMessage.error('无法获取块ID')
      return
    }
    
    const verNum = (version.version_number ?? version.version ?? version)
    if (!verNum) {
      ElMessage.error('无法获取版本号')
      return
    }
    
    
    
    // 获取旧版本数据
    const res = await getChunkVersion(props.documentId, chunkId, Number(verNum))
    
    // 提取版本数据：后端返回 { code: 0, message: "ok", data: ChunkVersionResponse }
    const verData = (res as any)?.data || res
    
    // 获取当前块完整内容（如果只有预览）
    let currentContent = currentChunk.value?.content || ''
    if (!currentContent || currentContent.length < 100) {
      // 如果内容太短，可能是预览，尝试获取完整内容
      try {
        const chunkDetailRes = await getChunkDetail(props.documentId, chunkId)
        const chunkDetail = (chunkDetailRes as any)?.data || chunkDetailRes
        currentContent = chunkDetail?.content || currentContent
      } catch (e) {
        // ignore
      }
    }
    
    // 准备对比数据
    const oldContent = String(verData?.content || '')
    const newContent = String(currentContent || '')
    
    
    
    if (!oldContent && !newContent) {
      ElMessage.warning('两个版本都没有内容可对比')
      return
    }
    
    compareVersions.value = {
      new: { ...currentChunk.value, content: newContent },
      old: { ...verData, content: oldContent }
    }
    
    // 生成高亮对比 HTML（行级 + 行内词级）
    const { oldHtml, newHtml } = diffLinesWithWordLevel(oldContent, newContent)
    compareHtmlOld.value = oldHtml || EMPTY_PLACEHOLDER
    compareHtmlNew.value = newHtml || EMPTY_PLACEHOLDER
    
    
    
    compareDialogVisible.value = true
  } catch (error: any) {
    ElMessage.error(`加载版本对比失败: ${error?.message || '未知错误'}`)
  }
}

// 行级 + 行内词级差分，便于阅读长段
function diffLinesWithWordLevel(oldText: string, newText: string): { oldHtml: string, newHtml: string } {
  const oldLines = oldText.split(/\r?\n/)
  const newLines = newText.split(/\r?\n/)
  const m = oldLines.length, n = newLines.length
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0))
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      dp[i][j] = oldLines[i] === newLines[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])
    }
  }
  let i = 0, j = 0
  const oldParts: string[] = []
  const newParts: string[] = []
  while (i < m && j < n) {
    if (oldLines[i] === newLines[j]) {
      const v = escapeHtml(oldLines[i])
      oldParts.push(v)
      newParts.push(v)
      i++; j++
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      // 行被删除：对该行做词级高亮，整体标红
      const { oldHtml } = diffWords(oldLines[i], '')
      oldParts.push(oldHtml || `<span class="diff-del">${escapeHtml(oldLines[i])}</span>`)
      i++
    } else {
      // 行被新增：对该行做词级高亮，整体标绿
      const { newHtml } = diffWords('', newLines[j])
      newParts.push(newHtml || `<span class="diff-ins">${escapeHtml(newLines[j])}</span>`)
      j++
    }
  }
  while (i < m) { oldParts.push(`<span class="diff-del">${escapeHtml(oldLines[i++])}</span>`) }
  while (j < n) { newParts.push(`<span class="diff-ins">${escapeHtml(newLines[j++])}</span>`) }
  return { oldHtml: oldParts.join('\n'), newHtml: newParts.join('\n') }
}

const handleRestoreVersion = async (version: any) => {
  try {
    const verNum = (version.version_number ?? version.version ?? version)
    if (!verNum) {
      ElMessage.error('无法获取版本号')
      return
    }

    // 如果已经是当前版本，不应该执行回退
    if (verNum === currentChunk.value?.version) {
      ElMessage.warning('当前已经是此版本，无需回退')
      return
    }

    await ElMessageBox.confirm(
      `确定要回退到版本 V${verNum} 吗？当前版本将保存为历史版本。`,
      '确认回退',
      { type: 'warning' }
    )

    const chunkId = (currentChunk.value?.id ?? currentChunk.value?.chunk_id)
    if (!chunkId) {
      ElMessage.error('无法获取块ID')
      return
    }

    // ✅ 立即更新版本号，禁用恢复按钮（防止重复点击）
    if (currentChunk.value) {
      currentChunk.value.version = Number(verNum)
    }

    await restoreChunkVersion(props.documentId, Number(chunkId), Number(verNum))
    ElMessage.success('恢复成功，正在刷新数据...')

    // ✅ 先刷新左侧列表，确保获取最新的块数据（包括回退后的 meta）
    await loadChunks()
    
    // ✅ 从刷新后的列表中找到当前块，更新 currentChunk（确保所有字段都是最新的）
    const freshChunk = (chunks.value || []).find((c: any) => (c.id ?? c.chunk_id) === chunkId)
    if (freshChunk) {
      currentChunk.value = { ...freshChunk }
      // ✅ 确保版本号正确（从后端返回的最新数据）
      if (freshChunk.version !== undefined) {
        currentChunk.value.version = freshChunk.version
      }
      editorContent.value = freshChunk.content || ''
    } else {
      // 如果找不到，至少确保版本号已更新
      if (currentChunk.value) {
        currentChunk.value.version = Number(verNum)
      }
    }
    
    // ✅ 重新加载版本历史
    await loadChunkVersions(Number(chunkId))

    // ✅ 若为表格块，强制刷新整表数据（等待后端更新完成）
    if (isTableChunk.value) {
      // 短暂延迟，确保后端 document_tables 更新完成
      await new Promise(resolve => setTimeout(resolve, 300))
      try {
        const metaRaw = currentChunk.value?.meta
        const meta = typeof metaRaw === 'string' ? JSON.parse(metaRaw || '{}') : (metaRaw || {})
        const tableGroupUid = meta?.table_group_uid
        const tableUid = meta?.table_id || meta?.table_uid
        if (tableGroupUid) {
          const res = await getTableGroupByUid(`${tableGroupUid}?_=${Date.now()}`)
          const t = (res as any)?.data || {}
          const cells = Array.isArray(t.cells) ? t.cells : []
          tableData.value = cells.map((r: any[]) => Array.isArray(r) ? r.map(v => String(v ?? '')) : [String(r ?? '')])
          tableHtml.value = ''
        } else if (tableUid) {
          const res = await getTableByUid(`${tableUid}?_=${Date.now()}`)
          const t = (res as any)?.data || {}
          const cells = typeof t.cells_json === 'string' ? JSON.parse(t.cells_json || '[]') : (t.cells_json || [])
          tableData.value = Array.isArray(cells) ? cells.map((r: any[]) => Array.isArray(r) ? r.map(v => String(v ?? '')) : [String(r ?? '')]) : []
          tableHtml.value = t.source_html || ''
        }
      } catch (e) {
        console.warn('回退后刷新表格数据失败:', e)
      }
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('恢复失败')
    }
  }
}

const getTypeColor = (type: string) => {
  const map: Record<string, string> = {
    text: '',
    heading: 'success',
    code: 'warning',
    table: 'info'
  }
  return map[type] || ''
}

// 词级 LCS diff（不引第三方），保留空白字符分隔，效果直观
function diffWords(oldText: string, newText: string): { oldHtml: string, newHtml: string } {
  const A = oldText.split(/(\s+)/)
  const B = newText.split(/(\s+)/)
  const m = A.length, n = B.length
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0))
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      dp[i][j] = A[i] === B[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])
    }
  }
  let i = 0, j = 0
  const oldParts: string[] = []
  const newParts: string[] = []
  while (i < m && j < n) {
    if (A[i] === B[j]) {
      const v = escapeHtml(A[i])
      oldParts.push(v)
      newParts.push(v)
      i++; j++
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      oldParts.push(`<span class=\"diff-del\">${escapeHtml(A[i])}</span>`) ; i++
    } else {
      newParts.push(`<span class=\"diff-ins\">${escapeHtml(B[j])}</span>`); j++
    }
  }
  while (i < m) { oldParts.push(`<span class=\"diff-del\">${escapeHtml(A[i++])}</span>`) }
  while (j < n) { newParts.push(`<span class=\"diff-ins\">${escapeHtml(B[j++])}</span>`) }
  return { oldHtml: oldParts.join(''), newHtml: newParts.join('') }
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

onMounted(() => {
  loadChunks()
})

watch(tableTab, () => {
  nextTick(() => renderLuckysheet())
})

watch(tableData, () => {
  nextTick(() => renderLuckysheet())
})

watch(() => currentChunk.value?.chunk_index, () => {
  destroyLuckysheet()
  nextTick(() => renderLuckysheet())
})

onBeforeUnmount(() => {
  destroyLuckysheet()
})
</script>

<style lang="scss" scoped>
.chunk-editor-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100vh;
  padding: 12px;
  box-sizing: border-box;
}

.chunk-editor {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 300px 1fr 300px;
  gap: 20px;

  .chunk-list {
    .chunk-list-card {
      .list-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
    }

    .chunk-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 12px;
      height: 46px;
      margin: 16px 0; /* 明显缝隙 */
      box-sizing: border-box;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.06); /* 淡底色，便于区分 */
      border: 1px solid rgba(255, 255, 255, 0.10);
      box-shadow: 0 2px 8px rgba(0,0,0,0.18);
      transition: background 0.15s ease;
      
      &:hover { background: rgba(255, 255, 255, 0.10); }

      .chunk-info {
        display: flex;
        align-items: center;
        gap: 22px; /* 数字与类型之间距离更大 */
        
        .chunk-index {
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
          font-size: 16px;
          font-weight: 700;
          letter-spacing: 0.2px;
          width: 28px; height: 28px;
          display: inline-flex;
          align-items: center; justify-content: center;
          border-radius: 50%;
          color: #fff;
          background: radial-gradient( circle at 30% 30%, rgba(74, 144, 255, 0.85), rgba(74,144,255,0.45) );
          box-shadow: 0 0 8px rgba(74,144,255,0.35), inset 0 0 0 1px rgba(255,255,255,0.25);
        }
      }

      :deep(.type-tag) {
        border-radius: 8px;
        height: 26px;
        line-height: 24px;
        padding: 0 12px;
        font-size: 14px;
        margin-left: 10px;
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.15);
        border: none;
      }

      /* 科技感色系 */
      :deep(.type-tag.text) {
        color: #e9f3ff;
        background: linear-gradient(135deg, rgba(0, 140, 255, 0.75), rgba(0, 120, 255, 0.35));
        box-shadow: 0 0 12px rgba(0,140,255,0.35);
      }
      :deep(.type-tag.table) {
        color: #ecfff7;
        background: linear-gradient(135deg, rgba(0, 220, 155, 0.75), rgba(0, 205, 145, 0.35));
        box-shadow: 0 0 12px rgba(0,220,155,0.35);
      }
    }

    /* 表格风格（根据你的截图弱化 hover 高亮、收窄行距） */
    :deep(.chunk-table) {
      background: transparent;
      .el-table__header th { background: rgba(255,255,255,0.06); color: #dfe7f3; padding: 8px 0; }
      .el-table__row { height: 36px; }
      .el-table__row:hover > td { background: rgba(255,255,255,0.045) !important; color: #e6ecf5; }
      .el-table__row.current-row > td { background: rgba(64,158,255,0.10) !important; color: #eaf2ff; }
      .type-pill { display: inline-block; min-width: 48px; padding: 2px 10px; border-radius: 999px; font-size: 13px; }
    }
    
    /* ✅ 表格预览样式 */
    .table-html-wrapper {
      width: 100%;
      overflow-x: auto;
      padding: 10px;
      background: #fff;
      border-radius: 4px;
    }
    
    .table-html {
      width: 100%;
      overflow-x: auto;
      
      :deep(table) {
        width: 100%;
        border-collapse: collapse;
        border: 1px solid #ddd;
        background: white;
        
        th, td {
          border: 1px solid #ddd;
          padding: 8px 12px;
          text-align: left;
          vertical-align: top;
        }
        
        th {
          background-color: #f5f5f5;
          font-weight: 600;
        }
        
        tr:nth-child(even) {
          background-color: #f9f9f9;
        }
        
        tr:hover {
          background-color: #f0f0f0;
        }
      }
      
      :deep(thead) {
        background-color: #f5f5f5;
      }
    }
    
    .table-preview-from-cells {
      width: 100%;
      .table-hint {
        font-size: 13px;
        color: #94a3b8;
        margin-bottom: 6px;
      }
      .table-scroll-wrapper {
        width: 100%;
        overflow-x: auto;
        overflow-y: hidden;
        cursor: grab;
      }
      .table-container {
        display: inline-block;
        min-width: max-content;
        overflow: visible;
        background: white;
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12) !important;
        border: 1px solid #e0e0e0 !important;
        
        .preview-table {
          width: auto;
          min-width: max-content;
          table-layout: auto;
          border-collapse: separate;
          border-spacing: 0;
          background: white;
          font-size: 16px;
          line-height: 1.8;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
          
          .table-header {
            background: linear-gradient(to bottom, #4a90e2, #357abd) !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            font-size: 16px !important;
            padding: 16px 20px !important;
            text-align: left !important;
            vertical-align: middle !important;
            border-bottom: 3px solid #2c5f8a !important;
            border-right: 2px solid rgba(255, 255, 255, 0.2) !important;
            white-space: nowrap !important;
            position: sticky !important;
            top: 0 !important;
            z-index: 10 !important;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1) !important;
            letter-spacing: 0.3px !important;
            
            &:first-child {
              border-left: none;
              border-top-left-radius: 6px;
            }
            
            &:last-child {
              border-right: none;
              border-top-right-radius: 6px;
            }
          }
          
          .table-cell {
            padding: 16px 20px !important;
            text-align: left !important;
            vertical-align: top !important;
            border-bottom: 2px solid #d0d0d0 !important;
            border-right: 2px solid #d0d0d0 !important;
            color: #2c3e50 !important;
            background: white !important;
            word-wrap: break-word !important;
            word-break: break-word !important;
            font-size: 15px !important;
            line-height: 1.8 !important;
            min-height: 48px !important;
            
            &:first-child {
              border-left: none;
              font-weight: 600;
              color: #34495e;
              background: linear-gradient(to right, #f8f9fa, #ffffff);
              border-right: 2px solid #d0d0d0;
            }
            
            &:last-child {
              border-right: none;
            }
          }
          
          .table-row-even {
            .table-cell {
              background-color: #f9fafb;
              
              &:first-child {
                background: linear-gradient(to right, #f0f2f5, #f9fafb);
              }
            }
          }
          
          tbody tr:hover {
            .table-cell {
              background-color: #e8f4f8 !important;
              border-color: #b0d4e8;
              
              &:first-child {
                background: linear-gradient(to right, #e0ecf0, #e8f4f8) !important;
              }
            }
          }
          
          tbody tr:last-child {
            .table-cell {
              border-bottom: 2px solid #d0d0d0;
            }
          }
          
          // 第一列（对比维度）特殊样式
          tbody tr .table-cell:first-child {
            min-width: 120px;
            max-width: 200px;
          }
        }
      }
    }
  }
  
  .type-pill.text { background: linear-gradient(135deg, rgba(0,140,255,0.6), rgba(0,120,255,0.28)); color: #eaf2ff; box-shadow: 0 0 6px rgba(0,140,255,0.2); }
  .type-pill.table { background: linear-gradient(135deg, rgba(0,210,150,0.6), rgba(0,200,140,0.28)); color: #ecfff7; box-shadow: 0 0 6px rgba(0,210,150,0.2); }

  .editor-main {
    .editor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .editor-content {
      .editor {
        min-height: 400px;
        
        :deep(.ql-container) {
          min-height: 400px;
        }
      }
      .table-editor { margin-top: 6px; }
      .table-editor-tools { display: flex; gap: 8px; }
      .luckysheet-wrapper {
        height: 60vh;
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 8px;
        overflow: hidden;
        .luckysheet-container {
          width: 100%;
          height: 100%;
          background: #fff;
        }
      }
    }
  }

  .version-history {
    .version-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      
      .version-comment {
        flex: 1;
        font-size: 14px;
        color: #e2e8f0;
        font-weight: 500;
        letter-spacing: .2px;
      }
      :deep(.el-tag) {
        font-size: 12px;
        padding: 2px 8px;
      }
    }
    
    .version-actions {
      display: flex;
      gap: 8px;
      margin-top: 8px;
    }
  }

  .compare-content {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    max-height: 600px;
    overflow-y: auto;

    .compare-left,
    .compare-right {
      h4 {
        margin-bottom: 10px;
      }

      pre {
        padding: 10px;
        background: #f5f5f5;
        border-radius: 4px;
        white-space: pre-wrap;
        word-break: break-all;
      }
    }
  }
}

.compare-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;

  .compare-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
    
    h4 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
    }
    
    .version-time {
      font-size: 12px;
      color: #999;
      margin-left: auto;
    }
  }

  pre {
    background: #0f172a;
    color: #e2e8f0;
    padding: 16px;
    border-radius: 6px;
    white-space: pre-wrap;
    word-break: break-word;
    min-height: 200px;
    max-height: 500px;
    overflow-y: auto;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 14px;
    line-height: 1.6;
  }
  
  :deep(.diff-ins) { 
    background: #083c19; 
    color: #c6f6d5; 
    padding: 2px 4px;
    border-radius: 3px;
  }
  
  :deep(.diff-del) { 
    background: #5b0000; 
    color: #fed7d7; 
    text-decoration: line-through;
    padding: 2px 4px;
    border-radius: 3px;
  }
}

.compare-legend {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
  .legend-ins { color: #38a169; }
  .legend-del { color: #e53e3e; text-decoration: line-through; }
}
</style>

<style lang="scss">
.chunk-editor .table-scroll-wrapper::-webkit-scrollbar {
  height: 12px;
}
.chunk-editor .table-scroll-wrapper::-webkit-scrollbar-track {
  background: rgba(34, 197, 94, 0.2);
  border-radius: 999px;
}
.chunk-editor .table-scroll-wrapper::-webkit-scrollbar-thumb {
  background: linear-gradient(90deg, #4ade80, #22c55e);
  border-radius: 999px;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.45);
}
.chunk-editor .table-scroll-wrapper::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(90deg, #22c55e, #16a34a);
}
</style>
