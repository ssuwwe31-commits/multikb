# 前端快速部署指南

## 方式一：使用部署脚本（推荐）

### 1. 上传代码到服务器

```bash
# 方式1: 使用 git
git clone <你的仓库地址> multikb-knowledge-frontend
cd multikb-knowledge-frontend/multikb-knowledge-frontend

# 方式2: 使用 scp 上传
scp -r multikb-knowledge-frontend user@server:/path/to/
```

### 2. 执行部署脚本

```bash
# 进入前端目录
cd multikb-knowledge-frontend

# 给脚本执行权限
chmod +x deploy.sh

# 执行部署（默认后端地址）
./deploy.sh

# 或指定后端地址
./deploy.sh http://your-backend-server:8081
```

## 方式二：手动部署

### 1. 准备服务器环境

```bash
# 安装 Docker（如果未安装）
curl -fsSL https://get.docker.com | bash

# 安装 Docker Compose（如果未安装）
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 上传代码

```bash
# 使用 git clone 或 scp 上传代码到服务器
cd /path/to/multikb-knowledge-frontend
```

### 3. 配置后端地址

编辑 `docker/nginx/default.conf`，修改后端 API 地址：

```nginx
location /api {
    proxy_pass http://your-backend-server:8081;  # 修改这里
    # ...
}
```

### 4. 构建并启动

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看状态
docker-compose ps
```

## 方式三：使用 Docker 镜像（生产环境推荐）

### 1. 构建并推送镜像到镜像仓库

```bash
# 构建镜像
docker build -t your-registry/multikb-knowledge-frontend:latest .

# 推送到镜像仓库
docker push your-registry/multikb-knowledge-frontend:latest
```

### 2. 在服务器上拉取并运行

```bash
# 拉取镜像
docker pull your-registry/multikb-knowledge-frontend:latest

# 运行容器
docker run -d \
  --name multikb-frontend \
  -p 3000:80 \
  -v $(pwd)/docker/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro \
  your-registry/multikb-knowledge-frontend:latest
```

## 配置说明

### 修改端口

编辑 `docker-compose.yml`：

```yaml
ports:
  - "你的端口:80"  # 例如 "80:80" 或 "8080:80"
```

### 修改后端地址

方式1: 修改 `docker/nginx/default.conf` 中的 `proxy_pass`

方式2: 使用环境变量（需要修改 nginx 配置支持环境变量）

### 生产环境建议

1. **使用域名和 HTTPS**：
   - 配置 Nginx SSL 证书
   - 使用 Let's Encrypt 免费证书

2. **防火墙配置**：
   ```bash
   # 开放端口
   sudo ufw allow 3000/tcp
   ```

3. **设置自动重启**：
   ```yaml
   restart: always  # docker-compose.yml 中已配置
   ```

4. **日志管理**：
   ```bash
   # 查看日志
   docker-compose logs -f --tail=100
   
   # 限制日志大小（在 docker-compose.yml 中添加）
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

## 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f

# 查看状态
docker-compose ps

# 重新构建
docker-compose build --no-cache
docker-compose up -d

# 进入容器
docker-compose exec frontend sh
```

## 故障排查

### 1. 端口被占用

```bash
# 检查端口占用
netstat -tulpn | grep 3000
# 或
lsof -i :3000

# 修改 docker-compose.yml 中的端口
```

### 2. 无法访问后端 API

- 检查后端服务是否运行
- 检查防火墙规则
- 检查 nginx 配置中的后端地址是否正确
- 查看容器日志：`docker-compose logs frontend`

### 3. 构建失败

- 检查网络连接（需要拉取 Docker 镜像）
- 检查 Docker 磁盘空间：`docker system df`
- 清理未使用的镜像：`docker system prune -a`

## 快速部署检查清单

- [ ] 服务器已安装 Docker 和 Docker Compose
- [ ] 代码已上传到服务器
- [ ] 已修改后端 API 地址配置
- [ ] 已开放服务器端口（3000 或自定义端口）
- [ ] 防火墙规则已配置
- [ ] 服务已启动并运行正常

