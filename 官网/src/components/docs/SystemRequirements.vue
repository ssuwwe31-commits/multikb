<template>
  <div class="system-requirements">
    <!-- Title -->
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
        系统要求
      </h1>
      <p class="text-xl text-gray-600">
        查看 Knowledge Base 的系统要求、依赖服务和环境配置
      </p>
    </div>

    <!-- Server Requirements -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">
          💻
        </div>
        <h2 class="text-3xl font-bold text-gray-900">服务器要求</h2>
      </div>

      <div class="grid md:grid-cols-3 gap-6 mb-8">
        <div class="p-6 rounded-xl bg-gradient-to-br from-gray-50 to-blue-50 border-2 border-gray-200">
          <h3 class="text-lg font-bold text-gray-900 mb-4">最低配置</h3>
          <ul class="space-y-2 text-sm text-gray-700">
            <li>• CPU: 4 核</li>
            <li>• 内存: 8GB RAM</li>
            <li>• GPU: 8GB 显存</li>
            <li>• 存储: 50GB</li>
            <li>• 系统: Linux</li>
          </ul>
        </div>
        <div class="p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-300">
          <div class="mb-2">
            <span class="px-3 py-1 bg-blue-600 text-white rounded-full text-xs font-bold">推荐</span>
          </div>
          <h3 class="text-lg font-bold text-gray-900 mb-4">推荐配置</h3>
          <ul class="space-y-2 text-sm text-gray-700">
            <li>• CPU: 16 核</li>
            <li>• 内存: 32GB RAM</li>
            <li>• GPU: 24GB 显存</li>
            <li>• 存储: 1TB (SSD)</li>
            <li>• 系统: Ubuntu 22.04</li>
          </ul>
        </div>
        <div class="p-6 rounded-xl bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-200">
          <h3 class="text-lg font-bold text-gray-900 mb-4">生产环境</h3>
          <ul class="space-y-2 text-sm text-gray-700">
            <li>• CPU: 64 核</li>
            <li>• 内存: 256GB RAM</li>
            <li>• GPU: 128GB 显存</li>
            <li>• 存储: 10TB (SSD)</li>
            <li>• 网络: 千兆网络</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- GPU Requirements -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xl">
          🎮
        </div>
        <h2 class="text-3xl font-bold text-gray-900">GPU 要求</h2>
      </div>

      <div class="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 mb-6 border-2 border-indigo-100">
        <div class="grid md:grid-cols-2 gap-6">
          <div>
            <h3 class="text-xl font-bold text-gray-900 mb-4">最低要求</h3>
            <ul class="space-y-3">
              <li class="flex items-start space-x-3">
                <svg class="w-6 h-6 text-indigo-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <div>
                  <div class="font-semibold text-gray-900">显存：8GB（最低）</div>
                  <div class="text-sm text-gray-600">最低显存要求，用于运行LLM和向量化模型</div>
                </div>
              </li>
              <li class="flex items-start space-x-3">
                <svg class="w-6 h-6 text-indigo-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <div>
                  <div class="font-semibold text-gray-900">CUDA：11.8+</div>
                  <div class="text-sm text-gray-600">CUDA工具包版本要求</div>
                </div>
              </li>
              <li class="flex items-start space-x-3">
                <svg class="w-6 h-6 text-indigo-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <div>
                  <div class="font-semibold text-gray-900">驱动：520+</div>
                  <div class="text-sm text-gray-600">NVIDIA驱动版本要求</div>
                </div>
              </li>
            </ul>
          </div>
          <div>
            <h3 class="text-xl font-bold text-gray-900 mb-4">推荐配置</h3>
            <ul class="space-y-3">
              <li class="flex items-start space-x-3">
                <svg class="w-6 h-6 text-purple-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <div>
                  <div class="font-semibold text-gray-900">显存：24GB（推荐）</div>
                  <div class="text-sm text-gray-600">推荐显存，支持更大模型和更高并发</div>
                </div>
              </li>
              <li class="flex items-start space-x-3">
                <svg class="w-6 h-6 text-purple-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <div>
                  <div class="font-semibold text-gray-900">显存：128GB（生产环境）</div>
                  <div class="text-sm text-gray-600">生产环境推荐，支持大规模部署和高并发场景</div>
                </div>
              </li>
              <li class="flex items-start space-x-3">
                <svg class="w-6 h-6 text-purple-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <div>
                  <div class="font-semibold text-gray-900">多GPU支持</div>
                  <div class="text-sm text-gray-600">支持多GPU并行，提升处理能力</div>
                </div>
              </li>
              <li class="flex items-start space-x-3">
                <svg class="w-6 h-6 text-purple-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <div>
                  <div class="font-semibold text-gray-900">GPU型号推荐</div>
                  <div class="text-sm text-gray-600">RTX 3090、RTX 4090、A100等</div>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div class="bg-yellow-50 border-2 border-yellow-200 rounded-xl p-6">
        <div class="flex items-start space-x-3">
          <svg class="w-6 h-6 text-yellow-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
          </svg>
          <div>
            <div class="font-semibold text-yellow-900 mb-1">重要提示</div>
            <div class="text-sm text-yellow-800">
              GPU是运行LLM模型和向量化的关键资源。虽然系统可以在CPU模式下运行，但性能会显著下降。强烈建议使用GPU以获得最佳体验。
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Python Environment -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">
          🐍
        </div>
        <h2 class="text-3xl font-bold text-gray-900">Python 环境</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 mb-6 border-2 border-green-100">
        <h3 class="text-xl font-bold text-gray-900 mb-4">Python 版本</h3>
        <div class="grid md:grid-cols-3 gap-4">
          <div class="text-center p-4 bg-white rounded-lg">
            <div class="text-2xl font-bold text-red-600 mb-2">3.8</div>
            <div class="text-sm text-gray-600">不支持</div>
          </div>
          <div class="text-center p-4 bg-white rounded-lg border-2 border-green-500">
            <div class="text-2xl font-bold text-green-600 mb-2">3.9+</div>
            <div class="text-sm text-gray-600">最低版本</div>
          </div>
          <div class="text-center p-4 bg-white rounded-lg border-2 border-blue-500">
            <div class="text-2xl font-bold text-blue-600 mb-2">3.10/3.11</div>
            <div class="text-sm text-gray-600">推荐版本</div>
          </div>
        </div>
      </div>

      <h3 class="text-xl font-bold text-gray-900 mb-4">主要依赖包</h3>
      <div class="grid md:grid-cols-2 gap-4">
        <div v-for="pkg in pythonPackages" :key="pkg" 
             class="p-4 rounded-lg bg-white border-2 border-gray-200">
          <code class="text-sm font-mono text-gray-900">{{ pkg }}</code>
        </div>
      </div>
    </section>

    <!-- Database Requirements -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">
          🗄️
        </div>
        <h2 class="text-3xl font-bold text-gray-900">数据库要求</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 mb-6 border-2 border-orange-100">
        <h3 class="text-xl font-bold text-gray-900 mb-4">MySQL</h3>
        <div class="grid md:grid-cols-2 gap-6">
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">版本要求</h4>
            <ul class="space-y-2 text-sm text-gray-700">
              <li>• MySQL 8.0+</li>
              <li>• 或 MariaDB 10.6+</li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">配置要求</h4>
            <ul class="space-y-2 text-sm text-gray-700">
              <li>• 字符集: utf8mb4</li>
              <li>• 存储引擎: InnoDB</li>
              <li>• 连接数: 100+</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- Service Requirements -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">
          ⚙️
        </div>
        <h2 class="text-3xl font-bold text-gray-900">依赖服务</h2>
      </div>

      <div class="space-y-4">
        <div v-for="service in services" :key="service.name" 
             class="p-6 rounded-xl bg-white border-2 border-gray-200 hover:border-purple-300 transition-all">
          <div class="flex items-center space-x-4 mb-4">
            <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">
              {{ service.icon }}
            </div>
            <div class="flex-1">
              <h3 class="text-xl font-bold text-gray-900">{{ service.name }}</h3>
              <p class="text-sm text-gray-600">{{ service.version }}</p>
            </div>
            <div class="text-right">
              <div class="text-sm font-semibold text-gray-900">端口</div>
              <div class="text-lg font-bold text-purple-600">{{ service.port }}</div>
            </div>
          </div>
          <p class="text-gray-700 mb-3">{{ service.desc }}</p>
          <div class="flex flex-wrap gap-2">
            <span v-for="tag in service.tags" :key="tag" 
                  class="px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-xs font-medium">
              {{ tag }}
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- Port Requirements -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-xl">
          🌐
        </div>
        <h2 class="text-3xl font-bold text-gray-900">网络端口</h2>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full border-collapse">
          <thead>
            <tr class="bg-gray-50">
              <th class="px-6 py-4 text-left text-sm font-semibold text-gray-900 border-b">服务</th>
              <th class="px-6 py-4 text-center text-sm font-semibold text-gray-900 border-b">端口</th>
              <th class="px-6 py-4 text-left text-sm font-semibold text-gray-900 border-b">说明</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="port in ports" :key="port.service" class="hover:bg-gray-50">
              <td class="px-6 py-4 text-sm font-medium text-gray-900">{{ port.service }}</td>
              <td class="px-6 py-4 text-center">
                <code class="px-3 py-1 bg-gray-100 rounded text-sm font-mono">{{ port.port }}</code>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">{{ port.desc }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Environment Variables -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center text-white text-xl">
          📋
        </div>
        <h2 class="text-3xl font-bold text-gray-900">环境变量配置</h2>
      </div>

      <div class="bg-gray-900 rounded-xl p-6 mb-6 overflow-x-auto">
        <pre class="text-sm text-gray-300"><code># 应用配置
