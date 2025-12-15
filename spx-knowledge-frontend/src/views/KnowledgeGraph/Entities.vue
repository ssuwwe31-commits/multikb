<template>
  <div class="entities-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>实体管理</span>
          <div>
            <el-select
              v-model="selectedKnowledgeBase"
              placeholder="选择知识库"
              style="width: 200px; margin-right: 10px"
              @change="loadEntities"
            >
              <el-option
                v-for="kb in knowledgeBases"
                :key="kb.id"
                :label="kb.name"
                :value="kb.id"
              />
            </el-select>
            <el-button type="primary" @click="showCreateDialog = true">创建实体</el-button>
          </div>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filters">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索实体名称..."
          style="width: 200px; margin-right: 10px"
          clearable
          @input="loadEntities"
        />
        <el-select
          v-model="filters.type"
          placeholder="实体类型"
          style="width: 200px; margin-right: 10px"
          clearable
          @change="loadEntities"
        >
          <el-option label="全部" value="" />
          <el-option-group
            v-for="level in [1, 2, 3]"
            :key="level"
            :label="`${level}级分类`"
          >
            <el-option
              v-for="type in entityTypes.filter(t => t.level === level)"
              :key="type.code"
              :label="getTypeDisplayName(type)"
              :value="type.code"
            >
              <span>{{ getTypeDisplayName(type) }}</span>
            </el-option>
          </el-option-group>
        </el-select>
      </div>

      <!-- 实体列表 -->
      <el-table
        v-loading="loading"
        :data="entities"
        stripe
        border
        style="width: 100%"
      >
        <el-table-column prop="name" label="名称" width="200" />
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag
              :type="entityTypeMap[row.type]?.tag_type || 'info'"
              :color="entityTypeMap[row.type]?.color"
            >
              {{ entityTypeMap[row.type]?.name || row.type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="{ row }">
            {{ (row.confidence * 100).toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column prop="related_entities_count" label="关联实体" width="100" />
        <el-table-column prop="related_documents_count" label="关联文档" width="100" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewEntity(row.id)">查看</el-button>
            <el-button link type="primary" @click="editEntity(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDeleteEntity(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadEntities"
          @current-change="loadEntities"
        />
      </div>
    </el-card>

    <!-- 创建/编辑实体对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingEntity ? '编辑实体' : '创建实体'"
      width="600px"
    >
      <el-form
        ref="entityFormRef"
        :model="entityForm"
        :rules="entityFormRules"
        label-width="100px"
      >
        <el-form-item label="知识库" prop="knowledge_base_id">
          <el-select v-model="entityForm.knowledge_base_id" placeholder="选择知识库" style="width: 100%">
            <el-option
              v-for="kb in knowledgeBases"
              :key="kb.id"
              :label="kb.name"
              :value="kb.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="entityForm.name" placeholder="实体名称" />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-select v-model="entityForm.type" placeholder="选择类型" style="width: 100%">
            <el-option-group
              v-for="level in [1, 2, 3]"
              :key="level"
              :label="`${level}级分类`"
            >
              <el-option
                v-for="type in entityTypes.filter(t => t.level === level)"
                :key="type.code"
                :label="getTypeDisplayName(type)"
                :value="type.code"
              >
                <span>{{ getTypeDisplayName(type) }}</span>
                <span style="color: #909399; font-size: 12px; margin-left: 8px">
                  {{ type.description || '' }}
                </span>
              </el-option>
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="entityForm.description"
            type="textarea"
            :rows="3"
            placeholder="实体描述"
          />
        </el-form-item>
        <el-form-item label="别名">
          <el-input
            v-model="aliasesInput"
            placeholder="多个别名用逗号分隔"
            @blur="handleAliasesInput"
          />
        </el-form-item>
        <el-form-item label="置信度">
          <el-slider
            v-model="entityForm.confidence"
            :min="0"
            :max="1"
            :step="0.01"
            show-input
            :format-tooltip="(val: number) => (val * 100).toFixed(1) + '%'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="submitEntity" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getKnowledgeBases } from '@/api/modules/knowledge-bases'
import {
  getEntities,
  createEntity,
  updateEntity,
  deleteEntity,
  getEntityDetail,
  getEntityTypes,
  type KnowledgeGraphEntity,
  type EntityCreate,
  type EntityUpdate,
  type EntityType
} from '@/api/modules/knowledge-graph'
import type { KnowledgeBase } from '@/types'

const loading = ref(false)
const knowledgeBases = ref<KnowledgeBase[]>([])
const selectedKnowledgeBase = ref<number>()
const entities = ref<KnowledgeGraphEntity[]>([])
const entityTypes = ref<EntityType[]>([])
const entityTypeMap = ref<Record<string, EntityType>>({})
const pagination = ref({
  page: 1,
  size: 20,
  total: 0
})
const filters = ref({
  keyword: '',
  type: ''
})

const showCreateDialog = ref(false)
const editingEntity = ref<KnowledgeGraphEntity | null>(null)
const entityFormRef = ref<FormInstance>()
const submitting = ref(false)
const entityForm = ref<EntityCreate & { id?: number }>({
  knowledge_base_id: 0,
  name: '',
  type: 'concept',
  description: '',
  aliases: [],
  confidence: 0.7
})
const aliasesInput = ref('')

const entityFormRules: FormRules = {
  knowledge_base_id: [{ required: true, message: '请选择知识库', trigger: 'change' }],
  name: [{ required: true, message: '请输入实体名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择实体类型', trigger: 'change' }]
}

// 加载实体类型列表
const loadEntityTypes = async () => {
  try {
    const params: any = { is_enabled: true }
    if (selectedKnowledgeBase.value) {
      params.knowledge_base_id = selectedKnowledgeBase.value
    }
    const res = await getEntityTypes(params)
    entityTypes.value = (res.data as any).types || []
    // 构建类型映射
    entityTypeMap.value = {}
    entityTypes.value.forEach(type => {
      entityTypeMap.value[type.code] = type
    })
  } catch (error: any) {
    ElMessage.error('加载实体类型失败: ' + (error.message || '未知错误'))
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

// 实体类型标签颜色（兼容旧代码）
const getEntityTypeTagType = (type: string) => {
  return entityTypeMap.value[type]?.tag_type || 'info'
}

// 处理别名输入
const handleAliasesInput = () => {
  if (aliasesInput.value) {
    entityForm.value.aliases = aliasesInput.value
      .split(',')
      .map(s => s.trim())
      .filter(s => s.length > 0)
  } else {
    entityForm.value.aliases = []
  }
}

// 加载知识库列表
const loadKnowledgeBases = async () => {
  try {
    const res = await getKnowledgeBases({ page: 1, size: 100 })
    knowledgeBases.value = (res.data as any)?.list || (res.data as any)?.items || []
  } catch (error: any) {
    ElMessage.error('加载知识库列表失败: ' + (error.message || '未知错误'))
  }
}

// 监听知识库选择变化，重新加载类型
watch(selectedKnowledgeBase, () => {
  loadEntityTypes()
})

// 加载实体列表
const loadEntities = async () => {
  if (!selectedKnowledgeBase.value) return

  loading.value = true
  try {
    const res = await getEntities({
      knowledge_base_id: selectedKnowledgeBase.value,
      page: pagination.value.page,
      size: pagination.value.size,
      keyword: filters.value.keyword || undefined,
      type: filters.value.type || undefined
    })

    entities.value = (res.data as any)?.list || (res.data as any)?.items || []
    pagination.value.total = res.data?.total || 0
  } catch (error: any) {
    ElMessage.error('加载实体列表失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 查看实体
const viewEntity = async (id: number) => {
  try {
    await getEntityDetail(id)
    // TODO: 显示实体详情对话框或跳转到详情页
    ElMessage.info('实体详情功能开发中')
  } catch (error: any) {
    ElMessage.error('加载实体详情失败: ' + (error.message || '未知错误'))
  }
}

// 编辑实体
const editEntity = (entity: KnowledgeGraphEntity) => {
  editingEntity.value = entity
  entityForm.value = {
    knowledge_base_id: entity.knowledge_base_id,
    name: entity.name,
    type: entity.type,
    description: entity.description || '',
    aliases: entity.aliases || [],
    confidence: entity.confidence,
    id: entity.id
  }
  aliasesInput.value = (entity.aliases || []).join(', ')
  showCreateDialog.value = true
}

// 删除实体
const handleDeleteEntity = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定要删除该实体吗？删除后相关关系也会被删除。', '确认删除', {
      type: 'warning'
    })

    await deleteEntity(id)
    ElMessage.success('删除成功')
    loadEntities()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.message || '未知错误'))
    }
  }
}

// 提交实体表单
const submitEntity = async () => {
  if (!entityFormRef.value) return

  await entityFormRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      if (editingEntity.value) {
        // 更新实体
        const updateData: EntityUpdate = {
          name: entityForm.value.name,
          type: entityForm.value.type,
          description: entityForm.value.description,
          aliases: entityForm.value.aliases,
          confidence: entityForm.value.confidence
        }
        await updateEntity(editingEntity.value.id, updateData)
        ElMessage.success('更新成功')
      } else {
        // 创建实体
        const createData: EntityCreate = {
          knowledge_base_id: entityForm.value.knowledge_base_id || selectedKnowledgeBase.value!,
          name: entityForm.value.name,
          type: entityForm.value.type,
          description: entityForm.value.description,
          aliases: entityForm.value.aliases,
          confidence: entityForm.value.confidence
        }
        await createEntity(createData)
        ElMessage.success('创建成功')
      }

      showCreateDialog.value = false
      resetForm()
      loadEntities()
    } catch (error: any) {
      ElMessage.error((editingEntity.value ? '更新' : '创建') + '失败: ' + (error.message || '未知错误'))
    } finally {
      submitting.value = false
    }
  })
}

// 重置表单
const resetForm = () => {
  editingEntity.value = null
  entityForm.value = {
    knowledge_base_id: selectedKnowledgeBase.value || 0,
    name: '',
    type: 'concept',
    description: '',
    aliases: [],
    confidence: 0.7
  }
  aliasesInput.value = ''
  entityFormRef.value?.resetFields()
}

onMounted(async () => {
  await loadKnowledgeBases()
})
</script>

<style scoped lang="scss">
.entities-page {
  padding: 20px;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .filters {
    margin-bottom: 20px;
    display: flex;
    align-items: center;
  }

  .pagination {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>

