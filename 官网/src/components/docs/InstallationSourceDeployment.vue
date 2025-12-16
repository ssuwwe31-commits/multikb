<template>
  <div class="installation-source-deployment">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">源码部署</h1>
      <p class="text-xl text-gray-600">从源码编译部署，完全自定义配置</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">💻</div>
        <h2 class="text-3xl font-bold text-gray-900">前置要求</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <div class="grid md:grid-cols-2 gap-6">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-3">系统要求</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>Python 3.10+</li>
              <li>Node.js 18+</li>
              <li>MySQL 5.7+</li>
              <li>Redis 6.0+</li>
              <li>OpenSearch 2.0+</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-3">开发工具</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>Git</li>
              <li>pip / poetry</li>
              <li>npm / yarn</li>
              <li>虚拟环境工具</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">📦</div>
        <h2 class="text-3xl font-bold text-gray-900">后端部署</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">1. 克隆代码</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">git clone &lt;repository-url&gt;<br>cd multikb-knowledge-backend</code>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">2. 创建虚拟环境</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">python -m venv venv<br>source venv/bin/activate  # Linux/Mac<br># 或 venv\Scripts\activate  # Windows</code>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">3. 安装依赖</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">pip install -r requirements.txt<br># 或使用 poetry<br>poetry install</code>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">4. 配置环境变量</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">cp env.example .env<br># 编辑 .env 文件，配置数据库、Redis等连接信息</code>
        </div>

        <div class="bg-gradient-to-br from-yellow-50 to-amber-50 rounded-xl p-6 border-2 border-yellow-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">5. 初始化数据库</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">mysql -u root -p &lt; init.sql<br># 或使用 Alembic 迁移<br>alembic upgrade head</code>
        </div>

        <div class="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border-2 border-indigo-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">6. 启动服务</h3>
          <div class="space-y-2">
            <div>
              <p class="text-sm text-gray-700 mb-1">开发模式：</p>
              <code class="block bg-gray-900 text-green-400 px-4 py-2 rounded-lg font-mono text-sm">uvicorn app.main:app --reload</code>
            </div>
            <div>
              <p class="text-sm text-gray-700 mb-1">生产模式：</p>
              <code class="block bg-gray-900 text-green-400 px-4 py-2 rounded-lg font-mono text-sm">gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker</code>
            </div>
            <div>
              <p class="text-sm text-gray-700 mb-1">启动Celery Worker：</p>
              <code class="block bg-gray-900 text-green-400 px-4 py-2 rounded-lg font-mono text-sm">celery -A app.tasks.celery_app worker --loglevel=info</code>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">🖥️</div>
        <h2 class="text-3xl font-bold text-gray-900">前端部署</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">1. 安装依赖</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">cd multikb-knowledge-frontend<br>npm install</code>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">2. 配置环境变量</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">cp .env.example .env<br># 设置 VITE_API_BASE_URL 和 VITE_WS_BASE_URL</code>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">3. 开发模式</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">npm run dev</code>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">4. 生产构建</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">npm run build<br># 构建产物在 dist/ 目录<br># 可以使用 nginx 或其他静态服务器托管</code>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">🔧</div>
        <h2 class="text-3xl font-bold text-gray-900">进程管理</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">使用 Supervisor</h3>
            <p class="text-sm text-gray-700 mb-2">配置 Supervisor 管理后端和 Celery 进程：</p>
            <code class="block bg-gray-900 text-green-400 px-4 py-2 rounded-lg font-mono text-sm">sudo apt-get install supervisor<br># 配置 /etc/supervisor/conf.d/spx.conf</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">使用 systemd</h3>
            <p class="text-sm text-gray-700 mb-2">创建 systemd 服务文件管理应用：</p>
            <code class="block bg-gray-900 text-green-400 px-4 py-2 rounded-lg font-mono text-sm">sudo systemctl enable spx-backend<br>sudo systemctl start spx-backend</code>
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

