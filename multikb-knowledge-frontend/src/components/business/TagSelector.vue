<template>
  <div class="tag-selector">
      <!-- 已选择的标签 -->
      <div v-if="selectedTags.length > 0" class="selected-tags">
        <el-tag
          v-for="(tag, index) in selectedTags"
          :key="index"
          closable
          @close="removeTag(index)"
          style="margin-right: 8px; margin-bottom: 8px;"
        >
          {{ tag }}
        </el-tag>
      </div>

      <!-- 推荐标签 -->
      <div v-if="recommendedTags.length > 0" class="recommended-tags">
        <div class="tags-header">
          <span class="tags-title">推荐标签：</span>
        </div>
        <el-tag
          v-for="tag in recommendedTags"
          :key="tag"
          :effect="selectedTags.includes(tag) ? 'dark' : 'plain'"
          @click="toggleTag(tag)"
          class="tag-item"
        >
          {{ tag }}
        </el-tag>
      </div>

      <!-- 自定义标签输入 -->
      <el-input
        v-model="customTag"
        placeholder="输入自定义标签并按回车"
        @keydown.enter="addCustomTag"
        class="tag-input"
      >
        <template #append>
          <el-button @click="addCustomTag">添加</el-button>
        </template>
      </el-input>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  modelValue: string[]
  recommendedTags?: string[]
  maxTags?: number
}>()

const emit = defineEmits(['update:modelValue'])

const selectedTags = ref<string[]>([])
const customTag = ref('')
const recommendedTags = ref<string[]>([])

watch(() => props.modelValue, (val) => {
  selectedTags.value = val || []
}, { immediate: true })

watch(() => props.recommendedTags, (val) => {
  recommendedTags.value = val || []
}, { immediate: true })

// 切换标签
const toggleTag = (tag: string) => {
  const index = selectedTags.value.indexOf(tag)
  if (index > -1) {
    selectedTags.value.splice(index, 1)
  } else {
    if (props.maxTags && selectedTags.value.length >= props.maxTags) {
      ElMessage.warning(`最多只能选择${props.maxTags}个标签`)
      return
    }
    selectedTags.value.push(tag)
  }
  emit('update:modelValue', selectedTags.value)
}

// 移除标签
const removeTag = (index: number) => {
  selectedTags.value.splice(index, 1)
  emit('update:modelValue', selectedTags.value)
}

// 添加自定义标签
const addCustomTag = () => {
  if (!customTag.value.trim()) {
    return
  }

  if (selectedTags.value.includes(customTag.value.trim())) {
    ElMessage.warning('该标签已存在')
    return
  }

  if (props.maxTags && selectedTags.value.length >= props.maxTags) {
    ElMessage.warning(`最多只能选择${props.maxTags}个标签`)
    return
  }

  selectedTags.value.push(customTag.value.trim())
  emit('update:modelValue', selectedTags.value)
  customTag.value = ''
}

onMounted(() => {
  if (props.recommendedTags) {
    recommendedTags.value = props.recommendedTags
  }
})
</script>

<style lang="scss" scoped>
.tag-selector {
  .selected-tags {
    min-height: 32px;
    padding: 8px;
    border: 1px solid var(--el-border-color);
    border-radius: 4px;
    margin-bottom: 12px;
  }

  .recommended-tags {
    margin-bottom: 12px;

    .tags-header {
      margin-bottom: 8px;
      
      .tags-title {
        font-size: 14px;
        color: #e9eef5;
        font-weight: 600;
        letter-spacing: 0.2px;
        text-shadow: 0 1px 2px rgba(0,0,0,.35);
      }
    }

    .tag-item {
      margin-right: 8px;
      margin-bottom: 8px;
      cursor: pointer;
      transition: all 0.2s ease;
      border: 1px solid #60a5fa !important;
      background: rgba(59, 130, 246, 0.12) !important;
      color: #eaf2ff !important;
      box-shadow: 0 0 0 rgba(96,165,250,0);

      &:hover {
        transform: translateY(-1px) scale(1.04);
        box-shadow: 0 0 12px rgba(96,165,250,0.45);
      }
    }
  }

  .tag-input :deep(.el-input__inner) {
    color: var(--el-text-color-primary);
  }
}
</style>
