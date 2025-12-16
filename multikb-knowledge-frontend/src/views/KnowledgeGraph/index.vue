<template>
  <div class="knowledge-graph-page">
    <el-card v-loading="loading || graphLoading">
      <template #header>
        <div class="card-header">
          <span>知识图谱可视化</span>
          <div class="header-actions">
            <el-select
              v-model="selectedKnowledgeBase"
              placeholder="选择知识库"
              style="width: 200px; margin-right: 10px"
              @change="handleKnowledgeBaseSelectChange"
            >
              <el-option
                v-for="kb in knowledgeBases"
                :key="kb.id"
                :label="kb.name"
                :value="kb.id"
              />
            </el-select>
            <el-dropdown v-if="selectedKnowledgeBase" @command="handleTaskCommand" style="margin-right: 10px">
              <el-button>
                任务列表<el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="view-tasks">查看任务列表</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button @click="loadGraphData" :loading="loading">刷新</el-button>
            <el-button @click="showExtractDialog = true">提取实体</el-button>
          </div>
        </div>
      </template>

      <div v-if="!selectedKnowledgeBase" class="empty-state">
        <el-empty description="请选择一个知识库" />
      </div>

      <div v-else class="graph-container">
        <!-- 工具栏 -->
        <div class="toolbar">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索实体..."
            style="width: 200px; margin-right: 10px"
            clearable
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
            <el-select
              v-model="selectedEntityType"
              placeholder="选择实体类型"
              clearable
              style="width: 250px; margin-right: 10px"
              @change="loadGraphData"
            >
              <el-option label="全部" value="" />
              <!-- 调试信息：显示实体类型数量 -->
              <!-- <el-option disabled>调试: 共{{ entityTypes.length }}个类型</el-option> -->
              <!-- 调试：显示实体类型总数 -->
              <el-option disabled v-if="entityTypes.length === 0">暂无实体类型 (调试: 共0个)</el-option>
              <!-- 按层级分组显示实体类型 -->
              <template v-if="entityTypes.length > 0">
                <el-option-group
                  v-for="level in [1, 2, 3]"
                  :key="level"
                  :label="`${level}级分类 (${entityTypes.filter(t => t && t.level === level).length})`"
                >
                  <el-option
                    v-for="type in entityTypes.filter(t => t && t.level === level)"
                    :key="type.code || type.id"
                    :label="getTypeDisplayName(type)"
                    :value="type.code"
                  >
                    <span>{{ getTypeDisplayName(type) }}</span>
                    <span v-if="type.is_system" style="color: #909399; font-size: 11px; margin-left: 5px">(系统)</span>
                  </el-option>
                </el-option-group>
                <!-- 如果实体类型没有level或level不在1-3范围内，显示在"其他"分组中 -->
                <el-option-group
                  v-if="entityTypes.filter(t => !t || !t.level || (t.level !== 1 && t.level !== 2 && t.level !== 3)).length > 0"
                  :label="`其他 (${entityTypes.filter(t => !t || !t.level || (t.level !== 1 && t.level !== 2 && t.level !== 3)).length})`"
                >
                  <el-option
                    v-for="type in entityTypes.filter(t => !t || !t.level || (t.level !== 1 && t.level !== 2 && t.level !== 3))"
                    :key="type.code || type.id"
                    :label="getTypeDisplayName(type)"
                    :value="type.code"
                  >
                    <span>{{ getTypeDisplayName(type) }}</span>
                    <span v-if="type.is_system" style="color: #909399; font-size: 11px; margin-left: 5px">(系统)</span>
                  </el-option>
                </el-option-group>
              </template>
            </el-select>
          <el-select
            v-model="selectedLayout"
            placeholder="布局"
            style="width: 120px; margin-right: 10px"
            @change="changeLayout"
          >
            <el-option label="力导向" value="force" />
            <el-option label="层次" value="hierarchical" />
            <el-option label="圆形" value="circular" />
          </el-select>
          <el-button @click="resetView">重置视图</el-button>
          <el-button @click="exportImage">导出图片</el-button>
        </div>

        <!-- 图谱可视化区域 -->
        <div ref="graphContainer" class="graph-visualization" v-loading="graphLoading">
          <!-- 空状态提示 -->
          <div v-if="!graphLoading && !hasGraphData" class="empty-graph-hint">
            <el-empty 
              :image-size="120"
            >
              <template #description>
                <div style="margin-top: 10px">
                  <p style="font-size: 16px; color: #303133">
                    {{ selectedEntityType 
                      ? `当前知识库中没有"${entityTypeMap[selectedEntityType]?.name || selectedEntityType}"类型的实体` 
                      : '当前知识库中没有实体数据' }}
                  </p>
                  <p style="color: #909399; font-size: 14px; margin-top: 8px">
                    请点击右上角的"提取实体"按钮，从文档中提取实体和关系
                  </p>
                </div>
              </template>
            </el-empty>
          </div>
        </div>

        <!-- 详情面板 -->
        <el-drawer
          v-model="detailDrawerVisible"
          :title="detailDrawerTitle"
          size="400px"
          direction="rtl"
        >
          <div v-if="selectedEntity" class="entity-detail">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="名称">{{ selectedEntity.name }}</el-descriptions-item>
              <el-descriptions-item label="类型">{{ getEntityTypeLabel(selectedEntity.type) }}</el-descriptions-item>
              <el-descriptions-item label="描述">{{ selectedEntity.description || '无' }}</el-descriptions-item>
              <el-descriptions-item label="置信度">{{ (selectedEntity.confidence * 100).toFixed(1) }}%</el-descriptions-item>
              <el-descriptions-item label="别名" v-if="selectedEntity.aliases && selectedEntity.aliases.length > 0">
                <el-tag v-for="alias in selectedEntity.aliases" :key="alias" style="margin-right: 5px">
                  {{ alias }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>

            <el-divider>相关关系</el-divider>
            <div v-if="entityRelationships.length > 0">
              <div
                v-for="rel in entityRelationships"
                :key="rel.id"
                class="relationship-item"
                @click="viewRelationship(rel)"
              >
                <div class="relationship-type">{{ getRelationTypeLabel(rel.relation_type) }}</div>
                <div class="relationship-target">
                  {{ rel.source_entity_id === selectedEntity.id ? rel.target_entity?.name : rel.source_entity?.name }}
                </div>
                <div class="relationship-weight">权重: {{ (rel.weight * 100).toFixed(1) }}%</div>
              </div>
            </div>
            <el-empty v-else description="暂无相关关系" :image-size="80" />
          </div>

          <div v-if="selectedRelationship" class="relationship-detail">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="源实体">
                {{ selectedRelationship.source_entity?.name }}
              </el-descriptions-item>
              <el-descriptions-item label="关系类型">
                {{ getRelationTypeLabel(selectedRelationship.relation_type) }}
              </el-descriptions-item>
              <el-descriptions-item label="目标实体">
                {{ selectedRelationship.target_entity?.name }}
              </el-descriptions-item>
              <el-descriptions-item label="描述">
                {{ selectedRelationship.description || '无' }}
              </el-descriptions-item>
              <el-descriptions-item label="权重">
                {{ (selectedRelationship.weight * 100).toFixed(1) }}%
                <el-tooltip content="关系权重表示关系强度，基于共现频率、语义相似度等计算" placement="top">
                  <el-icon style="margin-left: 5px; cursor: help; color: #909399"><QuestionFilled /></el-icon>
                </el-tooltip>
              </el-descriptions-item>
              <el-descriptions-item label="置信度">
                {{ (selectedRelationship.confidence * 100).toFixed(1) }}%
                <el-tooltip 
                  content="关系置信度由LLM根据文档中的证据强度评定：高置信度(>90%)用于明确的关系，低置信度(<70%)用于推测的关系" 
                  placement="top"
                >
                  <el-icon style="margin-left: 5px; cursor: help; color: #909399"><QuestionFilled /></el-icon>
                </el-tooltip>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-drawer>
      </div>
    </el-card>

    <!-- 任务列表对话框 -->
    <el-dialog v-model="showTaskListDialog" title="提取任务列表" width="900px">
      <el-table
        :data="extractionTasks"
        v-loading="tasksLoading"
        style="width: 100%"
        stripe
      >
        <el-table-column prop="id" label="任务ID" width="80" />
        <el-table-column prop="document_id" label="文档ID" width="100" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_entities" label="实体数" width="100" />
        <el-table-column prop="total_relationships" label="关系数" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="completed_at" label="完成时间" width="180">
          <template #default="{ row }">
            {{ row.completed_at ? formatDateTime(row.completed_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              type="danger"
              size="small"
              @click="handleDeleteTask(row.id)"
              :loading="deletingTaskId === row.id"
            >
              删除
            </el-button>
            <el-button
              type="primary"
              size="small"
              @click="handleRegenerateTask(row.id)"
              :loading="regeneratingTaskId === row.id"
              :disabled="!row.document_id"
            >
              重新生成
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="taskPagination.page"
        v-model:page-size="taskPagination.size"
        :total="taskPagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadExtractionTasks"
        @current-change="loadExtractionTasks"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-dialog>

    <!-- 提取实体对话框 -->
    <el-dialog v-model="showExtractDialog" title="提取实体" width="600px">
      <el-form :model="extractForm" label-width="120px">
        <el-form-item label="知识库">
          <el-select 
            v-model="extractForm.knowledge_base_id" 
            placeholder="选择知识库" 
            style="width: 100%"
            @change="handleKnowledgeBaseChange"
          >
            <el-option
              v-for="kb in knowledgeBases"
              :key="kb.id"
              :label="kb.name"
              :value="kb.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="文档范围">
          <el-radio-group v-model="extractForm.scope">
            <el-radio label="all">全部文档</el-radio>
            <el-radio label="selected">指定文档</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="extractForm.scope === 'selected'" label="选择文档">
          <el-select
            v-model="extractForm.document_ids"
            placeholder="请选择要提取的文档"
            multiple
            filterable
            style="width: 100%"
            :loading="documentsLoading"
            :disabled="!extractForm.knowledge_base_id"
          >
            <el-option
              v-for="doc in availableDocuments"
              :key="doc.id"
              :label="doc.title || doc.file_name"
              :value="doc.id"
            >
              <span>{{ doc.title || doc.file_name }}</span>
              <span style="color: #909399; font-size: 12px; margin-left: 8px">
                ({{ doc.file_type || '未知类型' }})
              </span>
            </el-option>
          </el-select>
          <div v-if="extractForm.scope === 'selected' && !extractForm.knowledge_base_id" style="color: #909399; font-size: 12px; margin-top: 4px">
            请先选择知识库
          </div>
          <div v-if="extractForm.scope === 'selected' && extractForm.knowledge_base_id && availableDocuments.length === 0 && !documentsLoading" style="color: #909399; font-size: 12px; margin-top: 4px">
            该知识库暂无文档
          </div>
        </el-form-item>
        <el-form-item label="实体类型模式">
          <el-select 
            v-model="extractForm.entity_type_mode" 
            placeholder="选择实体类型提取模式" 
            style="width: 100%"
            @change="handleEntityTypeModeChange"
          >
            <el-option label="系统默认类型" value="system">
              <div>
                <div style="font-weight: 500">系统默认类型</div>
                <div style="color: #909399; font-size: 12px; margin-top: 4px">
                  仅使用系统预定义的实体类型（如：人物、地点、概念等）
                </div>
              </div>
            </el-option>
            <el-option label="用户创建类型" value="user">
              <div>
                <div style="font-weight: 500">用户创建类型</div>
                <div style="color: #909399; font-size: 12px; margin-top: 4px">
                  仅使用您自定义创建的实体类型（一级、二级、三级分类）
                </div>
              </div>
            </el-option>
            <el-option label="模型自由提取" value="model">
              <div>
                <div style="font-weight: 500">模型自由提取</div>
                <div style="color: #909399; font-size: 12px; margin-top: 4px">
                  不限制类型，让AI模型根据文档内容自由提取最合适的类型
                </div>
              </div>
            </el-option>
          </el-select>
          <div style="color: #909399; font-size: 12px; margin-top: 4px">
            <el-icon style="vertical-align: middle; margin-right: 4px"><QuestionFilled /></el-icon>
            选择不同的提取模式会影响实体类型的来源和范围
          </div>
        </el-form-item>
        <el-form-item 
          v-if="extractForm.entity_type_mode !== 'model'" 
          label="选择实体类型"
          :rules="[{ required: extractForm.entity_type_mode !== 'model', message: '请至少选择一个实体类型', trigger: 'change' }]"
        >
          <el-select
            v-model="extractForm.entity_type_codes"
            placeholder="请选择要提取的实体类型（必选）"
            multiple
            filterable
            style="width: 100%"
            :loading="extractEntityTypesLoading"
            :disabled="!extractForm.knowledge_base_id || extractForm.entity_type_mode === 'model'"
          >
            <el-option
              v-for="type in extractEntityTypes"
              :key="type.code"
              :label="type.name"
              :value="type.code"
            >
              <span>{{ type.name }}</span>
              <span v-if="type.code" style="color: #909399; font-size: 12px; margin-left: 8px">
                ({{ type.code }})
              </span>
            </el-option>
          </el-select>
          <div v-if="!extractForm.knowledge_base_id" style="color: #909399; font-size: 12px; margin-top: 4px">
            请先选择知识库
          </div>
          <div v-if="extractForm.knowledge_base_id && extractEntityTypes.length === 0 && !extractEntityTypesLoading" style="color: #909399; font-size: 12px; margin-top: 4px">
            该模式下暂无可用实体类型
          </div>
          <div style="color: #909399; font-size: 12px; margin-top: 4px">
            <el-icon style="vertical-align: middle; margin-right: 4px"><QuestionFilled /></el-icon>
            必须至少选择一个实体类型，系统将只提取选中类型的实体
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button 
          plain
          @click="showExtractDialog = false"
          style="color: #606266; border-color: #dcdfe6;"
        >
          取消
        </el-button>
        <el-button 
          type="primary" 
          @click="handleExtract" 
          :loading="extracting"
          :disabled="extractForm.scope === 'selected' && (!extractForm.document_ids || extractForm.document_ids.length === 0)"
        >
          开始提取
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, ArrowDown, QuestionFilled } from '@element-plus/icons-vue'
import { getKnowledgeBases } from '@/api/modules/knowledge-bases'
import { getDocuments } from '@/api/modules/documents'
import {
  getVisualizationData,
  getEntityDetail,
  extractEntities,
  searchEntities,
  getEntityTypes,
  listExtractionTasks,
  deleteExtractionTask,
  regenerateExtractionTask,
  type KnowledgeGraphEntity,
  type KnowledgeGraphRelationship,
  type EntityType,
  type ExtractionTask
} from '@/api/modules/knowledge-graph'
import type { KnowledgeBase, Document } from '@/types'

// 使用ECharts Graph进行可视化（因为项目已有echarts依赖）
import * as echarts from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { LabelLayout } from 'echarts/features'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent
} from 'echarts/components'

echarts.use([
  GraphChart,
  CanvasRenderer,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  LabelLayout // 启用LabelLayout功能，确保标签正确跟随节点
])

const loading = ref(false)
const graphLoading = ref(false)
const knowledgeBases = ref<KnowledgeBase[]>([])
const selectedKnowledgeBase = ref<number>()
const entityTypes = ref<EntityType[]>([])
const entityTypeMap = ref<Record<string, EntityType>>({})
const searchKeyword = ref('')
const selectedEntityType = ref('')
const selectedLayout = ref('force')
const graphContainer = ref<HTMLElement>()
let graphChart: echarts.ECharts | null = null

const detailDrawerVisible = ref(false)
const detailDrawerTitle = ref('')
const selectedEntity = ref<KnowledgeGraphEntity | null>(null)
const selectedRelationship = ref<KnowledgeGraphRelationship | null>(null)
const entityRelationships = ref<KnowledgeGraphRelationship[]>([])
const hasGraphData = ref(false)  // 是否有图谱数据

const showExtractDialog = ref(false)
const extractForm = ref({
  knowledge_base_id: undefined as number | undefined,
  scope: 'all' as 'all' | 'selected',
  document_ids: [] as number[],
  entity_type_mode: 'system' as 'system' | 'user' | 'model',
  entity_type_codes: [] as string[]  // 选中的实体类型代码列表
})
const extracting = ref(false)
const availableDocuments = ref<Document[]>([])
const documentsLoading = ref(false)
const extractEntityTypes = ref<EntityType[]>([])  // 提取对话框中的实体类型列表
const extractEntityTypesLoading = ref(false)

// 任务列表相关
const showTaskListDialog = ref(false)
const extractionTasks = ref<ExtractionTask[]>([])
const tasksLoading = ref(false)
const taskPagination = ref({
  page: 1,
  size: 20,
  total: 0
})
const deletingTaskId = ref<number | null>(null)
const regeneratingTaskId = ref<number | null>(null)

// 加载实体类型列表
const loadEntityTypes = async () => {
  console.log('[实体类型] 开始加载实体类型...')
  try {
    // 先尝试不限制 is_enabled，获取所有类型（包括未启用的）
    // 如果数据库中没有启用的类型，至少可以显示所有类型
    let params: any = { size: 1000 } // 增加size以获取所有类型
    
    // 如果选择了知识库，加载该知识库的实体类型；否则加载所有类型
    if (selectedKnowledgeBase.value) {
      params.knowledge_base_id = selectedKnowledgeBase.value
      console.log('[实体类型] 加载知识库ID:', selectedKnowledgeBase.value, '的实体类型')
      // 对于知识库，不限制 is_enabled，因为知识库配置的类型可能未启用
    } else {
      console.log('[实体类型] 加载所有实体类型（不限制启用状态）')
      // 不设置 is_enabled，让后端返回所有类型
      // 如果还是没有数据，尝试只获取启用的类型
      params.is_enabled = true
    }
    console.log('[实体类型] 请求参数:', params)
    const res = await getEntityTypes(params)
    console.log('[实体类型] API调用成功，开始解析响应...')
    
    // 详细调试：打印完整响应结构
    console.log('[实体类型] 完整响应:', res)
    console.log('[实体类型] res.data:', res.data)
    console.log('[实体类型] res.data类型:', typeof res.data)
    console.log('[实体类型] res.data是否为数组:', Array.isArray(res.data))
    
    // 兼容不同的响应格式
    // 后端可能返回: { success: true, message: "...", data: { list: [...], items: [...] } }
    // 或者: { code: 200, message: "...", data: { list: [...], items: [...] } }
    let rawData: any[] = []
    
    // 首先尝试从 res.data 获取（标准格式）
    if (res && res.data) {
      // 如果 data 本身就是数组（直接返回数组的情况）
      if (Array.isArray(res.data)) {
        rawData = res.data
        console.log('[实体类型] data是数组，直接使用，数量:', rawData.length)
      } 
      // 如果 data 是对象，尝试从 list、items、types 中获取
      else if (typeof res.data === 'object' && res.data !== null) {
        rawData = res.data.items || res.data.list || res.data.types || []
        console.log('[实体类型] 从data对象中提取:', {
          hasItems: !!res.data.items,
          hasList: !!res.data.list,
          hasTypes: !!res.data.types,
          itemsLength: res.data.items?.length || 0,
          listLength: res.data.list?.length || 0,
          typesLength: res.data.types?.length || 0,
          extractedLength: rawData.length
        })
        
        // 如果提取到了数据，打印第一条数据示例
        if (rawData.length > 0) {
          console.log('[实体类型] 第一条数据示例:', rawData[0])
        }
      }
    }
    
    // 如果还是空，尝试从响应根级别获取（兼容其他可能的格式）
    if (rawData.length === 0) {
      if (Array.isArray(res)) {
        rawData = res
        console.log('[实体类型] res本身是数组，数量:', rawData.length)
      } else if (res.items && Array.isArray(res.items)) {
        rawData = res.items
        console.log('[实体类型] 从res.items获取，数量:', rawData.length)
      } else if (res.list && Array.isArray(res.list)) {
        rawData = res.list
        console.log('[实体类型] 从res.list获取，数量:', rawData.length)
      } else if (res.types && Array.isArray(res.types)) {
        rawData = res.types
        console.log('[实体类型] 从res.types获取，数量:', rawData.length)
      }
    }
    
    // 如果仍然为空，打印完整的响应结构用于调试
    if (rawData.length === 0) {
      console.warn('[实体类型] 无法从响应中提取数据，完整响应结构:', JSON.stringify(res, null, 2))
      
      // 如果指定了知识库但没有数据，尝试加载所有全局类型
      if (selectedKnowledgeBase.value && params.knowledge_base_id) {
        console.log('[实体类型] 知识库没有配置类型，尝试加载所有全局类型...')
        try {
          const globalParams = { size: 1000 } // 不限制 is_enabled，获取所有类型
          const globalRes = await getEntityTypes(globalParams)
          const globalData = globalRes.data?.items || globalRes.data?.list || globalRes.data?.types || []
          if (globalData.length > 0) {
            console.log('[实体类型] 成功加载全局类型，数量:', globalData.length)
            rawData = globalData
          }
        } catch (globalError) {
          console.error('[实体类型] 加载全局类型失败:', globalError)
        }
      }
    }
    
    // 确保 rawData 是数组
    if (!Array.isArray(rawData)) {
      console.error('[实体类型] rawData 不是数组:', rawData)
      rawData = []
    }
    
    entityTypes.value = rawData
    
    // 构建类型映射
    entityTypeMap.value = {}
    entityTypes.value.forEach(type => {
      if (type && type.code) {
        entityTypeMap.value[type.code] = type
      }
    })
    
    // 调试信息：打印加载的实体类型详情
    console.log(`[实体类型] 加载完成: 共${entityTypes.value.length}个类型`)
    console.log(`[实体类型] entityTypes.value 内容:`, entityTypes.value)
    console.log(`[实体类型] 是否有level=1的类型:`, entityTypes.value.filter(t => t.level === 1).length)
    console.log(`[实体类型] 是否有level=2的类型:`, entityTypes.value.filter(t => t.level === 2).length)
    console.log(`[实体类型] 是否有level=3的类型:`, entityTypes.value.filter(t => t.level === 3).length)
    if (entityTypes.value.length > 0) {
      console.log('[实体类型] 示例数据:', entityTypes.value.slice(0, 3))
      console.log('[实体类型] Level分布:', {
        level1: entityTypes.value.filter(t => t.level === 1).length,
        level2: entityTypes.value.filter(t => t.level === 2).length,
        level3: entityTypes.value.filter(t => t.level === 3).length,
        other: entityTypes.value.filter(t => !t.level || (t.level !== 1 && t.level !== 2 && t.level !== 3)).length
      })
    } else {
      console.warn('[实体类型] 警告: 没有加载到任何实体类型')
      console.log('[实体类型] 完整响应结构:', JSON.stringify(res, null, 2))
    }
  } catch (error: any) {
    console.error('[实体类型] 加载失败:', error)
    console.error('[实体类型] 错误详情:', {
      message: error.message,
      response: error.response,
      stack: error.stack
    })
    ElMessage.error('加载实体类型失败: ' + (error.message || '未知错误'))
    entityTypes.value = []
  }
}

// 实体类型标签（兼容旧代码）
const getEntityTypeLabel = (type: string) => {
  return entityTypeMap.value[type]?.name || type
}

// 获取类型显示名称（包含层级路径）
const getTypeDisplayName = (type: EntityType): string => {
  if (!type.parent_id) {
    return type.name
  }
  
  // 构建路径
  const path: string[] = []
  let current: EntityType | undefined = type
  
  while (current) {
    path.unshift(current.name)
    if (current.parent_id) {
      current = entityTypes.value.find(t => t.id === current!.parent_id)
    } else {
      break
    }
  }
  
  return path.join(' > ')
}

// 关系类型标签
const getRelationTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    belongs_to: '属于',
    references: '引用',
    depends_on: '依赖',
    compares: '对比',
    implements: '实现',
    related_to: '相关',
    part_of: '部分',
    has_part: '包含',
    created_by: '创建者',
    occurs_in: '发生在',
    other: '其他'
  }
  return labels[type] || type
}

