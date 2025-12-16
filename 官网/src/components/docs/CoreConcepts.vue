<template>
  <div class="core-concepts">
    <!-- Title -->
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
        核心概念
      </h1>
      <p class="text-xl text-gray-600 dark:text-gray-300">
        了解 Multikb Base 的核心概念，帮助您更好地理解和使用系统
      </p>
    </div>

    <!-- Knowledge Base -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">
          📚
        </div>
        <h2 class="text-3xl font-bold text-gray-900 dark:text-gray-100">知识库（Knowledge Base）</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-xl p-6 mb-6 border-2 border-blue-100 dark:border-blue-800">
        <h3 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-3">定义</h3>
        <p class="text-gray-700 dark:text-gray-300 leading-relaxed">
          <strong>知识库</strong>是 Multikb Base 中的核心组织单元，用于管理和组织相关的文档和知识。
        </p>
      </div>

      <h3 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-4">特点</h3>
      <ul class="space-y-3 mb-6">
        <li class="flex items-start space-x-3">
          <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
          </svg>
          <span class="text-gray-700"><strong>独立存储</strong>：每个知识库拥有独立的数据存储空间</span>
        </li>
        <li class="flex items-start space-x-3">
          <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
          </svg>
          <span class="text-gray-700"><strong>数据隔离</strong>：不同知识库之间的数据完全隔离</span>
        </li>
        <li class="flex items-start space-x-3">
          <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
          </svg>
          <span class="text-gray-700"><strong>权限控制</strong>：可以设置知识库的可见性和访问权限</span>
        </li>
        <li class="flex items-start space-x-3">
          <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
          </svg>
          <span class="text-gray-700"><strong>分类管理</strong>：支持分类和标签管理</span>
        </li>
      </ul>

      <h3 class="text-xl font-bold text-gray-900 mb-4">使用场景</h3>
      <div class="grid md:grid-cols-3 gap-4">
        <div class="p-4 rounded-lg bg-white border-2 border-gray-200">
          <div class="font-semibold text-gray-900 mb-2">按项目组织</div>
          <div class="text-sm text-gray-600">项目A文档、项目B文档</div>
        </div>
        <div class="p-4 rounded-lg bg-white border-2 border-gray-200">
          <div class="font-semibold text-gray-900 mb-2">按部门组织</div>
          <div class="text-sm text-gray-600">技术部知识库、产品部知识库</div>
        </div>
        <div class="p-4 rounded-lg bg-white border-2 border-gray-200">
          <div class="font-semibold text-gray-900 mb-2">按主题组织</div>
          <div class="text-sm text-gray-600">技术文档、产品文档</div>
        </div>
      </div>
    </section>

    <!-- Document -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">
          📄
        </div>
        <h2 class="text-3xl font-bold text-gray-900">文档（Document）</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 mb-6 border-2 border-green-100">
        <h3 class="text-xl font-bold text-gray-900 mb-3">定义</h3>
        <p class="text-gray-700 dark:text-gray-300 leading-relaxed">
          <strong>文档</strong>是知识库中的基本内容单元，代表一个完整的文件或内容源。
        </p>
      </div>

      <h3 class="text-xl font-bold text-gray-900 mb-4">文档类型</h3>
      <p class="text-gray-700 mb-4">Multikb Base 支持 <strong>9种文档格式</strong>：</p>
      <div class="grid md:grid-cols-3 gap-4 mb-6">
        <div v-for="format in documentFormats" :key="format.name" 
             class="p-4 rounded-lg bg-white border-2 border-gray-200 hover:border-green-300 transition-all">
          <div class="text-2xl mb-2">{{ format.icon }}</div>
          <div class="font-semibold text-gray-900">{{ format.name }}</div>
          <div class="text-sm text-gray-600 mt-1">{{ format.desc }}</div>
        </div>
      </div>

      <h3 class="text-xl font-bold text-gray-900 mb-4">文档处理流程</h3>
      <div class="bg-gradient-to-br from-gray-50 to-blue-50 rounded-xl p-6 border-2 border-gray-200">
        <div class="flex items-center justify-between mb-4">
          <div v-for="(step, index) in documentProcess" :key="index" 
               class="flex-1 text-center">
            <div class="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-white flex items-center justify-center font-bold mx-auto mb-2">
              {{ index + 1 }}
            </div>
            <div class="text-sm font-semibold text-gray-900">{{ step }}</div>
          </div>
        </div>
        <div class="flex items-center justify-between px-4">
          <div v-for="i in 4" :key="i" class="flex-1">
            <div class="h-1 bg-gradient-to-r from-blue-500 to-purple-600"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- Chunk -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">
          🧩
        </div>
        <h2 class="text-3xl font-bold text-gray-900">块（Chunk）</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 mb-6 border-2 border-purple-100">
        <h3 class="text-xl font-bold text-gray-900 mb-3">定义</h3>
        <p class="text-gray-700 dark:text-gray-300 leading-relaxed">
          <strong>块</strong>是文档被分割后的最小检索单元，是向量检索的基础。
        </p>
      </div>

      <h3 class="text-xl font-bold text-gray-900 mb-4">分块策略</h3>
      <p class="text-gray-700 mb-4">Multikb Base 采用<strong>智能分块</strong>策略：</p>
      <ul class="space-y-3 mb-6">
        <li class="flex items-start space-x-3">
          <span class="w-2 h-2 bg-purple-500 rounded-full mt-2 flex-shrink-0"></span>
          <span class="text-gray-700"><strong>基于文档结构</strong>：保留文档的层次结构</span>
        </li>
        <li class="flex items-start space-x-3">
          <span class="w-2 h-2 bg-purple-500 rounded-full mt-2 flex-shrink-0"></span>
          <span class="text-gray-700"><strong>语义完整性</strong>：尽量保持语义完整</span>
        </li>
        <li class="flex items-start space-x-3">
          <span class="w-2 h-2 bg-purple-500 rounded-full mt-2 flex-shrink-0"></span>
          <span class="text-gray-700"><strong>大小控制</strong>：默认块大小为 1000 字符（可配置）</span>
        </li>
        <li class="flex items-start space-x-3">
          <span class="w-2 h-2 bg-purple-500 rounded-full mt-2 flex-shrink-0"></span>
          <span class="text-gray-700"><strong>重叠处理</strong>：相邻块之间可以重叠，提高检索准确性</span>
        </li>
      </ul>
    </section>

    <!-- Vector -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">
          🔢
        </div>
        <h2 class="text-3xl font-bold text-gray-900">向量（Vector）</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 mb-6 border-2 border-orange-100">
        <h3 class="text-xl font-bold text-gray-900 mb-3">定义</h3>
        <p class="text-gray-700 dark:text-gray-300 leading-relaxed">
          <strong>向量</strong>是文本内容的数学表示，用于语义相似度计算。
        </p>
      </div>

      <h3 class="text-xl font-bold text-gray-900 mb-4">向量化过程</h3>
      <div class="bg-white rounded-xl p-6 border-2 border-gray-200 mb-6">
        <div class="flex items-center justify-between">
          <div class="text-center flex-1">
            <div class="text-lg font-semibold text-gray-900 mb-2">文本内容</div>
            <div class="text-sm text-gray-600">原始文档</div>
          </div>
          <div class="mx-4">
            <svg class="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </div>
          <div class="text-center flex-1">
            <div class="text-lg font-semibold text-gray-900 mb-2">嵌入模型</div>
            <div class="text-sm text-gray-600">nomic-embed-text</div>
          </div>
          <div class="mx-4">
            <svg class="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </div>
          <div class="text-center flex-1">
            <div class="text-lg font-semibold text-gray-900 mb-2">向量表示</div>
            <div class="text-sm text-gray-600">768维向量</div>
          </div>
        </div>
      </div>
    </section>

    <!-- Retrieval Strategies -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-xl">
          🔍
        </div>
        <h2 class="text-3xl font-bold text-gray-900">检索策略</h2>
      </div>

      <p class="text-gray-700 mb-6">Multikb Base 提供 <strong>6种检索策略</strong>：</p>
      <div class="grid md:grid-cols-2 gap-6">
        <div v-for="strategy in retrievalStrategies" :key="strategy.name" 
             class="p-6 rounded-xl bg-white border-2 border-gray-200 hover:border-cyan-300 transition-all">
          <div class="flex items-center space-x-3 mb-3">
            <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white">
              {{ strategy.icon }}
            </div>
            <div>
              <h3 class="text-lg font-bold text-gray-900">{{ strategy.name }}</h3>
              <p class="text-sm text-gray-500">{{ strategy.type }}</p>
            </div>
          </div>
          <p class="text-gray-700 mb-3">{{ strategy.desc }}</p>
          <div class="flex flex-wrap gap-2">
            <span v-for="tag in strategy.tags" :key="tag" 
                  class="px-3 py-1 bg-cyan-50 text-cyan-700 rounded-full text-xs font-medium">
              {{ tag }}
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- Next Steps -->
    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">下一步</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/system-requirements" 
                     class="px-4 py-2 bg-white text-blue-600 rounded-lg font-medium hover:bg-blue-50 transition-colors">
          查看系统要求 →
        </router-link>
        <router-link to="/docs/getting-started" 
                     class="px-4 py-2 bg-white text-blue-600 rounded-lg font-medium hover:bg-blue-50 transition-colors">
          快速开始 →
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const documentFormats = [
  { name: 'PDF', icon: '📕', desc: '便携式文档格式' },
  { name: 'DOCX', icon: '📘', desc: 'Microsoft Word 文档' },
  { name: 'PPTX', icon: '📗', desc: 'Microsoft PowerPoint' },
  { name: 'Excel', icon: '📊', desc: 'Microsoft Excel' },
  { name: 'HTML', icon: '🌐', desc: '网页文档' },
  { name: 'MD', icon: '📝', desc: 'Markdown 文档' },
  { name: 'TXT', icon: '📄', desc: '纯文本文件' },
  { name: 'JSON', icon: '📋', desc: 'JSON 数据文件' },
  { name: 'XML', icon: '📑', desc: 'XML 数据文件' }
]

