<template>
  <div class="entity-types-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>实体类型管理</span>
          <el-button type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            创建类型
          </el-button>
        </div>
      </template>

      <!-- 搜索和筛选 -->
      <div class="filter-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索类型名称或代码"
          clearable
          style="width: 300px"
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select
          v-model="filterEnabled"
          placeholder="状态筛选"
          clearable
          style="width: 150px"
          @change="handleFilterChange"
        >
          <el-option label="全部" value="" />
          <el-option label="已启用" :value="true" />
          <el-option label="已禁用" :value="false" />
        </el-select>
        <el-select
          v-model="filterSystem"
          placeholder="类型筛选"
          clearable
          style="width: 150px"
          @change="handleFilterChange"
        >
          <el-option label="全部" value="" />
          <el-option label="系统类型" :value="true" />
          <el-option label="自定义类型" :value="false" />
        </el-select>
        <el-select
          v-model="filterLevel"
          placeholder="层级筛选"
          clearable
          style="width: 150px"
          @change="handleFilterChange"
        >
          <el-option label="全部" value="" />
          <el-option label="一级分类" :value="1" />
          <el-option label="二级分类" :value="2" />
          <el-option label="三级分类" :value="3" />
        </el-select>
        <el-button @click="showTreeView = !showTreeView">
          {{ showTreeView ? '列表视图' : '树形视图' }}
        </el-button>
      </div>

      <!-- 树形视图 -->
      <div v-if="showTreeView" class="tree-view-container">
        <el-tree
          v-loading="loading"
          :data="typeTree"
          :props="{ children: 'children', label: 'name' }"
          :expand-on-click-node="false"
          default-expand-all
          class="entity-type-tree"
        >
        <template #default="{ data }">
          <div class="tree-node">
            <el-tag :type="data.tag_type || 'info'" :color="data.color" size="small">
              {{ data.name }}
            </el-tag>
            <span class="tree-node-info">
              <el-tag v-if="data.is_system" type="warning" size="small" style="margin-left: 8px">系统</el-tag>
              <el-tag v-else type="success" size="small" style="margin-left: 8px">自定义</el-tag>
              <span style="margin-left: 8px; color: #909399; font-size: 12px">
                L{{ data.level }} | {{ data.code }}
              </span>
            </span>
            <div class="tree-node-actions">
              <el-button
                v-if="!data.is_system"
                type="primary"
                link
                size="small"
                @click="handleEdit(data)"
              >
                编辑
              </el-button>
              <el-button
                v-if="!data.is_system"
                type="danger"
                link
                size="small"
                @click="handleDelete(data)"
              >
                删除
              </el-button>
              <el-button
                v-if="data.level < 3"
                type="success"
                link
                size="small"
                @click="handleCreateChild(data)"
              >
                添加子类型
              </el-button>
              <span v-if="data.is_system" style="color: rgba(255, 255, 255, 0.5); font-size: 12px; margin-left: 8px">
                系统默认
              </span>
            </div>
          </div>
        </template>
      </el-tree>
      </div>

      <!-- 列表视图（支持树形折叠） -->
      <el-table
        v-else
        v-loading="loading"
        :data="treeTableData"
        stripe
        border
        row-key="id"
        :tree-props="needPagination ? undefined : { children: 'children', indent: 40 }"
        :row-class-name="getRowClassName"
        :default-expand-all="!needPagination"
        class="entity-types-table"
        style="margin-top: 20px; width: 100%"
        table-layout="auto"
        header-cell-class-name="custom-header-cell"
      >
        <el-table-column prop="code" label="代码" width="250" min-width="200" class-name="code-column" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="code-cell-wrapper" :style="`padding-left: ${(row.level - 1) * 40}px;`">
              {{ row.code }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" width="220" class-name="name-column">
          <template #default="{ row }">
            <div class="name-cell-wrapper" :class="`level-${row.level}`" :style="`padding-left: ${(row.level - 1) * 40}px;`">
              <div class="name-cell">
                <el-tag :type="row.tag_type || 'info'" :color="row.color" size="small">
                  {{ row.name }}
                </el-tag>
                <el-tag v-if="row.level > 1" type="info" size="small" class="level-tag">L{{ row.level }}</el-tag>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="父类型" width="120" v-if="needPagination">
          <template #default="{ row }">
            <span v-if="row.parent_id">
              {{ getParentTypeName(row.parent_id) }}
            </span>
            <span v-else style="color: #909399">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="350" show-overflow-tooltip />
        <el-table-column prop="icon" label="图标" width="100">
          <template #default="{ row }">
            <el-icon v-if="row.icon">
              <component :is="row.icon" />
            </el-icon>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column prop="is_system" label="类型" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_system" type="warning" size="small">系统</el-tag>
            <el-tag v-else type="success" size="small">自定义</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_enabled"
              :disabled="row.is_system"
              @change="handleToggle(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="!row.is_system"
              type="primary"
              link
              size="small"
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
            <el-button
              v-if="!row.is_system"
              type="danger"
              link
              size="small"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
            <el-button
              v-if="row.level < 3"
              type="success"
              link
              size="small"
              @click="handleCreateChild(row)"
            >
              添加子类型
            </el-button>
            <span v-if="row.is_system" style="color: rgba(255, 255, 255, 0.5); font-size: 12px">
              系统默认
            </span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页（列表视图时显示） -->
      <div v-if="!showTreeView && pagination.total > 0" class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadEntityTypes"
          @current-change="loadEntityTypes"
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="showDialog"
      :title="editingType ? '编辑实体类型' : (parentTypeForChild ? `创建子类型（${parentTypeForChild.name}）` : '创建实体类型')"
      width="600px"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="类型代码" prop="code" v-if="!editingType">
          <el-input
            v-model="formData.code"
            placeholder="如：method、tool、framework"
            :disabled="editingType"
          />
          <div class="form-tip">唯一标识，创建后不可修改</div>
        </el-form-item>
        <el-form-item label="类型名称" prop="name">
          <el-input v-model="formData.name" placeholder="如：方法、工具、框架" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="类型描述"
          />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="formData.icon" placeholder="图标名称（如：user、location）" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-color-picker v-model="formData.color" />
        </el-form-item>
        <el-form-item label="标签类型">
          <el-select v-model="formData.tag_type" placeholder="选择标签类型" style="width: 100%">
            <el-option label="默认" value="" />
            <el-option label="danger" value="danger" />
            <el-option label="success" value="success" />
            <el-option label="primary" value="primary" />
            <el-option label="warning" value="warning" />
            <el-option label="info" value="info" />
          </el-select>
        </el-form-item>
        <el-form-item label="父类型" v-if="!editingType || (editingType.level < 3 && !editingType.is_system)">
          <el-select
            v-model="formData.parent_id"
            placeholder="选择父类型（可选，最多3级）"
            clearable
            style="width: 100%"
            :disabled="(editingType && editingType.level >= 3) || (editingType && editingType.is_system)"
          >
            <el-option
              v-for="type in availableParentTypes"
              :key="type.id"
              :label="getTypePath(type)"
              :value="type.id"
            />
          </el-select>
          <div class="form-tip">
            {{ formData.parent_id ? `当前层级: ${getCurrentLevel()}级` : '一级分类（根分类）' }}
            <span v-if="getCurrentLevel() >= 3" style="color: #f56c6c">（已达最大层级）</span>
          </div>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="formData.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="formData.is_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import {
  getEntityTypes,
  getEntityTypeTree,
  createEntityType,
  updateEntityType,
  deleteEntityType,
  toggleEntityType,
  type EntityType,
  type EntityTypeCreate,
  type EntityTypeUpdate
} from '@/api/modules/knowledge-graph'

const loading = ref(false)
const searchKeyword = ref('')
const filterEnabled = ref<boolean | ''>('')
const filterSystem = ref<boolean | ''>('')
const filterLevel = ref<number | ''>('')
const showTreeView = ref(false)
const entityTypes = ref<EntityType[]>([])
const typeTree = ref<EntityType[]>([])
const showDialog = ref(false)
const editingType = ref<EntityType | null>(null)
const parentTypeForChild = ref<EntityType | null>(null)
const formRef = ref()

// 分页状态
const pagination = ref({
  page: 1,
  size: 20,
  total: 0
})

const formData = ref<EntityTypeCreate & { id?: number }>({
  code: '',
  name: '',
  description: '',
  icon: '',
  color: '',
  tag_type: '',
  sort_order: 0,
  is_enabled: true,
  parent_id: null
})

const formRules = {
  code: [{ required: true, message: '请输入类型代码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入类型名称', trigger: 'blur' }]
}

// 将平铺数据转换为树形结构（用于表格树形展示）
const treeTableData = computed(() => {
  // 如果使用了搜索或筛选，不展示树形结构（因为会打乱层级），使用平铺展示
  // 注意：只有在有搜索或筛选条件时才使用平铺，否则构建树形结构
  if (needPagination.value) {
    // 有搜索或筛选时返回平铺数据，移除children属性
    return entityTypes.value.map(item => ({ ...item, children: undefined }))
  }
  
  // 如果没有数据，返回空数组
  if (entityTypes.value.length === 0) {
    return []
  }
  
  // 构建父子映射
  const typeMap = new Map<number, EntityType & { children?: EntityType[] }>()
  const rootTypes: (EntityType & { children?: EntityType[] })[] = []
  
  // 先创建所有节点（深拷贝，避免修改原始数据）
  entityTypes.value.forEach(type => {
    typeMap.set(type.id, { ...type, children: [] })
  })
  
  // 构建树形结构
  entityTypes.value.forEach(type => {
    const node = typeMap.get(type.id)!
    if (type.parent_id && typeMap.has(type.parent_id)) {
      // 有父节点，添加到父节点的children
      const parent = typeMap.get(type.parent_id)!
      if (!parent.children) {
        parent.children = []
      }
      parent.children.push(node)
    } else {
      // 根节点（没有parent_id或父节点不在当前数据中）
      rootTypes.push(node)
    }
  })
  
  // 按排序顺序排序（每个层级的children单独排序）
  const sortTree = (nodes: (EntityType & { children?: EntityType[] })[]) => {
    nodes.sort((a, b) => {
      // 同一层级内按sort_order排序
      return a.sort_order - b.sort_order
    })
    // 递归排序子节点
    nodes.forEach(node => {
      if (node.children && node.children.length > 0) {
        sortTree(node.children)
      }
    })
  }
  
  sortTree(rootTypes)
  return rootTypes
})

// 注意：现在使用服务端分页，不再需要客户端过滤
// 保留computed用于兼容性，但实际数据来自服务端
const filteredTypes = computed(() => entityTypes.value)

// 可用的父类型（排除当前编辑的类型及其子类型，且层级小于3）
const availableParentTypes = computed(() => {
  let types = entityTypes.value.filter(t => t.is_enabled && t.level < 3)
  
  // 如果正在编辑，排除当前类型及其所有子类型
  if (editingType.value) {
    const excludeIds = new Set([editingType.value.id])
    const collectChildren = (parentId: number) => {
      entityTypes.value.forEach(t => {
        if (t.parent_id === parentId) {
          excludeIds.add(t.id)
          collectChildren(t.id)
        }
      })
    }
    collectChildren(editingType.value.id)
    types = types.filter(t => !excludeIds.has(t.id))
  }
  
  return types.sort((a, b) => {
    if (a.level !== b.level) return a.level - b.level
    return a.sort_order - b.sort_order
  })
})

// 获取当前层级
const getCurrentLevel = () => {
  if (!formData.value.parent_id) return 1
  const parent = entityTypes.value.find(t => t.id === formData.value.parent_id)
  return parent ? parent.level + 1 : 1
}

// 获取类型路径（用于显示）
const getTypePath = (type: EntityType): string => {
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

// 获取父类型名称
const getParentTypeName = (parentId: number): string => {
  const parent = entityTypes.value.find(t => t.id === parentId)
  return parent ? parent.name : '-'
}

// 获取表格行的类名（用于层级样式）
const getRowClassName = ({ row }: { row: EntityType }) => {
  return `level-${row.level}`
}

// 检查是否需要使用分页
const needPagination = computed(() => {
  // 如果有搜索关键词或筛选条件，使用分页
  return !!(searchKeyword.value || filterLevel.value !== '' || filterEnabled.value !== '' || filterSystem.value !== '')
})

// 加载实体类型列表
const loadEntityTypes = async () => {
  loading.value = true
  try {
    const params: any = {}
    
    // 如果有搜索或筛选条件，使用分页
    if (needPagination.value) {
      // 有搜索或筛选：使用分页
      params.page = pagination.value.page
      params.size = pagination.value.size
    } else {
      // 没有搜索或筛选：加载所有数据以确保树形结构完整
      params.page = 1
      params.size = 1000  // 加载足够多的数据
      params.include_children = true  // 包含子类型，确保层级完整
    }
    
    if (filterEnabled.value !== '') {
      params.is_enabled = filterEnabled.value
    }
    if (filterSystem.value !== '') {
      params.is_system = filterSystem.value
    }
    if (filterLevel.value !== '') {
      params.level = filterLevel.value
    }
    if (searchKeyword.value) {
      params.keyword = searchKeyword.value
    }

    const res = await getEntityTypes(params)
    const data = res.data as any
    entityTypes.value = data.list || data.items || data.types || []
    pagination.value.total = data.total || 0
    
    // 如果使用树形视图，加载树形数据
    if (showTreeView.value) {
      await loadTypeTree()
    }
  } catch (error: any) {
    ElMessage.error('加载实体类型失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 加载类型树
const loadTypeTree = async () => {
  try {
    const res = await getEntityTypeTree()
    typeTree.value = (res.data as any).tree || []
  } catch (error: any) {
    ElMessage.error('加载类型树失败: ' + (error.message || '未知错误'))
  }
}

// 搜索
const handleSearch = () => {
  // 重置到第一页并重新加载
  pagination.value.page = 1
  loadEntityTypes()
}

// 筛选条件变化
const handleFilterChange = () => {
  // 重置到第一页并重新加载
  pagination.value.page = 1
  loadEntityTypes()
}

// 创建
const handleCreate = () => {
  editingType.value = null
  parentTypeForChild.value = null
  formData.value = {
    code: '',
    name: '',
    description: '',
    icon: '',
    color: '',
    tag_type: '',
    sort_order: 0,
    is_enabled: true,
    parent_id: null
  }
  showDialog.value = true
}

// 创建子类型
const handleCreateChild = (parent: EntityType) => {
  if (parent.level >= 3) {
    ElMessage.warning('已达到最大层级（3级），无法继续添加子类型')
    return
  }
  editingType.value = null
  parentTypeForChild.value = parent
  formData.value = {
    code: '',
    name: '',
    description: '',
    icon: '',
    color: '',
    tag_type: '',
    sort_order: 0,
    is_enabled: true,
    parent_id: parent.id
  }
  showDialog.value = true
}

// 编辑
const handleEdit = (type: EntityType) => {
  editingType.value = type
  parentTypeForChild.value = null
  formData.value = {
    id: type.id,
    code: type.code,
    name: type.name,
    description: type.description || '',
    icon: type.icon || '',
    color: type.color || '',
    tag_type: type.tag_type || '',
    sort_order: type.sort_order,
    is_enabled: type.is_enabled,
    parent_id: type.parent_id || null
  }
  showDialog.value = true
}

// 提交
const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return

    try {
      // 验证层级限制
      const currentLevel = getCurrentLevel()
      if (currentLevel > 3) {
        ElMessage.error('实体类型最多支持3级分类，当前层级超过限制')
        return
      }
      
      if (editingType.value) {
        // 更新
        const updateData: EntityTypeUpdate = {
          name: formData.value.name,
          description: formData.value.description,
          icon: formData.value.icon,
          color: formData.value.color,
          tag_type: formData.value.tag_type,
          sort_order: formData.value.sort_order,
          is_enabled: formData.value.is_enabled
        }
        // 系统类型不允许修改parent_id
        if (!editingType.value.is_system) {
          updateData.parent_id = formData.value.parent_id || null
        }
        await updateEntityType(editingType.value.id, updateData)
        ElMessage.success('更新成功')
      } else {
        // 创建
        const createData: EntityTypeCreate = {
          ...formData.value,
          parent_id: formData.value.parent_id || null
        }
        await createEntityType(createData)
        ElMessage.success('创建成功')
      }
      showDialog.value = false
      await loadEntityTypes()
    } catch (error: any) {
      ElMessage.error((error.message || '操作失败'))
    }
  })
}

// 删除
const handleDelete = async (type: EntityType) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除实体类型 "${type.name}" 吗？`,
      '确认删除',
      {
        type: 'warning'
      }
    )
    await deleteEntityType(type.id)
    ElMessage.success('删除成功')
    loadEntityTypes()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

// 启用/禁用
const handleToggle = async (type: EntityType) => {
  // 系统类型不允许修改状态
  if (type.is_system) {
    ElMessage.warning('系统默认类型不允许修改状态')
    type.is_enabled = true // 强制保持启用状态
    return
  }
  
  try {
    await toggleEntityType(type.id, type.is_enabled)
    ElMessage.success(`${type.is_enabled ? '启用' : '禁用'}成功`)
  } catch (error: any) {
    type.is_enabled = !type.is_enabled // 回滚
    ElMessage.error(error.message || '操作失败')
  }
}

// 监听树形视图切换
watch(showTreeView, (newVal) => {
  if (newVal) {
    loadTypeTree()
  }
})

onMounted(() => {
  loadEntityTypes()
})
</script>

<style scoped lang="scss">
.entity-types-container {
  padding: 20px;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .filter-bar {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
  }

  .form-tip {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
  }

  // 树形视图容器
  .tree-view-container {
    margin-top: 20px;
    padding: 24px;
    background: rgba(6, 12, 24, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(10px);
    min-height: 400px;
  }

  // 树形组件样式优化
  :deep(.entity-type-tree) {
    background: transparent !important;
    color: rgba(255, 255, 255, 0.9);
    
    .el-tree-node {
      margin-bottom: 8px;
      
      .el-tree-node__content {
        height: auto;
        min-height: 48px;
        padding: 12px 18px;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 6px;
        
        &:hover {
          background: rgba(64, 158, 255, 0.15) !important;
          border-color: rgba(64, 158, 255, 0.4);
          transform: translateX(4px);
          box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
        }
      }
      
      &.is-current > .el-tree-node__content {
        background: rgba(64, 158, 255, 0.2) !important;
        border-color: rgba(64, 158, 255, 0.5);
        box-shadow: 0 4px 16px rgba(64, 158, 255, 0.3);
      }
      
      .el-tree-node__expand-icon {
        color: rgba(255, 255, 255, 0.7);
        font-size: 18px;
        padding: 6px;
        border-radius: 6px;
        transition: all 0.2s;
        width: 28px;
        height: 28px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        
        &:hover {
          color: #409eff;
          background: rgba(64, 158, 255, 0.15);
          transform: scale(1.1);
        }
      }
      
      .el-tree-node__label {
        width: 100%;
      }
    }
    
    // 子节点的缩进和连接线
    .el-tree-node__children {
      padding-left: 32px;
      margin-top: 4px;
      position: relative;
      
      &::before {
        content: '';
        position: absolute;
        left: 16px;
        top: 0;
        bottom: 0;
        width: 2px;
        background: linear-gradient(
          to bottom,
          transparent 0%,
          rgba(64, 158, 255, 0.4) 5%,
          rgba(64, 158, 255, 0.5) 50%,
          rgba(64, 158, 255, 0.4) 95%,
          transparent 100%
        );
        border-radius: 1px;
      }
    }
  }

  .tree-node {
    display: flex;
    align-items: center;
    flex: 1;
    font-size: 14px;
    padding: 4px 0;
    width: 100%;

    .tree-node-info {
      margin-left: 14px;
      flex: 1;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .tree-node-actions {
      margin-left: auto;
      display: flex;
      gap: 10px;
      opacity: 0.6;
      transition: opacity 0.2s;
    }
    
    &:hover .tree-node-actions {
      opacity: 1;
    }
  }

  // 分页样式
  .pagination {
    margin-top: 20px;
    display: flex;
    justify-content: center;
  }

  // 优化分页组件样式（深色主题）
  :deep(.el-pagination) {
    color: rgba(255, 255, 255, 0.85);
    
    .el-pagination__total,
    .el-pagination__jump {
      color: rgba(255, 255, 255, 0.85) !important;
    }
    
    .btn-prev,
    .btn-next {
      color: rgba(255, 255, 255, 0.85) !important;
      background-color: rgba(255, 255, 255, 0.05) !important;
      border-color: rgba(255, 255, 255, 0.2) !important;
      
      &:hover:not(.disabled) {
        color: #409eff !important;
        border-color: #409eff !important;
        background-color: rgba(64, 158, 255, 0.1) !important;
      }
      
      &.disabled {
        color: rgba(255, 255, 255, 0.3) !important;
        border-color: rgba(255, 255, 255, 0.1) !important;
        background-color: transparent !important;
        cursor: not-allowed;
      }
    }
    
    .el-pager {
      li {
        color: rgba(255, 255, 255, 0.85) !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        
        &:hover {
          color: #409eff !important;
          border-color: #409eff !important;
          background-color: rgba(64, 158, 255, 0.1) !important;
        }
        
        &.is-active {
          color: #ffffff !important;
          background-color: #409eff !important;
          border-color: #409eff !important;
          font-weight: 600;
        }
      }
    }
    
    .el-pagination__editor {
      .el-input {
        .el-input__inner {
          background-color: rgba(255, 255, 255, 0.08) !important;
          border-color: rgba(255, 255, 255, 0.2) !important;
          color: rgba(255, 255, 255, 0.95) !important;
          font-size: 14px;
          
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
    
    .el-pagination__sizes {
      .el-select {
        .el-input__inner {
          background-color: rgba(255, 255, 255, 0.08) !important;
          border-color: rgba(255, 255, 255, 0.2) !important;
          color: rgba(255, 255, 255, 0.95) !important;
          
          &:hover {
            border-color: #409eff !important;
          }
        }
        
        .el-input__wrapper {
          background-color: rgba(255, 255, 255, 0.08) !important;
          border-color: rgba(255, 255, 255, 0.2) !important;
        }
      }
      
      .el-select-dropdown {
        background-color: rgba(30, 35, 50, 0.95) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        
        .el-select-dropdown__item {
          color: rgba(255, 255, 255, 0.85) !important;
          
          &:hover {
            background-color: rgba(64, 158, 255, 0.2) !important;
            color: #409eff !important;
          }
          
          &.selected {
            color: #409eff !important;
            background-color: rgba(64, 158, 255, 0.15) !important;
          }
        }
      }
    }
  }

  // 表格样式优化
  :deep(.entity-types-table),
  :deep(.el-table) {
    --el-table-row-hover-bg-color: rgba(64, 158, 255, 0.12) !important;
    --el-table-bg-color: rgba(6, 12, 24, 0.4) !important;
    --el-table-header-bg-color: rgba(6, 12, 24, 0.8) !important;
    --el-table-tr-bg-color: rgba(6, 12, 24, 0.4) !important;
    background-color: rgba(6, 12, 24, 0.4) !important;
    color: rgba(255, 255, 255, 0.85);
    
    // 表格整体背景
    .el-table__inner-wrapper {
      background-color: rgba(6, 12, 24, 0.4) !important;
    }
    
    .el-table__header-wrapper {
      background-color: rgba(6, 12, 24, 0.8) !important;
      
      th {
        background-color: rgba(6, 12, 24, 0.8) !important;
        color: #ffffff !important;
        border-bottom: 2px solid rgba(255, 255, 255, 0.15) !important;
        font-weight: 600 !important;
        text-align: center !important;
        
        .cell {
          color: #ffffff !important;
          font-weight: 600 !important;
          font-size: 16px !important;
          text-align: center !important;
          padding: 14px 0 !important;
          line-height: 1.5 !important;
        }
      }
    }
    
    // 确保表头样式优先级最高
    :deep(.el-table__header) {
      th {
        text-align: center !important;
        
        .cell {
          text-align: center !important;
          color: #ffffff !important;
          font-size: 16px !important;
          font-weight: 600 !important;
        }
      }
    }
    
    // 使用自定义类名确保样式生效
    :deep(.custom-header-cell) {
      text-align: center !important;
      background-color: rgba(6, 12, 24, 0.8) !important;
      
      .cell {
        text-align: center !important;
        color: #ffffff !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        padding: 14px 0 !important;
      }
    }
    
    // 全局表头样式
    :deep(.entity-types-table .el-table__header-wrapper .el-table__header th),
    :deep(.el-table .el-table__header-wrapper .el-table__header th) {
      text-align: center !important;
      
      .cell {
        text-align: center !important;
        color: #ffffff !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        padding: 14px 0 !important;
      }
    }
    
    .el-table__body-wrapper {
      background-color: rgba(6, 12, 24, 0.4) !important;
      
      tr {
        background-color: rgba(6, 12, 24, 0.4) !important;
        color: rgba(255, 255, 255, 0.85);
        
        td {
          background-color: rgba(6, 12, 24, 0.4) !important;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          color: rgba(255, 255, 255, 0.85);
        }
        
        &:hover {
          background-color: rgba(64, 158, 255, 0.12) !important;
          
          td {
            background-color: rgba(64, 158, 255, 0.12) !important;
            color: rgba(255, 255, 255, 0.95);
          }
        }
        
        // 隔行换色（条纹效果）
        &:nth-child(even) {
          background-color: rgba(255, 255, 255, 0.03) !important;
          
          td {
            background-color: rgba(255, 255, 255, 0.03) !important;
          }
          
          &:hover {
            background-color: rgba(64, 158, 255, 0.12) !important;
            
            td {
              background-color: rgba(64, 158, 255, 0.12) !important;
              color: rgba(255, 255, 255, 0.95);
            }
          }
        }
      }
    }
    
    // 确保表格边框也是深色
    &::before {
      background-color: rgba(255, 255, 255, 0.1) !important;
    }
    
    .el-table__inner-wrapper::before {
      background-color: rgba(255, 255, 255, 0.1) !important;
    }
  }
  
  // 树形表格缩进优化 - 使用更大的缩进，让层级更明显
  // 每级缩进40px，这样二级=40px，三级=80px，层级非常清晰
  :deep(.entity-types-table .el-table__indent),
  :deep(.el-table .el-table__indent) {
    width: 40px !important;
    min-width: 40px !important;
    max-width: 40px !important;
    display: inline-block !important;
    padding: 0 !important;
    margin: 0 !important;
    flex: none !important;
    position: relative;
    
    // 添加层级连接线 - 实线效果，更明显
    &::after {
      content: '';
      position: absolute;
      left: 50%;
      top: 0;
      bottom: 0;
      width: 2px;
      background: linear-gradient(
        to bottom,
        rgba(64, 158, 255, 0.2) 0%,
        rgba(64, 158, 255, 0.5) 50%,
        rgba(64, 158, 255, 0.2) 100%
      );
      transform: translateX(-50%);
      border-radius: 1px;
    }
  }
  
  // 名称列的自定义样式 - 手动添加缩进和左侧边框区分层级
  .name-cell-wrapper {
    position: relative;
    min-height: 40px;
    display: flex;
    align-items: center;
    width: 100%;
    transition: padding-left 0.2s;
    
    // 左侧层级指示条 - 位置根据缩进自动调整
    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 4px;
      border-radius: 0 2px 2px 0;
      transition: all 0.2s;
      z-index: 1;
    }
    
    .name-cell {
      display: flex;
      align-items: center;
      gap: 8px;
      padding-left: 8px;
      width: 100%;
      position: relative;
      z-index: 2;
    }
    
    // 一级分类 - 无缩进，蓝色边框
    &.level-1 {
      &::before {
        background: linear-gradient(to bottom, rgba(64, 158, 255, 0.6), rgba(64, 158, 255, 0.4));
        box-shadow: 0 0 8px rgba(64, 158, 255, 0.3);
        left: 0;
      }
      
      .name-cell {
        font-weight: 500;
      }
    }
    
    // 二级分类 - 40px缩进，绿色边框
    &.level-2 {
      &::before {
        background: linear-gradient(to bottom, rgba(103, 194, 58, 0.6), rgba(103, 194, 58, 0.4));
        box-shadow: 0 0 8px rgba(103, 194, 58, 0.3);
        left: 0;
      }
      
      .name-cell {
        opacity: 0.95;
      }
    }
    
    // 三级分类 - 80px缩进，橙色边框
    &.level-3 {
      &::before {
        background: linear-gradient(to bottom, rgba(230, 162, 60, 0.6), rgba(230, 162, 60, 0.4));
        box-shadow: 0 0 8px rgba(230, 162, 60, 0.3);
        left: 0;
      }
      
      .name-cell {
        opacity: 0.9;
      }
    }
  }
  
  // 代码列的单元格样式
  :deep(.code-column) {
    .cell {
      padding: 10px 0 !important;
    }
  }
  
  .code-cell-wrapper {
    padding-left: 8px;
    padding-right: 8px;
    transition: padding-left 0.2s;
    word-break: break-all;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
    max-width: 100%;
  }
  
  // 名称列的单元格样式
  :deep(.name-column) {
    .cell {
      padding: 10px 0 !important;
    }
  }
  
  // 确保表格行也应用层级背景
  :deep(.entity-types-table .el-table__body-wrapper) {
    .el-table__row {
      &.level-2 {
        background-color: rgba(103, 194, 58, 0.02) !important;
        
        td {
          background-color: rgba(103, 194, 58, 0.02) !important;
        }
      }
      
      &.level-3 {
        background-color: rgba(230, 162, 60, 0.02) !important;
        
        td {
          background-color: rgba(230, 162, 60, 0.02) !important;
        }
      }
    }
  }
  
  // 展开图标优化 - 更大更明显
  :deep(.entity-types-table .el-table__expand-icon),
  :deep(.el-table .el-table__expand-icon) {
    margin-right: 10px;
    font-size: 18px;
    color: rgba(255, 255, 255, 0.8);
    width: 24px;
    height: 24px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: all 0.2s;
    
    &:hover {
      color: #409eff;
      background-color: rgba(64, 158, 255, 0.1);
    }
  }
  
  // 展开图标样式
  :deep(.entity-types-table .el-table__expand-icon) {
    margin-right: 8px;
    font-size: 16px;
    color: rgba(255, 255, 255, 0.7);
    
    &:hover {
      color: #409eff;
    }
  }
  
  :deep(.el-table .el-table__expand-icon) {
    margin-right: 8px;
    font-size: 16px;
    color: rgba(255, 255, 255, 0.7);
    
    &:hover {
      color: #409eff;
    }
  }
}
</style>