// 加载知识库列表
const loadKnowledgeBases = async () => {
  try {
    const res = await getKnowledgeBases({ page: 1, size: 100 })
    knowledgeBases.value = res.data?.list || res.data?.items || []
  } catch (error: any) {
    ElMessage.error('加载知识库列表失败: ' + (error.message || '未知错误'))
  }
}

// 加载图谱数据
const loadGraphData = async () => {
  if (!selectedKnowledgeBase.value) return

  graphLoading.value = true
  try {
    const params: any = {
      knowledge_base_id: selectedKnowledgeBase.value,
      max_nodes: 100,
      layout: selectedLayout.value
    }
    // 如果选择了实体类型筛选，添加到参数中
    if (selectedEntityType.value) {
      params.entity_type = selectedEntityType.value
    }
    
    const res = await getVisualizationData(params)

    // 响应格式: { code: 0, message: "...", data: { nodes: [], edges: [], layout: "..." } }
    // 所以应该访问 res.data 而不是 res.data?.data
    const data = res.data || res.data?.data
    console.log('可视化数据响应:', res)
    console.log('解析后的数据:', data)
    
    // 确保 DOM 已经准备好
    await nextTick()
    
    if (data) {
      // 检查是否有节点数据
      if (data.nodes && data.nodes.length > 0) {
        console.log(`准备渲染图谱: ${data.nodes.length} 个节点, ${data.edges?.length || 0} 条边`)
        // 再次检查容器是否存在
        if (graphContainer.value) {
          renderGraph(data)
          hasGraphData.value = true
        } else {
          console.warn('图表容器不存在，延迟渲染')
          // 如果容器不存在，等待一下再试
          setTimeout(() => {
            if (graphContainer.value) {
              renderGraph(data)
              hasGraphData.value = true
            }
          }, 100)
        }
      } else {
        console.log('没有节点数据，清空图表')
        // 清空图表
        if (graphChart) {
          graphChart.dispose()
          graphChart = null
        }
        hasGraphData.value = false
      }
    } else {
      console.log('数据为空')
      hasGraphData.value = false
      if (graphChart) {
        graphChart.dispose()
        graphChart = null
      }
    }
  } catch (error: any) {
    console.error('加载图谱数据失败:', error)
    ElMessage.error('加载图谱数据失败: ' + (error.message || '未知错误'))
    hasGraphData.value = false
  } finally {
    graphLoading.value = false
  }
}

