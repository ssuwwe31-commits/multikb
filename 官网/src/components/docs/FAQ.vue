<template>
  <div class="faq">
    <!-- Title -->
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
        常见问题
      </h1>
      <p class="text-xl text-gray-600">
        安装、配置、使用中的常见问题和解决方案
      </p>
    </div>

    <!-- Installation FAQs -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">
          📦
        </div>
        <h2 class="text-3xl font-bold text-gray-900">安装相关问题</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">Q: 如何快速部署 Multikb Base？</h3>
          <div class="text-gray-700 space-y-2">
            <p><strong>A:</strong> 推荐使用 Docker Compose 一键部署：</p>
            <ol class="list-decimal list-inside space-y-2 ml-4">
              <li>克隆项目仓库</li>
              <li>复制 <code class="bg-gray-200 px-2 py-1 rounded">env.example</code> 为 <code class="bg-gray-200 px-2 py-1 rounded">.env</code> 并配置</li>
              <li>运行 <code class="bg-gray-200 px-2 py-1 rounded">docker-compose up -d</code></li>
              <li>访问 <code class="bg-gray-200 px-2 py-1 rounded">http://localhost:3000</code></li>
            </ol>
            <p class="mt-3">详细步骤请参考 <router-link to="/docs/docker-deployment" class="text-blue-600 hover:underline">Docker部署文档</router-link>。</p>
          </div>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">Q: 系统要求是什么？</h3>
          <div class="text-gray-700 space-y-2">
            <p><strong>A:</strong> 最低配置要求：</p>
            <ul class="list-disc list-inside space-y-1 ml-4">
              <li>CPU: 4核</li>
              <li>内存: 8GB RAM</li>
              <li>GPU: 8GB 显存（用于LLM和向量化）</li>
              <li>存储: 50GB</li>
              <li>操作系统: Linux (Ubuntu 20.04+, CentOS 7+)</li>
            </ul>
            <p class="mt-3">详细要求请参考 <router-link to="/docs/system-requirements" class="text-blue-600 hover:underline">系统要求文档</router-link>。</p>
          </div>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">Q: 必须使用GPU吗？</h3>
          <div class="text-gray-700">
            <p><strong>A:</strong> GPU不是必须的，但强烈推荐使用。系统可以在CPU模式下运行，但性能会显著下降：</p>
            <ul class="list-disc list-inside space-y-1 ml-4 mt-2">
              <li><strong>有GPU</strong>：LLM推理速度快，向量化效率高，适合生产环境</li>
              <li><strong>无GPU</strong>：可以运行，但响应速度慢，仅适合测试和小规模使用</li>
            </ul>
            <p class="mt-3">建议至少使用 8GB 显存的GPU（最低配置）或 24GB+ 显存（推荐配置）。</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Configuration FAQs -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">
          ⚙️
        </div>
        <h2 class="text-3xl font-bold text-gray-900">配置相关问题</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">Q: 如何配置Ollama服务？</h3>
          <div class="text-gray-700 space-y-2">
            <p><strong>A:</strong> 配置步骤：</p>
            <ol class="list-decimal list-inside space-y-2 ml-4">
              <li>安装并启动Ollama服务</li>
              <li>下载所需的模型：
                <ul class="list-disc list-inside ml-6 mt-1">
                  <li>LLM模型：<code class="bg-gray-200 px-2 py-1 rounded">llama2</code> 或 <code class="bg-gray-200 px-2 py-1 rounded">qwen2</code></li>
                  <li>Embedding模型：<code class="bg-gray-200 px-2 py-1 rounded">nomic-embed-text</code></li>
                  <li>OCR模型：<code class="bg-gray-200 px-2 py-1 rounded">qwen2-vl:7b</code></li>
                </ul>
              </li>
              <li>在 <code class="bg-gray-200 px-2 py-1 rounded">.env</code> 中配置 <code class="bg-gray-200 px-2 py-1 rounded">OLLAMA_BASE_URL</code></li>
              <li>测试连接：<code class="bg-gray-200 px-2 py-1 rounded">curl http://localhost:11434/api/tags</code></li>
            </ol>
          </div>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">Q: OpenSearch连接失败怎么办？</h3>
          <div class="text-gray-700 space-y-2">
            <p><strong>A:</strong> 检查以下项目：</p>
            <ul class="list-disc list-inside space-y-1 ml-4">
              <li>确认OpenSearch服务已启动：<code class="bg-gray-200 px-2 py-1 rounded">curl http://localhost:9200</code></li>
              <li>检查 <code class="bg-gray-200 px-2 py-1 rounded">OPENSEARCH_URL</code> 配置是否正确</li>
              <li>确认防火墙规则允许9200端口访问</li>
              <li>检查OpenSearch日志：<code class="bg-gray-200 px-2 py-1 rounded">tail -f /var/log/opensearch/opensearch.log</code></li>
              <li>确认已安装 <code class="bg-gray-200 px-2 py-1 rounded">opensearch-knn</code> 插件</li>
            </ul>
          </div>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">Q: 如何配置ClamAV病毒扫描？</h3>
          <div class="text-gray-700 space-y-2">
            <p><strong>A:</strong> ClamAV是可选的，但生产环境强烈推荐：</p>
            <ol class="list-decimal list-inside space-y-2 ml-4">
              <li>安装ClamAV：<code class="bg-gray-200 px-2 py-1 rounded">sudo apt-get install clamav clamav-daemon</code></li>
              <li>更新病毒库：<code class="bg-gray-200 px-2 py-1 rounded">sudo freshclam</code></li>
              <li>启动ClamAV服务：<code class="bg-gray-200 px-2 py-1 rounded">sudo systemctl start clamav-daemon</code></li>
              <li>在 <code class="bg-gray-200 px-2 py-1 rounded">.env</code> 中设置 <code class="bg-gray-200 px-2 py-1 rounded">CLAMAV_ENABLED=true</code></li>
              <li>配置ClamAV连接地址（默认：<code class="bg-gray-200 px-2 py-1 rounded">localhost:3310</code>）</li>
            </ol>
          </div>
        </div>
      </div>
    </section>

    <!-- Usage FAQs -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">
          💬
        </div>
        <h2 class="text-3xl font-bold text-gray-900">使用相关问题</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">Q: 文档上传后为什么无法检索？</h3>
          <div class="text-gray-700 space-y-2">
            <p><strong>A:</strong> 可能的原因和解决方法：</p>
            <ul class="list-disc list-inside space-y-1 ml-4">
              <li><strong>文档正在处理中</strong>：检查文档状态，等待处理完成</li>
              <li><strong>向量化失败</strong>：检查Ollama服务是否正常，查看错误日志</li>
              <li><strong>索引更新失败</strong>：检查OpenSearch连接和索引状态</li>
              <li><strong>文档格式不支持</strong>：确认文档格式在支持列表中（PDF, DOCX, PPTX等）</li>
            </ul>
            <p class="mt-3">查看文档处理状态和错误信息，参考 <router-link to="/docs/error-troubleshooting" class="text-blue-600 hover:underline">错误排查文档</router-link>。</p>
          </div>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">Q: 问答结果不准确怎么办？</h3>
          <div class="text-gray-700 space-y-2">
            <p><strong>A:</strong> 可以尝试以下优化方法：</p>
            <ul class="list-disc list-inside space-y-1 ml-4">
              <li><strong>调整检索策略</strong>：尝试混合检索或多模态检索</li>
              <li><strong>增加检索数量</strong>：提高Top-K值，召回更多相关文档</li>
              <li><strong>启用Rerank</strong>：使用Rerank模型对结果进行精排</li>
              <li><strong>优化文档分块</strong>：调整分块大小和策略，确保语义完整性</li>
              <li><strong>检查知识库内容</strong>：确保相关文档已正确上传和处理</li>
            </ul>
          </div>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">Q: 支持哪些文档格式？</h3>
          <div class="text-gray-700 space-y-2">
            <p><strong>A:</strong> Multikb Base 支持以下9种文档格式：</p>
            <div class="grid md:grid-cols-3 gap-2 mt-3">
              <div class="bg-white p-3 rounded-lg border border-gray-200">📄 PDF</div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">📝 DOCX</div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">📊 PPTX</div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">📈 Excel</div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">🌐 HTML</div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">📋 Markdown</div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">📄 TXT</div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">🔧 JSON</div>
              <div class="bg-white p-3 rounded-lg border border-gray-200">📦 XML</div>
            </div>
          </div>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">Q: 如何管理文档版本？</h3>
          <div class="text-gray-700 space-y-2">
            <p><strong>A:</strong> Multikb Base 提供双层版本管理：</p>
            <ul class="list-disc list-inside space-y-1 ml-4">
              <li><strong>文档级版本</strong>：记录整个文档的修改历史，支持版本恢复和对比</li>
              <li><strong>块级版本</strong>：对每个知识块进行细粒度版本控制</li>
            </ul>
            <p class="mt-3">在文档详情页可以查看版本历史、对比差异、恢复到任意版本。详细操作请参考 <router-link to="/docs/version-management" class="text-blue-600 hover:underline">版本管理文档</router-link>。</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Performance FAQs -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center text-white text-xl">
          ⚡
        </div>
        <h2 class="text-3xl font-bold text-gray-900">性能相关问题</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">Q: 系统响应慢怎么办？</h3>
          <div class="text-gray-700 space-y-2">
            <p><strong>A:</strong> 可以从以下几个方面优化：</p>
            <ul class="list-disc list-inside space-y-1 ml-4">
              <li><strong>使用GPU</strong>：GPU可以显著提升LLM推理和向量化速度</li>
              <li><strong>增加Redis缓存</strong>：启用缓存可以减少重复计算</li>
              <li><strong>优化OpenSearch</strong>：调整索引配置，增加分片和副本</li>
              <li><strong>调整Celery并发</strong>：根据服务器资源调整Worker数量</li>
              <li><strong>使用SSD存储</strong>：提升I/O性能</li>
            </ul>
            <p class="mt-3">详细优化方法请参考 <router-link to="/docs/performance-issues" class="text-blue-600 hover:underline">性能问题文档</router-link>。</p>
          </div>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">Q: 内存占用过高怎么办？</h3>
          <div class="text-gray-700 space-y-2">
            <p><strong>A:</strong> 优化建议：</p>
            <ul class="list-disc list-inside space-y-1 ml-4">
              <li>限制OpenSearch的JVM堆大小（推荐物理内存的50%）</li>
              <li>调整Celery Worker的内存限制</li>
              <li>定期清理Redis缓存</li>
              <li>优化文档分块大小，减少内存占用</li>
              <li>考虑增加服务器内存或使用内存更大的配置</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- Still Need Help -->
    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">仍然需要帮助？</h3>
      <p class="text-gray-700 mb-4">
        如果以上问题无法解决您的问题，您可以：
      </p>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/error-troubleshooting" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          查看错误排查 →
        </router-link>
        <router-link to="/docs/community-support" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
          获取社区支持 →
        </router-link>
        <router-link to="/contact" class="px-4 py-2 bg-white border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
          联系我们 →
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

