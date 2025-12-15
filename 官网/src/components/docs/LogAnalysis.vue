<template>
  <div class="log-analysis">
    <!-- Title -->
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
        日志分析
      </h1>
      <p class="text-xl text-gray-600">
        日志查看、日志分析、问题定位方法
      </p>
    </div>

    <!-- Log Locations -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">
          📁
        </div>
        <h2 class="text-3xl font-bold text-gray-900">日志文件位置</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">应用日志</h3>
          <div class="space-y-2 text-sm text-gray-700">
            <p><strong>主日志文件：</strong></p>
            <code class="block bg-gray-200 px-3 py-2 rounded mt-1">logs/app.log</code>
            <p class="mt-3"><strong>错误日志：</strong></p>
            <code class="block bg-gray-200 px-3 py-2 rounded mt-1">logs/error.log</code>
            <p class="mt-3"><strong>访问日志：</strong></p>
            <code class="block bg-gray-200 px-3 py-2 rounded mt-1">logs/access.log</code>
          </div>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">服务日志</h3>
          <div class="space-y-2 text-sm text-gray-700">
            <p><strong>MySQL：</strong></p>
            <code class="block bg-gray-200 px-3 py-2 rounded mt-1">/var/log/mysql/error.log</code>
            <p class="mt-3"><strong>OpenSearch：</strong></p>
            <code class="block bg-gray-200 px-3 py-2 rounded mt-1">/var/log/opensearch/opensearch.log</code>
            <p class="mt-3"><strong>Redis：</strong></p>
            <code class="block bg-gray-200 px-3 py-2 rounded mt-1">/var/log/redis/redis-server.log</code>
            <p class="mt-3"><strong>Celery：</strong></p>
            <code class="block bg-gray-200 px-3 py-2 rounded mt-1">logs/celery.log</code>
          </div>
        </div>
      </div>
    </section>

    <!-- Log Viewing Commands -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">
          👁️
        </div>
        <h2 class="text-3xl font-bold text-gray-900">日志查看命令</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-gray-50 to-slate-50 rounded-xl p-6 border-2 border-gray-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">实时查看日志</h3>
          <div class="space-y-3">
            <div>
              <p class="text-sm text-gray-600 mb-2">查看应用主日志（实时）：</p>
              <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">tail -f logs/app.log</code>
            </div>
            <div>
              <p class="text-sm text-gray-600 mb-2">查看错误日志（实时）：</p>
              <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">tail -f logs/error.log</code>
            </div>
            <div>
              <p class="text-sm text-gray-600 mb-2">查看最近100行日志：</p>
              <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">tail -n 100 logs/app.log</code>
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-br from-gray-50 to-slate-50 rounded-xl p-6 border-2 border-gray-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">搜索日志内容</h3>
          <div class="space-y-3">
            <div>
              <p class="text-sm text-gray-600 mb-2">搜索包含"ERROR"的日志：</p>
              <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">grep -i "ERROR" logs/app.log</code>
            </div>
            <div>
              <p class="text-sm text-gray-600 mb-2">搜索特定时间段的日志：</p>
              <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">grep "2024-01-15" logs/app.log</code>
            </div>
            <div>
              <p class="text-sm text-gray-600 mb-2">搜索并显示上下文（前后5行）：</p>
              <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">grep -C 5 "ERROR" logs/app.log</code>
            </div>
            <div>
              <p class="text-sm text-gray-600 mb-2">统计错误数量：</p>
              <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">grep -c "ERROR" logs/app.log</code>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Log Analysis Methods -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">
          🔬
        </div>
        <h2 class="text-3xl font-bold text-gray-900">日志分析方法</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">1. 按时间线分析</h3>
          <p class="text-gray-700 mb-3">按照时间顺序查看日志，了解问题发生的时间点和前后事件：</p>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">grep "2024-01-15 14:" logs/app.log | less</code>
          <p class="text-sm text-gray-600 mt-3">这样可以清楚地看到问题发生前后的系统状态变化。</p>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">2. 按错误级别分析</h3>
          <p class="text-gray-700 mb-3">根据日志级别（ERROR、WARNING、INFO）筛选关键信息：</p>
          <div class="space-y-2">
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">grep "ERROR" logs/app.log > errors.txt</code>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">grep "WARNING" logs/app.log > warnings.txt</code>
          </div>
          <p class="text-sm text-gray-600 mt-3">优先关注ERROR级别的日志，这些通常指向问题的根本原因。</p>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">3. 按模块/功能分析</h3>
          <p class="text-gray-700 mb-3">根据不同的功能模块筛选相关日志：</p>
          <div class="space-y-2">
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">grep "document" logs/app.log</code>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">grep "vectorization" logs/app.log</code>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">grep "search" logs/app.log</code>
          </div>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">4. 关联分析</h3>
          <p class="text-gray-700 mb-3">结合多个日志文件，找出问题的关联性：</p>
          <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
            <li>同时查看应用日志和服务日志</li>
            <li>对比错误发生时间，找出因果关系</li>
            <li>检查是否有多个服务同时报错</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Common Log Patterns -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center text-white text-xl">
          📊
        </div>
        <h2 class="text-3xl font-bold text-gray-900">常见日志模式</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl p-6 border-2 border-yellow-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">连接错误模式</h3>
          <div class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mb-3">
            ERROR: Connection refused to OpenSearch at localhost:9200
          </div>
          <p class="text-sm text-gray-700"><strong>含义：</strong>无法连接到OpenSearch服务</p>
          <p class="text-sm text-gray-700 mt-2"><strong>解决方法：</strong>检查OpenSearch服务状态和端口配置</p>
        </div>

        <div class="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl p-6 border-2 border-yellow-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">超时错误模式</h3>
          <div class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mb-3">
            ERROR: Request timeout after 30s
          </div>
          <p class="text-sm text-gray-700"><strong>含义：</strong>请求处理超时</p>
          <p class="text-sm text-gray-700 mt-2"><strong>解决方法：</strong>检查服务性能，考虑增加超时时间或优化处理逻辑</p>
        </div>

        <div class="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl p-6 border-2 border-yellow-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">内存不足模式</h3>
          <div class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mb-3">
            WARNING: Out of memory, killing process
          </div>
          <p class="text-sm text-gray-700"><strong>含义：</strong>系统内存不足</p>
          <p class="text-sm text-gray-700 mt-2"><strong>解决方法：</strong>增加服务器内存，或优化内存使用配置</p>
        </div>

        <div class="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl p-6 border-2 border-yellow-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">向量化失败模式</h3>
          <div class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mb-3">
            ERROR: Vectorization failed: Model unavailable
          </div>
          <p class="text-sm text-gray-700"><strong>含义：</strong>向量化模型不可用</p>
          <p class="text-sm text-gray-700 mt-2"><strong>解决方法：</strong>检查Ollama服务，确认模型已下载</p>
        </div>
      </div>
    </section>

    <!-- Log Tools -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xl">
          🛠️
        </div>
        <h2 class="text-3xl font-bold text-gray-900">日志分析工具</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border-2 border-indigo-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">命令行工具</h3>
          <ul class="space-y-2 text-sm text-gray-700">
            <li>• <code class="bg-gray-200 px-2 py-1 rounded">tail</code> - 实时查看日志</li>
            <li>• <code class="bg-gray-200 px-2 py-1 rounded">grep</code> - 搜索日志内容</li>
            <li>• <code class="bg-gray-200 px-2 py-1 rounded">less</code> - 分页查看日志</li>
            <li>• <code class="bg-gray-200 px-2 py-1 rounded">awk</code> - 日志统计分析</li>
            <li>• <code class="bg-gray-200 px-2 py-1 rounded">sed</code> - 日志文本处理</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">可视化工具</h3>
          <ul class="space-y-2 text-sm text-gray-700">
            <li>• <strong>ELK Stack</strong> - Elasticsearch + Logstash + Kibana</li>
            <li>• <strong>Grafana Loki</strong> - 日志聚合和查询</li>
            <li>• <strong>Prometheus</strong> - 指标监控和告警</li>
            <li>• <strong>Jaeger</strong> - 分布式追踪</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Best Practices -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white text-xl">
          ✅
        </div>
        <h2 class="text-3xl font-bold text-gray-900">最佳实践</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 border-2 border-green-100">
        <ul class="space-y-3">
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">定期清理日志</strong>
              <p class="text-sm text-gray-700 mt-1">设置日志轮转策略，避免日志文件过大占用磁盘空间</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">设置日志级别</strong>
              <p class="text-sm text-gray-700 mt-1">生产环境使用INFO级别，开发环境使用DEBUG级别</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">记录关键操作</strong>
              <p class="text-sm text-gray-700 mt-1">在关键操作点添加日志记录，便于问题追踪</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">统一日志格式</strong>
              <p class="text-sm text-gray-700 mt-1">使用统一的日志格式，包含时间戳、级别、模块、消息等信息</p>
            </div>
          </li>
        </ul>
      </div>
    </section>

    <!-- Related Resources -->
    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/error-troubleshooting" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          错误排查 →
        </router-link>
        <router-link to="/docs/performance-issues" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
          性能问题 →
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