// 层次布局：计算节点位置
const calculateHierarchicalLayout = (nodes: any[], edges: any[]) => {
  // 简单的层次布局算法：根据节点的连接关系分层
  const nodeLevels = new Map<string, number>()
  const visited = new Set<string>()
  
  // 找到根节点（没有入边的节点）
  const inDegree = new Map<string, number>()
  nodes.forEach(node => {
    const nodeId = String(node.id)
    inDegree.set(nodeId, 0)
  })
  
  edges.forEach(edge => {
    const targetId = String(edge.to || edge.target)
    inDegree.set(targetId, (inDegree.get(targetId) || 0) + 1)
  })
  
  // 找到根节点（入度为0的节点）
  const rootNodes = nodes.filter(node => {
    const nodeId = String(node.id)
    return (inDegree.get(nodeId) || 0) === 0
  })
  
  // 如果没有根节点，选择第一个节点作为根
  if (rootNodes.length === 0 && nodes.length > 0) {
    rootNodes.push(nodes[0])
  }
  
  // BFS计算层级
  const queue: Array<{ node: any; level: number }> = []
  rootNodes.forEach(root => {
    const rootId = String(root.id)
    nodeLevels.set(rootId, 0)
    visited.add(rootId)
    queue.push({ node: root, level: 0 })
  })
  
  while (queue.length > 0) {
    const { node, level } = queue.shift()!
    const nodeId = String(node.id)
    
    // 找到所有子节点
    edges.forEach(edge => {
      const sourceId = String(edge.from || edge.source)
      const targetId = String(edge.to || edge.target)
      
      if (sourceId === nodeId && !visited.has(targetId)) {
        const childNode = nodes.find(n => String(n.id) === targetId)
        if (childNode) {
          nodeLevels.set(targetId, level + 1)
          visited.add(targetId)
          queue.push({ node: childNode, level: level + 1 })
        }
      }
    })
  }
  
  // 为未访问的节点分配层级
  nodes.forEach(node => {
    const nodeId = String(node.id)
    if (!nodeLevels.has(nodeId)) {
      nodeLevels.set(nodeId, 999) // 未连接的节点放在最后
    }
  })
  
  // 计算每层的节点数量
  const levelCounts = new Map<number, number>()
  nodeLevels.forEach(level => {
    levelCounts.set(level, (levelCounts.get(level) || 0) + 1)
  })
  
  // 计算节点位置
  const levelPositions = new Map<number, number>() // 每层当前x位置索引
  const levelYPositions = new Map<number, number>() // 每层的y位置
  
  const maxLevel = Math.max(...Array.from(nodeLevels.values()))
  const nodeHeight = 150 // 每层之间的垂直距离
  const nodeWidth = 200 // 同层节点之间的水平距离
  
  // 计算每层的y位置
  for (let level = 0; level <= maxLevel; level++) {
    const count = levelCounts.get(level) || 0
    levelYPositions.set(level, (level - maxLevel / 2) * nodeHeight)
    levelPositions.set(level, 0)
  }
  
  // 为每个节点计算位置
  const nodePositions = new Map<string, { x: number; y: number }>()
  nodes.forEach(node => {
    const nodeId = String(node.id)
    const level = nodeLevels.get(nodeId) || 0
    const xIndex = levelPositions.get(level) || 0
    const count = levelCounts.get(level) || 1
    
    // 居中分布
    const totalWidth = (count - 1) * nodeWidth
    const startX = -totalWidth / 2
    const x = startX + xIndex * nodeWidth
    const y = levelYPositions.get(level) || 0
    
    nodePositions.set(nodeId, { x, y })
    levelPositions.set(level, xIndex + 1)
  })
  
  return nodePositions
}

