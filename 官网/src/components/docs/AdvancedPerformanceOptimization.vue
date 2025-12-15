<template>
  <div class="advanced-performance-optimization">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">性能优化</h1>
      <p class="text-xl text-gray-600">系统性能优化、缓存策略、并发调优</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">⚡</div>
        <h2 class="text-3xl font-bold text-gray-900">系统优化</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">数据库优化</h3>
          <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li>添加合适的索引，提升查询速度</li>
            <li>优化慢查询，使用EXPLAIN分析</li>
            <li>配置连接池，减少连接开销</li>
            <li>定期清理历史数据</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">OpenSearch优化</h3>
          <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li>调整分片和副本数量</li>
            <li>优化JVM堆内存配置</li>
            <li>使用SSD存储索引</li>
            <li>定期优化索引（force merge）</li>
            <li>调整knn参数（HNSW_M、HNSW_EF_CONSTRUCTION）</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">Celery优化</h3>
          <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li>增加Worker数量提升并发</li>
            <li>使用prefork模式</li>
            <li>设置任务优先级</li>
            <li>优化任务超时时间</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">💾</div>
        <h2 class="text-3xl font-bold text-gray-900">缓存策略</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
        <div class="grid md:grid-cols-2 gap-6">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-3">Redis缓存</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>缓存频繁查询的结果</li>
              <li>缓存向量检索结果</li>
              <li>缓存用户会话信息</li>
              <li>设置合理的过期时间</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-3">应用层缓存</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>内存缓存常用数据</li>
              <li>缓存模型推理结果</li>
              <li>缓存配置信息</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">🔄</div>
        <h2 class="text-3xl font-bold text-gray-900">并发调优</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">API并发</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>使用异步处理提升并发能力</li>
              <li>实现请求队列和限流</li>
              <li>使用连接池减少连接开销</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">任务并发</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>调整Celery Worker并发数</li>
              <li>使用任务优先级队列</li>
              <li>批量处理提升效率</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/performance-issues" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">性能问题 →</router-link>
        <router-link to="/docs/retrieval-optimization" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">检索优化 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

