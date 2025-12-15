# Nginx 部署指南

## 快速部署步骤

### 1. 构建项目

```bash
cd 官网
npm run build
```

构建完成后，会在 `官网/dist` 目录生成静态文件。

### 2. 配置 Nginx

#### 方式一：使用提供的配置文件（推荐）

1. **Linux/Mac 系统：**

```bash
# 将 dist 目录复制到 nginx 目录
sudo cp -r 官网/dist /usr/share/nginx/html/

# 复制配置文件
sudo cp 官网/nginx.conf /etc/nginx/sites-available/website.conf

# 创建软链接
sudo ln -s /etc/nginx/sites-available/website.conf /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 nginx
sudo systemctl restart nginx
```

2. **Windows 系统：**

```powershell
# 修改 nginx.conf 中的 root 路径，例如：
# root C:/nginx/html/dist;

# 将配置文件复制到 nginx 配置目录（通常在 nginx 安装目录的 conf 文件夹下）
# 或直接在 nginx.conf 主配置文件中包含此配置

# 测试配置
nginx.exe -t

# 重启 nginx（以管理员身份运行）
nginx.exe -s reload
```

#### 方式二：直接修改主配置文件

编辑 `/etc/nginx/nginx.conf`（Linux）或 `nginx.conf`（Windows），在 `http` 块中添加：

```nginx
server {
    listen 80;
    server_name localhost;  # 修改为您的域名
    
    root /usr/share/nginx/html/dist;  # 修改为您的 dist 目录路径
    index index.html;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA 路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 3. 路径说明

- **dist 目录路径：** 将构建生成的 `dist` 目录放到 nginx 可以访问的位置
- **配置文件路径：** nginx 配置文件路径因系统而异
  - Linux: `/etc/nginx/nginx.conf` 或 `/etc/nginx/sites-available/`
  - Windows: `C:\nginx\conf\nginx.conf`
  - Mac (Homebrew): `/usr/local/etc/nginx/nginx.conf`

### 4. 验证部署

访问 `http://localhost` 或您配置的域名，应该能看到网站正常显示。

### 5. 常见问题

#### 问题1：页面刷新后 404

**解决方案：** 确保配置了 `try_files $uri $uri/ /index.html;`，这是 SPA 应用必需的配置。

#### 问题2：静态资源加载失败

**解决方案：** 检查 `root` 路径是否正确，确保指向 `dist` 目录（不是 `dist` 的父目录）。

#### 问题3：中文路径问题

**解决方案：** 在 nginx 配置的 `http` 块中添加：

```nginx
charset utf-8;
```

#### 问题4：HTTPS 配置（可选）

如果需要 HTTPS，可以使用 Let's Encrypt 证书：

```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com
```

然后修改配置添加 SSL：

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # ... 其他配置
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### 6. 性能优化建议

1. **启用 Gzip 压缩**（已在配置中包含）
2. **静态资源缓存**（已在配置中包含）
3. **使用 CDN** 加速静态资源
4. **启用 HTTP/2**（需要 HTTPS）

### 7. 检查命令

```bash
# 检查 nginx 配置语法
nginx -t

# 重新加载配置（不中断服务）
nginx -s reload

# 查看 nginx 状态
systemctl status nginx  # Linux
# 或查看进程
ps aux | grep nginx
```
