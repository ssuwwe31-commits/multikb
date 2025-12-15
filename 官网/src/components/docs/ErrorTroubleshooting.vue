<template>
  <div class="error-troubleshooting">
    <!-- Title -->
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
        错误排查
      </h1>
      <p class="text-xl text-gray-600">
        常见错误代码、错误原因和解决方法
      </p>
    </div>

    <!-- Common Error Codes -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center text-white text-xl">
          🐛
        </div>
        <h2 class="text-3xl font-bold text-gray-900">常见错误代码</h2>
      </div>

      <div class="space-y-4">
        <!-- Validation Errors -->
        <div class="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl p-6 border-2 border-red-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">内容验证错误 (7001-7003)</h3>
          <div class="space-y-3">
            <div class="bg-white rounded-lg p-4 border border-gray-200">
              <div class="flex items-start space-x-3">
                <span class="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-bold">7001</span>
                <div class="flex-1">
                  <h4 class="font-semibold text-gray-900">CONTENT_TOO_LONG</h4>
                  <p class="text-sm text-gray-600 mt-1">内容长度超过限制</p>
                  <p class="text-sm text-gray-700 mt-2"><strong>解决方法：</strong>减少内容长度，或调整系统配置中的最大长度限制</p>
                </div>
              </div>
            </div>
            <div class="bg-white rounded-lg p-4 border border-gray-200">
              <div class="flex items-start space-x-3">
                <span class="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-bold">7002</span>
                <div class="flex-1">
                  <h4 class="font-semibold text-gray-900">CONTENT_FORMAT_ERROR</h4>
                  <p class="text-sm text-gray-600 mt-1">内容格式不正确</p>
                  <p class="text-sm text-gray-700 mt-2"><strong>解决方法：</strong>检查内容格式是否符合要求，确保编码正确</p>
                </div>
              </div>
            </div>
            <div class="bg-white rounded-lg p-4 border border-gray-200">
              <div class="flex items-start space-x-3">
                <span class="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-bold">7003</span>
                <div class="flex-1">
                  <h4 class="font-semibold text-gray-900">CONTENT_ENCODING_ERROR</h4>
                  <p class="text-sm text-gray-600 mt-1">字符编码错误</p>
                  <p class="text-sm text-gray-700 mt-2"><strong>解决方法：</strong>确保文档使用UTF-8编码，检查文件编码设置</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Processing Errors -->
        <div class="bg-gradient-to-br from-orange-50 to-yellow-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">处理错误 (7004-7006)</h3>
          <div class="space-y-3">
            <div class="bg-white rounded-lg p-4 border border-gray-200">
              <div class="flex items-start space-x-3">
                <span class="px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-sm font-bold">7004</span>
                <div class="flex-1">
                  <h4 class="font-semibold text-gray-900">CHUNK_NOT_FOUND</h4>
                  <p class="text-sm text-gray-600 mt-1">块不存在或已被删除</p>
                  <p class="text-sm text-gray-700 mt-2"><strong>解决方法：</strong>刷新页面，检查文档是否已被删除或修改</p>
                </div>
              </div>
            </div>
            <div class="bg-white rounded-lg p-4 border border-gray-200">
              <div class="flex items-start space-x-3">
                <span class="px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-sm font-bold">7005</span>
                <div class="flex-1">
                  <h4 class="font-semibold text-gray-900">PERMISSION_DENIED</h4>
                  <p class="text-sm text-gray-600 mt-1">没有修改权限</p>
                  <p class="text-sm text-gray-700 mt-2"><strong>解决方法：</strong>联系管理员获取相应权限，或检查知识库访问权限设置</p>
                </div>
              </div>
            </div>
            <div class="bg-white rounded-lg p-4 border border-gray-200">
              <div class="flex items-start space-x-3">
                <span class="px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-sm font-bold">7006</span>
                <div class="flex-1">
                  <h4 class="font-semibold text-gray-900">VERSION_CONFLICT</h4>
                  <p class="text-sm text-gray-600 mt-1">版本冲突</p>
                  <p class="text-sm text-gray-700 mt-2"><strong>解决方法：</strong>刷新页面获取最新版本，然后重新尝试操作</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Vectorization Errors -->
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">向量化错误 (7007-7008)</h3>
          <div class="space-y-3">
            <div class="bg-white rounded-lg p-4 border border-gray-200">
              <div class="flex items-start space-x-3">
                <span class="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-bold">7007</span>
                <div class="flex-1">
                  <h4 class="font-semibold text-gray-900">VECTORIZATION_FAILED</h4>
                  <p class="text-sm text-gray-600 mt-1">向量化失败</p>
                  <p class="text-sm text-gray-700 mt-2"><strong>解决方法：</strong></p>
                  <ul class="list-disc list-inside text-sm text-gray-700 mt-1 ml-4">
                    <li>检查Ollama服务是否正常运行</li>
                    <li>确认Embedding模型已正确下载</li>
                    <li>查看Ollama日志：<code class="bg-gray-200 px-1 rounded">docker logs ollama</code></li>
                    <li>测试Ollama连接：<code class="bg-gray-200 px-1 rounded">curl http://localhost:11434/api/tags</code></li>
                  </ul>
                </div>
              </div>
            </div>
            <div class="bg-white rounded-lg p-4 border border-gray-200">
              <div class="flex items-start space-x-3">
                <span class="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-bold">7008</span>
                <div class="flex-1">
                  <h4 class="font-semibold text-gray-900">MODEL_UNAVAILABLE</h4>
                  <p class="text-sm text-gray-600 mt-1">向量化模型不可用</p>
                  <p class="text-sm text-gray-700 mt-2"><strong>解决方法：</strong></p>
                  <ul class="list-disc list-inside text-sm text-gray-700 mt-1 ml-4">
                    <li>检查模型是否已下载：<code class="bg-gray-200 px-1 rounded">ollama list</code></li>
                    <li>下载缺失的模型：<code class="bg-gray-200 px-1 rounded">ollama pull nomic-embed-text</code></li>
                    <li>确认.env中的模型名称配置正确</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Index Errors -->
        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">索引更新错误 (7009-7010)</h3>
          <div class="space-y-3">
            <div class="bg-white rounded-lg p-4 border border-gray-200">
              <div class="flex items-start space-x-3">
                <span class="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-bold">7009</span>
                <div class="flex-1">
                  <h4 class="font-semibold text-gray-900">INDEX_UPDATE_FAILED</h4>
                  <p class="text-sm text-gray-600 mt-1">索引更新失败</p>
                  <p class="text-sm text-gray-700 mt-2"><strong>解决方法：</strong></p>
                  <ul class="list-disc list-inside text-sm text-gray-700 mt-1 ml-4">
                    <li>检查OpenSearch服务状态</li>
                    <li>确认OpenSearch连接配置正确</li>
                    <li>查看OpenSearch日志：<code class="bg-gray-200 px-1 rounded">tail -f /var/log/opensearch/opensearch.log</code></li>
                    <li>检查索引是否存在：<code class="bg-gray-200 px-1 rounded">curl http://localhost:9200/_cat/indices</code></li>
                  </ul>
                </div>
              </div>
            </div>
            <div class="bg-white rounded-lg p-4 border border-gray-200">
              <div class="flex items-start space-x-3">
                <span class="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-bold">7010</span>
                <div class="flex-1">
                  <h4 class="font-semibold text-gray-900">CACHE_UPDATE_FAILED</h4>
                  <p class="text-sm text-gray-600 mt-1">缓存更新失败</p>
                  <p class="text-sm text-gray-700 mt-2"><strong>解决方法：</strong></p>
                  <ul class="list-disc list-inside text-sm text-gray-700 mt-1 ml-4">
                    <li>检查Redis服务是否正常运行</li>
                    <li>测试Redis连接：<code class="bg-gray-200 px-1 rounded">redis-cli ping</code></li>
                    <li>检查Redis内存使用情况</li>
                    <li>清理Redis缓存：<code class="bg-gray-200 px-1 rounded">redis-cli FLUSHDB</code></li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Service Connection Errors -->
        <div class="bg-gradient-to-br from-gray-50 to-slate-50 rounded-xl p-6 border-2 border-gray-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">服务连接错误</h3>
          <div class="space-y-3">
            <div class="bg-white rounded-lg p-4 border border-gray-200">
              <h4 class="font-semibold text-gray-900 mb-2">OPENSEARCH_CONNECTION_FAILED</h4>
              <p class="text-sm text-gray-700"><strong>解决方法：</strong></p>
              <ul class="list-disc list-inside text-sm text-gray-700 mt-1 ml-4">
                <li>检查OpenSearch是否启动：<code class="bg-gray-200 px-1 rounded">systemctl status opensearch</code></li>
                <li>确认端口9200未被占用</li>
                <li>检查防火墙规则</li>
                <li>验证.env中的OPENSEARCH_URL配置</li>
              </ul>
            </div>
            <div class="bg-white rounded-lg p-4 border border-gray-200">
              <h4 class="font-semibold text-gray-900 mb-2">OLLAMA_API_FAILED</h4>
              <p class="text-sm text-gray-700"><strong>解决方法：</strong></p>
              <ul class="list-disc list-inside text-sm text-gray-700 mt-1 ml-4">
                <li>检查Ollama服务状态</li>
                <li>确认OLLAMA_BASE_URL配置正确</li>
                <li>检查GPU资源是否充足</li>
                <li>查看Ollama错误日志</li>
              </ul>
            </div>
            <div class="bg-white rounded-lg p-4 border border-gray-200">
              <h4 class="font-semibold text-gray-900 mb-2">MINIO_UPLOAD_FAILED</h4>
              <p class="text-sm text-gray-700"><strong>解决方法：</strong></p>
              <ul class="list-disc list-inside text-sm text-gray-700 mt-1 ml-4">
                <li>检查MinIO服务状态</li>
                <li>确认存储桶已创建</li>
                <li>验证访问密钥配置</li>
                <li>检查存储空间是否充足</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Error Diagnosis Steps -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">
          🔍
        </div>
        <h2 class="text-3xl font-bold text-gray-900">错误诊断步骤</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <ol class="space-y-4">
          <li class="flex items-start space-x-4">
            <span class="flex-shrink-0 w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center font-bold">1</span>
            <div>
              <h3 class="font-semibold text-gray-900">查看错误信息</h3>
              <p class="text-sm text-gray-700 mt-1">仔细阅读错误消息，记录错误代码和详细描述</p>
            </div>
          </li>
          <li class="flex items-start space-x-4">
            <span class="flex-shrink-0 w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center font-bold">2</span>
            <div>
              <h3 class="font-semibold text-gray-900">检查服务状态</h3>
              <p class="text-sm text-gray-700 mt-1">确认相关服务（MySQL、OpenSearch、Redis、MinIO、Ollama）是否正常运行</p>
            </div>
          </li>
          <li class="flex items-start space-x-4">
            <span class="flex-shrink-0 w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center font-bold">3</span>
            <div>
              <h3 class="font-semibold text-gray-900">查看日志文件</h3>
              <p class="text-sm text-gray-700 mt-1">检查应用日志、服务日志，查找相关错误信息。参考 <router-link to="/docs/log-analysis" class="text-blue-600 hover:underline">日志分析文档</router-link></p>
            </div>
          </li>
          <li class="flex items-start space-x-4">
            <span class="flex-shrink-0 w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center font-bold">4</span>
            <div>
              <h3 class="font-semibold text-gray-900">验证配置</h3>
              <p class="text-sm text-gray-700 mt-1">检查.env配置文件，确认所有配置项正确无误</p>
            </div>
          </li>
          <li class="flex items-start space-x-4">
            <span class="flex-shrink-0 w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center font-bold">5</span>
            <div>
              <h3 class="font-semibold text-gray-900">尝试解决方案</h3>
              <p class="text-sm text-gray-700 mt-1">根据错误代码和上述解决方法，尝试修复问题</p>
            </div>
          </li>
          <li class="flex items-start space-x-4">
            <span class="flex-shrink-0 w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center font-bold">6</span>
            <div>
              <h3 class="font-semibold text-gray-900">寻求帮助</h3>
              <p class="text-sm text-gray-700 mt-1">如果问题仍未解决，查看 <router-link to="/docs/faq" class="text-blue-600 hover:underline">常见问题</router-link> 或联系 <router-link to="/docs/community-support" class="text-blue-600 hover:underline">社区支持</router-link></p>
            </div>
          </li>
        </ol>
      </div>
    </section>

    <!-- Related Resources -->
    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/faq" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          常见问题 →
        </router-link>
        <router-link to="/docs/log-analysis" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
          日志分析 →
        </router-link>
        <router-link to="/docs/performance-issues" class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
          性能问题 →
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

