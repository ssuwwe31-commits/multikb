<template>
  <div class="api-document">
    <!-- Title -->
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
        文档管理API
      </h1>
      <p class="text-xl text-gray-600">
        文档上传、查询、更新、删除等接口文档
      </p>
    </div>

    <!-- Base Path -->
    <section class="mb-16">
      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">基础路径</h3>
        <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">/api/v1/documents</code>
      </div>
    </section>

    <!-- Document Upload -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">
          📤
        </div>
        <h2 class="text-3xl font-bold text-gray-900">文档上传</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">单文件上传</h3>
          <div class="space-y-3">
            <div>
              <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/documents/upload</p>
              <p class="text-sm text-gray-600">上传单个文档文件</p>
            </div>
            <div>
              <p class="text-sm text-gray-700 mb-2"><strong>请求参数：</strong></p>
              <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
                <li><code class="bg-gray-200 px-1 rounded">file</code> (File) - 文档文件（支持PDF、DOCX、PPTX、Excel、HTML、MD、TXT、JSON、XML）</li>
                <li><code class="bg-gray-200 px-1 rounded">knowledge_base_id</code> (Integer) - 知识库ID</li>
                <li><code class="bg-gray-200 px-1 rounded">category_id</code> (Integer, 可选) - 分类ID</li>
                <li><code class="bg-gray-200 px-1 rounded">tags</code> (Array, 可选) - 标签列表</li>
              </ul>
            </div>
            <div>
              <p class="text-sm text-gray-700 mb-2"><strong>响应示例：</strong></p>
              <pre class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm overflow-x-auto"><code>{
  "code": 200,
  "data": {
    "id": 123,
    "name": "example.pdf",
    "status": "processing",
    "knowledge_base_id": 1
  }
}</code></pre>
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">批量上传</h3>
          <div class="space-y-3">
            <div>
              <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/documents/batch-upload</p>
              <p class="text-sm text-gray-600">批量上传多个文档文件</p>
            </div>
            <div>
              <p class="text-sm text-gray-700 mb-2"><strong>请求参数：</strong></p>
              <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
                <li><code class="bg-gray-200 px-1 rounded">files</code> (Array[File]) - 文档文件数组</li>
                <li><code class="bg-gray-200 px-1 rounded">knowledge_base_id</code> (Integer) - 知识库ID</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Document Query -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">
          🔍
        </div>
        <h2 class="text-3xl font-bold text-gray-900">文档查询</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">获取文档列表</h3>
          <div class="space-y-3">
            <div>
              <p class="text-sm font-semibold text-gray-700 mb-1">GET /api/v1/documents</p>
              <p class="text-sm text-gray-600">获取文档列表，支持分页和筛选</p>
            </div>
            <div>
              <p class="text-sm text-gray-700 mb-2"><strong>查询参数：</strong></p>
              <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
                <li><code class="bg-gray-200 px-1 rounded">knowledge_base_id</code> (Integer, 可选) - 知识库ID</li>
                <li><code class="bg-gray-200 px-1 rounded">page</code> (Integer, 默认1) - 页码</li>
                <li><code class="bg-gray-200 px-1 rounded">size</code> (Integer, 默认20) - 每页数量</li>
                <li><code class="bg-gray-200 px-1 rounded">status</code> (String, 可选) - 文档状态</li>
                <li><code class="bg-gray-200 px-1 rounded">search</code> (String, 可选) - 搜索关键词</li>
              </ul>
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">获取文档详情</h3>
          <div class="space-y-3">
            <div>
              <p class="text-sm font-semibold text-gray-700 mb-1">GET /api/v1/documents/{doc_id}</p>
              <p class="text-sm text-gray-600">获取指定文档的详细信息</p>
            </div>
            <div>
              <p class="text-sm text-gray-700 mb-2"><strong>路径参数：</strong></p>
              <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
                <li><code class="bg-gray-200 px-1 rounded">doc_id</code> (Integer) - 文档ID</li>
              </ul>
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">获取文档分块</h3>
          <div class="space-y-3">
            <div>
              <p class="text-sm font-semibold text-gray-700 mb-1">GET /api/v1/documents/{doc_id}/chunks</p>
              <p class="text-sm text-gray-600">获取文档的所有分块</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Document Update -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">
          ✏️
        </div>
        <h2 class="text-3xl font-bold text-gray-900">文档更新</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
        <h3 class="text-xl font-bold text-gray-900 mb-4">更新文档信息</h3>
        <div class="space-y-3">
          <div>
            <p class="text-sm font-semibold text-gray-700 mb-1">PUT /api/v1/documents/{doc_id}</p>
            <p class="text-sm text-gray-600">更新文档的元数据信息</p>
          </div>
          <div>
            <p class="text-sm text-gray-700 mb-2"><strong>请求体：</strong></p>
            <pre class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm overflow-x-auto"><code>{
  "name": "新文档名称",
  "category_id": 2,
  "tags": ["标签1", "标签2"]
}</code></pre>
          </div>
        </div>
      </div>
    </section>

    <!-- Document Delete -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-pink-600 flex items-center justify-center text-white text-xl">
          🗑️
        </div>
        <h2 class="text-3xl font-bold text-gray-900">文档删除</h2>
      </div>

      <div class="bg-gradient-to-br from-red-50 to-pink-50 rounded-xl p-6 border-2 border-red-100">
        <h3 class="text-xl font-bold text-gray-900 mb-4">删除文档</h3>
        <div class="space-y-3">
          <div>
            <p class="text-sm font-semibold text-gray-700 mb-1">DELETE /api/v1/documents/{doc_id}</p>
            <p class="text-sm text-gray-600">删除指定文档（包括所有分块和向量）</p>
          </div>
          <div>
            <p class="text-sm text-gray-700 mb-2"><strong>批量删除：</strong></p>
            <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/documents/batch/delete</p>
            <p class="text-sm text-gray-600">批量删除多个文档</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Other Operations -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xl">
          🔧
        </div>
        <h2 class="text-3xl font-bold text-gray-900">其他操作</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-4">
        <div class="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border-2 border-indigo-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">文档预览</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">GET /api/v1/documents/{doc_id}/preview</p>
          <p class="text-sm text-gray-600">获取文档预览内容</p>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">重新处理</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/documents/{doc_id}/reprocess</p>
          <p class="text-sm text-gray-600">重新处理文档（重新分块和向量化）</p>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">批量移动</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/documents/batch/move</p>
          <p class="text-sm text-gray-600">批量移动文档到其他知识库</p>
        </div>

        <div class="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl p-6 border-2 border-yellow-100">
          <h3 class="text-lg font-bold text-gray-900 mb-2">标签管理</h3>
          <p class="text-sm font-semibold text-gray-700 mb-1">POST /api/v1/documents/batch/tags/add</p>
          <p class="text-sm text-gray-600">批量添加、删除、替换标签</p>
        </div>
      </div>
    </section>

    <!-- Related Resources -->
    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/api-overview" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          API概览 →
        </router-link>
        <router-link to="/docs/api-openapi" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
          OpenAPI规范 →
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

