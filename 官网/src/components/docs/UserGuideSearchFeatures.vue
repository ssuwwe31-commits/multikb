<template>
  <div class="user-guide-search-features">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">搜索功能</h1>
      <p class="text-xl text-gray-600">六种检索策略的使用场景和最佳实践</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">🔍</div>
        <h2 class="text-3xl font-bold text-gray-900">检索策略</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">1. 向量检索</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>适用场景：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>语义相似的问题查询</li>
              <li>概念性、抽象性查询</li>
              <li>需要理解用户意图的场景</li>
            </ul>
            <p class="text-gray-700 mt-3"><strong>特点：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>基于语义相似度匹配</li>
              <li>能够理解同义词和近义词</li>
              <li>适合自然语言查询</li>
            </ul>
            <p class="text-gray-700 mt-3"><strong>示例：</strong></p>
            <div class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">
              查询："如何提高系统性能"<br>
              会匹配到："系统优化方法"、"性能提升技巧"等相关内容
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">2. 关键词检索</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>适用场景：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>精确的关键词匹配</li>
              <li>代码片段、函数名搜索</li>
              <li>专有名词、术语查询</li>
            </ul>
            <p class="text-gray-700 mt-3"><strong>特点：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>快速、精确的全文检索</li>
              <li>支持布尔查询和通配符</li>
              <li>高召回率</li>
            </ul>
          </div>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">3. 混合检索</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>适用场景：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>需要平衡语义和精确匹配</li>
              <li>通用搜索场景（推荐）</li>
              <li>不确定使用哪种策略时</li>
            </ul>
            <p class="text-gray-700 mt-3"><strong>特点：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>结合向量和关键词优势</li>
              <li>可配置权重比例</li>
              <li>平衡准确性和召回率</li>
            </ul>
          </div>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">4. 精确检索</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>适用场景：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>特定短语或句子搜索</li>
              <li>代码片段精确匹配</li>
              <li>引用内容查找</li>
            </ul>
          </div>
        </div>

        <div class="bg-gradient-to-br from-yellow-50 to-amber-50 rounded-xl p-6 border-2 border-yellow-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">5. 模糊检索</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>适用场景：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>用户输入可能有错别字</li>
              <li>不完整的查询</li>
              <li>拼写不确定的情况</li>
            </ul>
          </div>
        </div>

        <div class="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border-2 border-indigo-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">6. 多模态检索</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>适用场景：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>图文混合查询</li>
              <li>需要理解图片内容</li>
              <li>跨模态内容搜索</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">💡</div>
        <h2 class="text-3xl font-bold text-gray-900">最佳实践</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <ul class="space-y-3">
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">选择合适的检索策略</strong>
              <p class="text-sm text-gray-700 mt-1">根据查询类型选择最合适的检索策略，一般推荐使用混合检索</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">使用Rerank精排</strong>
              <p class="text-sm text-gray-700 mt-1">启用Rerank模型可以对检索结果进行二次排序，提升相关性</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">调整Top-K值</strong>
              <p class="text-sm text-gray-700 mt-1">根据需求调整返回结果数量，平衡准确性和性能</p>
            </div>
          </li>
          <li class="flex items-start space-x-3">
            <svg class="w-6 h-6 text-green-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <strong class="text-gray-900">利用搜索历史</strong>
              <p class="text-sm text-gray-700 mt-1">查看搜索历史，快速重复之前的搜索</p>
            </div>
          </li>
        </ul>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/api-search" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">搜索API →</router-link>
        <router-link to="/docs/knowledge-qa" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">知识问答 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

