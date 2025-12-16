<template>
  <div class="create-knowledge-base-page">
    <el-card>
      <template #header>
        <span>创建知识库</span>
      </template>

      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="知识库名称" required>
          <el-input 
            v-model="form.name" 
            placeholder="请输入知识库名称"
            class="kb-name-input"
          />
        </el-form-item>

        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="4" placeholder="请输入描述" />
        </el-form-item>

        <el-form-item label="分类" prop="categoryValue">
          <el-select
            v-model="form.categoryValue"
            filterable
            allow-create
            default-first-option
            clearable
            :loading="loadingCategories"
            placeholder="选择或输入分类"
          >
            <el-option
              v-for="opt in categoryOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="saving">创建</el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createKnowledgeBase, getCategories } from '@/api/modules/knowledge-bases'

const router = useRouter()
const saving = ref(false)
const loadingCategories = ref(false)
const categoryOptions = ref<{ label: string; value: number }[]>([])

const form = ref({
  name: '',
  description: '',
  // 可能为 number(已有分类 id) 或 string(新输入分类名)
  categoryValue: '' as number | string | ''
})

const formRef = ref()
const rules = {
  name: [{ required: true, message: '请输入知识库名称', trigger: 'blur' }],
  categoryValue: [{ validator: (_: any, v: any, cb: any) => {
    if (typeof v === 'number') return cb()
    if (typeof v === 'string' && v.trim()) return cb()
    cb(new Error('请选择或输入分类'))
  }, trigger: 'change' }]
} as any

const loadCategories = async () => {
  try {
    loadingCategories.value = true
    const res = await getCategories()
    const list = res?.data?.list ?? res?.data ?? []
    categoryOptions.value = list.map((c: any) => ({ label: c.name, value: c.id }))
  } catch (error) {
    ElMessage.error('加载分类列表失败')
  } finally {
    loadingCategories.value = false
  }
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload: any = {
      name: form.value.name,
      description: form.value.description
    }
    const cv = form.value.categoryValue
    if (typeof cv === 'number') payload.category_id = cv
    else if (typeof cv === 'string' && cv.trim()) payload.category_name = cv.trim()

    await createKnowledgeBase(payload)
    ElMessage.success('创建成功')
    router.push('/knowledge-bases')
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadCategories()
})
</script>

<style lang="scss" scoped>
.create-knowledge-base-page {
  max-width: 800px;
  margin: 0 auto;
  
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
  }
  
  /* 知识库名称输入框 - 禁用hover效果和提示，确保深色背景 */
  :deep(.kb-name-input) {
    /* 强制覆盖所有可能的背景色 */
    * {
      &::selection {
        background: rgba(64, 158, 255, 0.3) !important;
      }
    }
    
    /* 强制设置所有状态的深色背景 - 使用更具体的选择器覆盖所有情况 */
    .el-input__wrapper {
      transition: none !important;
      background: rgba(255, 255, 255, 0.08) !important;
      background-color: rgba(255, 255, 255, 0.08) !important;
      border-color: rgba(255, 255, 255, 0.2) !important;
      
      /* 强制覆盖所有可能的白色背景 */
      background-image: none !important;
      
      /* 所有状态下都保持深色背景 */
      &,
      &:hover,
      &:focus,
      &:active,
      &:focus-within,
      &.is-hovering,
      &.is-focus,
      &.is-disabled,
      &[class*="is-"] {
        background: rgba(255, 255, 255, 0.08) !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
        background-image: none !important;
      }
      
      /* 聚焦时稍微亮一点 */
      &.is-focus,
      &:focus-within {
        background: rgba(255, 255, 255, 0.12) !important;
        background-color: rgba(255, 255, 255, 0.12) !important;
        border-color: #409eff !important;
      }
      
      /* hover状态 */
      &:hover,
      &.is-hovering {
        box-shadow: none !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        background: rgba(255, 255, 255, 0.08) !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
        background-image: none !important;
      }
    }
    
    .el-input__inner {
      transition: none !important;
      background: rgba(255, 255, 255, 0.08) !important;
      background-color: rgba(255, 255, 255, 0.08) !important;
      background-image: none !important;
      border-color: transparent !important;
      color: rgba(255, 255, 255, 0.95) !important;
      
      /* 强制覆盖所有可能的白色背景 */
      &::-webkit-input-placeholder {
        color: rgba(255, 255, 255, 0.5) !important;
      }
      
      &::-moz-placeholder {
        color: rgba(255, 255, 255, 0.5) !important;
      }
      
      /* 所有状态下都保持深色背景 */
      &,
      &:hover,
      &:focus,
      &:active,
      &:not(:focus),
      &:not(:hover),
      &[class*="is-"] {
        background: rgba(255, 255, 255, 0.08) !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
        background-image: none !important;
        color: rgba(255, 255, 255, 0.95) !important;
      }
      
      /* hover状态 */
      &:hover {
        border-color: transparent !important;
        cursor: text !important;
        background: rgba(255, 255, 255, 0.08) !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
      }
      
      /* 聚焦状态 */
      &:focus {
        background: rgba(255, 255, 255, 0.12) !important;
        background-color: rgba(255, 255, 255, 0.12) !important;
        border-color: transparent !important;
      }
    }
    
    /* 禁用整个输入框的hover状态 */
    &:hover {
      .el-input__wrapper {
        box-shadow: none !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        background: rgba(255, 255, 255, 0.08) !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
        background-image: none !important;
      }
      
      .el-input__inner {
        background: rgba(255, 255, 255, 0.08) !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
        background-image: none !important;
      }
    }
    
    /* 确保失去焦点后也保持深色背景 */
    &:not(:focus-within) {
      .el-input__wrapper {
        background: rgba(255, 255, 255, 0.08) !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
        background-image: none !important;
      }
      
      .el-input__inner {
        background: rgba(255, 255, 255, 0.08) !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
        background-image: none !important;
      }
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
