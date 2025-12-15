<template>
  <div class="advanced-multimodal-config">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">多模态配置</h1>
      <p class="text-xl text-gray-600">Qwen VL、CLIP模型配置和优化</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">🤖</div>
        <h2 class="text-3xl font-bold text-gray-900">Qwen VL OCR配置</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">环境变量配置</h3>
            <div class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">
              <code>OCR_ENGINE=qwen_vl<br>OLLAMA_OCR_MODEL=qwen2-vl:7b<br>OLLAMA_BASE_URL=http://localhost:11434</code>
            </div>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">模型下载</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">ollama pull qwen2-vl:7b</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">功能特点</h3>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>高精度OCR文字识别</li>
              <li>支持中英文混合识别</li>
              <li>理解图片中的表格和布局</li>
              <li>支持复杂场景文字识别</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">🖼️</div>
        <h2 class="text-3xl font-bold text-gray-900">CLIP模型配置</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">CLIP服务配置</h3>
            <p class="text-sm text-gray-700 mb-3">CLIP用于图片向量化，支持图片搜索功能</p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>可以通过API服务集成CLIP</li>
              <li>或使用本地部署的CLIP服务</li>
              <li>配置CLIP服务地址和端口</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">功能特点</h3>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>图片内容理解</li>
              <li>图片向量化</li>
              <li>以图搜图功能</li>
              <li>图文跨模态检索</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">⚙️</div>
        <h2 class="text-3xl font-bold text-gray-900">优化建议</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <ul class="space-y-3">
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">使用GPU加速</strong>
              <p class="text-sm text-gray-700 mt-1">Qwen VL和CLIP模型在GPU上运行速度更快</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">批量处理</strong>
              <p class="text-sm text-gray-700 mt-1">对于大量图片，使用批量处理提高效率</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">缓存机制</strong>
              <p class="text-sm text-gray-700 mt-1">对已处理的图片结果进行缓存，避免重复计算</p>
            </div>
          </li>
        </ul>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/system-config" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">系统配置 →</router-link>
        <router-link to="/docs/image-management" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">图片管理 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

