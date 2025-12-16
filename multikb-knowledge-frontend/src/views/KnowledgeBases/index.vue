<template>
  <div class="knowledge-bases-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>知识库管理</span>
          <el-button type="primary" @click="handleCreate">创建知识库</el-button>
        </div>
      </template>

      <el-table :data="knowledgeBases" v-loading="loading">
        <el-table-column prop="name" label="名称">
          <template #default="{ row }">
            <el-link type="primary" @click="handleDetail(row)">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="category_name" label="分类">
          <template #default="{ row }">
            <el-tag v-if="row.category_name" type="info">
              {{ row.category_name }}
            </el-tag>
            <span v-else class="no-category">未分类</span>
          </template>
        </el-table-column>
        <el-table-column prop="document_count" label="文档数" width="100">
          <template #default="{ row }">
            <el-tag>{{ row.document_count || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="role" label="我的角色" width="120">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)">
              {{ getRoleText(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="visibility" label="共享状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.visibility === 'shared' ? 'success' : 'info'">
              {{ row.visibility === 'shared' ? '共享' : '私有' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320">
          <template #default="{ row }">
            <div class="actions">
              <el-button size="small" @click="handleDetail(row)">详情</el-button>
              <el-button size="small" @click="openMembersDialog(row)">成员</el-button>
              <el-button
                size="small"
                :disabled="!canManageKb(row)"
                @click="handleEdit(row)"
              >
                编辑
              </el-button>
              <el-button
                size="small"
                type="danger"
                :disabled="row.role !== 'owner'"
                @click="handleDelete(row)"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        :total="total"
        @current-change="loadData"
      />
    </el-card>

    <!-- 成员管理对话框 -->
    <el-dialog
      v-model="showMembers"
      :title="`成员管理 - ${currentKb?.name || ''}`"
      width="600px"
      class="members-dialog"
    >
      <el-table :data="members" v-loading="membersLoading" size="small">
        <el-table-column label="用户" width="200">
          <template #default="{ row }">
            {{ getUserDisplayName(row.user_id) }}
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="140">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)">
              {{ getRoleText(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="invited_by" label="邀请人ID" width="120" />
        <el-table-column prop="invited_at" label="邀请时间" />
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <template v-if="row.role === 'owner'">
              <span style="color: rgba(255, 255, 255, 0.5); font-size: 12px;">拥有者不可操作</span>
            </template>
            <template v-else>
              <el-button
                size="small"
                text
                @click="editMember(row)"
                :disabled="!canManageKb(currentKb)"
              >
                修改
              </el-button>
              <el-button
                size="small"
                text
                type="danger"
                @click="removeMember(row)"
                :disabled="!canManageKb(currentKb)"
              >
                移除
              </el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <el-divider />

      <el-form :model="memberForm" label-width="80px">
        <el-form-item label="用户">
          <el-select 
            v-model="memberForm.user_id" 
            placeholder="选择用户" 
            style="width: 100%;"
            filterable
            clearable
          >
            <el-option
              v-for="user in availableUserList"
              :key="user.id"
              :label="`${user.nickname || user.username} (${user.username})`"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="memberForm.role" placeholder="选择角色" style="width: 100%;">
            <el-option label="拥有者 (owner)" value="owner" />
            <el-option label="管理员 (admin)" value="admin" />
            <el-option label="编辑者 (editor)" value="editor" />
            <el-option label="查看者 (viewer)" value="viewer" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showMembers = false">关闭</el-button>
        <el-button type="primary" :disabled="!canManageKb(currentKb)" @click="saveMember">
          保存成员
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  getKnowledgeBases,
  deleteKnowledgeBase,
  getKnowledgeBaseMembers,
  addKnowledgeBaseMember,
  updateKnowledgeBaseMember,
  removeKnowledgeBaseMember,
  type KnowledgeBaseMember,
} from '@/api/modules/knowledge-bases'
import { getUserList, type User } from '@/api/modules/users'
import { useUserStore } from '@/stores/modules/user'
import type { KnowledgeBase } from '@/types'

const router = useRouter()
const userStore = useUserStore()

const knowledgeBases = ref<KnowledgeBase[]>([])
const loading = ref(false)
const page = ref(1)
const size = ref(20)
const total = ref(0)

// 成员管理
const showMembers = ref(false)
const membersLoading = ref(false)
const currentKb = ref<KnowledgeBase | null>(null)
const members = ref<KnowledgeBaseMember[]>([])
const memberForm = ref<{ user_id: number | null; role: string }>({ user_id: null, role: 'viewer' })
const userList = ref<User[]>([])
const userListLoading = ref(false)

// 过滤掉当前用户的用户列表（用于下拉选择）
const availableUserList = computed(() => {
  const currentUserId = userStore.user?.id
  if (!currentUserId) return userList.value
  return userList.value.filter(user => user.id !== currentUserId)
})

const loadData = async () => {
  loading.value = true
  try {
      const res = await getKnowledgeBases({ page: page.value, size: size.value })
      // 后端返回格式: { code: 0, message: "ok", data: { list: [], total: 0 } }
      // 响应拦截器已经返回了 response.data，所以 res 就是响应数据本身
      if (res && typeof res === 'object') {
      if (res.code === 0 && res.data) {
        knowledgeBases.value = res.data.list ?? res.data.items ?? []
        total.value = res.data.total ?? 0
      } else if (res.data) {
        // 兼容没有 code 字段的格式
        knowledgeBases.value = res.data.list ?? res.data.items ?? []
        total.value = res.data.total ?? 0
      } else {
        knowledgeBases.value = []
        total.value = 0
      }
    } else {
      knowledgeBases.value = []
      total.value = 0
    }
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || error.message || '加载失败')
    knowledgeBases.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const getRoleTagType = (role?: string) => {
  const map: Record<string, string> = {
    owner: 'warning', // 改为橙色/黄色，更柔和
    admin: 'warning',
    editor: 'success',
    viewer: 'info',
  }
  return map[role || 'viewer'] || 'info'
}

const getRoleText = (role?: string) => {
  const map: Record<string, string> = {
    owner: '拥有者',
    admin: '管理员',
    editor: '编辑者',
    viewer: '查看者',
  }
  return map[role || 'viewer'] || role || '查看者'
}

const getUserDisplayName = (userId: number) => {
  // 优先从成员数据中获取用户名
  const member = members.value.find(m => m.user_id === userId)
  if (member && member.username) {
    return `${member.nickname || member.username} (${member.username})`
  }
  // 如果成员数据中没有，从用户列表中查找
  const user = userList.value.find(u => u.id === userId)
  if (user) {
    return `${user.nickname || user.username} (${user.username})`
  }
  return `用户 ${userId}`
}

const canManageKb = (kb: KnowledgeBase | null | undefined) => {
  if (!kb) return false
  return kb.role === 'owner' || kb.role === 'admin'
}

const handleCreate = () => {
  router.push('/knowledge-bases/create')
}

const handleDetail = (row: KnowledgeBase) => {
  router.push(`/knowledge-bases/${row.id}`)
}

const handleEdit = (row: KnowledgeBase) => {
  router.push(`/knowledge-bases/${row.id}/edit`)
}

const handleDelete = async (row: KnowledgeBase) => {
  try {
    await ElMessageBox.confirm('确定要删除该知识库吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteKnowledgeBase(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 成员管理相关逻辑
const loadMembers = async (kbId: number) => {
  membersLoading.value = true
  try {
    const res = await getKnowledgeBaseMembers(kbId)
    if (res.code === 0) {
      members.value = res.data || []
    } else {
      members.value = []
    }
  } catch (error) {
    members.value = []
  } finally {
    membersLoading.value = false
  }
}

const loadUserList = async () => {
  if (userList.value.length > 0) return // 已加载过，不再重复加载
  userListLoading.value = true
  try {
    const res = await getUserList()
    if (res.code === 0 && res.data) {
      userList.value = res.data
    }
  } catch (error) {
    console.error('加载用户列表失败:', error)
  } finally {
    userListLoading.value = false
  }
}

const openMembersDialog = async (kb: KnowledgeBase) => {
  currentKb.value = kb
  memberForm.value = { user_id: null, role: 'viewer' }
  showMembers.value = true
  await loadUserList() // 加载用户列表
  await loadMembers(kb.id)
}

const editMember = (member: KnowledgeBaseMember) => {
  // 不允许编辑拥有者
  if (member.role === 'owner') {
    ElMessage.warning('拥有者角色不可修改')
    return
  }
  memberForm.value = { user_id: member.user_id, role: member.role }
}

const saveMember = async () => {
  if (!currentKb.value || !memberForm.value.user_id) {
    ElMessage.warning('请选择用户')
    return
  }
  try {
    // 若成员已存在则更新角色，否则添加
    const exists = members.value.find(m => m.user_id === memberForm.value.user_id)
    if (exists) {
      // 不允许修改拥有者角色
      if (exists.role === 'owner') {
        ElMessage.warning('拥有者角色不可修改，知识库必须至少有一个拥有者')
        return
      }
      // 不允许将其他角色修改为 owner（转移所有权需要特殊处理）
      if (memberForm.value.role === 'owner') {
        ElMessage.warning('不能将成员角色设置为拥有者，如需转移所有权请联系系统管理员')
        return
      }
      await updateKnowledgeBaseMember(currentKb.value.id, memberForm.value.user_id, {
        role: memberForm.value.role,
      })
      ElMessage.success('成员角色已更新')
    } else {
      // 不允许直接添加 owner 角色
      if (memberForm.value.role === 'owner') {
        ElMessage.warning('不能直接添加拥有者角色，拥有者由系统自动创建')
        return
      }
      await addKnowledgeBaseMember(currentKb.value.id, {
        user_id: memberForm.value.user_id,
        role: memberForm.value.role,
      })
      ElMessage.success('成员已添加')
    }
    await loadMembers(currentKb.value.id)
    memberForm.value = { user_id: null, role: 'viewer' }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '保存成员失败')
  }
}

const removeMember = async (member: KnowledgeBaseMember) => {
  if (!currentKb.value) return
  // 不允许删除拥有者
  if (member.role === 'owner') {
    ElMessage.warning('拥有者不可移除，知识库必须至少有一个拥有者')
    return
  }
  try {
    await ElMessageBox.confirm('确定要移除该成员吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await removeKnowledgeBaseMember(currentKb.value.id, member.user_id)
    ElMessage.success('成员已移除')
    await loadMembers(currentKb.value.id)
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error?.response?.data?.detail || error?.message || '移除成员失败')
    }
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.knowledge-bases-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .no-category {
    color: #909399;
    font-size: 12px;
  }

  .actions {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
  }

  /* 调低表格行悬停高亮，避免过亮导致文字不清晰 */
  :deep(.el-table) {
    --el-table-row-hover-bg-color: rgba(180, 180, 180, 0.16);
  }

  /* 成员管理对话框深色主题样式 - 优化对比度 */
  :deep(.members-dialog) {
    .el-dialog {
      background-color: #2b2d30 !important; /* 使用更亮的灰色背景 */
      color: #ffffff !important; /* 纯白色文字，提高对比度 */
    }

    .el-dialog__header {
      background-color: #2b2d30 !important;
      border-bottom: 1px solid rgba(255, 255, 255, 0.15) !important;
      padding: 20px 20px 15px;
    }

    .el-dialog__title {
      color: #ffffff !important; /* 纯白色标题 */
      font-weight: 600;
      font-size: 16px;
    }

    .el-dialog__body {
      background-color: #2b2d30 !important;
      color: #ffffff !important; /* 纯白色文字 */
      padding: 20px;
    }

    .el-dialog__footer {
      background-color: #2b2d30 !important;
      border-top: 1px solid rgba(255, 255, 255, 0.15) !important;
      padding: 15px 20px 20px;
    }

    /* 表格样式 */
    .el-table {
      background-color: transparent !important;
      color: #ffffff !important; /* 纯白色文字 */
    }

    .el-table__header-wrapper {
      background-color: rgba(0, 0, 0, 0.3) !important; /* 稍微加深表头背景 */
    }

    .el-table th {
      background-color: rgba(0, 0, 0, 0.3) !important;
      color: #ffffff !important; /* 纯白色表头文字 */
      font-weight: 600;
      border-bottom: 1px solid rgba(255, 255, 255, 0.15) !important;
    }

    .el-table th > .cell {
      color: #ffffff !important; /* 纯白色 */
      font-weight: 600;
    }

    .el-table td {
      background-color: transparent !important;
      color: #ffffff !important; /* 纯白色单元格文字 */
      border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
    }

    .el-table td > .cell {
      color: #ffffff !important; /* 纯白色 */
    }

    .el-table__body tr:hover > td {
      background-color: rgba(64, 158, 255, 0.2) !important; /* 提高hover背景亮度 */
      color: #ffffff !important;
    }

    .el-table__body tr:hover > td > .cell {
      color: #ffffff !important;
    }

    /* 表单样式 */
    .el-form-item__label {
      color: #ffffff !important; /* 纯白色标签 */
      font-weight: 500;
    }

    .el-input__inner {
      background-color: rgba(255, 255, 255, 0.1) !important; /* 提高输入框背景亮度 */
      color: #ffffff !important; /* 纯白色输入文字 */
      border-color: rgba(255, 255, 255, 0.3) !important; /* 提高边框可见度 */
    }

    .el-input__inner::placeholder {
      color: rgba(255, 255, 255, 0.5) !important; /* 提高placeholder可见度 */
    }

    .el-select .el-input__inner {
      background-color: rgba(255, 255, 255, 0.1) !important;
      color: #ffffff !important;
    }

    /* 下拉选项样式 */
    .el-select-dropdown {
      background-color: #2b2d30 !important;
    }

    .el-select-dropdown__item {
      color: #ffffff !important;
    }

    .el-select-dropdown__item:hover {
      background-color: rgba(64, 158, 255, 0.2) !important;
      color: #ffffff !important;
    }

    /* 按钮文字颜色 */
    .el-button {
      color: #ffffff;
    }

    .el-button--text {
      color: rgba(255, 255, 255, 0.85) !important; /* 提高可见度 */
    }

    .el-button--text:hover {
      color: #409eff !important;
    }

    .el-button--text:disabled {
      color: rgba(255, 255, 255, 0.4) !important; /* 提高禁用状态可见度 */
    }

    /* 分割线 */
    .el-divider {
      border-color: rgba(255, 255, 255, 0.15) !important; /* 提高分割线可见度 */
    }
  }
}
</style>