// 渲染图谱
const renderGraph = (data: any) => {
  if (!graphContainer.value) {
    console.error('图表容器不存在，无法渲染')
    return
  }

  try {
    // 销毁旧图表
    if (graphChart) {
      graphChart.dispose()
      graphChart = null
    }

    // 确保容器有尺寸
    if (graphContainer.value.offsetWidth === 0 || graphContainer.value.offsetHeight === 0) {
      console.warn('图表容器尺寸为0，等待容器渲染')
      setTimeout(() => renderGraph(data), 100)
      return
    }

    // 创建新图表
    graphChart = echarts.init(graphContainer.value)

  // 准备节点和边数据
  console.log('原始节点数据示例 (前3个):', data.nodes.slice(0, 3))
  console.log('原始节点数据结构检查:', {
    hasId: data.nodes[0]?.hasOwnProperty('id'),
    hasLabel: data.nodes[0]?.hasOwnProperty('label'),
    hasType: data.nodes[0]?.hasOwnProperty('type'),
    idValue: data.nodes[0]?.id,
    labelValue: data.nodes[0]?.label,
    typeValue: data.nodes[0]?.type
  })
  
  // 确保节点id唯一，使用Map去重（保留第一个出现的节点）
  const nodeMap = new Map<string, any>()
  let duplicateCount = 0
  data.nodes.forEach((node: any, index: number) => {
    // 确保 nodeId 是有效的字符串
    const nodeId = (node.id != null && node.id !== undefined) ? String(node.id) : `node_${index}_${Date.now()}_${Math.random()}`
    
    if (!nodeMap.has(nodeId)) {
      const nodeType = (node.type || node.group || 'other').trim() || 'other'
      nodeMap.set(nodeId, {
        id: nodeId,
        name: (node.label || node.name || `实体${node.id}`).trim() || `实体${nodeId}`,
        categoryName: nodeType, // 保存原始类型名称
        value: node.value || 1,
        symbolSize: Math.max(20, Math.min(60, (node.value || 1) * 5)),
        itemStyle: {
          color: getEntityTypeColor(nodeType),
          borderColor: '#ffffff',
          borderWidth: 2,
          shadowBlur: 8,
          shadowColor: 'rgba(0, 0, 0, 0.15)'
        },
        label: {
          show: true,
          position: 'right', // 确保节点标签跟随节点移动
          fontSize: 12,
          color: '#303133', // 深色文字以适应白色背景
          fontWeight: 'normal',
          distance: 10 // 标签与节点的距离
        },
        // 如果是层次布局，设置固定位置
        ...(selectedLayout.value === 'hierarchical' ? {
          x: undefined as any, // 将在后面设置
          y: undefined as any  // 将在后面设置
        } : {})
      })
    } else {
      duplicateCount++
      if (duplicateCount <= 5) { // 只打印前5个重复的
        console.warn(`发现重复节点ID: ${nodeId}, 已跳过 (第${index + 1}个节点)`)
      }
    }
  })
  const nodesTemp = Array.from(nodeMap.values())
  
  console.log(`原始节点数: ${data.nodes.length}, 去重后节点数: ${nodesTemp.length}, 重复节点数: ${duplicateCount}`)
  console.log(`节点示例 (前3个):`, nodesTemp.slice(0, 3))
  
  // 生成categories列表（基于实际存在的节点类型）
  const categoryNames = Array.from(new Set(nodesTemp.map((n: any) => n.categoryName || 'other')))
  const categories = categoryNames.map((name: string) => ({ name }))
  
  // 将节点的categoryName转换为categories数组的索引
  const categoryIndexMap = new Map(categoryNames.map((name, index) => [name, index]))
  let nodes = nodesTemp.map((node: any) => ({
    ...node,
    category: categoryIndexMap.get(node.categoryName) || 0 // ECharts要求category是索引
  }))
  
  // 如果是层次布局，计算节点位置
  if (selectedLayout.value === 'hierarchical') {
    const nodePositions = calculateHierarchicalLayout(nodes, data.edges || [])
    nodes = nodes.map((node: any) => {
      const nodeId = String(node.id)
      const position = nodePositions.get(nodeId)
      if (position) {
        return {
          ...node,
          x: position.x,
          y: position.y,
          fixed: true // 固定位置，不允许拖动时改变
        }
      }
      return node
    })
    console.log('[层次布局] 已计算节点位置，共', nodePositions.size, '个节点')
  }
  
  console.log(`准备渲染: ${nodes.length} 个唯一节点, ${data.edges?.length || 0} 条边`)
  console.log(`节点类型: ${categoryNames.join(', ')}`)
  console.log(`Categories映射:`, Array.from(categoryIndexMap.entries()))

  // 准备边数据，确保source和target都存在
  const nodeIdSet = new Set(nodes.map((n: any) => n.id))
  const edges = (data.edges || []).filter((edge: any) => {
    const source = edge.from?.toString()
    const target = edge.to?.toString()
    return source && target && nodeIdSet.has(source) && nodeIdSet.has(target)
  }).map((edge: any, index: number) => {
    // 根据索引分配颜色，创建多彩的边
    const edgeColors = ['#67C23A', '#409EFF', '#E6A23C', '#F56C6C', '#909399', '#9C27B0', '#00BCD4']
    const edgeColor = edgeColors[index % edgeColors.length]
    
    return {
      source: edge.from.toString(),
      target: edge.to.toString(),
      value: edge.value || 0.5,
      label: {
        show: true,
        formatter: getRelationTypeLabel(edge.label || ''),
        fontSize: 10,
        color: '#606266'
      },
      lineStyle: {
        width: Math.max(2, Math.min(4, (edge.value || 0.5) * 4)),
        curveness: 0.3,
        color: edgeColor,
        type: 'solid'
      },
      // 添加边的动画效果
      emphasis: {
        lineStyle: {
          width: 5,
          color: edgeColor
        }
      }
    }
  })
  
  console.log(`过滤后的边数量: ${edges.length}`)

  const option: echarts.EChartsOption = {
    backgroundColor: '#ffffff', // 白色背景
    title: {
      text: '知识图谱',
      left: 'center',
      textStyle: {
        color: '#303133' // 深色文字以适应白色背景
      }
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(50, 50, 50, 0.9)',
      borderColor: '#409eff',
      borderWidth: 1,
      textStyle: {
        color: '#fff'
      },
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          return `${params.data.name}<br/>类型: ${getEntityTypeLabel(params.data.category)}`
        } else {
          return `${params.data.source} → ${params.data.target}`
        }
      }
    },
    legend: {
      data: ['实体'],
      orient: 'vertical',
      left: 'left',
      textStyle: {
        color: '#303133' // 深色文字
      }
    },
    series: [
      {
        type: 'graph',
        layout: selectedLayout.value === 'force' ? 'force' 
                : selectedLayout.value === 'circular' ? 'circular' 
                : selectedLayout.value === 'hierarchical' ? 'none'  // 层次布局使用none，需要手动计算位置
                : 'none',
        data: nodes,
        links: edges,
        // 使用动态生成的categories
        categories: categories,
        roam: true, // 允许缩放和平移
        // 启用节点拖动
        draggable: true,
        // 启用动画
        animation: true,
        animationDuration: 1000,
        animationEasing: 'cubicOut',
        label: {
          show: true,
          position: 'right', // 标签位置相对于节点（会跟随节点移动）
          formatter: '{b}',
          color: '#303133', // 深色文字以适应白色背景
          fontSize: 12,
          fontWeight: 'normal',
          // 确保标签跟随节点移动
          distance: 10 // 标签与节点的距离（不使用offset，让标签完全跟随节点）
        },
        // 节点样式（全局默认样式，节点数据中的itemStyle会覆盖此配置）
        itemStyle: {
          borderColor: '#ffffff',
          borderWidth: 2,
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.15)'
        },
        emphasis: {
          focus: 'adjacency',
          scale: true, // 放大效果
          itemStyle: {
            borderColor: '#409eff',
            borderWidth: 3,
            shadowBlur: 20,
            shadowColor: 'rgba(64, 158, 255, 0.5)'
          },
          lineStyle: {
            width: 4,
            color: '#409eff'
          },
          label: {
            fontSize: 14,
            fontWeight: 'bold',
            color: '#409eff'
          }
        },
        // 力导向布局配置
        force: {
          repulsion: 1000,
          gravity: 0.1,
          edgeLength: 200,
          layoutAnimation: true,
          // 添加布局动画效果
          initLayout: 'circular',
          friction: 0.6
        },
        // 边样式（edges数据中的lineStyle会覆盖此默认配置）
        lineStyle: {
          curveness: 0.3,
          width: 2,
          type: 'solid'
        },
        // 边的标签样式（跟随边的位置）
        edgeLabel: {
          show: true,
          formatter: '{c}',
          fontSize: 10,
          color: '#606266',
          position: 'middle', // 标签位置在边的中间
          rotate: true, // 标签跟随边的方向旋转
          distance: 5 // 标签与边的距离
        }
      }
    ]
  }

    graphChart.setOption(option)

    // 添加鼠标悬停动画效果
    graphChart.on('mouseover', (params: any) => {
      if (params.dataType === 'node') {
        // 节点悬停时的动画效果
        graphChart.dispatchAction({
          type: 'highlight',
          dataIndex: params.dataIndex
        })
      }
    })
    
    graphChart.on('mouseout', (params: any) => {
      if (params.dataType === 'node') {
        // 取消高亮
        graphChart.dispatchAction({
          type: 'downplay',
          dataIndex: params.dataIndex
        })
      }
    })

    // 监听点击事件
    graphChart.on('click', (params: any) => {
      if (params.dataType === 'node') {
        // 添加点击动画
        graphChart.dispatchAction({
          type: 'highlight',
          dataIndex: params.dataIndex
        })
        viewEntity(parseInt(params.data.id))
      }
    })
    
    // ECharts graph图表在节点拖动时会自动更新标签位置
    // 已启用LabelLayout功能，标签会自动跟随节点移动
    
    // 添加自动布局动画（持续优化布局）
    if (selectedLayout.value === 'force') {
      // 在力导向布局中，持续优化布局位置
      setTimeout(() => {
        graphChart.dispatchAction({
          type: 'restore'
        })
      }, 2000)
    }
  } catch (error) {
    console.error('渲染图谱失败:', error)
    ElMessage.error('渲染图谱失败: ' + (error instanceof Error ? error.message : '未知错误'))
  }
}

