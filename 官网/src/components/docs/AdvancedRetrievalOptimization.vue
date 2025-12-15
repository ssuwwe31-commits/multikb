<template>
  <div class="advanced-retrieval-optimization">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">检索优化</h1>
      <p class="text-xl text-gray-600">向量检索、Rerank模型调优和性能优化</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">🔍</div>
        <h2 class="text-3xl font-bold text-gray-900">向量检索优化</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">Embedding模型选择</h3>
          <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li><strong>nomic-embed-text</strong>：通用推荐，平衡性能和效果</li>
            <li><strong>bge-large-en-v1.5</strong>：英文场景效果更好</li>
            <li><strong>bge-large-zh-v1.5</strong>：中文场景效果更好</li>
            <li>根据实际使用场景选择合适的模型</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">向量维度优化</h3>
          <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li>选择合适的向量维度（通常768或1024）</li>
            <li>维度越高精度越好，但存储和计算成本也更高</li>
            <li>在OpenSearch中配置knn插件参数</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">索引优化</h3>
          <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li>调整OpenSearch的knn索引参数</li>
            <li>优化分片和副本数量</li>
            <li>定期优化索引，提升查询性能</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">📊</div>
        <h2 class="text-3xl font-bold text-gray-900">Rerank模型调优</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">模型配置</h3>
            <div class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">
              <code>RERANK_ENABLED=true<br>RERANK_MODEL_NAME=BAAI/bge-reranker-v2-m3</code>
            </div>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">Top-K配置</h3>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>设置合适的RERANK_TOP_K值（推荐10-20）</li>
              <li>先召回更多结果，再用Rerank精排</li>
              <li>平衡准确性和性能</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">性能优化</h3>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>使用GPU加速Rerank模型</li>
              <li>批量处理多个查询</li>
              <li>缓存常见查询的Rerank结果</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">⚡</div>
        <h2 class="text-3xl font-bold text-gray-900">性能优化</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="grid md:grid-cols-2 gap-6">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-3">OpenSearch优化</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>增加分片数量提升并发</li>
              <li>优化JVM堆内存配置</li>
              <li>使用SSD存储索引</li>
              <li>定期清理旧索引</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-3">缓存策略</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>缓存频繁查询的结果</li>
              <li>设置合理的缓存过期时间</li>
              <li>使用Redis缓存向量检索结果</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/search-features" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">搜索功能 →</router-link>
        <router-link to="/docs/performance-optimization" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">性能优化 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

