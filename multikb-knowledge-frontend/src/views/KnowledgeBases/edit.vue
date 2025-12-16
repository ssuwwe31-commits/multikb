<template>
  <el-card>
    <template #header>
      <span>编辑知识库</span>
    </template>

    <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
      <el-form-item label="名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入知识库名称" disabled />
      </el-form-item>

      <el-form-item label="描述" prop="description">
        <el-input v-model="form.description" type="textarea" :rows="4" placeholder="请输入知识库描述" />
      </el-form-item>

      <el-form-item label="分类" prop="category_id">
        <el-select v-model="form.category_id" placeholder="请选择分类" clearable :loading="loadingCategories">
          <el-option
            v-for="opt in categoryOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="状态" prop="is_active">
        <el-switch
          v-model="form.is_active"
          :active-value="true"
          :inactive-value="false"
          active-text="启用"
          inactive-text="禁用"
        />
      </el-form-item>

      <el-form-item label="标签" prop="tags">
        <el-select
          v-model="form.tags"
          multiple
          filterable
          allow-create
          placeholder="请输入或选择标签"
        >
          <el-option
            v-for="tag in tags"
            :key="tag"
            :label="tag"
            :value="tag"
          />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="handleSubmit" :loading="loading">保存</el-button>
        <el-button @click="handleCancel">取消</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getKnowledgeBaseDetail, updateKnowledgeBase, getCategories } from '@/api/modules/knowledge-bases'

const route = useRoute()
const router = useRouter()
const knowledgeBaseId = Number(route.params.id)

const form = ref({
  name: '',
  description: '',
  category_id: null as number | null,
  is_active: true,
  tags: [] as string[]
})

const rules = {
  name: [{ required: true, message: '请输入知识库名称', trigger: 'blur' }]
}

const loading = ref(false)
const loadingCategories = ref(false)
const categoryOptions = ref<{ label: string; value: number }[]>([])
const tags = ref<string[]>([])
const formRef = ref()

const loadDetail = async () => {
  loading.value = true
  try {
    const res = await getKnowledgeBaseDetail(knowledgeBaseId)
    Object.assign(form.value, res.data)
  } catch (error) {
    ElMessage.error('加载详情失败')
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  try {
    loadingCategories.value = true
    const res = await getCategories()
    const list = res?.data?.list ?? res?.data ?? []
    categoryOptions.value = list.map((c: any) => ({ label: c.name, value: c.id }))
  } catch (error) {
    // 忽略错误
  } finally {
    loadingCategories.value = false
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid: boolean) => {
    if (valid) {
      loading.value = true
      try {
        // 仅提交允许修改的字段
        await updateKnowledgeBase(knowledgeBaseId, {
          description: form.value.description,
          category_id: form.value.category_id as number | undefined,
          is_active: form.value.is_active
        })
        ElMessage.success('保存成功')
        router.push(`/knowledge-bases/${knowledgeBaseId}`)
      } catch (error) {
        ElMessage.error('保存失败')
      } finally {
        loading.value = false
      }
    }
  })
}

const handleCancel = () => {
  router.back()
}

onMounted(() => {
  loadCategories()
  loadDetail()
})
</script>

<style lang="scss" scoped>
:deep(.el-card) {
  background: rgba(6, 12, 24, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
  
  .el-card__header {
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.95);
    font-size: 18px;
    font-weight: 600;
  }
  
  .el-card__body {
    color: rgba(255, 255, 255, 0.85);
  }
}

.el-form {
  max-width: 800px;
  
  /* 表单标签样式 */
  :deep(.el-form-item__label) {
    color: rgba(255, 255, 255, 0.95) !important;
    font-size: 15px;
    font-weight: 600;
    
    &::before {
      color: #f56c6c !important;
    }
  }
  
  /* 输入框样式 */
  :deep(.el-input__inner),
  :deep(.el-textarea__inner) {
    background: rgba(255, 255, 255, 0.08) !important;
    border-color: rgba(255, 255, 255, 0.2) !important;
    color: rgba(255, 255, 255, 0.95) !important;
    font-size: 15px;
    
    &::placeholder {
      color: rgba(255, 255, 255, 0.5) !important;
    }
    
    &:focus {
      border-color: #409eff !important;
      background: rgba(255, 255, 255, 0.12) !important;
    }
    
    &:disabled {
      background: rgba(255, 255, 255, 0.05) !important;
      color: rgba(255, 255, 255, 0.6) !important;
    }
  }
  
  /* 下拉选择框样式 */
  :deep(.el-select) {
    .el-input__inner {
      background: rgba(255, 255, 255, 0.08) !important;
      border-color: rgba(255, 255, 255, 0.2) !important;
      color: rgba(255, 255, 255, 0.95) !important;
    }
    
    .el-input__suffix {
      .el-select__caret {
        color: rgba(255, 255, 255, 0.6) !important;
      }
    }
  }
  
  /* 下拉选项样式 */
  :deep(.el-select-dropdown) {
    background: rgba(6, 12, 24, 0.98) !important;
    border: 1px solid rgba(64, 158, 255, 0.3) !important;
    
    .el-select-dropdown__item {
      color: rgba(255, 255, 255, 0.9) !important;
      background: transparent !important;
      
      &:hover {
        background: rgba(64, 158, 255, 0.15) !important;
        color: rgba(255, 255, 255, 1) !important;
      }
      
      &.selected {
        color: #409eff !important;
        background: rgba(64, 158, 255, 0.1) !important;
      }
    }
  }
  
  /* 开关样式 */
  :deep(.el-switch) {
    .el-switch__label {
      color: rgba(255, 255, 255, 0.9) !important;
      font-size: 14px;
      font-weight: 500;
      
      &.is-active {
        color: #409eff !important;
      }
    }
    
    .el-switch__core {
      background-color: rgba(255, 255, 255, 0.2) !important;
      border-color: rgba(255, 255, 255, 0.3) !important;
    }
    
    &.is-checked .el-switch__core {
      background-color: #409eff !important;
      border-color: #409eff !important;
    }
  }
  
  /* 按钮样式 */
  :deep(.el-button) {
    font-size: 15px;
    font-weight: 500;
    
    &:not(.el-button--primary):not(.el-button--danger) {
      color: rgba(255, 255, 255, 0.9) !important;
      border-color: rgba(255, 255, 255, 0.3) !important;
      background: rgba(255, 255, 255, 0.08) !important;
      
      &:hover {
        color: #409eff !important;
        border-color: #409eff !important;
        background: rgba(64, 158, 255, 0.1) !important;
      }
    }
    
    &.el-button--primary {
      background: #409eff !important;
      border-color: #409eff !important;
      
      &:hover {
        background: #66b1ff !important;
        border-color: #66b1ff !important;
      }
    }
  }
}
</style>
