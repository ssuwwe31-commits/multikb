<template>
  <div class="user-guide-security-scanning">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">安全扫描</h1>
      <p class="text-xl text-gray-600">ClamAV病毒扫描配置和使用指南</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center text-white text-xl">🛡️</div>
        <h2 class="text-3xl font-bold text-gray-900">ClamAV配置</h2>
      </div>

      <div class="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl p-6 border-2 border-red-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">安装ClamAV</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mb-3">sudo apt-get install clamav clamav-daemon</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">更新病毒库</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mb-3">sudo freshclam</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">启动服务</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm mb-3">sudo systemctl start clamav-daemon</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">配置环境变量</h3>
            <div class="bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">
              <code>CLAMAV_ENABLED=true<br>CLAMAV_HOST=localhost<br>CLAMAV_PORT=3310</code>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-yellow-600 flex items-center justify-center text-white text-xl">⚙️</div>
        <h2 class="text-3xl font-bold text-gray-900">扫描模式</h2>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-gradient-to-br from-orange-50 to-yellow-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">实时扫描</h3>
          <p class="text-sm text-gray-700">文档上传时自动进行病毒扫描</p>
        </div>
        <div class="bg-gradient-to-br from-red-50 to-pink-50 rounded-xl p-6 border-2 border-red-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">强制扫描</h3>
          <p class="text-sm text-gray-700">必须通过扫描才能入库（CLAMAV_FORCE_SCAN=true）</p>
        </div>
        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">历史补扫描</h3>
          <p class="text-sm text-gray-700">对已入库的文档进行定期或按需扫描</p>
        </div>
        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-lg font-bold text-gray-900 mb-3">恶意脚本检测</h3>
          <p class="text-sm text-gray-700">基于规则检测潜在的恶意脚本</p>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">📊</div>
        <h2 class="text-3xl font-bold text-gray-900">扫描状态</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">pending</h4>
            <p class="text-sm text-gray-700">待扫描</p>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">scanning</h4>
            <p class="text-sm text-gray-700">扫描中</p>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">safe</h4>
            <p class="text-sm text-gray-700">安全</p>
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 mb-2">infected</h4>
            <p class="text-sm text-gray-700">感染（文件会被拒绝）</p>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/security-issues" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">安全问题 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

