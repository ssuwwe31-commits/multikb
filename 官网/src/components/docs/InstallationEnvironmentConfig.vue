<template>
  <div class="installation-environment-config">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">环境配置</h1>
      <p class="text-xl text-gray-600">MySQL、OpenSearch、Redis、MinIO等中间件配置</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">🗄️</div>
        <h2 class="text-3xl font-bold text-gray-900">MySQL配置</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">环境变量</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">DATABASE_URL=mysql+pymysql://user:password@localhost:3306/spx_knowledge<br>MYSQL_HOST=localhost<br>MYSQL_PORT=3306<br>MYSQL_USER=user<br>MYSQL_PASSWORD=password<br>MYSQL_DATABASE=spx_knowledge</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">性能优化</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>调整 innodb_buffer_pool_size（推荐为内存的70-80%）</li>
              <li>配置连接池大小</li>
              <li>启用慢查询日志</li>
              <li>定期优化表</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">🔍</div>
        <h2 class="text-3xl font-bold text-gray-900">OpenSearch配置</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">环境变量</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">OPENSEARCH_URL=http://localhost:9200</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">JVM配置</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>设置堆内存：-Xms4g -Xmx4g（推荐为系统内存的50%）</li>
              <li>配置GC参数</li>
              <li>调整线程池大小</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">索引配置</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>调整分片数量（number_of_shards）</li>
              <li>设置副本数量（number_of_replicas）</li>
              <li>配置knn参数（HNSW_M、HNSW_EF_CONSTRUCTION）</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center text-white text-xl">💾</div>
        <h2 class="text-3xl font-bold text-gray-900">Redis配置</h2>
      </div>

      <div class="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl p-6 border-2 border-red-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">环境变量</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">REDIS_URL=redis://localhost:6379/0</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">配置优化</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>设置最大内存限制（maxmemory）</li>
              <li>配置内存淘汰策略（maxmemory-policy）</li>
              <li>启用持久化（RDB或AOF）</li>
              <li>配置连接池</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">📦</div>
        <h2 class="text-3xl font-bold text-gray-900">MinIO配置</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">环境变量</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">MINIO_ENDPOINT=localhost:9000<br>MINIO_ROOT_USER=minioadmin<br>MINIO_ROOT_PASSWORD=minioadmin<br>MINIO_BUCKET_NAME=multikb-knowledge-base<br>MINIO_SECURE=false</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">存储配置</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>配置存储路径和容量</li>
              <li>设置访问策略</li>
              <li>配置生命周期规则</li>
              <li>启用版本控制（可选）</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-yellow-600 flex items-center justify-center text-white text-xl">🤖</div>
        <h2 class="text-3xl font-bold text-gray-900">Ollama配置</h2>
      </div>

      <div class="bg-gradient-to-br from-orange-50 to-yellow-50 rounded-xl p-6 border-2 border-orange-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">环境变量</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">OLLAMA_BASE_URL=http://localhost:11434<br>OLLAMA_MODEL=llama2<br>OLLAMA_EMBEDDING_MODEL=nomic-embed-text<br>OLLAMA_OCR_MODEL=qwen2-vl:7b</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">模型下载</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">ollama pull llama2<br>ollama pull nomic-embed-text<br>ollama pull qwen2-vl:7b</code>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/docker-deployment" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Docker部署 →</router-link>
        <router-link to="/docs/system-requirements" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">系统要求 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

