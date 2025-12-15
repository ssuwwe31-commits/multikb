<template>
  <div class="advanced-security-hardening">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">安全加固</h1>
      <p class="text-xl text-gray-600">安全最佳实践、漏洞防护、合规配置</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center text-white text-xl">🛡️</div>
        <h2 class="text-3xl font-bold text-gray-900">安全最佳实践</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl p-6 border-2 border-red-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">认证和授权</h3>
          <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li>使用强密码策略，要求密码复杂度</li>
            <li>实现Token过期和刷新机制</li>
            <li>使用HTTPS传输敏感信息</li>
            <li>实现多因素认证（MFA）</li>
            <li>定期审查和更新用户权限</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-yellow-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">数据加密</h3>
          <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li>加密存储敏感数据（密码、密钥等）</li>
            <li>使用TLS/SSL加密传输</li>
            <li>数据库连接使用SSL</li>
            <li>定期轮换加密密钥</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-yellow-50 to-amber-50 rounded-xl p-6 border-2 border-yellow-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">输入验证</h3>
          <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li>严格验证所有用户输入</li>
            <li>使用参数化查询防止SQL注入</li>
            <li>转义输出防止XSS攻击</li>
            <li>限制文件上传类型和大小</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">🔒</div>
        <h2 class="text-3xl font-bold text-gray-900">漏洞防护</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">依赖更新</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>定期更新依赖包，修复安全漏洞</li>
              <li>使用安全扫描工具检查依赖</li>
              <li>关注安全公告和CVE报告</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">安全扫描</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>启用ClamAV病毒扫描</li>
              <li>定期进行安全审计</li>
              <li>使用WAF防护Web攻击</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">访问控制</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>实现最小权限原则</li>
              <li>限制API访问频率</li>
              <li>使用IP白名单</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xl">📋</div>
        <h2 class="text-3xl font-bold text-gray-900">合规配置</h2>
      </div>

      <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">数据保护</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>符合GDPR数据保护要求</li>
              <li>实现数据脱敏</li>
              <li>数据备份和恢复机制</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">审计日志</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>记录所有关键操作</li>
              <li>保留审计日志</li>
              <li>定期审查日志</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/security-issues" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">安全问题 →</router-link>
        <router-link to="/docs/security-scanning" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">安全扫描 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

