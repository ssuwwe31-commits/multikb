<template>
  <div class="api-openapi">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">OpenAPI规范</h1>
      <p class="text-xl text-gray-600">完整的OpenAPI 3.0规范文档，支持代码生成</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">📖</div>
        <h2 class="text-3xl font-bold text-gray-900">OpenAPI文档</h2>
      </div>

      <div class="grid md:grid-cols-3 gap-6">
        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">Swagger UI</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mb-3">http://localhost:8000/docs</code>
          <p class="text-sm text-gray-600 mb-4">交互式API文档，可以直接测试API接口</p>
          <ul class="space-y-1 text-sm text-gray-700">
            <li>• 查看所有API接口</li>
            <li>• 在线测试API</li>
            <li>• 查看请求/响应示例</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">ReDoc</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mb-3">http://localhost:8000/redoc</code>
          <p class="text-sm text-gray-600 mb-4">美观的三栏式API文档展示</p>
          <ul class="space-y-1 text-sm text-gray-700">
            <li>• 清晰的文档结构</li>
            <li>• 响应式设计</li>
            <li>• 易于阅读</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">OpenAPI JSON</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mb-3">http://localhost:8000/openapi.json</code>
          <p class="text-sm text-gray-600 mb-4">机器可读的OpenAPI规范</p>
          <ul class="space-y-1 text-sm text-gray-700">
            <li>• 支持代码生成</li>
            <li>• API客户端生成</li>
            <li>• 集成第三方工具</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">🔧</div>
        <h2 class="text-3xl font-bold text-gray-900">代码生成</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <h3 class="text-xl font-bold text-gray-900 mb-4">使用OpenAPI Generator</h3>
        <div class="space-y-3">
          <div>
            <p class="text-sm text-gray-700 mb-2"><strong>安装工具：</strong></p>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">npm install @openapitools/openapi-generator-cli -g</code>
          </div>
          <div>
            <p class="text-sm text-gray-700 mb-2"><strong>生成客户端代码：</strong></p>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">openapi-generator-cli generate -i http://localhost:8000/openapi.json -g typescript-axios -o ./api-client</code>
          </div>
          <div>
            <p class="text-sm text-gray-700 mb-2"><strong>支持的语言：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>TypeScript / JavaScript</li>
              <li>Python</li>
              <li>Java</li>
              <li>Go</li>
              <li>PHP</li>
              <li>更多...</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xl">📋</div>
        <h2 class="text-3xl font-bold text-gray-900">规范特性</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border-2 border-indigo-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">完整的API定义</h3>
          <ul class="space-y-2 text-sm text-gray-700">
            <li>• 所有91+个API接口</li>
            <li>• 请求/响应模型</li>
            <li>• 参数验证规则</li>
            <li>• 错误码定义</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">认证信息</h3>
          <ul class="space-y-2 text-sm text-gray-700">
            <li>• Bearer Token认证</li>
            <li>• 安全方案定义</li>
            <li>• 权限说明</li>
          </ul>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/api-overview" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">API概览 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