// 获取实体类型颜色（适应白色背景，使用更深的颜色）
const getEntityTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    person: '#FF6B6B',
    location: '#4ECDC4',
    concept: '#45B7D1',
    product: '#FF8C42',
    technology: '#5CB87A',
    event: '#F7B731',
    organization: '#9B59B6',
    software: '#3498DB',
    protocol: '#E74C3C',
    document: '#16A085',
    service: '#D35400',
    platform: '#8E44AD',
    framework: '#27AE60',
    other: '#7F8C8D'
  }
  return colors[type] || '#7F8C8D'
}

// 查看实体详情
const viewEntity = async (entityId: number) => {
  try {
    const res = await getEntityDetail(entityId)
    // 响应拦截器已经返回了 response.data，所以 res 就是后端返回的对象
    // 后端返回格式: {success: true, message: "...", data: {entity: {...}, relationships: [...], ...}}
    // 所以应该访问 res.data.entity 而不是 res.data.data.entity
    selectedEntity.value = res.data?.entity
    entityRelationships.value = res.data?.relationships || []
    selectedRelationship.value = null
    detailDrawerTitle.value = `实体详情: ${selectedEntity.value?.name}`
    detailDrawerVisible.value = true
  } catch (error: any) {
    ElMessage.error('加载实体详情失败: ' + (error.message || '未知错误'))
  }
}

