<template>
  <div class="installation-monitoring-alerting">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">监控告警</h1>
      <p class="text-xl text-gray-600">Prometheus、Grafana监控配置和告警设置</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">📊</div>
        <h2 class="text-3xl font-bold text-gray-900">Prometheus配置</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">安装Prometheus</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm"># 使用Docker<br>docker run -d \<br>&nbsp;&nbsp;--name prometheus \<br>&nbsp;&nbsp;-p 9090:9090 \<br>&nbsp;&nbsp;-v /path/to/prometheus.yml:/etc/prometheus/prometheus.yml \<br>&nbsp;&nbsp;prom/prometheus</code>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">配置采集目标</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">scrape_configs:<br>&nbsp;&nbsp;- job_name: 'spx-backend'<br>&nbsp;&nbsp;&nbsp;&nbsp;static_configs:<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- targets: ['localhost:8000']<br>&nbsp;&nbsp;- job_name: 'mysql'<br>&nbsp;&nbsp;&nbsp;&nbsp;static_configs:<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- targets: ['localhost:9104']</code>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">📈</div>
        <h2 class="text-3xl font-bold text-gray-900">Grafana配置</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">安装Grafana</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm"># 使用Docker<br>docker run -d \<br>&nbsp;&nbsp;--name grafana \<br>&nbsp;&nbsp;-p 3000:3000 \<br>&nbsp;&nbsp;grafana/grafana</code>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">配置数据源</h3>
          <ol class="list-decimal list-inside space-y-1 text-sm text-gray-700 ml-4">
            <li>访问 Grafana：http://localhost:3000</li>
            <li>默认账号：admin/admin</li>
            <li>添加 Prometheus 数据源</li>
            <li>配置数据源URL：http://prometheus:9090</li>
          </ol>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">创建仪表盘</h3>
          <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
            <li>导入预置仪表盘模板</li>
            <li>创建自定义监控面板</li>
            <li>配置关键指标展示：
              <ul class="list-disc list-inside ml-6 mt-2">
                <li>API请求量和响应时间</li>
                <li>数据库连接数和查询性能</li>
                <li>Celery任务执行情况</li>
                <li>系统资源使用率</li>
              </ul>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center text-white text-xl">🚨</div>
        <h2 class="text-3xl font-bold text-gray-900">告警配置</h2>
      </div>

      <div class="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl p-6 border-2 border-red-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">告警规则</h3>
            <p class="text-sm text-gray-700 mb-2">在Prometheus中配置告警规则：</p>
            <code class="block bg-gray-900 text-green-400 px-4 py-2 rounded-lg font-mono text-sm">groups:<br>&nbsp;&nbsp;- name: spx_alerts<br>&nbsp;&nbsp;&nbsp;&nbsp;rules:<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- alert: HighErrorRate<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;for: 5m</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">告警通知</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>配置Alertmanager接收告警</li>
              <li>集成邮件通知</li>
              <li>集成企业微信/钉钉</li>
              <li>集成Slack/Webhook</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">📋</div>
        <h2 class="text-3xl font-bold text-gray-900">监控指标</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">应用指标</h4>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>API请求量（QPS）</li>
              <li>响应时间（P50/P95/P99）</li>
              <li>错误率</li>
              <li>活跃会话数</li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">系统指标</h4>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>CPU使用率</li>
              <li>内存使用率</li>
              <li>磁盘IO</li>
              <li>网络流量</li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">数据库指标</h4>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>连接数</li>
              <li>查询性能</li>
              <li>慢查询数</li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">任务指标</h4>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>Celery任务数</li>
              <li>任务执行时间</li>
              <li>失败任务数</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/performance-optimization" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">性能优化 →</router-link>
        <router-link to="/docs/k8s-monitoring" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">K8s监控 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

