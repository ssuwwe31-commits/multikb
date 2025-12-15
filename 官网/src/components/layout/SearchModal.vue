<template>
  <Teleport to="body">
    <Transition name="modal">
      <div 
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4"
        @click.self="close"
      >
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/50 backdrop-blur-sm" @click="close"></div>
        
        <!-- Search Modal -->
        <div class="relative w-full max-w-2xl bg-white dark:bg-gray-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <!-- Search Input -->
          <div class="p-4 border-b border-gray-200 dark:border-gray-700">
            <div class="flex items-center space-x-3">
              <svg class="w-5 h-5 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                ref="searchInput"
                v-model="query"
                type="text"
                placeholder="搜索文档、功能、API..."
                class="flex-1 bg-transparent border-none outline-none text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 text-lg"
                @input="handleSearch"
                @keydown.esc="close"
                @keydown.enter="handleEnter"
                @keydown.down.prevent="navigateDown"
                @keydown.up.prevent="navigateUp"
              />
              <kbd class="px-2 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded">
                ESC
              </kbd>
            </div>
          </div>

          <!-- Search Results -->
          <div class="max-h-96 overflow-y-auto">
            <div v-if="query.trim() === ''" class="p-8 text-center text-gray-500 dark:text-gray-400">
              <svg class="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <p>输入关键词开始搜索</p>
              <p class="text-sm mt-2">支持搜索文档、功能、API等</p>
            </div>

            <div v-else-if="results.length === 0 && !isSearching" class="p-8 text-center text-gray-500 dark:text-gray-400">
              <p>未找到相关结果</p>
              <p class="text-sm mt-2">尝试使用其他关键词</p>
            </div>

            <div v-else-if="isSearching" class="p-8 text-center text-gray-500 dark:text-gray-400">
              <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p class="mt-4">搜索中...</p>
            </div>

            <div v-else class="divide-y divide-gray-200 dark:divide-gray-700">
              <div
                v-for="(result, index) in results"
                :key="index"
                :class="[
                  'p-4 cursor-pointer transition-colors',
                  selectedIndex === index 
                    ? 'bg-blue-50 dark:bg-blue-900/30' 
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700'
                ]"
                @click="navigateTo(result)"
                @mouseenter="selectedIndex = index"
              >
                <div class="flex items-start space-x-3">
                  <div class="mt-1">
                    <component :is="result.icon" class="w-5 h-5 text-gray-400 dark:text-gray-500" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center space-x-2 mb-1">
                      <h3 class="font-semibold text-gray-900 dark:text-gray-100">{{ result.title }}</h3>
                      <span class="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                        {{ result.category }}
                      </span>
                    </div>
                    <p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">{{ result.description }}</p>
                    <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">{{ result.path }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <div class="flex items-center space-x-4">
                <span class="flex items-center">
                  <kbd class="px-1.5 py-0.5 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded">↑↓</kbd>
                  <span class="ml-1">导航</span>
                </span>
                <span class="flex items-center">
                  <kbd class="px-1.5 py-0.5 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded">↵</kbd>
                  <span class="ml-1">选择</span>
                </span>
              </div>
              <span>{{ results.length }} 个结果</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  'update:isOpen': [value: boolean]
}>()

const router = useRouter()
const query = ref('')
const results = ref<any[]>([])
const selectedIndex = ref(-1)
const isSearching = ref(false)
const searchInput = ref<HTMLInputElement | null>(null)