// 查看关系详情
const viewRelationship = (relationship: KnowledgeGraphRelationship) => {
  selectedRelationship.value = relationship
  selectedEntity.value = null
  detailDrawerTitle.value = '关系详情'
}

// 搜索处理
const handleSearch = async () => {
  if (!searchKeyword.value || !selectedKnowledgeBase.value) {
    // 如果搜索关键词为空，重新加载图谱
    loadGraphData()
    return
  }
  
  try {
    const res = await searchEntities({
      q: searchKeyword.value,
      knowledge_base_id: selectedKnowledgeBase.value,
      type: selectedEntityType.value || undefined
    })
    
    const entities = res.data?.data?.entities || []
    if (entities.length > 0) {
      // 高亮搜索结果中的实体
      ElMessage.success(`找到 ${entities.length} 个相关实体`)
      // 可以扩展：在图谱中高亮显示这些实体
    } else {
      ElMessage.info('未找到相关实体')
    }
  } catch (error: any) {
    ElMessage.error('搜索失败: ' + (error.message || '未知错误'))
  }
}

// 应用筛选
const applyFilters = () => {
  loadGraphData()
}

// 切换布局
const changeLayout = () => {
  loadGraphData()
}

// 重置视图
const resetView = () => {
  if (graphChart) {
    graphChart.dispatchAction({
      type: 'restore'
    })
  }
}

