<template>
  <div class="installation-docker-deployment">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Docker部署</h1>
      <p class="text-xl text-gray-600">使用Docker Compose一键部署，最简单的方式</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">🐳</div>
        <h2 class="text-3xl font-bold text-gray-900">快速开始</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">前置要求</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>已安装 Docker（版本 20.10+）</li>
              <li>已安装 Docker Compose（版本 2.0+）</li>
              <li>至少 8GB 可用内存</li>
              <li>至少 50GB 可用磁盘空间</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">安装Docker</h3>
            <div class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">
              <code># Ubuntu/Debian<br>curl -fsSL https://get.docker.com | bash<br>sudo usermod -aG docker $USER<br><br># CentOS/RHEL<br>sudo yum install -y docker<br>sudo systemctl start docker<br>sudo systemctl enable docker</code>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">📦</div>
        <h2 class="text-3xl font-bold text-gray-900">部署步骤</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">1. 克隆代码</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">git clone &lt;repository-url&gt;<br>cd multikb-knowledge-backend</code>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">2. 配置环境变量</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">cp env.example .env<br># 编辑 .env 文件，配置数据库、Redis等连接信息</code>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">3. 启动服务</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">cd docker<br>docker-compose up -d</code>
          <p class="text-sm text-gray-700 mt-3">首次启动会自动下载镜像并创建容器，可能需要几分钟时间。</p>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">4. 验证部署</h3>
          <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
            <li>访问 <code class="bg-gray-200 px-1 rounded">http://localhost:8000/docs</code> 查看API文档</li>
            <li>访问 <code class="bg-gray-200 px-1 rounded">http://localhost:8000/health</code> 检查健康状态</li>
            <li>查看日志：<code class="bg-gray-200 px-1 rounded">docker-compose logs -f</code></li>
          </ul>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">⚙️</div>
        <h2 class="text-3xl font-bold text-gray-900">服务说明</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">后端服务</h4>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>端口：8000</li>
              <li>FastAPI应用</li>
              <li>Celery Worker</li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">MySQL</h4>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>端口：3306</li>
              <li>数据持久化</li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">Redis</h4>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>端口：6379</li>
              <li>缓存和任务队列</li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">OpenSearch</h4>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>端口：9200</li>
              <li>向量和全文检索</li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">MinIO</h4>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>端口：9000, 9001</li>
              <li>对象存储</li>
            </ul>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">Ollama</h4>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>端口：11434</li>
              <li>LLM和Embedding服务</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">🔧</div>
        <h2 class="text-3xl font-bold text-gray-900">常用操作</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
        <div class="space-y-3">
          <div>
            <h4 class="font-semibold text-gray-900 mb-1">查看日志</h4>
            <code class="block bg-gray-900 text-green-400 px-4 py-2 rounded-lg font-mono text-sm">docker-compose logs -f [service_name]</code>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-1">重启服务</h4>
            <code class="block bg-gray-900 text-green-400 px-4 py-2 rounded-lg font-mono text-sm">docker-compose restart [service_name]</code>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-1">停止服务</h4>
            <code class="block bg-gray-900 text-green-400 px-4 py-2 rounded-lg font-mono text-sm">docker-compose down</code>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-1">更新代码</h4>
            <code class="block bg-gray-900 text-green-400 px-4 py-2 rounded-lg font-mono text-sm">git pull<br>docker-compose build --no-cache<br>docker-compose up -d</code>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/environment-config" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">环境配置 →</router-link>
        <router-link to="/docs/system-requirements" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">系统要求 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

