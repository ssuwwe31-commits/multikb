<template>
  <div class="api-overview">
    <!-- Title -->
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
        API概览
      </h1>
      <p class="text-xl text-gray-600">
        91个API接口概览，认证方式和请求格式
      </p>
    </div>

    <!-- API Statistics -->
    <section class="mb-16">
      <div class="grid md:grid-cols-4 gap-6">
        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <div class="text-3xl font-bold text-blue-600 mb-2">91+</div>
          <div class="text-gray-700">API接口</div>
        </div>
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <div class="text-3xl font-bold text-green-600 mb-2">15+</div>
          <div class="text-gray-700">功能模块</div>
        </div>
        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <div class="text-3xl font-bold text-orange-600 mb-2">REST</div>
          <div class="text-gray-700">API风格</div>
        </div>
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <div class="text-3xl font-bold text-purple-600 mb-2">3.0</div>
          <div class="text-gray-700">OpenAPI版本</div>
        </div>
      </div>
    </section>

    <!-- Base URL -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">
          🌐
        </div>
        <h2 class="text-3xl font-bold text-gray-900">基础URL</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">生产环境</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">https://api.yourdomain.com/api/v1</code>
          </div>
          <div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">开发环境</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">http://localhost:8000/api/v1</code>
          </div>
        </div>
      </div>
    </section>

    <!-- Authentication -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">
          🔐
        </div>
        <h2 class="text-3xl font-bold text-gray-900">认证方式</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <h3 class="text-xl font-bold text-gray-900 mb-4">Bearer Token认证</h3>
        <p class="text-gray-700 mb-4">所有API请求（除认证接口外）都需要在请求头中携带Token：</p>
        <div class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mb-4">
          Authorization: Bearer &lt;your-token&gt;
        </div>
        
        <h4 class="font-semibold text-gray-900 mb-2 mt-6">获取Token</h4>
        <div class="space-y-3">
          <div>
            <p class="text-sm text-gray-600 mb-1">1. 登录接口获取Token：</p>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">POST /api/v1/auth/login</code>
          </div>
          <div>
            <p class="text-sm text-gray-600 mb-1">2. 请求体：</p>
            <pre class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm overflow-x-auto"><code>{
  "username": "your-username",
  "password": "your-password"
}</code></pre>
          </div>
          <div>
            <p class="text-sm text-gray-600 mb-1">3. 响应示例：</p>
            <pre class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm overflow-x-auto"><code>{
  "code": 200,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 3600
  }
}</code></pre>
          </div>
        </div>
      </div>
    </section>

    <!-- API Modules -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">
          📦
        </div>
        <h2 class="text-3xl font-bold text-gray-900">API模块</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">📚 文档管理</h3>
          <p class="text-sm text-gray-600 mb-3">文档上传、查询、更新、删除等操作</p>
          <ul class="space-y-1 text-sm text-gray-700">
            <li>• 文档上传（单文件/批量）</li>
            <li>• 文档查询和列表</li>
            <li>• 文档更新和删除</li>
            <li>• 文档分块管理</li>
            <li>• 文档预览和导出</li>
          </ul>
          <router-link to="/docs/api-document" class="inline-block mt-4 text-blue-600 hover:underline text-sm font-medium">
            查看详细文档 →
          </router-link>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">💬 智能问答</h3>
          <p class="text-sm text-gray-600 mb-3">文本问答、图片问答、流式输出</p>
          <ul class="space-y-1 text-sm text-gray-700">
            <li>• 文本问答</li>
            <li>• 图片问答</li>
            <li>• 图文混合问答</li>
            <li>• 流式问答输出</li>
            <li>• 问答会话管理</li>
          </ul>
          <router-link to="/docs/api-qa" class="inline-block mt-4 text-green-600 hover:underline text-sm font-medium">
            查看详细文档 →
          </router-link>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">🔍 搜索功能</h3>
          <p class="text-sm text-gray-600 mb-3">多种检索策略和高级搜索</p>
          <ul class="space-y-1 text-sm text-gray-700">
            <li>• 向量搜索</li>
            <li>• 关键词搜索</li>
            <li>• 混合搜索</li>
            <li>• 高级搜索</li>
            <li>• 搜索历史</li>
          </ul>
          <router-link to="/docs/api-search" class="inline-block mt-4 text-orange-600 hover:underline text-sm font-medium">
            查看详细文档 →
          </router-link>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">🖼️ 图片管理</h3>
          <p class="text-sm text-gray-600 mb-3">图片上传、OCR识别、图片搜索</p>
          <ul class="space-y-1 text-sm text-gray-700">
            <li>• 图片上传</li>
            <li>• OCR文字识别</li>
            <li>• 图片搜索</li>
            <li>• 图片向量化</li>
            <li>• 相似图片检索</li>
          </ul>
          <router-link to="/docs/api-image" class="inline-block mt-4 text-purple-600 hover:underline text-sm font-medium">
            查看详细文档 →
          </router-link>
        </div>

        <div class="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-xl p-6 border-2 border-indigo-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">📊 管理功能</h3>
          <p class="text-sm text-gray-600 mb-3">知识库、用户、系统管理</p>
          <ul class="space-y-1 text-sm text-gray-700">
            <li>• 知识库管理</li>
            <li>• 用户管理</li>
            <li>• 权限管理</li>
            <li>• 系统配置</li>
            <li>• 数据统计</li>
          </ul>
          <router-link to="/docs/api-management" class="inline-block mt-4 text-indigo-600 hover:underline text-sm font-medium">
            查看详细文档 →
          </router-link>
        </div>

        <div class="bg-gradient-to-br from-cyan-50 to-blue-50 rounded-xl p-6 border-2 border-cyan-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">🔌 WebSocket</h3>
          <p class="text-sm text-gray-600 mb-3">实时通信和消息推送</p>
          <ul class="space-y-1 text-sm text-gray-700">
            <li>• 实时问答</li>
            <li>• 任务进度推送</li>
            <li>• 文档状态更新</li>
            <li>• 消息通知</li>
          </ul>
          <router-link to="/docs/api-websocket" class="inline-block mt-4 text-cyan-600 hover:underline text-sm font-medium">
            查看详细文档 →
          </router-link>
        </div>
      </div>
    </section>

    <!-- Request/Response Format -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center text-white text-xl">
          📝
        </div>
        <h2 class="text-3xl font-bold text-gray-900">请求和响应格式</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl p-6 border-2 border-yellow-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">请求格式</h3>
          <ul class="space-y-3 text-gray-700">
            <li>
              <strong>Content-Type:</strong> 
              <code class="bg-gray-200 px-2 py-1 rounded text-sm">application/json</code>
            </li>
            <li>
              <strong>请求头:</strong>
              <pre class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mt-2">Authorization: Bearer &lt;token&gt;