// 导出图片
const exportImage = () => {
  if (graphChart) {
    const url = graphChart.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#fff'
    })
    const link = document.createElement('a')
    link.download = `knowledge-graph-${Date.now()}.png`
    link.href = url
    link.click()
  }
}

// 知识库变化时加载文档列表和实体类型
const handleKnowledgeBaseChange = async () => {
  if (!extractForm.value.knowledge_base_id) {
    availableDocuments.value = []
    extractEntityTypes.value = []
    extractForm.value.entity_type_codes = []
    return
  }
  
  if (extractForm.value.scope === 'selected') {
    await loadDocumentsForKnowledgeBase()
  }
  
  // 加载实体类型列表
  await loadExtractEntityTypes()
}

// 实体类型模式变化时重新加载实体类型列表
const handleEntityTypeModeChange = async () => {
  extractForm.value.entity_type_codes = []
  if (extractForm.value.knowledge_base_id && extractForm.value.entity_type_mode !== 'model') {
    await loadExtractEntityTypes()
  } else {
    extractEntityTypes.value = []
  }
}

// 加载提取对话框中的实体类型列表
const loadExtractEntityTypes = async () => {
  if (!extractForm.value.knowledge_base_id || extractForm.value.entity_type_mode === 'model') {
    extractEntityTypes.value = []
    return
  }
  
  extractEntityTypesLoading.value = true
  try {
    const res = await getEntityTypes({
      knowledge_base_id: extractForm.value.knowledge_base_id,
      is_enabled: true,
      is_system: extractForm.value.entity_type_mode === 'system' ? true : extractForm.value.entity_type_mode === 'user' ? false : undefined
    })
    
    let rawData: EntityType[] = []
    if (Array.isArray(res.data)) {
      rawData = res.data
    } else if (res.data && typeof res.data === 'object') {
      if (Array.isArray(res.data.items)) {
        rawData = res.data.items
      } else if (Array.isArray(res.data.list)) {
        rawData = res.data.list
      } else if (Array.isArray(res.data.data)) {
        rawData = res.data.data
      }
    }
    
    extractEntityTypes.value = rawData
  } catch (error: any) {
    console.error('[提取对话框] 加载实体类型失败:', error)
    extractEntityTypes.value = []
    ElMessage.error('加载实体类型失败: ' + (error.message || '未知错误'))
  } finally {
    extractEntityTypesLoading.value = false
  }
}

// 加载知识库的文档列表
const loadDocumentsForKnowledgeBase = async () => {
  if (!extractForm.value.knowledge_base_id) {
    availableDocuments.value = []
    return
  }
  
  documentsLoading.value = true
  try {
    const res = await getDocuments({
      knowledge_base_id: extractForm.value.knowledge_base_id,
      page: 1,
      size: 1000  // 获取所有文档
    })
    availableDocuments.value = res.data?.list || []
  } catch (error: any) {
    ElMessage.error('加载文档列表失败: ' + (error.message || '未知错误'))
    availableDocuments.value = []
  } finally {
    documentsLoading.value = false
  }
}

// 监听文档范围变化
watch(() => extractForm.value.scope, (newScope) => {
  if (newScope === 'selected' && extractForm.value.knowledge_base_id) {
    loadDocumentsForKnowledgeBase()
  } else if (newScope === 'all') {
    extractForm.value.document_ids = []
  }
})

// 提取实体
const handleExtract = async () => {
  if (!extractForm.value.knowledge_base_id) {
    ElMessage.warning('请选择知识库')
    return
  }
  
  if (extractForm.value.scope === 'selected') {
    if (!extractForm.value.document_ids || extractForm.value.document_ids.length === 0) {
      ElMessage.warning('请选择要提取的文档')
      return
    }
  }
  
  // 验证：如果选择的是system或user模式，必须至少选择一个实体类型
  if (extractForm.value.entity_type_mode !== 'model') {
    if (!extractForm.value.entity_type_codes || extractForm.value.entity_type_codes.length === 0) {
      ElMessage.warning('请至少选择一个实体类型')
      return
    }
  }

  extracting.value = true
  try {
    await extractEntities({
      knowledge_base_id: extractForm.value.knowledge_base_id!,
      document_ids: extractForm.value.scope === 'selected' ? extractForm.value.document_ids : undefined,
      entity_type_mode: extractForm.value.entity_type_mode,
      entity_type_codes: extractForm.value.entity_type_mode !== 'model' ? extractForm.value.entity_type_codes : undefined
    })
    ElMessage.success('实体提取任务已启动')
    showExtractDialog.value = false
    // 重置表单
    extractForm.value = {
      knowledge_base_id: undefined,
      scope: 'all',
      document_ids: [],
      entity_type_mode: 'system',
      entity_type_codes: []
    }
    extractEntityTypes.value = []
    availableDocuments.value = []
    // 延迟刷新图谱数据
    setTimeout(() => {
      loadGraphData()
    }, 2000)
  } catch (error: any) {
    ElMessage.error('启动提取任务失败: ' + (error.message || '未知错误'))
  } finally {
    extracting.value = false
  }
}

onMounted(async () => {
  console.log('[页面加载] 开始初始化...')
  await loadKnowledgeBases()
  console.log('[页面加载] 知识库加载完成，开始加载实体类型...')
  // 页面加载时就加载所有启用的实体类型（不依赖知识库选择）
  await loadEntityTypes()
  console.log('[页面加载] 实体类型加载完成，entityTypes.value.length =', entityTypes.value.length)
  await nextTick()
  if (graphContainer.value) {
    // 初始化图表容器大小
    const resizeObserver = new ResizeObserver(() => {
      if (graphChart) {
        graphChart.resize()
      }
    })
    resizeObserver.observe(graphContainer.value)
  }
  // 初始化时没有数据
  hasGraphData.value = false
})

// 知识库选择变化处理
const handleKnowledgeBaseSelectChange = () => {
  loadEntityTypes()
  loadGraphData()
  // 如果任务列表对话框已打开，重新加载任务列表
  if (showTaskListDialog.value) {
    loadExtractionTasks()
  }
}

// 任务列表相关函数
const handleTaskCommand = (command: string) => {
  console.log(`[任务列表] 用户操作: ${command}, 知识库ID=${selectedKnowledgeBase.value}`)
  if (command === 'view-tasks') {
    if (!selectedKnowledgeBase.value) {
      console.warn('[任务列表] 未选择知识库，无法打开任务列表')
      ElMessage.warning('请先选择知识库')
      return
    }
    showTaskListDialog.value = true
    console.log('[任务列表] 打开任务列表对话框')
    loadExtractionTasks()
  }
}

