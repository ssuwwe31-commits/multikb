# 前端 Docker 部署说明

## 快速开始

### 1. 构建并启动服务

```bash
# 在项目根目录执行
docker-compose up -d --build
```

### 2. 访问应用

前端服务将在 `http://localhost:3000` 启动

### 3. 停止服务

```bash
docker-compose down
```

## 配置说明

### 后端 API 地址配置

默认后端 API 地址为 `http://192.168.131.158:8081`。

如果需要修改后端地址，有两种方式：

#### 方式一：修改 nginx 配置文件

编辑 `docker/nginx/default.conf`，修改 `proxy_pass` 的值：

```nginx
location /api {
    proxy_pass http://your-backend-url:port;
    # ...
}
```

#### 方式二：使用环境变量（需要重新构建）

在 `docker-compose.yml` 中修改 `BACKEND_API_URL` 环境变量，然后重新构建：

```yaml
environment:
  - BACKEND_API_URL=http://your-backend-url:port
```

### 端口配置

默认前端端口为 `3000`，如需修改，编辑 `docker-compose.yml`：

```yaml
ports:
  - "你的端口:80"
```

## 文件说明

- `Dockerfile`: 多阶段构建文件，先构建前端项目，然后使用 nginx 服务
- `docker-compose.yml`: Docker Compose 配置文件
- `docker/nginx/default.conf`: Nginx 配置文件

## 注意事项

1. **后端地址**：如果后端也在 Docker 网络中，可以使用服务名（如 `http://backend:8000`）；如果在宿主机，使用 `host.docker.internal` 或宿主机 IP
2. **构建缓存**：首次构建会下载依赖，可能需要一些时间
3. **静态资源**：构建后的静态文件会缓存在镜像中，修改代码后需要重新构建镜像

## 开发模式

如果需要开发模式（热重载），可以使用 Vite 的开发服务器：

```bash
npm run dev
```

生产环境部署请使用 Docker Compose。