// Search data
const searchData = [
  // Pages
  { title: '首页', path: '/', category: '页面', description: 'Multikb Base 主页', icon: 'HomeIcon' },
  { title: '功能特性', path: '/features', category: '页面', description: '查看完整功能列表', icon: 'FeatureIcon' },
  { title: '文档', path: '/docs', category: '页面', description: '完整的使用文档', icon: 'DocsIcon' },
  { title: '定价', path: '/pricing', category: '页面', description: '查看定价方案', icon: 'PricingIcon' },
  { title: '案例', path: '/cases', category: '页面', description: '用户成功案例', icon: 'CaseIcon' },
  { title: '联系我们', path: '/contact', category: '页面', description: '联系我们的团队', icon: 'ContactIcon' },
  { title: '关于我们', path: '/about', category: '页面', description: '了解我们的团队', icon: 'AboutIcon' },
  { title: '更新日志', path: '/changelog', category: '页面', description: '查看版本更新历史', icon: 'ChangelogIcon' },
  
  // Documentation
  { title: '5分钟快速开始', path: '/docs/quick-start', category: '文档', description: '快速上手 Multikb Base', icon: 'DocsIcon' },
  { title: '核心概念', path: '/docs/core-concepts', category: '文档', description: '了解核心概念和术语', icon: 'DocsIcon' },
  { title: '系统要求', path: '/docs/system-requirements', category: '文档', description: '查看系统配置要求', icon: 'DocsIcon' },
  { title: 'Docker部署', path: '/docs/docker-deployment', category: '文档', description: '使用Docker快速部署', icon: 'DocsIcon' },
  { title: 'Kubernetes部署', path: '/docs/kubernetes-deployment', category: '文档', description: '在K8s集群中部署', icon: 'DocsIcon' },
  { title: 'API概览', path: '/docs/api-overview', category: '文档', description: 'RESTful API文档', icon: 'DocsIcon' },
  { title: '文档管理API', path: '/docs/api-document', category: '文档', description: '文档上传、查询、删除API', icon: 'DocsIcon' },
  { title: '问答API', path: '/docs/api-qa', category: '文档', description: '知识问答API接口', icon: 'DocsIcon' },
  { title: '搜索API', path: '/docs/api-search', category: '文档', description: '文档检索API', icon: 'DocsIcon' },
  
  // Features
  { title: '文档处理', path: '/features', category: '功能', description: '支持9种文档格式', icon: 'FeatureIcon' },
  { title: '知识问答', path: '/features', category: '功能', description: '多模态智能问答', icon: 'FeatureIcon' },
  { title: '安全扫描', path: '/features', category: '功能', description: 'ClamAV集成安全扫描', icon: 'FeatureIcon' },
  { title: '版本管理', path: '/features', category: '功能', description: '文档版本控制', icon: 'FeatureIcon' },
  { title: '多模态检索', path: '/features', category: '功能', description: '文本和图片检索', icon: 'FeatureIcon' },
]

// Icons - 使用 h 函数创建 SVG 组件
import { h } from 'vue'

const createIcon = (path: string) => {
  return () => h('svg', {
    fill: 'none',
    stroke: 'currentColor',
    viewBox: '0 0 24 24'
  }, [
    h('path', {
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round',
      'stroke-width': '2',
      d: path
    })
  ])
}

const HomeIcon = createIcon('M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6')
const FeatureIcon = createIcon('M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z')
const DocsIcon = createIcon('M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z')
const PricingIcon = createIcon('M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z')
const CaseIcon = createIcon('M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10')
const ContactIcon = createIcon('M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z')
const AboutIcon = createIcon('M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z')
const ChangelogIcon = createIcon('M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z')

const iconMap: Record<string, any> = {
  HomeIcon,
  FeatureIcon,
  DocsIcon,
  PricingIcon,
  CaseIcon,
  ContactIcon,
  AboutIcon,
  ChangelogIcon,
}

const handleSearch = () => {
  if (query.value.trim() === '') {
    results.value = []
    selectedIndex.value = -1
    return
  }

  isSearching.value = true
  
  // Simulate search delay
  setTimeout(() => {
    const searchTerm = query.value.toLowerCase().trim()
    results.value = searchData
      .filter(item => 
        item.title.toLowerCase().includes(searchTerm) ||
        item.description.toLowerCase().includes(searchTerm) ||
        item.category.toLowerCase().includes(searchTerm) ||
        item.path.toLowerCase().includes(searchTerm)
      )
      .map(item => ({
        ...item,
        icon: iconMap[item.icon] || DocsIcon
      }))
      .slice(0, 10) // Limit to 10 results
    
    selectedIndex.value = results.value.length > 0 ? 0 : -1
    isSearching.value = false
  }, 150)
}

const navigateTo = (result: any) => {
  router.push(result.path)
  close()
}

const handleEnter = () => {
  if (selectedIndex.value >= 0 && results.value[selectedIndex.value]) {
    navigateTo(results.value[selectedIndex.value])
  }
}

const navigateDown = () => {
  if (selectedIndex.value < results.value.length - 1) {
    selectedIndex.value++
  }
}

const navigateUp = () => {
  if (selectedIndex.value > 0) {
    selectedIndex.value--
  }
}

const close = () => {
  emit('update:isOpen', false)
  query.value = ''
  results.value = []
  selectedIndex.value = -1
}

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    nextTick(() => {
      searchInput.value?.focus()
    })
  }
})

// Keyboard shortcut (Cmd/Ctrl + K)
const handleKeyDown = (e: KeyboardEvent) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    emit('update:isOpen', !props.isOpen)
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .relative,
.modal-leave-active .relative {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.modal-enter-from .relative,
.modal-leave-to .relative {
  transform: translateY(-10px);
  opacity: 0;
}
</style>

