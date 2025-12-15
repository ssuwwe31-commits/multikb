<template>
  <div class="user-guide-system-config">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">系统配置</h1>
      <p class="text-xl text-gray-600">系统参数配置、模型切换、性能调优</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">🤖</div>
        <h2 class="text-3xl font-bold text-gray-900">模型配置</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">LLM模型</h3>
          <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
            <li>配置OLLAMA_BASE_URL</li>
            <li>设置OLLAMA_MODEL（如llama2、qwen2）</li>
            <li>可以在问答时切换模型</li>
          </ul>
        </div>
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">Embedding模型</h3>
          <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
            <li>设置OLLAMA_EMBEDDING_MODEL</li>
            <li>推荐使用nomic-embed-text</li>
            <li>影响向量化质量</li>
          </ul>
        </div>
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">OCR模型</h3>
          <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
            <li>配置OLLAMA_OCR_MODEL</li>
            <li>推荐使用qwen2-vl:7b</li>
            <li>用于图片文字识别</li>
          </ul>
        </div>
        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">Rerank模型</h3>
          <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
            <li>配置RERANK_MODEL_NAME</li>
            <li>推荐使用BAAI/bge-reranker-v2-m3</li>
            <li>提升检索结果相关性</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">⚡</div>
        <h2 class="text-3xl font-bold text-gray-900">性能调优</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">Celery并发</h3>
            <p class="text-sm text-gray-700 mb-2">调整CELERY_CONCURRENCY参数，根据服务器资源设置Worker数量</p>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">CELERY_CONCURRENCY=4</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">分块大小</h3>
            <p class="text-sm text-gray-700 mb-2">调整CHUNK_SIZE，平衡检索精度和处理效率</p>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">CHUNK_SIZE=1000</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">检索参数</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>调整Top-K值，控制返回结果数量</li>
              <li>配置相似度阈值</li>
              <li>优化混合检索权重</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">🔧</div>
        <h2 class="text-3xl font-bold text-gray-900">其他配置</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">文件限制</h3>
          <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
            <li>MAX_FILE_SIZE：最大文件大小</li>
            <li>ALLOWED_FILE_TYPES：允许的文件类型</li>
          </ul>
        </div>
        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">服务配置</h3>
          <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
            <li>数据库连接配置</li>
            <li>OpenSearch配置</li>
            <li>Redis配置</li>
            <li>MinIO配置</li>
          </ul>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/system-requirements" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">系统要求 →</router-link>
        <router-link to="/docs/performance-issues" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">性能问题 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

