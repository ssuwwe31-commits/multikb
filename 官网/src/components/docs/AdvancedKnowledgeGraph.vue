<template>
  <div class="advanced-knowledge-graph">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">知识图谱</h1>
      <p class="text-xl text-gray-600">知识图谱构建、实体提取、关系识别（企业版）</p>
    </div>

    <div class="mb-6 p-4 bg-yellow-50 border-2 border-yellow-200 rounded-xl">
      <div class="flex items-start space-x-3">
        <svg class="w-6 h-6 text-yellow-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
        </svg>
        <div>
          <div class="font-semibold text-yellow-900 mb-1">企业版功能</div>
          <div class="text-sm text-yellow-800">知识图谱功能仅在企业版中提供，需要企业版License。</div>
        </div>
      </div>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">📊</div>
        <h2 class="text-3xl font-bold text-gray-900">知识图谱概述</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <p class="text-gray-700 mb-4">知识图谱通过实体和关系的方式组织知识，提供更结构化的知识表示和查询能力。</p>
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">核心概念</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li><strong>实体</strong>：知识的基本单元（人物、地点、概念等）</li>
              <li><strong>关系</strong>：实体之间的连接（属于、引用、依赖等）</li>
              <li><strong>图谱</strong>：实体和关系构成的网络结构</li>
            </ul>
          </div>
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">主要功能</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>自动实体提取</li>
              <li>关系识别</li>
              <li>图谱可视化</li>
              <li>关系查询</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">🔍</div>
        <h2 class="text-3xl font-bold text-gray-900">实体提取</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">实体类型</h3>
            <div class="grid md:grid-cols-4 gap-3">
              <div class="bg-white p-3 rounded-lg border border-gray-200">
                <div class="font-semibold text-gray-900">人物</div>
                <div class="text-xs text-gray-600">person</div>
              </div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">
                <div class="font-semibold text-gray-900">地点</div>
                <div class="text-xs text-gray-600">location</div>
              </div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">
                <div class="font-semibold text-gray-900">概念</div>
                <div class="text-xs text-gray-600">concept</div>
              </div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">
                <div class="font-semibold text-gray-900">产品</div>
                <div class="text-xs text-gray-600">product</div>
              </div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">
                <div class="font-semibold text-gray-900">技术</div>
                <div class="text-xs text-gray-600">technology</div>
              </div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">
                <div class="font-semibold text-gray-900">事件</div>
                <div class="text-xs text-gray-600">event</div>
              </div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">
                <div class="font-semibold text-gray-900">组织</div>
                <div class="text-xs text-gray-600">organization</div>
              </div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">
                <div class="font-semibold text-gray-900">其他</div>
                <div class="text-xs text-gray-600">other</div>
              </div>
            </div>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">自动提取</h3>
            <p class="text-sm text-gray-700">系统使用LLM自动从文档中提取实体，支持批量处理</p>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">手动创建</h3>
            <p class="text-sm text-gray-700">可以手动创建和编辑实体，补充自动提取的结果</p>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">🔗</div>
        <h2 class="text-3xl font-bold text-gray-900">关系识别</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">关系类型</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li><strong>belongs_to</strong>：属于关系</li>
              <li><strong>references</strong>：引用关系</li>
              <li><strong>depends_on</strong>：依赖关系</li>
              <li><strong>compares</strong>：对比关系</li>
              <li><strong>implements</strong>：实现关系</li>
              <li><strong>related_to</strong>：相关关系</li>
              <li><strong>part_of</strong>：部分关系</li>
              <li><strong>has_part</strong>：包含关系</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">自动识别</h3>
            <p class="text-sm text-gray-700">系统自动识别实体之间的关系，并计算关系权重</p>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">📈</div>
        <h2 class="text-3xl font-bold text-gray-900">图谱可视化</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">交互式可视化</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>节点和边的可视化展示</li>
              <li>支持缩放、拖拽、搜索</li>
              <li>点击节点查看详细信息</li>
              <li>高亮显示关系路径</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">关系查询</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>查询实体的所有关系</li>
              <li>查找两个实体之间的路径</li>
              <li>按关系类型筛选</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/pricing" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">了解企业版 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

