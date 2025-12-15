<template>
  <div class="installation-security-config">
    <div class="mb-8">
      <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">安全配置</h1>
      <p class="text-xl text-gray-600">SSL证书、防火墙、访问控制等安全配置</p>
    </div>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl">🔒</div>
        <h2 class="text-3xl font-bold text-gray-900">HTTPS/SSL配置</h2>
      </div>

      <div class="space-y-4">
        <div class="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-6 border-2 border-blue-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">使用Let's Encrypt</h3>
          <div class="space-y-2">
            <p class="text-sm text-gray-700 mb-2">安装Certbot：</p>
            <code class="block bg-gray-900 text-green-400 px-4 py-2 rounded-lg font-mono text-sm">sudo apt-get install certbot python3-certbot-nginx</code>
            <p class="text-sm text-gray-700 mb-2 mt-3">获取证书：</p>
            <code class="block bg-gray-900 text-green-400 px-4 py-2 rounded-lg font-mono text-sm">sudo certbot --nginx -d your-domain.com</code>
          </div>
        </div>

        <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
          <h3 class="text-xl font-bold text-gray-900 mb-4">Nginx SSL配置</h3>
          <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">server {<br>&nbsp;&nbsp;listen 443 ssl http2;<br>&nbsp;&nbsp;server_name your-domain.com;<br><br>&nbsp;&nbsp;ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;<br>&nbsp;&nbsp;ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;<br><br>&nbsp;&nbsp;ssl_protocols TLSv1.2 TLSv1.3;<br>&nbsp;&nbsp;ssl_ciphers HIGH:!aNULL:!MD5;<br>}</code>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center text-white text-xl">🛡️</div>
        <h2 class="text-3xl font-bold text-gray-900">防火墙配置</h2>
      </div>

      <div class="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl p-6 border-2 border-red-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">UFW配置（Ubuntu）</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">sudo ufw allow 22/tcp    # SSH<br>sudo ufw allow 80/tcp    # HTTP<br>sudo ufw allow 443/tcp   # HTTPS<br>sudo ufw enable</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">firewalld配置（CentOS）</h3>
            <code class="block bg-gray-900 text-green-400 px-4 py-3 rounded-lg font-mono text-sm">sudo firewall-cmd --permanent --add-service=ssh<br>sudo firewall-cmd --permanent --add-service=http<br>sudo firewall-cmd --permanent --add-service=https<br>sudo firewall-cmd --reload</code>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-white text-xl">🔐</div>
        <h2 class="text-3xl font-bold text-gray-900">访问控制</h2>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">IP白名单</h3>
            <p class="text-sm text-gray-700 mb-2">在Nginx中配置IP白名单：</p>
            <code class="block bg-gray-900 text-green-400 px-4 py-2 rounded-lg font-mono text-sm">location /admin {<br>&nbsp;&nbsp;allow 192.168.1.0/24;<br>&nbsp;&nbsp;deny all;<br>}</code>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">API限流</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>使用Nginx limit_req模块限制请求频率</li>
              <li>在应用层实现Token限流</li>
              <li>配置Celery任务队列限流</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">认证配置</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>使用JWT Token认证</li>
              <li>配置Token过期时间</li>
              <li>实现刷新Token机制</li>
              <li>启用多因素认证（MFA）</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-16">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xl">🔍</div>
        <h2 class="text-3xl font-bold text-gray-900">安全扫描</h2>
      </div>

      <div class="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl p-6 border-2 border-green-100">
        <div class="space-y-4">
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">ClamAV配置</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>安装和配置ClamAV病毒扫描</li>
              <li>启用实时扫描</li>
              <li>配置强制扫描模式</li>
            </ul>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900 mb-2">依赖扫描</h3>
            <ul class="list-disc list-inside space-y-1 text-sm text-gray-700 ml-4">
              <li>使用safety检查Python依赖漏洞</li>
              <li>使用npm audit检查前端依赖</li>
              <li>定期更新依赖包</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <div class="mt-16 p-6 rounded-xl bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-100">
      <h3 class="text-xl font-bold text-gray-900 mb-4">相关资源</h3>
      <div class="flex flex-wrap gap-3">
        <router-link to="/docs/security-scanning" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">安全扫描 →</router-link>
        <router-link to="/docs/security-hardening" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">安全加固 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
</style>

