<template>
  <div class="search-page">
    <el-card class="neo-card">
      <template #header>
        <span>搜索</span>
      </template>

      <!-- 搜索模式切换 -->
      <el-tabs v-model="searchMode" class="search-mode-tabs">
        <!-- 文本搜索 -->
        <el-tab-pane label="文本搜索" name="text">
          <div class="search-layout">
            <!-- 左侧搜索历史边栏 -->
            <div v-if="searchHistory.length > 0" class="search-history-sidebar">
              <div class="history-header">
                <div class="history-title">
                  <el-icon class="history-icon"><Clock /></el-icon>
                  <span>搜索历史</span>
                </div>
                <el-button 
                  type="text" 
                  size="small" 
                  class="clear-btn"
                  @click="handleClearHistory"
                >
                  清空
                </el-button>
              </div>
              <div class="history-list">
                <div
                  v-for="item in searchHistory"
                  :key="item.id"
                  class="history-item"
                  @click="handleHistoryClick(item)"
                >
                  <el-icon class="history-item-icon"><Search /></el-icon>
                  <div class="history-content">
                    <div class="history-query">{{ item.query_text }}</div>
                    <div class="history-meta">
                      <el-icon class="time-icon"><Clock /></el-icon>
                      <span>{{ formatTime(item.created_at) }}</span>
                    </div>
                  </div>
                  <el-icon 
                    class="history-delete" 
                    @click.stop="handleDeleteHistory(item.id)"
                  >
                    <Close />
                  </el-icon>
                </div>
              </div>
            </div>

            <!-- 右侧搜索表单 -->
            <div class="search-form-wrapper">
              <el-form :model="searchForm" @submit.prevent="handleSearch" class="search-form">
                <!-- 知识库选择 - 必需项，支持多选 -->
                <el-form-item label="选择知识库" required>
                  <el-select 
                    v-model="searchForm.knowledge_base_id" 
                    placeholder="请选择知识库（可多选）" 
                    multiple
                    clearable
                    style="width: 100%"
                    size="large"
                  >
                    <el-option
                      v-for="kb in knowledgeBases"
                      :key="kb.id"
                      :label="kb.name"
                      :value="kb.id"
                    />
                  </el-select>
                </el-form-item>

                <el-form-item>
                  <el-input
                    v-model="searchForm.query"
                    placeholder="请输入搜索关键词..."
                    size="large"
                    @keyup.enter="handleSearch"
                  >
                    <template #append>
                      <el-button type="primary" @click="handleSearch" :loading="searching">搜索</el-button>
                    </template>
                  </el-input>
                </el-form-item>

            <el-form-item class="mode-row">
              <el-radio-group v-model="searchForm.search_type">
                <el-radio label="vector">向量搜索</el-radio>
                <el-radio label="keyword">关键词搜索</el-radio>
                <el-radio label="hybrid">混合搜索</el-radio>
                <el-radio label="exact">精确匹配</el-radio>
              </el-radio-group>
            </el-form-item>

            <!-- Rerank说明：向量、关键词、混合搜索都使用Rerank精排 -->
            <div v-if="searchForm.search_type === 'vector' || searchForm.search_type === 'keyword' || searchForm.search_type === 'hybrid'" class="info-banner">
              <el-icon><InfoFilled /></el-icon>
              <span>向量搜索、关键词搜索、混合搜索均使用 Rerank 精排，将优先展示最相关的结果</span>
            </div>

            <!-- 阈值设置（向量/混合时显示） -->
            <div v-if="searchForm.search_type === 'vector' || searchForm.search_type === 'hybrid'" class="advanced-bar">
              <span style="color:#cfd8e6;font-size:14px;margin-right:8px;">相似度阈值（0–1）</span>
              <el-slider
                v-model="searchForm.similarity_threshold"
                :min="0"
                :max="1"
                :step="0.01"
                show-input
                :show-input-controls="false"
                input-size="small"
                style="flex:1;max-width:520px;"
              />
            </div>

            <!-- 显示过滤与视图切换（前端过滤 rerank/score 过低的结果） -->
            <!-- 精确匹配不使用Rerank，所以隐藏此滑块 -->
            <div v-if="searchForm.search_type !== 'exact'" class="advanced-bar">
              <span style="color:#cfd8e6;font-size:14px;margin-right:8px;">最低Rerank分（0–1）</span>
              <el-slider
                v-model="minDisplayScore"
                :min="0"
                :max="1"
                :step="0.01"
                show-input
                :show-input-controls="false"
                input-size="small"
                style="flex:1;max-width:400px;"
              />

              <el-radio-group v-model="viewMode" size="small" style="margin-left:12px;">
                <el-radio-button label="card">卡片</el-radio-button>
                <el-radio-button label="table">表格</el-radio-button>
              </el-radio-group>
            </div>
            
            <!-- 精确匹配信息提示与视图切换 -->
            <div v-else>
              <div class="info-banner" style="margin-bottom:8px;">
                <el-icon><InfoFilled /></el-icon>
                <span>精确匹配使用短语匹配（match_phrase），不使用 Rerank / 相似度阈值。建议输入尽量完整的短语。</span>
              </div>
              <div class="advanced-bar">
              <el-radio-group v-model="viewMode" size="small">
                <el-radio-button label="card">卡片</el-radio-button>
                <el-radio-button label="table">表格</el-radio-button>
              </el-radio-group>
            </div>
            </div>

            <div class="advanced-bar">
              <el-switch
                v-model="useAdvanced"
                active-text="启用高级搜索"
                inactive-text="高级搜索"
                :disabled="searchForm.search_type !== 'exact'"
              />
              <el-button type="text" @click="showAdvanced = !showAdvanced">
                展开/收起
              </el-button>
              <span v-if="searchForm.search_type !== 'exact'" class="tip-muted">仅“精确匹配”支持高级搜索</span>
            </div>

            <el-collapse-transition>
              <div v-show="showAdvanced && searchForm.search_type === 'exact'" class="advanced-panel">
                <el-divider content-position="left">范围</el-divider>
                <el-form-item label="分类">
                  <el-select v-model="searchForm.category_id" placeholder="全部" clearable>
                    <el-option label="全部" :value="null" />
                    <!-- TODO: 加载分类 -->
                  </el-select>
                </el-form-item>

                <el-form-item label="相似度阈值">
                  <el-slider v-model="searchForm.similarity_threshold" :min="0" :max="1" :step="0.1" show-input />
                </el-form-item>

                <el-divider content-position="left">高级条件</el-divider>
                <el-form-item label="布尔查询">
                  <el-input v-model="advForm.bool_query" placeholder="例：(MongoDB AND 连接) OR (Redis AND 配置)" clearable />
                </el-form-item>
                <el-form-item label="精确短语">
                  <el-input v-model="advForm.exact_phrase" placeholder='精确短语，如："MongoDB 连接"' clearable />
                </el-form-item>
                <el-form-item label="通配符">
                  <el-input v-model="advForm.wildcard" placeholder="通配符，如：Mongo*" clearable />
                </el-form-item>
                <el-form-item label="正则表达式">
                  <el-input v-model="advForm.regex" placeholder="正则，如：/^Mongo.*DB$/" clearable />
                </el-form-item>
              </div>
            </el-collapse-transition>
              </el-form>

              <!-- 文本搜索结果 -->
              <div v-if="filteredResults.length > 0" class="search-results">
            <div class="results-header">
              <span>搜索结果 ({{ filteredResults.length }})</span>
              <el-tag v-if="searchForm.search_type === 'hybrid'" type="success" size="small">
                <el-icon><Star /></el-icon>
                混合搜索 Rerank精排
              </el-tag>
              <el-tag v-else-if="searchForm.search_type === 'vector'" type="info" size="small">
                向量搜索
              </el-tag>
              <el-tag v-else-if="searchForm.search_type === 'keyword'" type="warning" size="small">
                关键词搜索
              </el-tag>
              <el-tag v-else-if="searchForm.search_type === 'exact'" type="primary" size="small">
                精确匹配
              </el-tag>
            </div>

            <!-- 表格视图 -->
            <el-table v-if="viewMode === 'table'" :data="filteredResults" stripe style="width: 100%" size="small" class="results-list-table">
              <el-table-column prop="document_id" label="文档ID" width="90" />
              <el-table-column label="内容" min-width="420">
                <template #default="{ row }">
                  <template v-if="isTable(row)">
                    <el-table
                      :data="getTableRows(row)"
                      border
                      size="small"
                      style="width:100%;font-size:12px"
                    >
                      <el-table-column
                        v-for="(col, idx) in getTableCols(row)"
                        :key="idx"
                        :prop="'c' + idx"
                        :label="col"
                      />
                    </el-table>
                  </template>
                  <template v-else>
                    {{ row.title || (row.content || '').slice(0, 160) }}
                  </template>
                </template>
              </el-table-column>
              <el-table-column label="分数" width="120" align="center">
                <template #default="{ row }">
                  <el-tag size="small" type="success" v-if="getScore(row) >= 0">
                    {{ (getScore(row) * 100).toFixed(1) }}%
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="knowledge_base_id" label="知识库" width="100" />
            </el-table>

            <!-- 卡片视图 -->
            <el-card
              v-else
              v-for="item in filteredResults"
              :key="item.id || item.chunk_id"
              class="result-item"
              @click="handleItemClick(item)"
            >
              <div v-if="!isTable(item)" class="result-title">{{ item.title || item.content?.substring(0, 100) }}</div>
              <div class="result-content">
                <template v-if="isTable(item)">
                  <el-table
                    v-loading="item._loadingChunk"
                    :data="getTableRows(item)"
                    border
                    size="small"
                    style="width:100%"
                  >
                    <el-table-column
                      v-for="(col, idx) in getTableCols(item)"
                      :key="idx"
                      :prop="'c' + idx"
                      :label="col"
                    />
                  </el-table>
                </template>
                <template v-else>
                  <!-- 优先显示高亮内容，如果没有则显示原始内容 -->
                  <div 
                    class="result-content-text" 
                    v-html="item.highlighted_content || item.content"
                  />
                </template>
              </div>
              <div class="result-meta">
                <el-tag size="small">{{ item.source_type || '文档' }}</el-tag>
                <span class="similarity">分数: {{ (getScore(item) * 100).toFixed(1) }}%</span>
                <el-tag v-if="item.rerank_score" type="success" size="small">
                  Rerank: {{ (item.rerank_score * 100).toFixed(1) }}%
                </el-tag>
                <el-tag v-if="isTable(item)" type="warning" size="small">表格</el-tag>
                <el-tag v-if="item.has_image_ocr" type="info" size="small">
                  <el-icon><Picture /></el-icon>
                  {{ item.image_ocr_count || 0 }}张关联图片
                </el-tag>
              </div>
            </el-card>

            <el-pagination
              v-if="filteredResults.length > 0"
              v-model:current-page="page"
              v-model:page-size="size"
              :total="filteredResults.length"
              @current-change="handleSearch"
            />
              </div>
              <!-- 文本搜索空态 -->
              <div v-else-if="textSearched && !searching" class="empty-state">
                <el-empty description="没有找到匹配的结果">
                  <div class="empty-hints">
                    <div>• 尝试放宽关键词或减少过滤条件</div>
                    <div>• 适当降低相似度阈值/最低Rerank分</div>
                  </div>
                </el-empty>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 图片搜索 -->
        <el-tab-pane label="图片搜索" name="image">
          <!-- 知识库选择 - 必需项，支持多选 -->
          <el-form-item label="选择知识库" required style="margin-bottom: 20px;">
            <el-select 
              v-model="searchForm.knowledge_base_id" 
              placeholder="请选择知识库（可多选）" 
              multiple
              clearable
              style="width: 100%"
              size="large"
            >
              <el-option
                v-for="kb in knowledgeBases"
                :key="kb.id"
                :label="kb.name"
                :value="kb.id"
              />
            </el-select>
          </el-form-item>

          <el-tabs v-model="imageSearchType" class="sub-tabs">
            <!-- 以图搜图 -->
            <el-tab-pane label="以图搜图" name="by-image">
              <div class="vision-panel">
                <div class="panel-left">
                  <el-upload
                    drag
                    class="upload-dropzone"
                    :auto-upload="false"
                    :show-file-list="false"
                    accept="image/*"
                    @change="handleImageUpload"
                  >
                    <el-icon class="upload-icon"><Picture /></el-icon>
                    <div class="el-upload__text">
                      拖拽图片到此处，或 <em>点击选择</em>
                    </div>
                    <div class="sub-hint">支持 PNG / JPG / JPEG，最大 10MB</div>
                  </el-upload>

                  <div class="controls-card">
                    <div class="control-row">
                      <span class="control-label">相似度阈值（0–1）</span>
                      <el-slider
                        v-model="imageSearchSimilarityThreshold"
                        :min="0"
                        :max="1"
                        :step="0.01"
                        show-input
                        :show-input-controls="false"
                        input-size="small"
                      />
                    </div>
                    <div class="actions">
                      <el-button
                        type="primary"
                        size="large"
                        :loading="imageSearching"
                        :disabled="!uploadedImage"
                        @click="handleSearchByImage"
                      >
                        开始搜索
                      </el-button>
                      <span class="tiny-hint">使用 CLIP 图像编码器进行语义检索</span>
                    </div>
                  </div>
                </div>

                <div class="panel-right">
                  <div v-if="uploadedImage" class="preview-card">
                    <img :src="uploadedImageUrl" alt="预览" />
                    <div class="preview-meta">
                      <span class="meta-title">已选择图片</span>
                      <span class="meta-desc">用于语义匹配的查询向量将依据此图生成</span>
                    </div>
                  </div>
                  <div v-else class="empty-card">未选择图片</div>
                </div>
              </div>
            </el-tab-pane>

            <!-- 以文搜图 -->
            <el-tab-pane label="以文搜图" name="by-text">
              <div class="vision-panel single">
                <div class="query-card">
                  <div class="query-title">用文字描述你想找的图片</div>
                  <el-input
                    v-model="imageSearchText"
                    placeholder="输入图片描述，如：找一张有狗的图片"
                    size="large"
                    clearable
                    @keyup.enter="handleSearchByText"
                  >
                    <template #append>
                      <el-button type="primary" @click="handleSearchByText" :loading="imageSearching">搜索</el-button>
                    </template>
                  </el-input>
                  <div class="query-sub">
                    <el-icon><InfoFilled /></el-icon>
                    使用 CLIP 文本编码器进行语义检索
                  </div>

                  <div class="control-row" style="margin-top:12px;">
                    <span class="control-label">相似度阈值（0–1）</span>
                    <el-slider
                      v-model="imageSearchSimilarityThreshold"
                      :min="0"
                      :max="1"
                      :step="0.01"
                      show-input
                      :show-input-controls="false"
                      input-size="small"
                    />
                  </div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>

          <!-- 图片搜索结果 -->
          <div v-if="imageResults.length > 0" class="search-results">
            <div class="results-header">
              <span>找到 {{ imageTotal }} 张相似图片</span>
            </div>

            <div class="image-grid">
              <div
                v-for="image in imageResults"
                :key="image.image_id || image.id"
                class="image-item"
                @click="viewImage(image)"
              >
                <img :src="image.image_path" :alt="image.description || '图片'" />
                <div class="image-info">
                  <div class="similarity">相似度: {{ ((image.similarity_score || image.similarity || 0) * 100).toFixed(1) }}%</div>
                  <div class="description">{{ image.description || image.ocr_text || '无描述' }}</div>
                </div>
              </div>
            </div>
          </div>
          <!-- 图片搜索空态 -->
          <div v-else-if="(imageSearchType === 'by-image' || imageSearchType === 'by-text') && imageSearched && !imageSearching" class="empty-state">
            <el-empty description="未检索到相关图片">
              <div class="empty-hints">
                <div>• 尝试更换图片或描述</div>
                <div>• 适当降低相似度阈值</div>
              </div>
            </el-empty>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 图片详情对话框 -->
    <el-dialog v-model="imageDetailVisible" title="图片详情" width="900px">
      <div v-if="selectedImage" class="image-detail">
        <div class="detail-info">
          <div class="advanced-bar" style="margin:6px 0 12px;">
            <span style="color:#9aa6bf;font-size:12px;margin-right:8px;">最小关联置信度</span>
            <el-slider v-model="imageAssocMinConf" :min="0" :max="1" :step="0.01" style="width:240px;" @change="refreshImageContext" />
          </div>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="图片ID">{{ selectedImage.image_id || selectedImage.id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="来源文档ID">
              <span v-if="selectedImage.document_id">
                {{ selectedImage.document_id }}
                <el-button type="text" size="small" @click="viewDocument(selectedImage.document_id)" style="margin-left: 8px;">
                  查看文档
                </el-button>
              </span>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="图片类型">{{ selectedImage.image_type || '-' }}</el-descriptions-item>
            <el-descriptions-item label="相似度" v-if="selectedImage.similarity_score">
              {{ ((selectedImage.similarity_score || 0) * 100).toFixed(1) }}%
            </el-descriptions-item>
            <el-descriptions-item label="图片尺寸" v-if="selectedImage.width && selectedImage.height">
              {{ selectedImage.width }} × {{ selectedImage.height }} 像素
            </el-descriptions-item>
            <el-descriptions-item label="向量模型">{{ selectedImage.vector_model || '-' }}</el-descriptions-item>
            <el-descriptions-item label="向量维度">{{ selectedImage.vector_dim || '-' }}</el-descriptions-item>
            <el-descriptions-item label="处理状态">{{ selectedImage.status || '-' }}</el-descriptions-item>
          </el-descriptions>
          
          <el-divider />
          
          <div v-if="selectedImage.description" class="info-section">
            <h4>描述</h4>
            <p>{{ selectedImage.description }}</p>
          </div>
          
          <div v-if="selectedImage.ocr_text" class="info-section">
            <h4>OCR识别文字</h4>
            <p class="ocr-text">{{ selectedImage.ocr_text }}</p>
          </div>

          <div v-if="selectedImage.page_number" class="info-section">
            <h4>页码</h4>
            <p>第 {{ selectedImage.page_number }} 页</p>
          </div>

          <div v-if="selectedImage._context?.associations?.length" class="info-section">
            <h4>关联文本（Top{{ selectedImage._context.associations.length }}）</h4>
            <div v-for="a in selectedImage._context.associations" :key="a.chunk_id" style="margin:8px 0;">
              <div style="color:#9aa6bf;font-size:12px;">置信度 {{ (a.confidence*100).toFixed(1) }}%</div>
              <div style="white-space:pre-wrap;line-height:1.6;border:1px solid rgba(148,163,184,.16);padding:8px;border-radius:6px;">
                {{ a.context?.display?.merged_text || '—' }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 命中上下文对话框 -->
    <el-dialog v-model="contextVisible" title="上下文" width="900px">
      <div v-if="contextData">
        <div style="margin-bottom:8px;color:#9aa6bf;">合并文本</div>
        <div class="context-merged">
          <template v-if="contextSegments.length">
            <template v-for="(segment, idx) in contextSegments" :key="idx">
              <div v-if="segment.kind === 'text'" class="context-text">{{ segment.content }}</div>
              <div v-else class="context-inline-image">
                <img
                  :src="segment.src"
                  alt="上下文图片"
                  @click="handleContextImageClick(segment.raw)"
                />
                <div v-if="segment.description" class="context-inline-caption">{{ segment.description }}</div>
              </div>
            </template>
          </template>
          <template v-else>
            <div class="context-text">{{ contextData.display?.merged_text || '暂无' }}</div>
          </template>
        </div>
        <el-divider />
        <div style="color:#9aa6bf;">邻接块</div>
        <div class="neighbors">
          <div>
            <div style="color:#9aa6bf;font-size:12px;margin:6px 0;">上文</div>
            <div v-for="n in (contextData.context?.neighbors?.prev||[])" :key="n.chunk_id" style="margin-bottom:8px;">{{ n.content?.slice(0,200) }}</div>
          </div>
          <div>
            <div style="color:#9aa6bf;font-size:12px;margin:6px 0;">下文</div>
            <div v-for="n in (contextData.context?.neighbors?.next||[])" :key="n.chunk_id" style="margin-bottom:8px;">{{ n.content?.slice(0,200) }}</div>
          </div>
        </div>
        <el-divider v-if="remainingContextImages.length" />
        <div v-if="remainingContextImages.length">
          <div style="color:#9aa6bf;">相关图片</div>
          <div class="context-images">
            <div class="context-image-card" v-for="img in remainingContextImages" :key="img.chunk_id || img.image_id || img.index">
              <img :src="img.src" alt="上下文图片" @click="handleContextImageClick(img)" />
              <div class="context-image-desc">
                <div>ID: {{ img.image_id || img.chunk_id }}</div>
                <div class="context-image-text">{{ img.description || '图片' }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { getDocumentChunks, getChunkDetail, getChunkContext, getImageContext } from '@/api/modules/documents'
import { ElMessage } from 'element-plus'
import { Picture, InfoFilled, Star, Clock, Search, Close } from '@element-plus/icons-vue'
import { search, advancedSearch, searchByImage, searchByTextForImages, getSearchHistory, deleteSearchHistory, clearSearchHistory } from '@/api/modules/search'
import { getImageDetail } from '@/api/modules/images'
import { formatFileSize } from '@/utils/format'
import { getKnowledgeBases } from '@/api/modules/knowledge-bases'
import type { KnowledgeBase } from '@/types'

const searchMode = ref<'text' | 'image'>('text')
const imageSearchType = ref<'by-image' | 'by-text'>('by-image')

const searchForm = reactive({
  query: '',
  search_type: 'hybrid',
  knowledge_base_id: [] as number[],
  category_id: null as number | null,
  similarity_threshold: 0.3
})

const showAdvanced = ref(false)
const useAdvanced = ref(false)
const textResults = ref<any[]>([])
const imageResults = ref<any[]>([])
const knowledgeBases = ref<KnowledgeBase[]>([])
const page = ref(1)
const size = ref(20)
const textTotal = ref(0)
// 搜索触发标记，用于显示空态
const textSearched = ref(false)
const imageSearched = ref(false)
// 视图模式与前端显示过滤
const viewMode = ref<'card' | 'table'>('card')
const minDisplayScore = ref(0.2)
// 搜索加载状态
const searching = ref(false)

// 预览图与坐标高亮
const refreshImageContext = async () => {
  try {
    if (!selectedImage.value?.document_id) return
    const id = selectedImage.value.image_id || selectedImage.value.id
    if (!id) return
    const ctxRes:any = await getImageContext(
      selectedImage.value.document_id,
      id,
      { neighbor_pre: 2, neighbor_next: 2, min_confidence: imageAssocMinConf.value }
    )
    selectedImage.value._context = ctxRes?.data?.data || ctxRes?.data || ctxRes
  } catch {}
}

const getScore = (row: any) => {
  return (
    row?.rerank_score ??
    row?.score ??
    row?.similarity_score ??
    row?.knn_score ?? 0
  )
}

const filteredResults = computed(() => {
  return (textResults.value || []).filter((it) => getScore(it) >= minDisplayScore.value)
})

// 判断是否表格（包含启发式判断：Markdown 管道表）
const isTable = (item: any) => {
  const ct = (
    item?.chunk_type ||
    item?.chunkType ||
    item?.metadata?.chunk_type ||
    item?._chunk?.chunk_type || ''
  ).toString().toLowerCase()
  if (ct === 'table') return true
  if (item?._chunk?.metadata?.cells || item?._chunk?.metadata?.rows) return true
  const content: string = (item?._chunk?.content || item?.content || '').trim()
  // 识别 Markdown 管道表：至少2行包含'|', 且每行列数>=2
  const lines = content.split(/\n+/).filter((l) => l.includes('|'))
  if (lines.length >= 2) {
    const colsCount = lines[0].split('|').filter(Boolean).length
    if (colsCount >= 2) return true
  }
  return false
}

// 预加载表格类 chunk（从 MySQL/接口获取结构化信息）
const getDocId = (it: any) => it?.document_id ?? it?.doc_id ?? it?.documentId ?? it?.document?.id
const getChunkId = (it: any) => it?.chunk_id ?? it?.chunkId ?? (it?.id && typeof it?.document_id !== 'undefined' ? it.id : undefined)
const preloadTableChunks = async () => {
  const candidates = (textResults.value || []).filter((it) => {
    const t = (it.chunk_type || it.metadata?.chunk_type || it.source_type || it.type || '').toString().toLowerCase()
    // 如果后端已经返回了 cells/matrix/table，就不需要额外请求
    const hasTable = Array.isArray(it.cells) || Array.isArray((it.table||{}).rows) || Array.isArray(it.matrix)
    return t === 'table' && !hasTable && getDocId(it) && getChunkId(it)
  })
  for (const it of candidates) {
    if (it._chunk) continue
    try {
      it._loadingChunk = true
      const res: any = await getDocumentChunks(getDocId(it))
      const chunks = (res?.data?.chunks) || res?.chunks || res?.data || []
      const targetId = getChunkId(it)
      const found = Array.isArray(chunks) ? chunks.find((c: any) => (c.id || c.chunk_id) === targetId) : null
      if (found) {
        // 继续拉取块详情，拿到 cells/rows/content
        try {
          const detailRes: any = await getChunkDetail(getDocId(it), targetId)
          const detail = detailRes?.data?.chunk || detailRes?.data || detailRes
          // 可能 metadata 为字符串，尝试解析
          if (detail && typeof detail.metadata === 'string') {
            try { detail.metadata = JSON.parse(detail.metadata) } catch {}
          }
          it._chunk = detail || found
        } catch {
          it._chunk = found
        }
      }
    } catch (e) {
      // 忽略单条失败
    } finally {
      it._loadingChunk = false
    }
  }
}

// 解析表格矩阵
const getTableMatrix = (item: any): string[][] => {
  // 优先使用后端直接返回的 cells/matrix/table
  if (Array.isArray(item?.cells)) return item.cells
  if (Array.isArray(item?.matrix)) return item.matrix
  if (item?.table && (Array.isArray(item.table.headers) || Array.isArray(item.table.rows))) {
    const headers = item.table.headers || []
    const rows = item.table.rows || []
    return [headers, ...rows]
  }

  const ch = item?._chunk
  let meta = ch?.meta || ch?.metadata || {}
  if (typeof meta === 'string') {
    try { meta = JSON.parse(meta) } catch {}
  }
  let matrix: any = meta?.cells || meta?.table || meta?.matrix
  if (!matrix && (meta?.headers || meta?.rows)) {
    const headers = meta?.headers || []
    const rows = meta?.rows || []
    matrix = [headers, ...rows]
  }
  if (Array.isArray(matrix)) return matrix as string[][]

  // 尝试从 content 粗糙解析 markdown/管道表
  const content = ch?.content || item?.content || ''
  const lines = content.split(/\n+/).filter((l: string) => l.includes('|'))
  if (lines.length) {
    const rows = lines.map((l: string) => l.split('|').map((s: string) => s.trim()).filter(Boolean))
    return rows
  }
  // 再兜底：若 chunk_type=table 但无 cells/管道表，尝试以“字段：值”对渲染两列
  const ct = (item?.chunk_type || '').toString().toLowerCase()
  if (ct === 'table' && content) {
    const rows = content.split(/\n+/).map((l: string) => {
      const parts = l.split(/[:：]/)
      if (parts.length >= 2) return [parts[0].trim(), parts.slice(1).join(':').trim()]
      return [l.trim()]
    }).filter((r: string[]) => r.some(Boolean))
    if (rows.length) {
      const maxCols = Math.max(...rows.map(r => r.length))
      const header = Array.from({ length: maxCols }, (_, i) => i === 0 ? '字段' : (i === 1 ? '值' : `列${i+1}`))
      return [header, ...rows]
    }
  }
  return []
}

const getTableCols = (item: any): string[] => {
  const m = getTableMatrix(item)
  if (m.length > 0) return m[0]
  return []
}

const getTableRows = (item: any) => {
  const m = getTableMatrix(item)
  const body = m.length > 1 ? m.slice(1) : m
  return body.map((row: string[]) => {
    const obj: any = {}
    row.forEach((v: string, i: number) => (obj['c' + i] = v))
    return obj
  })
}
const imageTotal = ref(0)
// 高级搜索表单
const advForm = reactive({
  bool_query: '',
  exact_phrase: '',
  wildcard: '',
  regex: ''
})

// 图片搜索相关
const imageSearchText = ref('')
const imageSearchSimilarityThreshold = ref(0.3)  // 图片搜索的相似度阈值

// 搜索历史
const searchHistory = ref<any[]>([])
const showHistory = ref(false)

// 加载搜索历史
const loadSearchHistory = async () => {
  try {
    const res = await getSearchHistory({ limit: 10 })
    const data = res?.data || res
    // 后端返回格式: { code: 0, data: { list: [], total: 0 } }
    if (data && typeof data === 'object') {
      if (data.list) {
        searchHistory.value = data.list
      } else if (data.items) {
        searchHistory.value = data.items
      } else if (Array.isArray(data)) {
        searchHistory.value = data
      } else {
        searchHistory.value = []
      }
    } else {
      searchHistory.value = []
    }
  } catch (error) {
    // 忽略错误
    searchHistory.value = []
  }
}

// 点击历史记录
const handleHistoryClick = (item: any) => {
  searchForm.query = item.query_text
  if (item.search_type) {
    searchForm.search_type = item.search_type
  }
  showHistory.value = false
  handleSearch()
}

// 删除单条历史
const handleDeleteHistory = async (historyId: number) => {
  try {
    await deleteSearchHistory(historyId)
    await loadSearchHistory()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

// 清空历史
const handleClearHistory = async () => {
  try {
    await ElMessageBox.confirm('确定要清空所有搜索历史吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await clearSearchHistory()
    searchHistory.value = []
    ElMessage.success('已清空')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清空失败')
    }
  }
}

// 格式化时间
const formatTime = (time: string) => {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString()
}
const uploadedImage = ref<File | null>(null)
const uploadedImageUrl = ref<string>('')
const imageSearching = ref(false)  // 图片搜索加载状态
const imageDetailVisible = ref(false)  // 图片详情对话框显示状态
const selectedImage = ref<any>(null)  // 选中的图片
const contextVisible = ref(false)
const contextData = ref<any>(null)
const imageAssocMinConf = ref(0.5) // 图片关联置信度阈值（获取上下文时使用）

type ContextSegment =
  | { kind: 'text'; content: string }
  | { kind: 'image'; imageIndex: number; src: string; description?: string; raw: any }

const resolveContextImageUrl = (img: any): string => {
  const candidate = img?.image_url || img?.image_path || img?.url
  if (!candidate) return ''
  if (typeof candidate === 'string') {
    if (/^https?:\/\//.test(candidate)) return candidate
    if (candidate.startsWith('/api/images/file')) return candidate
    const normalized = candidate.replace(/^\/+/, '')
    return `/api/images/file?object=${encodeURIComponent(normalized)}`
  }
  return ''
}

const contextSegments = computed<ContextSegment[]>(() => {
  const mergedText: string = contextData.value?.display?.merged_text ?? ''
  const images: any[] = contextData.value?.context?.images ?? []
  if (!mergedText) return []

  const tokens = mergedText.split('[图片]')
  const segments: ContextSegment[] = []
  let imageCursor = 0

  tokens.forEach((text, idx) => {
    if (text) {
      segments.push({ kind: 'text', content: text })
    }
    if (idx < tokens.length - 1) {
      const image = images[imageCursor]
      if (image) {
        segments.push({
          kind: 'image',
          imageIndex: imageCursor,
          src: resolveContextImageUrl(image),
          description: image.description || '',
          raw: image
        })
      } else {
        segments.push({ kind: 'text', content: '[图片]' })
      }
      imageCursor += 1
    }
  })

  return segments
})

const remainingContextImages = computed<any[]>(() => {
  const images: any[] = contextData.value?.context?.images ?? []
  if (!images.length) return []

  const usedIndices = new Set<number>()
  contextSegments.value.forEach((segment) => {
    if (segment.kind === 'image') {
      usedIndices.add(segment.imageIndex)
    }
  })

  return images
    .map((img: any, index: number) => ({
      ...img,
      index,
      src: resolveContextImageUrl(img)
    }))
    .filter((img) => !usedIndices.has(img.index))
})

const handleContextImageClick = (img: any) => {
  if (!img) return
  const fallbackSrc = resolveContextImageUrl(img)
  const normalized = {
    ...img,
    image_path: img.image_path || fallbackSrc,
    image_url: img.image_url || fallbackSrc
  }
  viewImage(normalized)
}

const handleSearch = async () => {
  if (!searchForm.knowledge_base_id || searchForm.knowledge_base_id.length === 0) {
    ElMessage.warning('请先选择至少一个知识库')
    return
  }
  if (!searchForm.query.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  searching.value = true
  textSearched.value = true
  try {
    
    // 是否启用高级搜索
    const hasAdvanced = (searchForm.search_type === 'exact') && (useAdvanced.value || advForm.bool_query || advForm.exact_phrase || advForm.wildcard || advForm.regex)

    let res: any
    if (hasAdvanced) {
      const advParams = {
        query: searchForm.query,
        bool_query: advForm.bool_query || undefined,
        exact_phrase: advForm.exact_phrase || undefined,
        wildcard: advForm.wildcard || undefined,
        regex: advForm.regex || undefined,
        knowledge_base_id: searchForm.knowledge_base_id,
        filters: searchForm.category_id ? { category_id: searchForm.category_id } : undefined,
        limit: size.value,
        offset: (page.value - 1) * size.value
      }
      res = await advancedSearch(advParams as any)
    } else {
      // 转换参数：page/size -> limit/offset
      const params: any = {
        query: searchForm.query,
        search_type: searchForm.search_type,
        knowledge_base_id: searchForm.knowledge_base_id,
        category_id: searchForm.category_id,
        limit: size.value,
        offset: (page.value - 1) * size.value
      }
      // 只在使用Rerank的搜索类型中传递这些参数
      if (searchForm.search_type === 'vector' || searchForm.search_type === 'hybrid') {
        params.similarity_threshold = searchForm.similarity_threshold
      }
      if (searchForm.search_type !== 'exact') {
        // 精确匹配不使用Rerank，所以不传递min_rerank_score
        params.min_rerank_score = minDisplayScore.value
      }
      res = await search(params)
    }
    const envelope: any = (res && (res as any).data !== undefined) ? (res as any).data : res
    const payload: any = envelope?.data ?? envelope
    const list: any[] = Array.isArray(payload)
      ? payload
      : (payload?.items || payload?.results || payload?.list || [])
    
    
    textResults.value = list
    // 预加载表格类 chunk 元数据
    preloadTableChunks()
    // total使用过滤后的实际数量（前端还会按minDisplayScore过滤一次）
    textTotal.value = list.length
    // 搜索成功后隐藏搜索历史并刷新历史记录
    showHistory.value = false
    await loadSearchHistory()
  } catch (error: any) {
    const message = error?.response?.data?.detail || error?.message || '搜索失败'
    ElMessage.error(message)
  } finally {
    searching.value = false
  }
}

// 图片上传
const handleImageUpload = (uploadFile: any) => {
  // el-upload 的 change 事件返回的是对象，包含 raw 或 file 属性
  // 如果之前有图片，先释放对象URL（避免内存泄漏）
  if (uploadedImageUrl.value) {
    URL.revokeObjectURL(uploadedImageUrl.value)
    uploadedImageUrl.value = ''
  }
  
  // 提取 File 对象
  const file = uploadFile?.raw || uploadFile?.file || uploadFile
  if (file instanceof File) {
    // 验证文件类型
    if (!file.type.startsWith('image/')) {
      ElMessage.error('请上传图片文件')
      return
    }
    
    // 验证文件大小（限制10MB）
    if (file.size > 10 * 1024 * 1024) {
      ElMessage.error('图片大小不能超过10MB')
      return
    }
    
    uploadedImage.value = file
    uploadedImageUrl.value = URL.createObjectURL(file)
  } else {
    ElMessage.error('文件格式不正确')
  }
}

// 以图搜图
const handleSearchByImage = async () => {
  if (!searchForm.knowledge_base_id) {
    ElMessage.warning('请先选择知识库')
    return
  }
  if (!uploadedImage.value) {
    ElMessage.warning('请先选择图片')
    return
  }

  imageSearching.value = true
  imageSearched.value = true
  try {
    const res = await searchByImage(uploadedImage.value, {
      similarity_threshold: imageSearchSimilarityThreshold.value,
      limit: 20,
      knowledge_base_id: searchForm.knowledge_base_id
    })
    const envelope: any = (res && (res as any).data !== undefined) ? (res as any).data : res
    const payload: any = envelope?.data ?? envelope
    const list: any[] = Array.isArray(payload) ? payload : (payload?.items || payload?.results || payload?.list || [])
    
    // 处理图片路径：确保使用代理 URL
    const processedList = list.map((img: any) => {
      if (img.image_path && !img.image_path.startsWith('/api/images/file') && !img.image_path.startsWith('http')) {
        const enc = encodeURIComponent(img.image_path)
        img.image_path = `/api/images/file?object=${enc}`
      }
      return img
    })
    
    imageResults.value = processedList
    imageTotal.value = processedList.length
  } catch (error: any) {
    const message = error?.response?.data?.detail || error?.message || '图片搜索失败'
    ElMessage.error(message)
  } finally {
    imageSearching.value = false
  }
}

// 以文搜图
const handleSearchByText = async () => {
  if (!searchForm.knowledge_base_id || searchForm.knowledge_base_id.length === 0) {
    ElMessage.warning('请先选择至少一个知识库')
    return
  }
  if (!imageSearchText.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  imageSearching.value = true
  imageSearched.value = true
  try {
    const res = await searchByTextForImages({
      query_text: imageSearchText.value,
      similarity_threshold: imageSearchSimilarityThreshold.value,
      limit: 20,
      knowledge_base_id: searchForm.knowledge_base_id
    })
    const envelope: any = (res && (res as any).data !== undefined) ? (res as any).data : res
    const payload: any = envelope?.data ?? envelope
    const list: any[] = Array.isArray(payload) ? payload : (payload?.items || payload?.results || payload?.list || [])
    
    // 处理图片路径：确保使用代理 URL
    const processedList = list.map((img: any) => {
      if (img.image_path && !img.image_path.startsWith('/api/images/file') && !img.image_path.startsWith('http')) {
        const enc = encodeURIComponent(img.image_path)
        img.image_path = `/api/images/file?object=${enc}`
      }
      return img
    })
    
    imageResults.value = processedList
    imageTotal.value = processedList.length
  } catch (error: any) {
    const message = error?.response?.data?.detail || error?.message || '图片搜索失败'
    ElMessage.error(message)
  } finally {
    imageSearching.value = false
  }
}

const handleItemClick = (item: any) => {
  // 优先展示上下文（如果有 chunk_id + document_id）
  const docId = item.document_id
  const chunkId = item.chunk_id
  if (docId && chunkId) {
    getChunkContext(docId, chunkId, { neighbor_pre: 2, neighbor_next: 2 }).then((res:any) => {
      contextData.value = res?.data?.data || res?.data || res
      contextVisible.value = true
    }).catch(() => {
      window.open(`/documents/${docId}`, '_blank')
    })
  } else if (docId) {
    window.open(`/documents/${docId}`, '_blank')
  }
}

const viewImage = async (image: any) => {
  try {
    // 如果有 image_id，加载完整图片详情
    if (image.image_id) {
      const detailRes = await getImageDetail(image.image_id)
      const detail = detailRes?.data || detailRes || image
      // 确保 image_path 可直接访问
      if (detail && typeof detail.image_path === 'string' && !/^https?:\/\//.test(detail.image_path)) {
        const enc = encodeURIComponent(detail.image_path)
        detail.image_path = `/api/images/file?object=${enc}`
      }
      selectedImage.value = detail
      // 拉取图片上下文
      if (detail.document_id && (detail.image_id || detail.id)) {
        try {
          const ctxRes:any = await getImageContext(
            detail.document_id,
            detail.image_id || detail.id,
            { neighbor_pre: 2, neighbor_next: 2, min_confidence: imageAssocMinConf.value }
          )
          selectedImage.value._context = ctxRes?.data?.data || ctxRes?.data || ctxRes
        } catch {}
      }
    } else {
      // 如果没有 image_id，使用搜索结果中的基本信息
      selectedImage.value = image
    }
    imageDetailVisible.value = true
  } catch (error: any) {
    // 如果加载详情失败，使用列表中的基本信息
    selectedImage.value = image
    imageDetailVisible.value = true
  }
}

const viewDocument = (documentId: number) => {
  window.open(`/documents/${documentId}`, '_blank')
}

// 加载知识库列表
;(async () => {
  try {
    const res = await getKnowledgeBases({ page: 1, size: 100 })
    const data = res?.data ?? {}
    knowledgeBases.value = data.list ?? data.items ?? []
  } catch (error) {
    // 加载知识库列表失败
  }
})()

// 页面加载时自动加载搜索历史
onMounted(async () => {
  await loadSearchHistory()
  // 如果有搜索历史且当前没有搜索结果，默认显示
  if (searchHistory.value.length > 0) {
    showHistory.value = true
  }
})

// 当搜索类型改变时，清空结果并关闭高级搜索
watch(() => searchForm.search_type, (val, oldVal) => {
  // 如果切换了检索方式（不是首次初始化），清空搜索结果
  if (oldVal !== undefined && oldVal !== val) {
    textResults.value = []
    textTotal.value = 0
    page.value = 1
    textSearched.value = false
  }
  // 当搜索类型不是精确匹配时，自动关闭并隐藏高级搜索
  if (val !== 'exact') {
    useAdvanced.value = false
    showAdvanced.value = false
  }
})

// 当图片搜索类型改变时（以图搜图/以文搜图），清空图片搜索结果
watch(() => imageSearchType.value, (val, oldVal) => {
  // 如果切换了图片搜索方式（不是首次初始化），清空图片搜索结果
  if (oldVal !== undefined && oldVal !== val) {
    imageResults.value = []
    imageTotal.value = 0
    // 同时清空上传的图片和文本输入
    if (val === 'by-text') {
      // 先释放图片 URL 内存
      if (uploadedImageUrl.value) {
        URL.revokeObjectURL(uploadedImageUrl.value)
      }
      uploadedImage.value = null
      uploadedImageUrl.value = ''
    } else if (val === 'by-image') {
      imageSearchText.value = ''
    }
    imageSearched.value = false
  }
})
</script>

<style lang="scss" scoped>
.search-page {
  min-height: calc(100vh - 120px);
  padding: 24px;
  background: radial-gradient(1200px 600px at 20% 0%, rgba(32, 160, 255, 0.08), transparent 60%),
              radial-gradient(1000px 500px at 90% 10%, rgba(99, 102, 241, 0.08), transparent 60%),
              linear-gradient(180deg, #0f172a 0%, #0b1020 100%);
  color: #e5eaf0;

  .neo-card {
    max-width: 1200px;
    margin: 0 auto;
    background: rgba(17, 25, 40, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.12);
    box-shadow: 0 10px 30px rgba(2, 6, 23, 0.6), inset 0 1px 0 rgba(255,255,255,0.03);
    backdrop-filter: blur(10px);
    border-radius: 14px;
  }

  // 搜索布局：左右分栏
  .search-layout {
    display: flex;
    gap: 20px;
    align-items: flex-start;
  }

  .search-form-wrapper {
    flex: 1;
    min-width: 0;
  }

  .search-form {
    .el-input__wrapper {
      background: rgba(15, 23, 42, 0.7);
      box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.25);
    }
  }

  .advanced-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 4px 0 8px;
  }
  .advanced-panel {
    background: rgba(99, 102, 241, 0.08);
    padding: 12px;
    border-radius: 8px;
    border: 1px solid rgba(148, 163, 184, 0.12);
  }
  .search-mode-tabs {
    margin-bottom: 20px;
    --el-color-primary: #60a5fa;
    
    /* 提升 Tab 可读性 */
    :deep(.el-tabs__item) {
      color: #cbd5e1;
      font-weight: 700;
      letter-spacing: 0.3px;
      font-size: 16px; /* 一级标签字号 */
      padding: 0 16px;
    }
    :deep(.el-tabs__item.is-active) {
      color: #ffffff;
      background: linear-gradient(180deg, rgba(96,165,250,0.28), rgba(96,165,250,0.12));
      border-radius: 10px 10px 0 0;
    }
    :deep(.el-tabs__active-bar) {
      background-color: #76b5ff;
      height: 4px;
      border-radius: 4px;
    }
    :deep(.el-tabs__nav-wrap::after){
      height: 2px;
      background-color: rgba(118,181,255,.35); /* 一级与面板分隔更明显 */
    }
  }

  /* 二级标签（图片搜索内的切换）视觉区分 */
  .sub-tabs{
    margin-bottom: 16px;
    --el-color-primary: #34d399; /* 青色系与一级形成对比 */
    :deep(.el-tabs__item){
      color:#cfe9df;
      font-weight:600;
      font-size:14px; /* 二级稍小 */
      padding: 0 12px;
    }
    :deep(.el-tabs__item.is-active){
      color:#10231c;
      background: linear-gradient(180deg, rgba(52,211,153,0.35), rgba(52,211,153,0.16));
      border-radius: 10px 10px 0 0;
    }
    :deep(.el-tabs__active-bar){
      background-color:#34d399;
      height:3px;
      border-radius: 3px;
    }
    :deep(.el-tabs__nav-wrap::after){
      height: 1px;
      background-color: rgba(52,211,153,.35);
    }
  }

  .search-tip {
    margin-top: 8px;
    color: #a7b0c0;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  /* 图片搜索 - 科技感布局 */
  .vision-panel{display:flex;gap:20px;align-items:stretch}
  .vision-panel.single{display:block}
  .panel-left,.panel-right{flex:1}
  .upload-dropzone{width:100%; padding:28px; border:1px dashed rgba(120,145,255,.45); background:linear-gradient(180deg,rgba(20,24,38,.45),rgba(20,24,38,.25)); backdrop-filter:blur(6px); border-radius:14px; text-align:center}
  .upload-icon{font-size:32px;color:#8ea2ff;margin-bottom:8px}
  .sub-hint{color:#98a2b3;font-size:12px;margin-top:6px}
  .controls-card{margin-top:16px;padding:16px;border-radius:12px;background:rgba(20,24,38,.55);border:1px solid rgba(120,145,255,.2)}
  .control-row{display:flex;align-items:center;gap:12px}
  .control-label{color:#cfd8e6;font-size:14px;white-space:nowrap}
  .actions{display:flex;align-items:center;gap:12px;margin-top:12px}
  .tiny-hint{color:#9aa6bf;font-size:12px}
  .preview-card{padding:14px;border-radius:12px;background:rgba(20,24,38,.55);border:1px solid rgba(120,145,255,.2); display:flex;gap:14px;align-items:flex-start}
  .preview-card img{width:180px;height:120px;object-fit:cover;border-radius:10px;border:1px solid rgba(255,255,255,.08)}
  .preview-meta{display:flex;flex-direction:column;gap:6px}
  .meta-title{color:#e6ecff;font-weight:600}
  .meta-desc{color:#9aa6bf;font-size:12px}
  .empty-card{height:154px;display:flex;align-items:center;justify-content:center;border-radius:12px;color:#9aa6bf;background:rgba(20,24,38,.35);border:1px dashed rgba(120,145,255,.2)}

  .query-card{padding:18px;border-radius:14px;background:rgba(20,24,38,.55);border:1px solid rgba(120,145,255,.2)}
  .query-title{color:#e6ecff;font-weight:600;margin-bottom:8px}
  .query-sub{display:flex;align-items:center;gap:6px;color:#9aa6bf;font-size:12px;margin-top:8px}

  @media (max-width: 992px){
    .vision-panel{flex-direction:column}
    .preview-card img{width:100%;height:auto}
  }

  /* 独立信息条，避免与控件混排 */
  .info-banner {
    margin: 8px 0 12px;
    padding: 8px 12px;
    background: rgba(99, 102, 241, 0.10);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 8px;
    color: #d7dee8;
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
  }

  /* 单选组与标签：加大字号、提升对比度 */
  :deep(.el-radio) {
    margin-right: 18px;
  }
  :deep(.el-radio__label) {
    color: #dde6f3; /* 提升灰字对比度 */
    font-size: 14px; /* 放大单选文字 */
    font-weight: 500;
  }
  :deep(.el-radio.is-checked .el-radio__label) {
    color: #f3f6fb;
  }

  .neighbors {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }

  .context-merged {
    line-height: 1.6;
    border: 1px solid rgba(148, 163, 184, 0.16);
    padding: 12px;
    border-radius: 6px;
    background: rgba(15, 23, 42, 0.5);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .context-text {
    white-space: pre-wrap;
    color: #dce4f5;
    font-size: 14px;
  }

  .context-inline-image {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .context-inline-image img {
    max-width: 100%;
    border-radius: 10px;
    border: 1px solid rgba(148, 163, 184, 0.22);
    box-shadow: 0 8px 20px rgba(2, 6, 23, 0.45);
    cursor: pointer;
    background: #0f172a;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }

  .context-inline-image img:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 26px rgba(2, 6, 23, 0.55);
  }

  .context-inline-caption {
    font-size: 12px;
    color: #9aa6bf;
  }

  .context-images {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 12px;
  }

  .context-image-card {
    width: 160px;
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 10px;
    overflow: hidden;
    background: rgba(15, 23, 42, 0.6);
    box-shadow: 0 8px 20px rgba(2, 6, 23, 0.4);
  }

  .context-image-card img {
    width: 100%;
    height: 110px;
    object-fit: cover;
    display: block;
    background: #0f172a;
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }

  .context-image-card img:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 26px rgba(2, 6, 23, 0.55);
  }

  .context-image-desc {
    padding: 8px 10px;
    font-size: 12px;
    color: #dce4f5;
    line-height: 1.4;
  }

  .context-image-text {
    margin-top: 4px;
    color: #9aa6bf;
  }

  /* 开关的文字：提升未激活态的可读性 */
  .advanced-bar {
    :deep(.el-switch__label) {
      color: #cfd8e6; /* 灰字更亮 */
      font-size: 14px; /* 放大标签文字 */
      font-weight: 500;
    }
    :deep(.el-switch.is-checked + .el-switch__label) {
      color: #e9eef7;
    }
  }

  .image-search-box {
    padding: 20px;
    text-align: center;

    .uploaded-image-preview {
      margin-top: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;

      img {
        max-width: 300px;
        max-height: 300px;
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      }
    }
  }

  .search-results {
    margin-top: 20px;

    .results-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      font-size: 14px;
      color: #c8d1dc;
    }

    /* 表格视图模式：嵌套表格样式优化 */
    .results-list-table {
      :deep(.el-table__body-wrapper) {
        .el-table__body {
          tr {
            td {
              .el-table {
                font-size: 12px;
                .el-table__header-wrapper {
                  .el-table__header {
                    th {
                      padding: 6px 8px;
                      font-size: 12px;
                      font-weight: 600;
                      color: #e8eef7;
                      background-color: rgba(30, 41, 59, 0.8);
                    }
                  }
                }
                .el-table__body-wrapper {
                  .el-table__body {
                    tr {
                      td {
                        padding: 4px 8px;
                        font-size: 12px;
                        color: #d1d5db;
                        line-height: 1.4;
                      }
                      &:hover {
                        td {
                          background-color: rgba(60, 130, 246, 0.15) !important;
                          color: #f3f4f6 !important;
                        }
                      }
                    }
                    tr:nth-child(even) {
                      background-color: rgba(17, 25, 40, 0.3);
                    }
                    tr:nth-child(odd) {
                      background-color: rgba(30, 41, 59, 0.2);
                    }
                  }
                }
                .el-table__border {
                  border-color: rgba(148, 163, 184, 0.2);
                }
              }
            }
          }
        }
      }
    }

    .result-item {
      margin-bottom: 20px;
      cursor: pointer;
      transition: box-shadow 0.3s, transform 0.2s;
      background: rgba(17, 25, 40, 0.5);
      border: 1px solid rgba(148, 163, 184, 0.12);

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(2, 6, 23, 0.5);
      }

      .result-title {
        font-weight: 600;
        margin-bottom: 8px;
        color: #e8eef7;
      }

      .result-content-text {
        line-height: 1.6;
        word-break: break-word;
        
        // 高亮样式
        :deep(mark) {
          background-color: #ffeb3b;
          padding: 2px 4px;
          border-radius: 2px;
          font-weight: 500;
          color: #333;
        }
      }
      
      .result-content {
        color: #9aa5b1;
        margin-bottom: 8px;

        /* 表格样式优化：更紧凑、hover时清晰 */
        :deep(.el-table) {
          font-size: 12px;
          .el-table__header-wrapper {
            .el-table__header {
              th {
                padding: 6px 8px;
                font-size: 12px;
                font-weight: 600;
                color: #e8eef7;
                background-color: rgba(30, 41, 59, 0.8);
              }
            }
          }
          .el-table__body-wrapper {
            .el-table__body {
              tr {
                td {
                  padding: 4px 8px;
                  font-size: 12px;
                  color: #d1d5db;
                  line-height: 1.4;
                }
                &:hover {
                  td {
                    background-color: rgba(60, 130, 246, 0.15) !important;
                    color: #f3f4f6 !important;
                  }
                }
              }
              tr:nth-child(even) {
                background-color: rgba(17, 25, 40, 0.3);
              }
              tr:nth-child(odd) {
                background-color: rgba(30, 41, 59, 0.2);
              }
            }
          }
          .el-table__border {
            border-color: rgba(148, 163, 184, 0.2);
          }
        }
      }

      .result-meta {
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;

        .similarity {
          color: #a7b0c0;
          font-size: 12px;
        }
      }
    }

    .image-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 16px;

      .image-item {
        border: 1px solid rgba(148, 163, 184, 0.12);
        border-radius: 4px;
        overflow: hidden;
        cursor: pointer;
        transition: all 0.2s;
        background: rgba(17, 25, 40, 0.5);

        &:hover {
          transform: translateY(-4px);
          box-shadow: 0 10px 20px rgba(2, 6, 23, 0.5);
        }

        img {
          width: 100%;
          height: 200px;
          object-fit: cover;
        }

        .image-info {
          padding: 12px;

          .similarity {
            font-weight: 600;
            color: #60a5fa;
            margin-bottom: 4px;
          }

          .description {
            font-size: 12px;
            color: #9aa5b1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
        }
      }
    }
  }

  .empty-state {
    margin-top: 28px;
    :deep(.el-empty__description) { color: #cbd5e1; }
    .empty-hints { color: #9aa6bf; font-size: 12px; margin-top: 6px; text-align: center; }
  }

  // 图片详情对话框样式
  :deep(.image-detail) {
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
          color: #606266;
          line-height: 1.6;
          margin: 0;
        }

        .ocr-text {
          background: #f5f7fa;
          padding: 12px;
          border-radius: 4px;
          font-family: 'Courier New', monospace;
          font-size: 13px;
          line-height: 1.6;
          white-space: pre-wrap;
          word-break: break-word;
        }
      }
    }
  }

  /* 搜索历史左侧边栏样式 */
  .search-history-sidebar {
    width: 280px;
    flex-shrink: 0;
    background: rgba(17, 25, 40, 0.6);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(148, 163, 184, 0.15);
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(2, 6, 23, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.03);
    overflow: hidden;
    height: fit-content;
    max-height: calc(100vh - 250px);
    display: flex;
    flex-direction: column;
  }

  .history-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.15);
    background: rgba(15, 23, 42, 0.4);
  }

  .history-title {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #e5eaf0;
    font-size: 14px;
    font-weight: 600;
  }

  .history-icon {
    font-size: 16px;
    color: #60a5fa;
  }

  .clear-btn {
    color: #9aa6bf !important;
    font-size: 13px;
    padding: 4px 8px;
    border-radius: 6px;
    transition: all 0.2s ease;
  }

  .clear-btn:hover {
    color: #e5eaf0 !important;
    background: rgba(148, 163, 184, 0.1);
  }

  .history-list {
    flex: 1;
    overflow-y: auto;
    padding: 4px 0;
    min-height: 0;
  }

  .history-list::-webkit-scrollbar {
    width: 6px;
  }

  .history-list::-webkit-scrollbar-track {
    background: rgba(15, 23, 42, 0.3);
  }

  .history-list::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.3);
    border-radius: 3px;
  }

  .history-list::-webkit-scrollbar-thumb:hover {
    background: rgba(148, 163, 184, 0.5);
  }

  .history-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    cursor: pointer;
    transition: all 0.2s ease;
    border-left: 3px solid transparent;
    position: relative;
  }

  .history-item:hover {
    background: rgba(96, 165, 250, 0.08);
    border-left-color: #60a5fa;
  }

  .history-item:active {
    background: rgba(96, 165, 250, 0.12);
  }

  .history-item-icon {
    font-size: 18px;
    color: #60a5fa;
    flex-shrink: 0;
  }

  .history-content {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .history-query {
    color: #e5eaf0;
    font-size: 14px;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .history-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    color: #9aa6bf;
    font-size: 12px;
  }

  .time-icon {
    font-size: 12px;
    color: #7c8ba1;
  }

  .history-delete {
    font-size: 16px;
    color: #7c8ba1;
    padding: 4px;
    border-radius: 4px;
    transition: all 0.2s ease;
    flex-shrink: 0;
    opacity: 0;
  }

  .history-item:hover .history-delete {
    opacity: 1;
  }

  .history-delete:hover {
    color: #ef4444;
    background: rgba(239, 68, 68, 0.1);
  }
}
</style>
