<template>
  <div class="features-page">
    <Navbar />
    
    <!-- Hero Section -->
    <section class="pt-32 pb-20 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <div class="text-center max-w-3xl mx-auto">
          <div class="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-blue-100 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 mb-6">
            <span class="text-sm font-medium text-blue-700 dark:text-blue-300">功能特性</span>
          </div>
          <h1 class="text-5xl md:text-6xl font-bold mb-6">
            <span class="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 bg-clip-text text-transparent">
              完整功能体系
            </span>
          </h1>
          <p class="text-xl text-gray-600 dark:text-gray-300">
            从文档入库、内容治理、语义检索到多模态问答，提供企业级知识库管理完整解决方案
          </p>
        </div>
      </div>
    </section>

    <!-- Feature Categories -->
    <section class="py-20 bg-white dark:bg-gray-900">
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <!-- Document Processing -->
        <div class="mb-32">
          <div class="flex items-center space-x-4 mb-12">
            <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <span class="text-3xl">📄</span>
            </div>
            <div>
              <h2 class="text-4xl font-bold text-gray-900 dark:text-gray-100">文档处理</h2>
              <p class="text-gray-600 dark:text-gray-300 mt-2">支持9种文档格式，智能解析与分块</p>
            </div>
          </div>

          <div class="grid md:grid-cols-2 gap-12 items-center mb-12">
            <div>
              <h3 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">支持的文档格式</h3>
              <div class="grid grid-cols-3 gap-4 mb-6">
                <div v-for="format in documentFormats" :key="format.name" 
                     class="p-4 rounded-xl bg-gray-50 dark:bg-gray-800 hover:bg-blue-50 dark:hover:bg-blue-900/30 border-2 border-transparent hover:border-blue-200 dark:hover:border-blue-700 transition-all duration-300 text-center">
                  <div class="text-3xl mb-2">{{ format.icon }}</div>
                  <div class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ format.name }}</div>
                </div>
              </div>
              
              <h3 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">核心能力</h3>
              <ul class="space-y-3">
                <li v-for="capability in documentCapabilities" :key="capability" 
                    class="flex items-start space-x-3">
                  <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                  </svg>
                  <span class="text-gray-700 dark:text-gray-300">{{ capability }}</span>
                </li>
              </ul>
            </div>
            
            <div class="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-2xl p-8 border-2 border-blue-100 dark:border-blue-800">
              <h4 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">处理流程</h4>
              <div class="space-y-4">
                <div v-for="(step, index) in documentProcess" :key="index" 
                     class="flex items-center space-x-4">
                  <div class="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold flex-shrink-0">
                    {{ index + 1 }}
                  </div>
                  <div class="flex-1">
                    <div class="font-semibold text-gray-900 dark:text-gray-100">{{ step.title }}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">{{ step.desc }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Knowledge Q&A -->
        <div class="mb-32">
          <div class="flex items-center space-x-4 mb-12">
            <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center">
              <span class="text-3xl">💬</span>
            </div>
            <div>
              <h2 class="text-4xl font-bold text-gray-900 dark:text-gray-100">知识问答</h2>
              <p class="text-gray-600 dark:text-gray-300 mt-2">多模态输入，智能检索，流式输出</p>
            </div>
          </div>

          <div class="grid md:grid-cols-2 gap-12 items-center mb-12">
            <div class="bg-gradient-to-br from-green-50 to-teal-50 dark:from-green-900/20 dark:to-teal-900/20 rounded-2xl p-8 border-2 border-green-100 dark:border-green-800">
              <h4 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">输入方式</h4>
              <div class="space-y-4">
                <div v-for="input in qaInputs" :key="input.type" 
                     class="flex items-center space-x-4 p-4 bg-white dark:bg-gray-800 rounded-xl">
                  <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">
                    {{ input.icon }}
                  </div>
                  <div class="flex-1">
                    <div class="font-semibold text-gray-900 dark:text-gray-100">{{ input.type }}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">{{ input.desc }}</div>
                  </div>
                </div>
              </div>
            </div>
            
            <div>
              <h3 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">检索策略</h3>
              <div class="grid grid-cols-2 gap-4 mb-6">
                <div v-for="strategy in retrievalStrategies" :key="strategy" 
                     class="p-4 rounded-xl bg-gray-50 dark:bg-gray-800 hover:bg-green-50 dark:hover:bg-green-900/30 border-2 border-transparent hover:border-green-200 dark:hover:border-green-700 transition-all duration-300 text-center">
                  <div class="text-sm font-semibold text-gray-900 dark:text-gray-100">{{ strategy }}</div>
                </div>
              </div>
              
              <h3 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">核心特性</h3>
              <ul class="space-y-3">
                <li v-for="feature in qaFeatures" :key="feature" 
                    class="flex items-start space-x-3">
                  <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                  </svg>
                  <span class="text-gray-700 dark:text-gray-300">{{ feature }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Enterprise Security -->
        <div class="mb-32">
          <div class="flex items-center space-x-4 mb-12">
            <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center">
              <span class="text-3xl">🔒</span>
            </div>
            <div>
              <h2 class="text-4xl font-bold text-gray-900">企业级安全</h2>
              <p class="text-gray-600 dark:text-gray-300 mt-2">唯一集成病毒扫描的知识库系统</p>
            </div>
          </div>

          <div class="grid md:grid-cols-3 gap-8 mb-12">
            <div v-for="security in securityFeatures" :key="security.title" 
                 class="p-6 rounded-2xl bg-gradient-to-br from-red-50 to-orange-50 border-2 border-red-100">
              <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center text-white text-xl mb-4">
                {{ security.icon }}
              </div>
              <h3 class="text-xl font-bold text-gray-900 mb-2">{{ security.title }}</h3>
              <p class="text-gray-600 mb-4">{{ security.desc }}</p>
              <ul class="space-y-2">
                <li v-for="item in security.items" :key="item" 
                    class="flex items-center space-x-2 text-sm text-gray-700">
                  <svg class="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                  </svg>
                  <span>{{ item }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Version Management -->
        <div class="mb-32">
          <div class="flex items-center space-x-4 mb-12">
            <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center">
              <span class="text-3xl">📊</span>
            </div>
            <div>
              <h2 class="text-4xl font-bold text-gray-900">版本管理</h2>
              <p class="text-gray-600 mt-2">文档级+块级双层版本管理，完整历史追踪</p>
            </div>
          </div>

          <div class="grid md:grid-cols-2 gap-12">
            <div>
              <h3 class="text-2xl font-bold text-gray-900 mb-6">版本层级</h3>
              <div class="space-y-6">
                <div class="p-6 rounded-xl bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-100">
                  <div class="flex items-center space-x-3 mb-3">
                    <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white font-bold">
                      文档
                    </div>
                    <h4 class="text-lg font-bold text-gray-900">文档级版本</h4>
                  </div>
                  <p class="text-gray-600 mb-4">追踪整个文档的变更历史</p>
                  <ul class="space-y-2 text-sm text-gray-700">
                    <li class="flex items-center space-x-2">
                      <span class="w-2 h-2 bg-purple-500 rounded-full"></span>
                      <span>文档上传、更新、删除记录</span>
                    </li>
                    <li class="flex items-center space-x-2">
                      <span class="w-2 h-2 bg-purple-500 rounded-full"></span>
                      <span>版本对比与差异查看</span>
                    </li>
                    <li class="flex items-center space-x-2">
                      <span class="w-2 h-2 bg-purple-500 rounded-full"></span>
                      <span>一键恢复到任意版本</span>
                    </li>
                  </ul>
                </div>

                <div class="p-6 rounded-xl bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-100">
                  <div class="flex items-center space-x-3 mb-3">
                    <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white font-bold">
                      块
                    </div>
                    <h4 class="text-lg font-bold text-gray-900">块级版本</h4>
                  </div>
                  <p class="text-gray-600 mb-4">追踪文档内每个块的变更历史</p>
                  <ul class="space-y-2 text-sm text-gray-700">
                    <li class="flex items-center space-x-2">
                      <span class="w-2 h-2 bg-pink-500 rounded-full"></span>
                      <span>块内容编辑、删除记录</span>
                    </li>
                    <li class="flex items-center space-x-2">
                      <span class="w-2 h-2 bg-pink-500 rounded-full"></span>
                      <span>块级版本对比</span>
                    </li>
                    <li class="flex items-center space-x-2">
                      <span class="w-2 h-2 bg-pink-500 rounded-full"></span>
                      <span>精确到块的版本恢复</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
            
            <div>
              <h3 class="text-2xl font-bold text-gray-900 mb-6">版本操作</h3>
              <div class="space-y-4">
                <div v-for="operation in versionOperations" :key="operation.title" 
                     class="p-6 rounded-xl bg-white border-2 border-gray-200 hover:border-purple-300 transition-all duration-300">
                  <div class="flex items-center space-x-3 mb-2">
                    <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white">
                      {{ operation.icon }}
                    </div>
                    <h4 class="text-lg font-bold text-gray-900">{{ operation.title }}</h4>
                  </div>
                  <p class="text-gray-600">{{ operation.desc }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Multi-modal Capabilities -->
        <div class="mb-32">
          <div class="flex items-center space-x-4 mb-12">
            <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <span class="text-3xl">🎨</span>
            </div>
            <div>
              <h2 class="text-4xl font-bold text-gray-900">多模态能力</h2>
              <p class="text-gray-600 mt-2">文本+图片+图文混合，完整多模态支持</p>
            </div>
          </div>

          <div class="grid md:grid-cols-3 gap-8">
            <div v-for="modal in multimodalFeatures" :key="modal.type" 
                 class="p-8 rounded-2xl bg-gradient-to-br from-cyan-50 to-blue-50 border-2 border-cyan-100">
              <div class="w-16 h-16 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-3xl mb-6">
                {{ modal.icon }}
              </div>
              <h3 class="text-2xl font-bold text-gray-900 mb-3">{{ modal.type }}</h3>
              <p class="text-gray-600 mb-6">{{ modal.desc }}</p>
              <ul class="space-y-2">
                <li v-for="feature in modal.features" :key="feature" 
                    class="flex items-center space-x-2 text-sm text-gray-700">
                  <svg class="w-4 h-4 text-cyan-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                  </svg>
                  <span>{{ feature }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Search Capabilities -->
        <div class="mb-32">
          <div class="flex items-center space-x-4 mb-12">
            <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center">
              <span class="text-3xl">🔍</span>
            </div>
            <div>
              <h2 class="text-4xl font-bold text-gray-900">智能检索</h2>
              <p class="text-gray-600 mt-2">六种检索策略，满足不同场景需求</p>
            </div>
          </div>

          <div class="grid md:grid-cols-2 gap-8">
            <div v-for="search in searchStrategies" :key="search.name" 
                 class="p-6 rounded-xl bg-white border-2 border-gray-200 hover:border-yellow-300 hover:shadow-lg transition-all duration-300">
              <div class="flex items-center space-x-4 mb-4">
                <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center text-white text-xl">
                  {{ search.icon }}
                </div>
                <div>
                  <h3 class="text-xl font-bold text-gray-900">{{ search.name }}</h3>
                  <p class="text-sm text-gray-500">{{ search.type }}</p>
                </div>
              </div>
              <p class="text-gray-600 mb-4">{{ search.desc }}</p>
              <div class="flex flex-wrap gap-2">
                <span v-for="tag in search.tags" :key="tag" 
                      class="px-3 py-1 bg-yellow-50 text-yellow-700 rounded-full text-xs font-medium">
                  {{ tag }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Technical Architecture -->
    <section class="py-20 bg-gradient-to-br from-gray-50 to-blue-50">
      <div class="max-w-7xl mx-auto px-6 lg:px-8">
        <div class="text-center mb-12">
          <h2 class="text-4xl font-bold text-gray-900 mb-4">技术架构</h2>
          <p class="text-xl text-gray-600">现代化技术栈，高性能、可扩展</p>
        </div>

        <div class="grid md:grid-cols-4 gap-6">
          <div v-for="tech in techStack" :key="tech.category" 
               class="p-6 rounded-xl bg-white border-2 border-gray-200 hover:border-blue-300 hover:shadow-lg transition-all duration-300">
            <h3 class="text-lg font-bold text-gray-900 mb-4">{{ tech.category }}</h3>
            <div class="space-y-2">
              <div v-for="item in tech.items" :key="item" 
                   class="flex items-center space-x-2 text-sm text-gray-700">
                <span class="w-2 h-2 bg-blue-500 rounded-full"></span>
                <span>{{ item }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Section -->
    <section class="py-20 bg-gradient-to-br from-blue-600 to-purple-600 text-white">
      <div class="max-w-4xl mx-auto px-6 lg:px-8 text-center">
        <h2 class="text-4xl md:text-5xl font-bold mb-6">
          开始使用 Knowledge Base
        </h2>
        <p class="text-xl text-blue-100 mb-8">
          体验完整的企业级知识库管理功能
        </p>
        <div class="flex flex-col sm:flex-row gap-4 justify-center">
          <button class="px-8 py-4 bg-white text-blue-600 rounded-xl font-semibold hover:bg-gray-50 transition-all duration-300 hover:shadow-lg">
            免费试用
          </button>
          <button class="px-8 py-4 bg-transparent border-2 border-white text-white rounded-xl font-semibold hover:bg-white/10 transition-all duration-300">
            查看文档
          </button>
        </div>
      </div>
    </section>

    <Footer />
  </div>
</template>

<script setup lang="ts">
import Navbar from '../components/layout/Navbar.vue'
import Footer from '../components/layout/Footer.vue'

const documentFormats = [
  { name: 'PDF', icon: '📕' },
  { name: 'DOCX', icon: '📘' },
  { name: 'PPTX', icon: '📗' },
  { name: 'Excel', icon: '📊' },
  { name: 'HTML', icon: '🌐' },
  { name: 'MD', icon: '📝' },
  { name: 'TXT', icon: '📄' },
  { name: 'JSON', icon: '📋' },
  { name: 'XML', icon: '📑' }
]

const documentCapabilities = [
  '结构化解析，保留文档结构',
  '智能分块，基于文档语义',
  '自动提取元数据',
  '支持批量上传',
  '处理进度实时追踪',
  '失败自动重试机制'
]

const documentProcess = [
  { title: '文档上传', desc: '支持单文件或批量上传，自动格式检测' },
  { title: '格式解析', desc: '根据文档类型选择对应解析器' },
  { title: '内容提取', desc: '提取文本、图片、表格等结构化内容' },
  { title: '智能分块', desc: '基于文档结构进行语义分块' },
  { title: '向量化', desc: '使用嵌入模型生成向量表示' },
  { title: '索引存储', desc: '存储到OpenSearch，建立全文和向量索引' }
]

const qaInputs = [
  { type: '文本问答', icon: '💬', desc: '纯文本输入，支持自然语言问题' },
  { type: '图片问答', icon: '🖼️', desc: '上传图片，自动OCR识别并问答' },
  { type: '图文混合', icon: '📸', desc: '同时输入文本和图片，多模态融合' }
]

const retrievalStrategies = [
  '向量搜索',
  '关键词搜索',
  '混合搜索',
  '精确匹配',
  '模糊匹配',
  '多模态检索'
]

const qaFeatures = [
  'WebSocket流式输出，实时响应',
  '引用溯源，显示答案来源',
  '多路召回，提高准确率',
  'Rerank精排，优化结果顺序',
  '降级策略，保证系统可用性',
  '会话管理，支持多轮对话'
]

const securityFeatures = [
  {
    icon: '🛡️',
    title: '病毒扫描',
    desc: '集成病毒扫描引擎，实时扫描上传文档',
    items: ['支持TCP/Socket连接', '实时扫描', '扫描状态追踪', '历史数据补扫描']
  },
  {
    icon: '⚠️',
    title: '恶意脚本检测',
    desc: '基于规则的模式匹配，检测恶意脚本',
    items: ['JavaScript检测', 'Shell脚本检测', 'SQL注入检测', 'XSS攻击检测']
  },
  {
    icon: '📋',
    title: '安全审计',
    desc: '完整的安全扫描记录和审计日志',
    items: ['扫描历史记录', '异常文件告警', '审计日志导出', '合规报告生成']
  }
]

const versionOperations = [
  { icon: '👁️', title: '版本查看', desc: '查看任意版本的文档内容，支持版本列表浏览' },
  { icon: '🔄', title: '版本对比', desc: '对比不同版本的差异，高亮显示变更内容' },
  { icon: '↩️', title: '版本恢复', desc: '一键恢复到指定版本，支持文档级和块级恢复' },
  { icon: '📝', title: '版本编辑', desc: '基于历史版本创建新版本，保留完整变更链' }
]

const multimodalFeatures = [
  {
    type: '文本处理',
    icon: '📝',
    desc: '完整的文本处理能力',
    features: [
      '自然语言理解',
      '语义向量化',
      '关键词提取',
      '文本摘要生成'
    ]
  },
  {
    type: '图片处理',
    icon: '🖼️',
    desc: '强大的图片处理能力',
    features: [
      'Qwen VL高精度OCR',
      'CLIP图片向量化',
      '图片内容理解',
      '图片相似度搜索'
    ]
  },
  {
    type: '多模态融合',
    icon: '🎨',
    desc: '文本与图片深度融合',
    features: [
      '图文混合问答',
      '多模态检索',
      '跨模态语义理解',
      '统一向量空间'
    ]
  }
]

const searchStrategies = [
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
    desc: '基于关键词的全文检索，快速定位相关内容',
    tags: ['全文索引', '分词', '相关性排序']
  },
  {
    name: '混合搜索',
    type: '融合检索',
    icon: '🔀',
    desc: '向量+关键词融合，兼顾语义和精确匹配',
    tags: ['融合算法', '权重调节', '结果合并']
  },
  {
    name: '精确匹配',
    type: '短语匹配',
    icon: '🎯',
    desc: '精确匹配查询短语，适合专业术语搜索',
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
    desc: '文本+图片融合检索，支持跨模态搜索',
    tags: ['多模态', '跨模态', '图文融合']
  }
]

const techStack = [
  {
    category: '后端',
    items: ['FastAPI', 'Celery', 'SQLAlchemy', 'Pydantic']
  },
  {
    category: '前端',
    items: ['Vue 3', 'TypeScript', 'Vite', 'Element Plus']
  },
  {
    category: '存储',
    items: ['MySQL', 'OpenSearch', 'Redis', 'MinIO']
  },
  {
    category: 'AI能力',
    items: ['Ollama', 'Qwen VL', 'CLIP', 'Rerank']
  }
]
</script>

<style scoped>
.features-page {
  min-height: 100vh;
}
</style>
