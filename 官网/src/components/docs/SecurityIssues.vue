<template>
  <div class="security-issues">
    <!-- Title -->
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
        安全问题
      </h1>
      <p class="text-xl text-gray-600">
        安全相关问题排查和解决方案
      </p>
    </div>

    <!-- Common Security Issues -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center text-white text-xl">
          🛡️
        </div>
        <h2 class="text-3xl font-bold text-gray-900">常见安全问题</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl p-6 border-2 border-red-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">1. 未授权访问</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>症状：</strong>未登录用户可以访问系统资源</p>
            <p class="text-gray-700"><strong>可能原因：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>认证中间件配置错误</li>
              <li>API路由未添加认证要求</li>
              <li>Token验证失败</li>
            </ul>
            <p class="text-gray-700 mt-3"><strong>解决方法：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>检查认证中间件是否正确配置</li>
              <li>确认所有API路由都添加了认证装饰器</li>
              <li>验证Token生成和验证逻辑</li>
              <li>检查CORS配置，限制允许的源</li>
            </ul>
          </div>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-yellow-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">2. 文件上传安全</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>症状：</strong>恶意文件被上传到系统</p>
            <p class="text-gray-700"><strong>可能原因：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>文件类型验证不严格</li>
              <li>文件大小限制未设置</li>
              <li>未启用病毒扫描</li>
            </ul>
            <p class="text-gray-700 mt-3"><strong>解决方法：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li><strong>启用ClamAV扫描</strong>：配置ClamAV病毒扫描服务</li>
              <li>严格限制允许的文件类型</li>
              <li>设置文件大小限制：<code class="bg-gray-200 px-1 rounded">MAX_FILE_SIZE=100MB</code></li>
              <li>检查文件扩展名和MIME类型</li>
              <li>隔离上传的文件，避免直接执行</li>
            </ul>
          </div>
        </div>

        <div class="bg-gradient-to-br from-yellow-50 to-amber-50 rounded-xl p-6 border-2 border-yellow-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">3. SQL注入</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>症状：</strong>恶意SQL语句被执行</p>
            <p class="text-gray-700"><strong>可能原因：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>直接拼接SQL语句</li>
              <li>未使用参数化查询</li>
            </ul>
            <p class="text-gray-700 mt-3"><strong>解决方法：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li><strong>使用ORM</strong>：使用SQLAlchemy ORM，避免直接写SQL</li>
              <li>使用参数化查询，不要拼接字符串</li>
              <li>验证和转义用户输入</li>
              <li>限制数据库用户权限</li>
            </ul>
          </div>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">4. XSS攻击</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>症状：</strong>恶意脚本在浏览器中执行</p>
            <p class="text-gray-700"><strong>可能原因：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>未转义用户输入</li>
              <li>直接渲染HTML内容</li>
            </ul>
            <p class="text-gray-700 mt-3"><strong>解决方法：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>转义所有用户输入</li>
              <li>使用内容安全策略（CSP）</li>
              <li>避免使用<code class="bg-gray-200 px-1 rounded">innerHTML</code>，使用<code class="bg-gray-200 px-1 rounded">textContent</code></li>
              <li>验证和清理用户输入</li>
            </ul>
          </div>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-3">5. 敏感信息泄露</h3>
          <div class="space-y-3">
            <p class="text-gray-700"><strong>症状：</strong>敏感信息（密码、密钥等）被泄露</p>
            <p class="text-gray-700"><strong>可能原因：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>敏感信息硬编码在代码中</li>
              <li>日志中记录敏感信息</li>
              <li>错误信息暴露系统细节</li>
            </ul>
            <p class="text-gray-700 mt-3"><strong>解决方法：</strong></p>
            <ul class="list-disc list-inside space-y-1 text-gray-700 ml-4">
              <li>使用环境变量存储敏感信息</li>
              <li>不要在日志中记录密码、Token等</li>
              <li>生产环境关闭详细错误信息</li>
              <li>使用密钥管理服务（如Vault）</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- Security Best Practices -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">
          ✅
        </div>
        <h2 class="text-3xl font-bold text-gray-900">安全最佳实践</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">1. 认证和授权</h3>
          <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li>使用强密码策略，要求密码复杂度</li>
            <li>实现Token过期和刷新机制</li>
            <li>使用HTTPS传输敏感信息</li>
            <li>实现基于角色的访问控制（RBAC）</li>
            <li>定期审查和更新用户权限</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">2. 数据安全</h3>
          <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li>加密敏感数据（密码、密钥等）</li>
            <li>实现数据备份和恢复机制</li>
            <li>定期更新数据库和依赖包</li>
            <li>限制数据库访问权限</li>
            <li>实现数据脱敏，避免泄露真实数据</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">3. 网络安全</h3>
          <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li>配置防火墙，只开放必要端口</li>
            <li>使用VPN或私有网络访问</li>
            <li>限制CORS允许的源</li>
            <li>使用WAF（Web应用防火墙）</li>
            <li>定期进行安全扫描和渗透测试</li>
          </ul>
        </div>

        <div class="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 border-2 border-orange-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">4. 应用安全</h3>
          <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
            <li><strong>启用ClamAV扫描</strong>：扫描上传的文件</li>
            <li>实现输入验证和输出转义</li>
            <li>使用参数化查询防止SQL注入</li>
            <li>实现速率限制，防止暴力攻击</li>
            <li>定期更新依赖包，修复安全漏洞</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Security Configuration -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xl">
          ⚙️
        </div>
        <h2 class="text-3xl font-bold text-gray-900">安全配置</h2>
      </div>

      <div class="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border-2 border-indigo-100">
        <h3 class="text-xl font-bold text-gray-900 mb-4">ClamAV配置</h3>
        <div class="space-y-3">
          <div>
            <p class="text-sm text-gray-600 mb-2">启用ClamAV扫描：</p>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">CLAMAV_ENABLED=true</code>
          </div>
          <div>
            <p class="text-sm text-gray-600 mb-2">配置ClamAV地址：</p>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">CLAMAV_HOST=localhost<br>CLAMAV_PORT=3310</code>
          </div>
          <div>
            <p class="text-sm text-gray-600 mb-2">强制扫描模式（必须通过扫描才能入库）：</p>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">CLAMAV_FORCE_SCAN=true</code>
          </div>
        </div>
      </div>
    </section>

    <!-- Security Audit -->
    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-gray-500 to-slate-600 flex items-center justify-center text-white text-xl">
          🔍
        </div>
        <h2 class="text-3xl font-bold text-gray-900">安全审计</h2>
      </div>

      <div class="bg-gradient-to-br from-gray-50 to-slate-50 rounded-xl p-6 border-2 border-gray-100">
        <h3 class="text-xl font-bold text-gray-900 mb-4">审计内容</h3>
        <ul class="list-disc list-inside space-y-2 text-gray-700 ml-4">
          <li><strong>操作日志</strong>：记录所有用户操作（上传、删除、修改等）</li>
          <li><strong>访问日志</strong>：记录API访问和认证信息</li>
          <li><strong>安全事件</strong>：记录登录失败、权限拒绝等安全事件</li>
          <li><strong>数据变更</strong>：记录重要数据的变更历史</li>
        </ul>
        <p class="text-gray-700 mt-4">定期审查审计日志，发现异常行为和安全威胁。</p>
      </div>
    </section>

    <!-- Related Resources -->
    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/faq" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          常见问题 →
        </router-link>
        <router-link to="/docs/error-troubleshooting" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
          错误排查 →
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