APP_NAME=SPX Knowledge Base
DEBUG=false
SECRET_KEY=your-secret-key-here

# 数据库
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/spx_knowledge

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenSearch
OPENSEARCH_URL=http://localhost:9200

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text</code></pre>
      </div>
    </section>

    <!-- Checklist -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white text-xl">
          ✅
        </div>
        <h2 class="text-3xl font-bold text-gray-900">环境检查清单</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="p-6 rounded-xl bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-100">
          <h3 class="text-lg font-bold text-gray-900 mb-4">安装前检查</h3>
          <ul class="space-y-2">
            <li v-for="item in checklist.install" :key="item" 
                class="flex items-center space-x-2 text-sm text-gray-700">
              <input type="checkbox" class="w-4 h-4 text-green-600 rounded">
              <span>{{ item }}</span>
            </li>
          </ul>
        </div>
        <div class="p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-4">配置检查</h3>
          <ul class="space-y-2">
            <li v-for="item in checklist.config" :key="item" 
                class="flex items-center space-x-2 text-sm text-gray-700">
              <input type="checkbox" class="w-4 h-4 text-blue-600 rounded">
              <span>{{ item }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Next Steps -->
    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">下一步</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/core-concepts" 
                     class="px-4 py-2 bg-white text-blue-600 rounded-lg font-medium hover:bg-blue-50 transition-colors">
          了解核心概念 →
        </router-link>
        <router-link to="/docs/getting-started" 
                     class="px-4 py-2 bg-white text-blue-600 rounded-lg font-medium hover:bg-blue-50 transition-colors">
          快速开始 →
        </router-link>
        <router-link to="/docs/docker-deployment" 
                     class="px-4 py-2 bg-white text-blue-600 rounded-lg font-medium hover:bg-blue-50 transition-colors">
          Docker 部署 →
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const pythonPackages = [
  'FastAPI 0.104+',
  'SQLAlchemy 2.0+',
  'Celery 5.3+',
  'Pydantic 2.0+',
  'PyMySQL 1.1+',
  'openpyxl 3.1+',
  'python-docx 1.1+',
  'pdfplumber 0.10+'
]

const services = [
  {
    name: 'MySQL',
    version: 'MySQL 8.0+',
    port: '3306',
    icon: '🗄️',
    desc: '存储结构化数据，文档元数据、用户信息等',
    tags: ['数据库', '必需']
  },
  {
    name: 'OpenSearch',
    version: 'OpenSearch 2.x',
    port: '9200',
    icon: '🔍',
    desc: '存储向量索引和全文索引，支持语义检索',
    tags: ['搜索引擎', '必需', 'IK插件']
  },
  {
    name: 'Redis',
    version: 'Redis 6.0+',
    port: '6379',
    icon: '🔴',
    desc: '缓存和任务队列，提升系统性能',
    tags: ['缓存', '必需', '任务队列']
  },
  {
    name: 'MinIO',
    version: '最新版本',
    port: '9000',
    icon: '📦',
    desc: '对象存储，存储原始文档和图片文件',
    tags: ['对象存储', '必需']
  },
  {
    name: 'Ollama',
    version: '最新版本',
    port: '11434',
    icon: '🤖',
    desc: 'LLM 服务，提供问答和向量化能力',
    tags: ['AI服务', '必需', 'GPU推荐']
  },
  {
    name: 'ClamAV',
    version: 'ClamAV 1.0+',
    port: '3310',
    icon: '🛡️',
    desc: '病毒扫描服务，企业级安全功能',
    tags: ['安全', '可选', '推荐']
  }
]

const ports = [
  { service: 'FastAPI', port: '8000', desc: '后端 API 服务' },
  { service: 'MySQL', port: '3306', desc: '数据库' },
  { service: 'OpenSearch', port: '9200', desc: '搜索引擎' },
  { service: 'Redis', port: '6379', desc: '缓存和队列' },
  { service: 'MinIO', port: '9000', desc: '对象存储' },
  { service: 'Ollama', port: '11434', desc: 'LLM 服务' },
  { service: 'ClamAV', port: '3310', desc: '病毒扫描（可选）' }
]

const checklist = {
  install: [
    'Python 3.9+ 已安装',
    'GPU 显存已配置（最低8GB，推荐24GB，生产环境128GB）',
    'CUDA 11.8+ 已安装',
    'MySQL 8.0+ 已安装并运行',
    'OpenSearch 2.x 已安装并运行',
    'Redis 6.0+ 已安装并运行',
    'MinIO 已安装并运行',
    'Ollama 已安装并运行',
    '所有端口已开放',
    '防火墙配置正确'
  ],
  config: [
    '环境变量已配置',
    '数据库已初始化',
    'OpenSearch 索引已创建',
    'MinIO 存储桶已创建',
    '模型已下载',
    'API 服务正常启动',
    'Celery Worker 正常运行',
    '功能测试通过'
  ]
}
</script>

<style scoped>
.system-requirements {
  max-width: none;
}
</style>