Content-Type: application/json</pre>
            </li>
            <li>
              <strong>请求体示例:</strong>
              <pre class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mt-2 overflow-x-auto"><code>{
  "name": "示例文档",
  "knowledge_base_id": 1
}</code></pre>
            </li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">响应格式</h3>
          <ul class="space-y-3 text-gray-700">
            <li>
              <strong>成功响应:</strong>
              <pre class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mt-2 overflow-x-auto"><code>{
  "code": 200,
  "message": "success",
  "data": { ... }
}</code></pre>
            </li>
            <li>
              <strong>错误响应:</strong>
              <pre class="bg-gray-900 text-red-400 px-4 py-3 rounded-lg font-mono text-sm mt-2 overflow-x-auto"><code>{
  "code": 400,
  "message": "错误描述",
  "error_code": "ERROR_CODE"
}</code></pre>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <!-- HTTP Status Codes -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center text-white text-xl">
          📊
        </div>
        <h2 class="text-3xl font-bold text-gray-900">HTTP状态码</h2>
      </div>

      <div class="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl p-6 border-2 border-red-100">
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">成功响应</h3>
            <ul class="space-y-1 text-sm text-gray-700">
              <li><code class="bg-gray-200 px-2 py-1 rounded">200</code> - 请求成功</li>
              <li><code class="bg-gray-200 px-2 py-1 rounded">201</code> - 创建成功</li>
              <li><code class="bg-gray-200 px-2 py-1 rounded">204</code> - 无内容（删除成功）</li>
            </ul>
          </div>
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">错误响应</h3>
            <ul class="space-y-1 text-sm text-gray-700">
              <li><code class="bg-gray-200 px-2 py-1 rounded">400</code> - 请求参数错误</li>
              <li><code class="bg-gray-200 px-2 py-1 rounded">401</code> - 未授权</li>
              <li><code class="bg-gray-200 px-2 py-1 rounded">403</code> - 禁止访问</li>
              <li><code class="bg-gray-200 px-2 py-1 rounded">404</code> - 资源不存在</li>
              <li><code class="bg-gray-200 px-2 py-1 rounded">500</code> - 服务器错误</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- Rate Limiting -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-gray-500 to-slate-600 flex items-center justify-center text-white text-xl">
          ⏱️
        </div>
        <h2 class="text-3xl font-bold text-gray-900">速率限制</h2>
      </div>

      <div class="bg-gradient-to-br from-gray-50 to-slate-50 rounded-xl p-6 border-2 border-gray-100">
        <p class="text-gray-700 mb-4">为了保护系统稳定性，API实施了速率限制：</p>
        <ul class="space-y-2 text-gray-700">
          <li>• <strong>普通用户：</strong> 100 请求/分钟</li>
          <li>• <strong>认证用户：</strong> 500 请求/分钟</li>
          <li>• <strong>企业用户：</strong> 1000 请求/分钟</li>
        </ul>
        <p class="text-sm text-gray-600 mt-4">超过限制时，将返回 <code class="bg-gray-200 px-2 py-1 rounded">429 Too Many Requests</code> 错误。</p>
      </div>
    </section>

    <!-- OpenAPI Documentation -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xl">
          📖
        </div>
        <h2 class="text-3xl font-bold text-gray-900">OpenAPI文档</h2>
      </div>

      <div class="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border-2 border-indigo-100">
        <p class="text-gray-700 mb-4">Knowledge Base 提供完整的OpenAPI 3.0规范文档：</p>
        <div class="space-y-3">
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">Swagger UI</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">http://localhost:8000/docs</code>
            <p class="text-sm text-gray-600 mt-2">交互式API文档，可以直接测试API</p>
          </div>
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">ReDoc</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">http://localhost:8000/redoc</code>
            <p class="text-sm text-gray-600 mt-2">美观的API文档展示</p>
          </div>
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">OpenAPI JSON</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">http://localhost:8000/openapi.json</code>
            <p class="text-sm text-gray-600 mt-2">机器可读的OpenAPI规范，支持代码生成</p>
          </div>
        </div>
        <router-link to="/docs/api-openapi" class="inline-block mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">
          查看OpenAPI规范详情 →
        </router-link>
      </div>
    </section>

    <!-- Next Steps -->
    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">下一步</h3>
      <p class="text-gray-700 mb-4">查看各个模块的详细API文档：</p>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/api-document" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          文档管理API →
        </router-link>
        <router-link to="/docs/api-qa" class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
          问答API →
        </router-link>
        <router-link to="/docs/api-search" class="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors">
          搜索API →
        </router-link>
        <router-link to="/docs/api-image" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
          图片API →
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

