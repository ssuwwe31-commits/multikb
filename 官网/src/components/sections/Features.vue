<template>
  <section id="features" class="py-32 bg-white dark:bg-gray-900">
    <div class="max-w-7xl mx-auto px-6 lg:px-8">
      <!-- Section Header -->
      <div class="text-center mb-20">
        <div class="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-blue-100 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 mb-6">
          <span class="text-sm font-medium text-blue-700 dark:text-blue-300">核心功能</span>
        </div>
        <h2 class="text-5xl md:text-6xl font-bold mb-6">
          <span class="bg-gradient-to-r from-gray-900 to-gray-600 dark:from-gray-100 dark:to-gray-400 bg-clip-text text-transparent">
            企业级能力
          </span>
        </h2>
        <p class="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
          提供从文档入库、内容治理、语义检索到多模态问答的完整解决方案
        </p>
      </div>

      <!-- Features Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        <div 
          v-for="(feature, index) in features" 
          :key="index"
          class="group relative p-8 rounded-2xl bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-2xl transition-all duration-300 hover:-translate-y-2"
        >
          <!-- Icon -->
          <div class="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-lg">
            <span class="text-2xl">{{ feature.icon }}</span>
          </div>

          <!-- Content -->
          <h3 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">{{ feature.title }}</h3>
          <p class="text-gray-600 dark:text-gray-300 leading-relaxed mb-4">{{ feature.description }}</p>

          <!-- Features List -->
          <ul class="space-y-2">
            <li 
              v-for="(item, i) in feature.items" 
              :key="i"
              class="flex items-start space-x-2 text-sm text-gray-600 dark:text-gray-300"
            >
              <svg class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              <span>{{ item }}</span>
            </li>
          </ul>

          <!-- Hover Effect -->
          <div class="absolute inset-0 rounded-2xl bg-gradient-to-br from-blue-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
const features = [
  {
    icon: '🔒',
    title: '企业级安全',
    description: '病毒扫描 + 恶意脚本检测，双重安全机制',
    items: [
      '支持TCP/Socket连接',
      '恶意脚本检测',
      '安全扫描状态追踪',
      '历史数据补扫描'
    ]
  },
  {
    icon: '📄',
    title: '9种文档格式',
    description: 'PDF、DOCX、PPTX、Excel、HTML、MD、TXT、JSON、XML',
    items: [
      '结构化解析，保留文档结构',
      '智能分块，基于文档结构',
      '完整格式支持',
      '批量处理能力'
    ]
  },
  {
    icon: '🎨',
    title: '多模态能力',
    description: '文本+图片+图文混合，六种检索策略',
    items: [
      '文本问答、图片问答',
      '图文混合问答',
      'Qwen VL高精度OCR',
      '多模态融合检索'
    ]
  },
  {
    icon: '📊',
    title: '版本管理',
    description: '文档级+块级双层版本管理',
    items: [
      '版本恢复',
      '版本对比',
      '修改追踪',
      '完整历史记录'
    ]
  },
  {
    icon: '🔍',
    title: '智能检索',
    description: '向量+关键词混合检索，Rerank精排',
    items: [
      '向量搜索',
      '关键词搜索',
      '混合检索',
      '多模态融合检索'
    ]
  },
  {
    icon: '🚀',
    title: '生产可用',
    description: '核心功能100%对齐设计文档',
    items: [
      '已通过生产环境验证',
      '完整API文档',
      '透明设计文档',
      '持续更新维护'
    ]
  }
]
</script>

