# 用户认证系统设计文档

## 1. 概述

### 1.1 设计目标

设计并实现一个基础的用户认证系统，为 SPX Knowledge Base 提供：
- **用户注册与登录**：支持邮箱/用户名注册，JWT Token 认证
- **用户信息管理**：个人资料、头像、偏好设置
- **数据隔离**：用户只能访问和管理自己创建的数据（知识库、文档、监控配置等）
- **安全机制**：密码加密、Token 刷新、登录锁定
- **用户体验**：简单易用的注册登录流程

### 1.2 设计原则

- **安全性优先**：密码加密存储、Token 过期机制、登录失败锁定
- **简单实用**：聚焦核心功能，避免过度设计
- **数据隔离**：用户数据完全隔离，用户只能管理自己的数据
- **向后兼容**：不影响现有功能，支持可选认证模式

### 1.3 技术选型

- **认证方式**：JWT (JSON Web Token)
- **密码加密**：bcrypt（已实现）
- **Token 算法**：HS256（已实现）

---

## 2. 数据模型设计

### 2.1 用户表 (users)

```sql
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '用户ID',
    `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    `email` VARCHAR(100) NOT NULL UNIQUE COMMENT '邮箱',
    `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希',
    `nickname` VARCHAR(100) COMMENT '昵称',
    `avatar_url` VARCHAR(500) COMMENT '头像URL',
    `phone` VARCHAR(20) COMMENT '手机号',
    `status` VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/inactive/locked',
    `email_verified` BOOLEAN DEFAULT FALSE COMMENT '邮箱是否已验证',
    `last_login_at` DATETIME COMMENT '最后登录时间',
    `last_login_ip` VARCHAR(50) COMMENT '最后登录IP',
    `login_count` INT DEFAULT 0 COMMENT '登录次数',
    `failed_login_attempts` INT DEFAULT 0 COMMENT '失败登录次数',
    `locked_until` DATETIME COMMENT '锁定到期时间',
    `preferences` JSON COMMENT '用户偏好设置JSON',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_username` (`username`),
    UNIQUE KEY `uk_user_email` (`email`),
    INDEX `idx_user_status` (`status`),
    INDEX `idx_user_email_verified` (`email_verified`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';
```

### 2.2 Token 刷新表 (refresh_tokens)

```sql
CREATE TABLE IF NOT EXISTS `refresh_tokens` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Token ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `token` VARCHAR(255) NOT NULL UNIQUE COMMENT '刷新Token',
    `expires_at` DATETIME NOT NULL COMMENT '过期时间',
    `device_info` VARCHAR(200) COMMENT '设备信息',
    `ip_address` VARCHAR(50) COMMENT 'IP地址',
    `is_revoked` BOOLEAN DEFAULT FALSE COMMENT '是否已撤销',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_refresh_token` (`token`),
    INDEX `idx_refresh_token_user_id` (`user_id`),
    INDEX `idx_refresh_token_expires` (`expires_at`),
    CONSTRAINT `fk_refresh_token_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='刷新Token表';
```

### 2.3 邮箱验证表 (email_verifications)

```sql
CREATE TABLE IF NOT EXISTS `email_verifications` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '验证ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `email` VARCHAR(100) NOT NULL COMMENT '邮箱',
    `verification_code` VARCHAR(10) NOT NULL COMMENT '验证码',
    `expires_at` DATETIME NOT NULL COMMENT '过期时间',
    `is_used` BOOLEAN DEFAULT FALSE COMMENT '是否已使用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `idx_email_verification_user_id` (`user_id`),
    INDEX `idx_email_verification_code` (`verification_code`),
    CONSTRAINT `fk_email_verification_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='邮箱验证表';
```

---

## 3. 数据模型关系

```
users (用户)
  ├── refresh_tokens (刷新Token)
  └── email_verifications (邮箱验证)
```

---

## 4. API 接口设计

### 4.1 认证相关接口

#### 4.1.1 用户注册

```http
POST /api/v1/auth/register
Content-Type: application/json

Request Body:
{
  "username": "string",      // 必填，3-50字符，字母数字下划线
  "email": "string",          // 必填，有效邮箱格式
  "password": "string",       // 必填，8-50字符，包含字母和数字
  "nickname": "string"        // 可选，昵称
}

Response 201:
{
  "code": 201,
  "message": "注册成功",
  "data": {
    "user_id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "email_verified": false,
    "created_at": "2024-01-01T10:00:00Z"
  }
}
```

#### 4.1.2 用户登录

```http
POST /api/v1/auth/login
Content-Type: application/json

Request Body:
{
  "username": "string",      // 用户名或邮箱
  "password": "string"        // 密码
}

Response 200:
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "refresh_token_string",
    "token_type": "Bearer",
    "expires_in": 1800,       // 30分钟
    "user": {
      "id": 1,
      "username": "testuser",
      "email": "test@example.com",
      "nickname": "测试用户",
      "avatar_url": null
    }
  }
}
```

#### 4.1.3 刷新 Token

```http
POST /api/v1/auth/refresh
Content-Type: application/json

Request Body:
{
  "refresh_token": "string"   // 刷新Token
}

Response 200:
{
  "code": 200,
  "message": "Token刷新成功",
  "data": {
    "access_token": "new_access_token",
    "refresh_token": "new_refresh_token",
    "expires_in": 1800
  }
}
```

#### 4.1.4 用户登出

```http
POST /api/v1/auth/logout
Authorization: Bearer {access_token}

Response 200:
{
  "code": 200,
  "message": "登出成功"
}
```

#### 4.1.5 获取当前用户信息

```http
GET /api/v1/auth/me
Authorization: Bearer {access_token}

Response 200:
{
  "code": 200,
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "nickname": "测试用户",
    "avatar_url": "https://example.com/avatar.jpg",
    "phone": "13800138000",
    "status": "active",
    "email_verified": true,
    "last_login_at": "2024-01-01T10:00:00Z",
    "created_at": "2024-01-01T09:00:00Z"
  }
}
```

### 4.2 用户管理接口

#### 4.2.1 更新用户信息

```http
PUT /api/v1/users/me
Authorization: Bearer {access_token}
Content-Type: application/json

Request Body:
{
  "nickname": "string",       // 可选
  "avatar_url": "string",     // 可选
  "phone": "string",          // 可选
  "preferences": {            // 可选，JSON对象
    "theme": "light",
    "language": "zh-CN"
  }
}

Response 200:
{
  "code": 200,
  "message": "更新成功",
  "data": {
    "id": 1,
    "nickname": "新昵称",
    ...
  }
}
```

#### 4.2.2 修改密码

```http
POST /api/v1/users/me/password
Authorization: Bearer {access_token}
Content-Type: application/json

Request Body:
{
  "old_password": "string",   // 必填，当前密码
  "new_password": "string"      // 必填，新密码（8-50字符）
}

Response 200:
{
  "code": 200,
  "message": "密码修改成功"
}
```

#### 4.2.3 发送邮箱验证码

```http
POST /api/v1/users/me/email/verify
Authorization: Bearer {access_token}
Content-Type: application/json

Request Body:
{
  "email": "string"           // 必填，要验证的邮箱（可以是当前邮箱或新邮箱）
}

Response 200:
{
  "code": 200,
  "message": "验证码已发送",
  "data": {
    "email": "test@example.com",  // 发送验证码的邮箱
    "expires_in": 600              // 验证码有效期（秒）
  }
}
```

#### 4.2.4 验证邮箱

```http
POST /api/v1/users/me/email/confirm
Authorization: Bearer {access_token}
Content-Type: application/json

Request Body:
{
  "email": "string",              // 必填，要验证的邮箱（必须与发送验证码时的邮箱一致）
  "verification_code": "string"  // 必填，6位验证码
}

Response 200:
{
  "code": 200,
  "message": "邮箱验证成功",
  "data": {
    "email": "test@example.com",
    "email_verified": true
  }
}
```

#### 4.2.5 密码重置（忘记密码）

```http
POST /api/v1/auth/password/reset
Content-Type: application/json

Request Body:
{
  "email": "string"           // 必填，注册邮箱
}

Response 200:
{
  "code": 200,
  "message": "重置密码验证码已发送到邮箱"
}

POST /api/v1/auth/password/reset/confirm
Content-Type: application/json

Request Body:
{
  "email": "string",              // 必填，注册邮箱
  "verification_code": "string",  // 必填，验证码
  "new_password": "string"        // 必填，新密码
}

Response 200:
{
  "code": 200,
  "message": "密码重置成功"
}
```


---

## 5. 认证流程设计

### 5.1 注册流程

```
用户提交注册信息
    ↓
验证用户名/邮箱唯一性
    ↓
验证密码强度
    ↓
密码加密（bcrypt）
    ↓
创建用户（status=active, email_verified=false）
    ↓
发送邮箱验证码（可选）
    ↓
返回用户信息
```

### 5.2 登录流程

```
用户提交用户名/密码
    ↓
查询用户（username/email）
    ↓
检查用户是否存在
    ↓
验证用户状态（active/locked）
    - 如果 locked：检查 locked_until 是否过期
    - 如果未过期：返回锁定错误
    - 如果已过期：解除锁定，重置失败次数
    ↓
验证密码（bcrypt）
    ↓
密码验证失败：
    - 增加 failed_login_attempts
    - 如果达到 MAX_LOGIN_ATTEMPTS：设置 locked_until
    - 返回错误
    ↓
密码验证成功：
    - 更新登录信息（last_login_at, last_login_ip, login_count）
    - 重置失败登录次数（failed_login_attempts = 0）
    - 清除锁定状态（locked_until = NULL）
    ↓
生成 JWT Access Token（30分钟）
    ↓
生成 Refresh Token（7天，存入数据库）
    ↓
返回 Token 和用户信息
```

### 5.3 Token 刷新流程

```
客户端提交 Refresh Token
    ↓
验证 Refresh Token（数据库查询）
    ↓
检查是否过期/已撤销
    - 如果过期或已撤销：返回错误
    ↓
验证用户状态（active/locked）
    - 如果用户被锁定或删除：返回错误
    ↓
生成新的 Access Token（30分钟）
    ↓
生成新的 Refresh Token（7天）
    ↓
撤销旧的 Refresh Token（is_revoked = TRUE）
    ↓
保存新的 Refresh Token 到数据库
    ↓
返回新 Token
```

### 5.4 密码重置流程

```
用户提交邮箱
    ↓
查询用户（email）
    ↓
生成验证码（6位数字，10分钟有效）
    ↓
发送验证码到邮箱
    ↓
用户提交验证码和新密码
    ↓
验证验证码（检查邮箱、验证码、过期时间）
    ↓
验证密码强度
    ↓
更新密码（bcrypt加密）
    ↓
撤销该用户的所有 Refresh Token（安全考虑）
    ↓
返回成功
```


---

## 6. 安全机制

### 6.1 密码安全

- **加密算法**：bcrypt，cost factor = 12
- **密码规则**：
  - 长度：8-50 字符
  - 必须包含：字母和数字
  - 可选：特殊字符
- **密码重置**：通过邮箱验证码重置（见 4.2.5 密码重置接口）

### 6.2 Token 安全

- **Access Token**：
  - 有效期：30 分钟
  - 算法：HS256
  - 存储：客户端（内存/安全存储）
- **Refresh Token**：
  - 有效期：7 天
  - 存储：数据库
  - 可撤销：登出时撤销
- **Token 刷新**：自动刷新机制，避免频繁登录
- **Token 清理**：定期清理过期的 Refresh Token（建议通过定时任务，每天清理一次）

### 6.3 登录安全

- **失败锁定**：连续 5 次失败登录，锁定 30 分钟
- **IP 记录**：记录登录 IP，异常登录提醒
- **设备管理**：支持多设备登录（通过 refresh_tokens 表管理）
  - 每个设备生成独立的 Refresh Token
  - 登出时撤销当前设备的 Refresh Token
  - 未来可扩展：查看所有设备、撤销指定设备

### 6.4 操作审计

- **记录内容**：
  - 操作类型（登录、登出、创建、修改、删除）
  - 用户信息（user_id, username）
  - 资源信息（resource_type, resource_id）
  - 请求信息（IP、User-Agent）
  - 时间戳
- **存储**：OperationLog 表（已存在）

---

## 7. 数据隔离机制

### 7.1 数据隔离原则

- **用户数据隔离**：每个用户只能访问和管理自己创建的数据
- **知识库隔离**：用户只能访问自己创建的知识库
- **文档隔离**：用户只能访问自己上传的文档
- **监控配置隔离**：用户只能管理自己创建的集群监控配置

### 7.2 实现方式

- 所有数据表添加 `user_id` 字段，关联到 `users.id`
- API 接口自动过滤，只返回当前用户的数据（WHERE user_id = current_user_id）
- 创建操作时，自动关联当前用户ID（从 JWT Token 中获取）
- 更新/删除操作时，验证数据归属权（确保 user_id = current_user_id）
- 查询操作时，自动添加 user_id 过滤条件

### 7.3 数据关联

需要在以下表中添加 `user_id` 字段：
- `knowledge_bases`：知识库表
- `documents`：文档表（已有 `last_modified_by`，需要添加 `user_id`）
- `cluster_configs`：集群配置表（监控系统）
- `qa_sessions`：问答会话表（已有 `user_id`，需要验证）

---

## 8. 前端集成方案

### 8.1 Token 存储

```typescript
// 使用 localStorage 存储（或 sessionStorage）
localStorage.setItem('access_token', accessToken)
localStorage.setItem('refresh_token', refreshToken)
```

### 8.2 请求拦截器

```typescript
// axios 请求拦截器
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器 - Token 刷新
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // 尝试刷新 Token
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const { data } = await refreshAccessToken(refreshToken)
          localStorage.setItem('access_token', data.access_token)
          // 重试原请求
          return axios.request(error.config)
        } catch {
          // 刷新失败，跳转登录
          router.push('/login')
        }
      }
    }
    return Promise.reject(error)
  }
)
```

### 8.3 路由守卫

```typescript
// Vue Router 守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  
  if (requiresAuth && !token) {
    next('/login')
  } else {
    next()
  }
})
```

### 8.4 用户状态管理（Pinia）

```typescript
// stores/modules/user.ts
export const useUserStore = defineStore('user', {
  state: () => ({
    user: null as User | null,
    token: localStorage.getItem('access_token') || null,
  }),
  
  actions: {
    async login(username: string, password: string) {
      const { data } = await authApi.login({ username, password })
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
    },
    
    async logout() {
      await authApi.logout()
      this.user = null
      this.token = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    },
    
    async fetchUserInfo() {
      const { data } = await authApi.getMe()
      this.user = data
    }
  }
})
```

---

## 9. 数据库迁移脚本

### 9.1 创建用户相关表

```sql
-- 文件：migrations/2025012001_user_authentication_tables.sql

-- 1. 用户表
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '用户ID',
    `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    `email` VARCHAR(100) NOT NULL UNIQUE COMMENT '邮箱',
    `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希',
    `nickname` VARCHAR(100) COMMENT '昵称',
    `avatar_url` VARCHAR(500) COMMENT '头像URL',
    `phone` VARCHAR(20) COMMENT '手机号',
    `status` VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/inactive/locked',
    `email_verified` BOOLEAN DEFAULT FALSE COMMENT '邮箱是否已验证',
    `last_login_at` DATETIME COMMENT '最后登录时间',
    `last_login_ip` VARCHAR(50) COMMENT '最后登录IP',
    `login_count` INT DEFAULT 0 COMMENT '登录次数',
    `failed_login_attempts` INT DEFAULT 0 COMMENT '失败登录次数',
    `locked_until` DATETIME COMMENT '锁定到期时间',
    `preferences` JSON COMMENT '用户偏好设置JSON',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_username` (`username`),
    UNIQUE KEY `uk_user_email` (`email`),
    INDEX `idx_user_status` (`status`),
    INDEX `idx_user_email_verified` (`email_verified`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 2. 刷新Token表
CREATE TABLE IF NOT EXISTS `refresh_tokens` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT 'Token ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `token` VARCHAR(255) NOT NULL UNIQUE COMMENT '刷新Token',
    `expires_at` DATETIME NOT NULL COMMENT '过期时间',
    `device_info` VARCHAR(200) COMMENT '设备信息',
    `ip_address` VARCHAR(50) COMMENT 'IP地址',
    `is_revoked` BOOLEAN DEFAULT FALSE COMMENT '是否已撤销',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_refresh_token` (`token`),
    INDEX `idx_refresh_token_user_id` (`user_id`),
    INDEX `idx_refresh_token_expires` (`expires_at`),
    CONSTRAINT `fk_refresh_token_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='刷新Token表';

-- 3. 邮箱验证表
CREATE TABLE IF NOT EXISTS `email_verifications` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '验证ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `email` VARCHAR(100) NOT NULL COMMENT '邮箱',
    `verification_code` VARCHAR(10) NOT NULL COMMENT '验证码',
    `expires_at` DATETIME NOT NULL COMMENT '过期时间',
    `is_used` BOOLEAN DEFAULT FALSE COMMENT '是否已使用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `idx_email_verification_user_id` (`user_id`),
    INDEX `idx_email_verification_code` (`verification_code`),
    CONSTRAINT `fk_email_verification_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='邮箱验证表';

-- 4. 更新 OperationLog 表，将 user_id 改为外键
-- 先检查外键是否已存在
SET @constraintname = 'fk_operation_log_user';
SET @tablename = 'operation_logs';
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (CONSTRAINT_NAME = @constraintname)
    ) > 0,
    'SELECT 1 AS result',
    CONCAT('ALTER TABLE `', @tablename, '` MODIFY COLUMN `user_id` INT NULL COMMENT ''用户ID'', ADD CONSTRAINT `', @constraintname, '` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 5. 为现有表添加 user_id 字段（数据隔离）
-- 注意：执行前请先检查字段是否已存在，避免重复添加

-- 5.1 知识库表添加 user_id（如果不存在）
-- MySQL 不支持 IF NOT EXISTS，需要使用动态SQL
SET @dbname = DATABASE();
SET @tablename = 'knowledge_bases';
SET @columnname = 'user_id';
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (COLUMN_NAME = @columnname)
    ) > 0,
    'SELECT 1 AS result',
    CONCAT('ALTER TABLE `', @tablename, '` ADD COLUMN `', @columnname, '` INT NULL COMMENT ''用户ID'' AFTER `is_active`;')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加索引（如果不存在）
SET @indexname = 'idx_kb_user_id';
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (INDEX_NAME = @indexname)
    ) > 0,
    'SELECT 1 AS result',
    CONCAT('ALTER TABLE `', @tablename, '` ADD INDEX `', @indexname, '` (`user_id`);')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加外键（如果不存在）
SET @constraintname = 'fk_kb_user';
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (CONSTRAINT_NAME = @constraintname)
    ) > 0,
    'SELECT 1 AS result',
    CONCAT('ALTER TABLE `', @tablename, '` ADD CONSTRAINT `', @constraintname, '` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 5.2 文档表添加 user_id（如果不存在）
SET @tablename = 'documents';
SET @columnname = 'user_id';
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (COLUMN_NAME = @columnname)
    ) > 0,
    'SELECT 1 AS result',
    CONCAT('ALTER TABLE `', @tablename, '` ADD COLUMN `', @columnname, '` INT NULL COMMENT ''用户ID'' AFTER `knowledge_base_id`;')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加索引
SET @indexname = 'idx_doc_user_id';
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (INDEX_NAME = @indexname)
    ) > 0,
    'SELECT 1 AS result',
    CONCAT('ALTER TABLE `', @tablename, '` ADD INDEX `', @indexname, '` (`user_id`);')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加外键
SET @constraintname = 'fk_doc_user';
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (CONSTRAINT_NAME = @constraintname)
    ) > 0,
    'SELECT 1 AS result',
    CONCAT('ALTER TABLE `', @tablename, '` ADD CONSTRAINT `', @constraintname, '` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 5.3 集群配置表添加 user_id（如果表存在且字段不存在）
-- 先检查表是否存在：SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cluster_configs';
-- 再检查字段是否存在：SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cluster_configs' AND COLUMN_NAME = 'user_id';
-- ALTER TABLE `cluster_configs` 
-- ADD COLUMN IF NOT EXISTS `user_id` INT NULL COMMENT '用户ID',
-- ADD INDEX IF NOT EXISTS `idx_cluster_user_id` (`user_id`);
-- ALTER TABLE `cluster_configs`
-- ADD CONSTRAINT `fk_cluster_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

-- 5.4 qa_sessions 表已有 user_id 字段，只需验证外键关系
-- 如果外键不存在，添加外键：
-- ALTER TABLE `qa_sessions`
-- ADD CONSTRAINT `fk_qa_session_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;
```

---

## 10. 实现计划

### 10.1 第一阶段：基础认证（1-2周）

- [ ] 创建用户数据模型（User）
- [ ] 实现用户注册接口
- [ ] 实现用户登录接口
- [ ] 实现 Token 生成和验证
- [ ] 实现用户信息查询接口
- [ ] 前端登录/注册页面

### 10.2 第二阶段：数据隔离（1周）

- [ ] 在知识库表添加 `user_id` 字段
- [ ] 在文档表添加 `user_id` 字段
- [ ] 在集群配置表添加 `user_id` 字段
- [ ] 更新现有接口，添加用户数据过滤
- [ ] 实现数据归属验证中间件

### 10.3 第三阶段：安全增强（1周）

- [ ] 实现 Refresh Token 机制
- [ ] 实现登录失败锁定
- [ ] 实现邮箱验证（可选）
- [ ] 实现密码重置功能
- [ ] 实现操作审计日志
- [ ] 密码修改接口
- [ ] Refresh Token 清理定时任务

### 10.4 第四阶段：用户体验（1周）

- [ ] 用户资料管理接口
- [ ] 头像上传功能
- [ ] 偏好设置
- [ ] 前端用户中心页面

---

## 11. 测试计划

### 11.1 单元测试

- 用户注册（成功/失败场景）
- 用户登录（成功/失败/锁定场景）
- Token 生成和验证
- 密码加密和验证

### 11.2 集成测试

- 完整的注册-登录-使用流程
- Token 刷新流程
- 用户信息更新流程

### 11.3 安全测试

- 密码强度验证
- Token 过期处理
- 登录失败锁定
- SQL 注入防护
- XSS 防护

---

## 12. 配置项

### 12.1 环境变量

```bash
# 认证配置
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 登录安全
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=30

# 密码规则
MIN_PASSWORD_LENGTH=8
MAX_PASSWORD_LENGTH=50
PASSWORD_REQUIRE_UPPERCASE=false
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBER=true
PASSWORD_REQUIRE_SPECIAL=false

# 邮箱验证（可选）
EMAIL_VERIFICATION_ENABLED=true
EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES=10
```

---

## 13. 注意事项

### 13.1 向后兼容与数据迁移

- **可选认证模式**：现有接口支持可选认证（`get_optional_user`），但启用用户系统后，建议所有接口都要求认证
- **数据迁移策略**：
  - 已存在的数据需要迁移：为现有数据分配 `user_id`
  - 方案1：创建一个系统用户（system_user），将所有历史数据关联到该用户
  - 方案2：根据创建者信息（如 last_modified_by）匹配用户
  - 方案3：如果无法匹配，设置为 NULL（需要业务逻辑处理 NULL 情况）
- **新数据规则**：新创建的数据必须关联用户ID，不允许 NULL
- **数据隔离策略**：
  - 已登录用户：只能访问自己的数据（user_id = current_user_id）
  - 未登录用户：无法访问任何数据（返回 401）
  - 历史数据（user_id = NULL）：需要特殊处理，建议迁移到系统用户

### 13.2 性能考虑

- Token 验证使用缓存（Redis）
- 用户信息缓存（减少数据库查询）

### 13.3 扩展性

- 预留多租户字段（organization_id）
- 支持 OAuth 登录（未来扩展）
- 支持 SSO 单点登录（未来扩展）
- 未来可扩展为团队协作（共享知识库、文档）

---

## 14. 参考文档

- [JWT 官方文档](https://jwt.io/)
- [FastAPI 安全文档](https://fastapi.tiangolo.com/tutorial/security/)
- [bcrypt 文档](https://github.com/pyca/bcrypt/)

---

**文档版本**：v1.0  
**创建日期**：2024-01-20  
**最后更新**：2024-01-20

