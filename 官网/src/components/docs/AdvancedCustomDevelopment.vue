<template>
  <div class="advanced-custom-development">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">二次开发</h1>
      <p class="text-xl text-gray-600">插件开发、API扩展、自定义功能开发</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">🔌</div>
        <h2 class="text-3xl font-bold text-gray-900">插件开发</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">插件架构</h3>
            <p class="text-sm text-gray-700 mb-3">Multikb Base 支持插件机制，可以扩展系统功能：</p>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>文档处理插件（自定义解析器）</li>
              <li>检索插件（自定义检索策略）</li>
              <li>问答插件（自定义问答逻辑）</li>
              <li>导出插件（自定义导出格式）</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">开发指南</h3>
            <ol class="list-decimal list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>实现插件接口</li>
              <li>注册插件到系统</li>
              <li>配置插件参数</li>
              <li>测试插件功能</li>
            </ol>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">🔧</div>
        <h2 class="text-3xl font-bold text-gray-900">API扩展</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">自定义API</h3>
            <p class="text-sm text-gray-700 mb-3">基于FastAPI框架，可以轻松添加自定义API：</p>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>创建新的路由文件</li>
              <li>实现业务逻辑</li>
              <li>注册到API路由器</li>
              <li>添加API文档</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">API示例</h3>
            <pre class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm overflow-x-auto"><code>from fastapi import APIRouter

router = APIRouter()

@router.get("/custom/endpoint")
async def custom_endpoint():
    return {"message": "Custom API"}</code></pre>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">🎨</div>
        <h2 class="text-3xl font-bold text-gray-900">自定义功能</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">前端定制</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>自定义UI组件</li>
              <li>扩展前端功能</li>
              <li>集成第三方服务</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">后端定制</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>扩展服务层</li>
              <li>自定义业务逻辑</li>
              <li>集成外部系统</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">数据库扩展</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>添加自定义数据表</li>
              <li>扩展现有模型</li>
              <li>自定义查询逻辑</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">📚</div>
        <h2 class="text-3xl font-bold text-gray-900">开发资源</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
        <div class="grid md:grid-cols-2 gap-6">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-3">技术栈</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>后端：FastAPI + Python</li>
              <li>前端：Vue 3 + TypeScript</li>
              <li>数据库：MySQL + OpenSearch</li>
              <li>任务队列：Celery + Redis</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-3">开发工具</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>代码格式化：Black、isort</li>
              <li>类型检查：mypy</li>
              <li>测试框架：pytest</li>
              <li>API文档：OpenAPI/Swagger</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/api-overview" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">API概览 →</router-link>
        <a href="https://github.com/ssuwwe31-commits/multikb" target="_blank" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">GitHub仓库 →</a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