const documentProcess = [
  '上传',
  '解析',
  '分块',
  '向量化',
  '索引存储'
]

const retrievalStrategies = [
  {
    name: '向量搜索',
    type: '语义检索',
    icon: '🔢',
    desc: '基于向量相似度的语义检索，理解查询意图',
    tags: ['语义理解', '相似度计算', 'k-NN搜索']
  },
  {
    name: '关键词搜索',
    type: '全文检索',
    icon: '🔤',
    desc: '基于关键词匹配的全文检索，精确匹配',
    tags: ['全文索引', '分词', '相关性排序']
  },
  {
    name: '混合搜索',
    type: '融合检索',
    icon: '🔀',
    desc: '向量搜索 + 关键词搜索融合，兼顾语义和精确匹配',
    tags: ['融合算法', '权重调节', '结果合并']
  },
  {
    name: '精确匹配',
    type: '短语匹配',
    icon: '🎯',
    desc: '完全匹配查询短语，适合专业术语搜索',
    tags: ['短语匹配', '精确查找', '专业术语']
  },
  {
    name: '模糊匹配',
    type: '容错检索',
    icon: '🔍',
    desc: '支持拼写错误和同义词，提高检索召回率',
    tags: ['容错算法', '同义词扩展', '拼写纠错']
  },
  {
    name: '多模态检索',
    type: '跨模态检索',
    icon: '🎨',
    desc: '文本 + 图片融合检索，支持跨模态搜索',
    tags: ['多模态', '跨模态', '图文融合']
  }
]
</script>

<style scoped>
.core-concepts {
  max-width: none;
}
</style>

