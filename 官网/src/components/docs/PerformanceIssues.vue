<template>
  <div class="performance-issues">
    <!-- Title -->
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
        性能问题
      </h1>
      <p class="text-xl text-gray-600">
        性能问题诊断和优化方法
      </p>
    </div>

    <!-- Performance Indicators -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">
          📊
        </div>
        <h2 class="text-3xl font-bold text-gray-900">性能指标</h2>
      </div>

      <div class="grid md:grid-cols-3 gap-6">
        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">响应时间</h3>
          <ul class="space-y-2 text-sm text-gray-700">
            <li>• API响应: &lt; 500ms</li>
            <li>• 问答响应: &lt; 3s</li>
            <li>• 文档处理: &lt; 30s/MB</li>
          </ul>
        </div>
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">吞吐量</h3>
          <ul class="space-y-2 text-sm text-gray-700">
            <li>• 并发用户: 100+</li>
            <li>• 文档处理: 10+ 个/分钟</li>
            <li>• 问答请求: 50+ 个/秒</li>
          </ul>
        </div>
        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">资源使用</h3>
          <ul class="space-y-2 text-sm text-gray-700">
            <li>• CPU使用率: &lt; 80%</li>
            <li>• 内存使用: &lt; 80%</li>
            <li>• GPU使用: &lt; 90%</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Common Performance Issues -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center text-white text-xl">
          ⚠️
        </div>
        <h2 class="text-3xl font-bold text-gray-900">常见性能问题</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl p-6 border-2 border-red-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">1. API响应慢</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>症状：</strong>API请求响应时间超过1秒</p>
            <p class="text-gray-700"><strong>可能原因：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>数据库查询慢</li>
              <li>OpenSearch检索慢</li>
              <li>Redis缓存未命中</li>
              <li>网络延迟高</li>
            </ul>
            <p class="text-gray-700 mt-3"><strong>解决方法：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>优化数据库查询，添加索引</li>
              <li>增加Redis缓存命中率</li>
              <li>优化OpenSearch查询语句</li>
              <li>使用连接池减少连接开销</li>
            </ul>
          </div>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-yellow-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">2. 问答响应慢</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>症状：</strong>问答功能响应时间超过5秒</p>
            <p class="text-gray-700"><strong>可能原因：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>LLM推理速度慢（CPU模式）</li>
              <li>向量检索慢</li>
              <li>Rerank模型处理慢</li>
              <li>上下文过长</li>
            </ul>
            <p class="text-gray-700 mt-3"><strong>解决方法：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li><strong>使用GPU加速</strong>：GPU可以显著提升LLM推理速度</li>
              <li>优化向量检索，减少Top-K值</li>
              <li>使用更快的LLM模型</li>
              <li>限制上下文长度</li>
            </ul>
          </div>
        </div>

        <div class="bg-gradient-to-br from-yellow-50 to-amber-50 rounded-xl p-6 border-2 border-yellow-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">3. 文档处理慢</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>症状：</strong>文档上传后处理时间过长</p>
            <p class="text-gray-700"><strong>可能原因：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>文档体积大</li>
              <li>向量化处理慢</li>
              <li>Celery Worker数量不足</li>
              <li>OpenSearch索引更新慢</li>
            </ul>
            <p class="text-gray-700 mt-3"><strong>解决方法：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>增加Celery Worker并发数</li>
              <li>使用GPU加速向量化</li>
              <li>优化文档分块策略</li>
              <li>批量处理文档</li>
            </ul>
          </div>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">4. 内存占用高</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>症状：</strong>系统内存使用率超过90%</p>
            <p class="text-gray-700"><strong>可能原因：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>OpenSearch JVM堆内存过大</li>
              <li>Celery Worker内存泄漏</li>
              <li>Redis缓存占用过多</li>
              <li>LLM模型占用大量内存</li>
            </ul>
            <p class="text-gray-700 mt-3"><strong>解决方法：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>调整OpenSearch JVM堆大小（推荐物理内存的50%）</li>
              <li>限制Celery Worker内存使用</li>
              <li>设置Redis最大内存和淘汰策略</li>
              <li>使用更小的LLM模型</li>
            </ul>
          </div>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">5. CPU使用率高</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>症状：</strong>CPU使用率持续超过80%</p>
            <p class="text-gray-700"><strong>可能原因：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>LLM在CPU模式下运行</li>
              <li>向量化处理占用CPU</li>
              <li>并发请求过多</li>
              <li>数据库查询复杂</li>
            </ul>
            <p class="text-gray-700 mt-3"><strong>解决方法：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li><strong>使用GPU</strong>：将LLM和向量化任务转移到GPU</li>
              <li>增加CPU核心数</li>
              <li>优化数据库查询</li>
              <li>限制并发请求数</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- Optimization Methods -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">
          ⚡
        </div>
        <h2 class="text-3xl font-bold text-gray-900">优化方法</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">1. 硬件优化</h3>
          <div class="grid md:grid-cols-2 gap-4">
            <div>
              <h4 class="font-semibold text-gray-900 mb-2">GPU加速</h4>
              <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
                <li>使用GPU运行LLM模型（推荐24GB+显存）</li>
                <li>GPU可以提升10-100倍推理速度</li>
                <li>推荐型号：RTX 3090、RTX 4090、A100</li>
              </ul>
            </div>
            <div>
              <h4 class="font-semibold text-gray-900 mb-2">SSD存储</h4>
              <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
                <li>使用SSD替代HDD</li>
                <li>提升I/O性能10倍以上</li>
                <li>加快数据库和索引访问速度</li>
              </ul>
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">2. 配置优化</h3>
          <div class="space-y-3">
            <div>
              <h4 class="font-semibold text-gray-900 mb-2">OpenSearch优化</h4>
              <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
                <li>增加分片数量：<code class="bg-gray-200 px-1 rounded">number_of_shards: 3</code></li>
                <li>增加副本数量：<code class="bg-gray-200 px-1 rounded">number_of_replicas: 1</code></li>
                <li>优化JVM堆大小：物理内存的50%</li>
                <li>使用SSD存储索引</li>
              </ul>
            </div>
            <div>
              <h4 class="font-semibold text-gray-900 mb-2">Redis优化</h4>
              <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
                <li>启用持久化：<code class="bg-gray-200 px-1 rounded">appendonly yes</code></li>
                <li>设置最大内存：<code class="bg-gray-200 px-1 rounded">maxmemory 4gb</code></li>
                <li>配置淘汰策略：<code class="bg-gray-200 px-1 rounded">maxmemory-policy allkeys-lru</code></li>
              </ul>
            </div>
            <div>
              <h4 class="font-semibold text-gray-900 mb-2">Celery优化</h4>
              <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
                <li>增加Worker数量：<code class="bg-gray-200 px-1 rounded">CELERY_CONCURRENCY=4</code></li>
                <li>使用prefork模式提升性能</li>
                <li>设置任务超时时间</li>
              </ul>
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">3. 代码优化</h3>
          <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li><strong>数据库查询优化</strong>：添加索引，避免N+1查询，使用连接池</li>
            <li><strong>缓存策略</strong>：缓存频繁访问的数据，减少数据库查询</li>
            <li><strong>异步处理</strong>：使用Celery异步处理耗时任务</li>
            <li><strong>批量操作</strong>：批量处理文档，减少API调用次数</li>
            <li><strong>分页查询</strong>：使用分页避免一次性加载大量数据</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Performance Monitoring -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xl">
          📈
        </div>
        <h2 class="text-3xl font-bold text-gray-900">性能监控</h2>
      </div>

      <div class="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border-2 border-indigo-100">
        <h3 class="text-xl font-bold text-gray-900 mb-4">监控工具</h3>
        <div class="grid md:grid-cols-2 gap-6">
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">系统监控</h4>
            <ul class="space-y-1 text-sm text-gray-700">
              <li>• <strong>htop</strong> - CPU和内存监控</li>
              <li>• <strong>nvidia-smi</strong> - GPU监控</li>
              <li>• <strong>iostat</strong> - I/O监控</li>
              <li>• <strong>netstat</strong> - 网络监控</li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">应用监控</h4>
            <ul class="space-y-1 text-sm text-gray-700">
              <li>• <strong>Prometheus</strong> - 指标收集</li>
              <li>• <strong>Grafana</strong> - 可视化展示</li>
              <li>• <strong>APM工具</strong> - 应用性能监控</li>
              <li>• <strong>日志分析</strong> - 性能问题定位</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- Related Resources -->
    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/faq" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          常见问题 →
        </router-link>
        <router-link to="/docs/log-analysis" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
          日志分析 →
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// No script logic needed for static content
</script>

<style scoped>
/* Add any specific styles for this document if needed */
</style>

