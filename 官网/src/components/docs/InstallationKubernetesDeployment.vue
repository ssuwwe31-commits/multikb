<template>
  <div class="installation-kubernetes-deployment">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Kubernetes部署</h1>
      <p class="text-xl text-gray-600">在K8s集群中部署，适合生产环境</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">☸️</div>
        <h2 class="text-3xl font-bold text-gray-900">前置要求</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
          <li>已部署 Kubernetes 集群（版本 1.20+）</li>
          <li>已安装 kubectl 并配置集群访问</li>
          <li>已配置 StorageClass 用于持久化存储</li>
          <li>已配置 Ingress Controller（可选）</li>
          <li>集群节点资源充足（推荐配置见系统要求）</li>
        </ul>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">📦</div>
        <h2 class="text-3xl font-bold text-gray-900">部署步骤</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">1. 准备配置文件</h3>
          <p class="text-sm text-gray-700 mb-3">创建 Kubernetes 部署配置文件，包括：</p>
          <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
            <li>Deployment：应用部署配置</li>
            <li>Service：服务暴露配置</li>
            <li>ConfigMap：配置管理</li>
            <li>Secret：敏感信息（数据库密码等）</li>
            <li>PersistentVolumeClaim：持久化存储</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">2. 创建命名空间</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">kubectl create namespace spx-knowledge</code>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">3. 创建Secret</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">kubectl create secret generic spx-secrets \<br>&nbsp;&nbsp;--from-literal=mysql-password=your-password \<br>&nbsp;&nbsp;--from-literal=redis-password=your-password \<br>&nbsp;&nbsp;-n spx-knowledge</code>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">4. 部署应用</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">kubectl apply -f k8s/ -n spx-knowledge</code>
        </div>

        <div class="bg-gradient-to-br from-yellow-50 to-amber-50 rounded-xl p-6 border-2 border-yellow-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">5. 检查部署状态</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">kubectl get pods -n spx-knowledge<br>kubectl get svc -n spx-knowledge<br>kubectl logs -f deployment/spx-backend -n spx-knowledge</code>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">⚙️</div>
        <h2 class="text-3xl font-bold text-gray-900">配置说明</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">资源限制</h3>
            <p class="text-sm text-gray-700 mb-2">为每个服务设置合适的资源请求和限制：</p>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>后端服务：CPU 2核，内存 4GB</li>
              <li>Celery Worker：CPU 1核，内存 2GB</li>
              <li>MySQL：CPU 2核，内存 4GB</li>
              <li>OpenSearch：CPU 4核，内存 8GB</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">持久化存储</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>MySQL数据：使用PVC持久化</li>
              <li>OpenSearch数据：使用PVC持久化</li>
              <li>MinIO数据：使用PVC持久化</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">服务暴露</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>使用Service暴露内部服务</li>
              <li>使用Ingress暴露HTTP/HTTPS服务</li>
              <li>配置LoadBalancer或NodePort（可选）</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">🔄</div>
        <h2 class="text-3xl font-bold text-gray-900">扩缩容</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="space-y-3">
          <div>
            <h4 class="font-semibold text-gray-900 mb-1">手动扩缩容</h4>
            <code class="block bg-gray-900 text-green-400 px-4 py-2 rounded-lg font-mono text-sm">kubectl scale deployment spx-backend --replicas=3 -n spx-knowledge</code>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-1">自动扩缩容（HPA）</h4>
            <p class="text-sm text-gray-700">配置HorizontalPodAutoscaler，根据CPU/内存使用率自动扩缩容</p>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/monitoring-alerting" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">监控告警 →</router-link>
        <router-link to="/docs/system-requirements" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">系统要求 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