// 加载提取任务列表
const loadExtractionTasks = async () => {
  if (!selectedKnowledgeBase.value) {
    console.warn('[任务列表] 未选择知识库，无法加载任务列表')
    ElMessage.warning('请先选择知识库')
    return
  }

  console.log(`[任务列表] 开始加载任务列表: 知识库ID=${selectedKnowledgeBase.value}, 页码=${taskPagination.value.page}, 每页=${taskPagination.value.size}`)
  tasksLoading.value = true
  try {
    const res = await listExtractionTasks({
      knowledge_base_id: selectedKnowledgeBase.value,
      page: taskPagination.value.page,
      size: taskPagination.value.size
    })
    extractionTasks.value = res.data.tasks || []
    taskPagination.value.total = res.data.total || 0
    console.log(`[任务列表] 加载成功: 总数=${taskPagination.value.total}, 当前页任务数=${extractionTasks.value.length}`)
    if (extractionTasks.value.length > 0) {
      console.log('[任务列表] 任务示例:', extractionTasks.value[0])
    }
  } catch (error: any) {
    console.error('[任务列表] 加载失败:', error)
    ElMessage.error('加载任务列表失败: ' + (error.message || '未知错误'))
  } finally {
    tasksLoading.value = false
  }
}

// 删除任务
const handleDeleteTask = async (taskId: number) => {
  console.log(`[删除任务] 用户点击删除任务: 任务ID=${taskId}`)
  
  try {
    await ElMessageBox.confirm(
      '删除任务将同步删除MySQL和图数据库中的相关数据，此操作不可恢复。确定要删除吗？',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    console.log(`[删除任务] 用户确认删除: 任务ID=${taskId}`)
    deletingTaskId.value = taskId
    
    const startTime = Date.now()
    await deleteExtractionTask(taskId)
    const duration = Date.now() - startTime
    
    console.log(`[删除任务] 删除成功: 任务ID=${taskId}, 耗时=${duration}ms`)
    ElMessage.success('任务删除成功')
    
    // 重新加载任务列表
    console.log('[删除任务] 重新加载任务列表')
    await loadExtractionTasks()
    
    // 刷新图谱数据
    console.log('[删除任务] 刷新图谱数据')
    await loadGraphData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error(`[删除任务] 删除失败: 任务ID=${taskId}, 错误=`, error)
      ElMessage.error('删除任务失败: ' + (error.message || '未知错误'))
    } else {
      console.log(`[删除任务] 用户取消删除: 任务ID=${taskId}`)
    }
  } finally {
    deletingTaskId.value = null
  }
}

// 重新生成任务
const handleRegenerateTask = async (taskId: number) => {
  console.log(`[重新生成任务] 用户点击重新生成任务: 任务ID=${taskId}`)
  
  try {
    await ElMessageBox.confirm(
      '重新生成任务将先删除现有数据，然后重新提取实体。确定要继续吗？',
      '确认重新生成',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    console.log(`[重新生成任务] 用户确认重新生成: 任务ID=${taskId}`)
    regeneratingTaskId.value = taskId
    
    const startTime = Date.now()
    const res = await regenerateExtractionTask(taskId)
    const duration = Date.now() - startTime
    
    console.log(`[重新生成任务] 重新生成成功: 旧任务ID=${taskId}, 新任务ID=${res.data.new_task_id}, 文档ID=${res.data.document_id}, 耗时=${duration}ms`)
    ElMessage.success('任务重新生成成功，新任务已启动')
    
    // 重新加载任务列表
    console.log('[重新生成任务] 重新加载任务列表')
    await loadExtractionTasks()
    
    // 延迟刷新图谱数据（等待任务完成）
    console.log('[重新生成任务] 将在5秒后刷新图谱数据')
    setTimeout(() => {
      console.log('[重新生成任务] 开始刷新图谱数据')
      loadGraphData()
    }, 5000)
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error(`[重新生成任务] 重新生成失败: 任务ID=${taskId}, 错误=`, error)
      ElMessage.error('重新生成任务失败: ' + (error.message || '未知错误'))
    } else {
      console.log(`[重新生成任务] 用户取消重新生成: 任务ID=${taskId}`)
    }
  } finally {
    regeneratingTaskId.value = null
  }
}

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  const typeMap: Record<string, string> = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const textMap: Record<string, string> = {
    pending: '等待中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return textMap[status] || status
}

// 格式化日期时间
const formatDateTime = (dateTime: string) => {
  if (!dateTime) return '-'
  const date = new Date(dateTime)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 监听知识库选择变化，重新加载该知识库的实体类型
watch(selectedKnowledgeBase, () => {
  loadEntityTypes()
  loadGraphData()
})

// 监听提取对话框打开，如果选择了知识库且范围是"指定文档"，加载文档列表
watch(showExtractDialog, (isOpen) => {
  if (isOpen) {
    if (extractForm.value.knowledge_base_id) {
      if (extractForm.value.scope === 'selected') {
        loadDocumentsForKnowledgeBase()
      }
      if (extractForm.value.entity_type_mode !== 'model') {
        loadExtractEntityTypes()
      }
    }
  } else {
    // 关闭对话框时重置实体类型选择
    extractForm.value.entity_type_codes = []
    extractEntityTypes.value = []
  }
})

onUnmounted(() => {
  if (graphChart) {
    graphChart.dispose()
  }
})
</script>

<style scoped lang="scss">
.knowledge-graph-page {
  padding: 20px;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-actions {
      display: flex;
      align-items: center;
    }
  }

  .empty-state {
    padding: 40px;
    text-align: center;
  }

  .graph-container {
    .toolbar {
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }

    .graph-visualization {
      width: 100%;
      height: 600px;
      border: 1px solid #e4e7ed;
      border-radius: 8px;
      position: relative;
      background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
      box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
      overflow: hidden;
      
      // 添加微妙的动态背景效果
      &::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: 
          radial-gradient(circle at 20% 50%, rgba(64, 158, 255, 0.03) 0%, transparent 50%),
          radial-gradient(circle at 80% 80%, rgba(103, 194, 58, 0.03) 0%, transparent 50%);
        pointer-events: none;
        animation: backgroundPulse 8s ease-in-out infinite;
      }
      
      @keyframes backgroundPulse {
        0%, 100% {
          opacity: 1;
        }
        50% {
          opacity: 0.8;
        }
      }

      .empty-graph-hint {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 100%;
        z-index: 1;
      }
    }
  }

  .entity-detail,
  .relationship-detail {
    .relationship-item {
      padding: 10px;
      margin-bottom: 10px;
      border: 1px solid #e4e7ed;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.3s;

      &:hover {
        background-color: #f5f7fa;
        border-color: #409eff;
      }

      .relationship-type {
        font-weight: bold;
        color: #409eff;
        margin-bottom: 5px;
      }

      .relationship-target {
        margin-bottom: 5px;
      }

      .relationship-weight {
        font-size: 12px;
        color: #909399;
      }
    }
  }
}
</style>

