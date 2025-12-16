# 前端快速部署脚本 (PowerShell)
# 使用方法: .\deploy.ps1 [-BackendUrl "http://your-backend:8081"]

param(
    [string]$BackendUrl = "http://192.168.131.158:8081"
)

Write-Host "========================================" -ForegroundColor Green
Write-Host "   MultiKB Knowledge Frontend 部署脚本" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# 检查 Docker 是否安装
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "错误: Docker 未安装，请先安装 Docker Desktop" -ForegroundColor Red
    exit 1
}

# 检查 Docker Compose
$dockerComposeCmd = $null
if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    $dockerComposeCmd = "docker-compose"
} elseif (docker compose version 2>$null) {
    $dockerComposeCmd = "docker compose"
} else {
    Write-Host "错误: Docker Compose 未安装" -ForegroundColor Red
    exit 1
}

Write-Host "后端 API 地址: $BackendUrl" -ForegroundColor Yellow

# 更新 nginx 配置中的后端地址
$nginxConfig = "docker\nginx\default.conf"
if (Test-Path $nginxConfig) {
    $content = Get-Content $nginxConfig -Raw
    $content = $content -replace 'proxy_pass http://[^;]+;', "proxy_pass $BackendUrl;"
    Set-Content -Path $nginxConfig -Value $content -NoNewline
    Write-Host "✓ Nginx 配置已更新" -ForegroundColor Green
} else {
    Write-Host "警告: $nginxConfig 不存在，跳过配置更新" -ForegroundColor Yellow
}

# 停止旧容器
Write-Host "停止旧容器..." -ForegroundColor Yellow
& $dockerComposeCmd down 2>$null

# 构建镜像
Write-Host "构建 Docker 镜像..." -ForegroundColor Yellow
& $dockerComposeCmd build --no-cache

if ($LASTEXITCODE -ne 0) {
    Write-Host "构建失败！" -ForegroundColor Red
    exit 1
}

# 启动服务
Write-Host "启动服务..." -ForegroundColor Yellow
& $dockerComposeCmd up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "启动失败！" -ForegroundColor Red
    exit 1
}

# 等待服务启动
Start-Sleep -Seconds 3

# 检查服务状态
$status = & $dockerComposeCmd ps 2>$null
if ($status -match "Up") {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  部署成功！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    
    # 获取本机 IP
    $ipAddress = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*"} | Select-Object -First 1).IPAddress
    if (-not $ipAddress) {
        $ipAddress = "localhost"
    }
    
    Write-Host "前端访问地址: http://${ipAddress}:3000" -ForegroundColor Green
    Write-Host "或: http://localhost:3000" -ForegroundColor Green
    Write-Host ""
    Write-Host "查看日志: $dockerComposeCmd logs -f" -ForegroundColor Yellow
    Write-Host "停止服务: $dockerComposeCmd down" -ForegroundColor Yellow
} else {
    Write-Host "部署失败，请检查日志: $dockerComposeCmd logs" -ForegroundColor Red
    exit 1
}

