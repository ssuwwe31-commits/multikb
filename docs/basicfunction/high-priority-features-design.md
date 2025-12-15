# 高优先级功能详细设计方案

## 目录

1. [搜索体验增强](#1-搜索体验增强)
2. [文档预览优化](#2-文档预览优化)
3. [批量操作](#3-批量操作)
4. [数据统计与分析](#4-数据统计与分析)
5. [导出与备份](#5-导出与备份)

---

## 1. 搜索体验增强

### 1.1 功能概述

增强搜索功能的用户体验，包括搜索历史记录、自动补全、结果高亮、高级筛选和搜索统计。

### 1.2 数据库设计

#### 1.2.1 搜索历史表（search_history）

```sql
CREATE TABLE search_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '用户ID',
    query_text VARCHAR(500) NOT NULL COMMENT '搜索关键词',
    search_type VARCHAR(50) COMMENT '搜索类型：vector/keyword/hybrid/exact',
    knowledge_base_id INT COMMENT '知识库ID（可选）',
    result_count INT DEFAULT 0 COMMENT '结果数量',
    search_time_ms INT COMMENT '搜索耗时（毫秒）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '搜索时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX idx_user_created (user_id, created_at DESC),
    INDEX idx_query (query_text(100)),
    INDEX idx_is_deleted (is_deleted),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='搜索历史记录表';
```

**注意**：虽然 SQLAlchemy 模型会继承 `BaseModel` 的 `created_at`、`updated_at`、`is_deleted` 字段，但 SQL 创建语句需要显式定义这些字段以保持一致性。

#### 1.2.2 搜索热词表（search_hotwords）

```sql
CREATE TABLE search_hotwords (
    id INT PRIMARY KEY AUTO_INCREMENT,
    keyword VARCHAR(200) NOT NULL COMMENT '关键词',
    search_count INT DEFAULT 1 COMMENT '搜索次数',
    last_searched_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '最后搜索时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '首次搜索时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    UNIQUE KEY uk_keyword (keyword),
    INDEX idx_count (search_count DESC),
    INDEX idx_last_searched (last_searched_at DESC),
    INDEX idx_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='搜索热词统计表';
```

#### 1.2.3 搜索建议缓存（使用 Redis）

- Key 格式：`search:suggest:{query_prefix}`
- Value：JSON 数组，包含建议关键词
- TTL：1 小时

### 1.3 后端 API 设计

#### 1.3.1 搜索历史相关接口

**获取搜索历史**
```
GET /api/v1/search/history
Query Parameters:
  - limit: int = 20 (返回数量)
  - offset: int = 0 (偏移量)
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "id": 1,
        "query_text": "Python",
        "search_type": "hybrid",
        "knowledge_base_id": 1,
        "result_count": 15,
        "search_time_ms": 234,
        "created_at": "2025-01-23T10:00:00Z"
      }
    ],
    "total": 50
  }
}
```

**注意**：
- 接口路径与现有 `/api/v1/search/history` 一致（已存在，见 `app/api/v1/routes/search.py:136`）
- 需要扩展现有接口以支持分页和用户过滤
- 响应格式与现有系统保持一致（`code: 0` 表示成功）

**保存搜索历史**（自动保存，无需单独接口）
- 在搜索接口中自动记录

**删除搜索历史**
```
DELETE /api/v1/search/history/{history_id}
Response:
{
  "code": 0,
  "message": "删除成功"
}
```

**清空搜索历史**
```
DELETE /api/v1/search/history
Response:
{
  "code": 0,
  "message": "清空成功"
}
```

#### 1.3.2 搜索建议/自动补全接口

**获取搜索建议**
```
GET /api/v1/search/suggestions
Query Parameters:
  - query: string (必需，输入的关键词前缀)
  - limit: int = 5 (建议数量)
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "suggestions": [
      {
        "text": "Python 教程",
        "type": "history",  // history/hotword/document
        "count": 5
      },
      {
        "text": "Python 基础",
        "type": "hotword",
        "count": 120
      }
    ]
  }
}
```

**注意**：
- 接口路径已存在（见 `app/api/v1/routes/search.py:115`）
- 需要扩展现有实现以支持多数据源（历史、热词、文档）
- 现有响应格式为 `SearchSuggestionResponse`，需要扩展以包含 `type` 和 `count` 字段

**实现逻辑**：
1. 优先从用户搜索历史中匹配
2. 其次从搜索热词表中匹配
3. 最后从文档标题/内容中提取关键词匹配
4. 结果去重并按相关性排序

#### 1.3.3 搜索结果高亮

**修改现有搜索接口响应**，添加高亮字段：

```python
{
  "id": 1,
  "content": "这是原始内容...",
  "highlighted_content": "这是<mark>Python</mark>教程内容...",  // 新增
  "highlighted_title": "<mark>Python</mark>基础教程",  // 新增
  "score": 0.95,
  ...
}
```

**实现方式**：
- 后端使用 OpenSearch 的 highlight 功能
- 或在前端使用正则表达式高亮关键词

#### 1.3.4 高级筛选接口

**扩展搜索请求参数**：

**注意**：`SearchRequest` 已经包含 `filters` 字段（见 `app/schemas/search.py`），无需新增字段。只需扩展 `filters` 的支持范围：

```python
# SearchRequest 已存在 filters 字段
# filters 结构支持：
{
    "date_range": {"start": "2025-01-01", "end": "2025-01-31"},
    "file_types": ["pdf", "docx"],
    "tags": ["Python", "教程"],
    "status": ["processed"],
    "min_score": 0.5,
    "category_id": 1,  # 分类筛选
    "knowledge_base_id": 1  # 知识库筛选（如果未在顶层指定）
}
```

**实现**：在 `SearchService` 中解析 `filters` 参数，应用到 OpenSearch 查询和数据库过滤。

#### 1.3.5 搜索统计接口

**获取搜索统计信息**
```
GET /api/v1/search/statistics
Query Parameters:
  - start_date: string (可选，开始日期)
  - end_date: string (可选，结束日期)
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "total_searches": 150,
    "avg_search_time_ms": 234,
    "top_keywords": [
      {"keyword": "Python", "count": 45},
      {"keyword": "教程", "count": 32}
    ],
    "search_type_distribution": {
      "hybrid": 80,
      "vector": 40,
      "keyword": 30
    },
    "daily_statistics": [
      {"date": "2025-01-23", "count": 25}
    ]
  }
}
```

### 1.4 前端设计

#### 1.4.1 搜索框增强

**组件位置**：`src/components/search/SearchInput.vue`

**功能**：
1. **自动补全下拉框**
   - 输入时实时请求建议接口
   - 防抖处理（300ms）
   - 显示建议列表，支持键盘导航
   - 点击或回车选择建议

2. **搜索历史下拉框**
   - 点击搜索框时显示最近 10 条历史
   - 支持点击历史记录快速搜索
   - 支持删除单条历史

3. **搜索统计显示**
   - 搜索后显示结果数量和耗时
   - 显示相关度分布（如果有）

#### 1.4.2 搜索结果高亮

**实现方式**：
```vue
<template>
  <div v-html="highlightText(content, query)"></div>
</template>

<script setup>
function highlightText(text: string, query: string): string {
  if (!query) return text
  const regex = new RegExp(`(${escapeRegex(query)})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}
</script>

<style>
mark {
  background-color: #ffeb3b;
  padding: 2px 4px;
  border-radius: 2px;
}
</style>
```

#### 1.4.3 高级筛选面板

**组件位置**：`src/components/search/AdvancedFilters.vue`

**筛选选项**：
- 日期范围选择器
- 文件类型多选
- 标签多选
- 知识库选择
- 状态筛选
- 相似度阈值滑块

#### 1.4.4 搜索历史侧边栏

**组件位置**：`src/components/search/SearchHistory.vue`

**功能**：
- 显示搜索历史列表
- 支持按时间排序
- 支持删除单条或清空全部
- 点击历史记录快速搜索

### 1.5 实施步骤

1. **第一阶段（3天）**：搜索历史
   - 创建数据库表
   - 实现搜索历史记录和查询接口
   - 前端显示搜索历史

2. **第二阶段（2天）**：搜索建议
   - 实现搜索建议接口
   - 前端自动补全功能
   - Redis 缓存优化

3. **第三阶段（2天）**：结果高亮和筛选
   - 后端高亮功能
   - 前端高亮显示
   - 高级筛选面板

4. **第四阶段（1天）**：搜索统计
   - 统计接口实现
   - 前端统计展示

---

## 2. 文档预览优化

### 2.1 功能概述

支持在线预览 PDF、Word、Excel 等格式文档，提供目录导航、全文搜索和阅读模式。

### 2.2 数据库设计

#### 2.2.1 文档目录表（document_toc）

```sql
CREATE TABLE document_toc (
    id INT PRIMARY KEY AUTO_INCREMENT,
    document_id INT NOT NULL COMMENT '文档ID',
    level INT NOT NULL COMMENT '目录级别（1-6）',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    page_number INT COMMENT '页码',
    position INT COMMENT '位置（用于排序）',
    parent_id INT COMMENT '父级目录ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX idx_document (document_id),
    INDEX idx_parent (parent_id),
    INDEX idx_is_deleted (is_deleted),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文档目录表';
```

### 2.3 后端 API 设计

#### 2.3.1 文档预览接口

**获取文档预览 URL**
```
GET /api/v1/documents/{document_id}/preview
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "preview_url": "/api/v1/documents/1/preview/file?token=xxx",
    "file_type": "pdf",
    "page_count": 25,
    "supports_preview": true
  }
}
```

**文档预览文件代理**
```
GET /api/v1/documents/{document_id}/preview/file
Query Parameters:
  - page: int (可选，PDF页码)
  - token: string (认证token，或使用 Authorization header)
Response:
  - 返回文件流（PDF/图片）
  - Content-Type: application/pdf 或 image/*
```

**注意**：
- 路径使用 `/api/v1/` 前缀以保持一致性
- 认证方式与图片代理接口一致（支持 query 参数或 header）
- 文档ID通过路径参数传递，更符合 RESTful 规范

**实现方式**：
- PDF：使用 `pdf.js` 或直接返回 PDF 文件流
- Word/Excel：转换为 PDF 后预览（使用 `libreoffice` 或 `pandoc`）
- 图片：直接返回

#### 2.3.2 文档目录接口

**获取文档目录**
```
GET /api/v1/documents/{document_id}/toc
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "toc": [
      {
        "id": 1,
        "level": 1,
        "title": "第一章",
        "page_number": 1,
        "children": [
          {
            "id": 2,
            "level": 2,
            "title": "1.1 小节",
            "page_number": 3
          }
        ]
      }
    ]
  }
}
```

**提取目录逻辑**：
- PDF：解析 PDF 书签
- Word：解析标题样式
- 存储到 `document_toc` 表

#### 2.3.3 文档内搜索接口

**在文档内搜索关键词**
```
GET /api/v1/documents/{document_id}/search
Query Parameters:
  - query: string (搜索关键词)
  - page: int (可选，指定页码)
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "results": [
      {
        "page": 5,
        "position": 120,
        "context": "...关键词上下文...",
        "highlight": "...<mark>关键词</mark>..."
      }
    ],
    "total": 10
  }
}
```

### 2.4 前端设计

#### 2.4.1 文档预览组件

**组件位置**：`src/components/document/DocumentPreview.vue`

**功能**：
1. **PDF 预览**
   - 使用 `pdf.js` 或 `vue-pdf` 组件
   - 支持翻页、缩放、全屏
   - 支持打印

2. **Word/Excel 预览**
   - 转换为 PDF 后预览
   - 或使用在线预览服务（如 Office Online）

3. **图片预览**
   - 使用图片查看器组件
   - 支持缩放、旋转

#### 2.4.2 目录导航组件

**组件位置**：`src/components/document/DocumentTOC.vue`

**功能**：
- 显示文档目录树
- 点击目录项跳转到对应位置
- 支持折叠/展开
- 高亮当前阅读位置

#### 2.4.3 文档内搜索组件

**组件位置**：`src/components/document/DocumentSearch.vue`

**功能**：
- 搜索框输入关键词
- 显示搜索结果列表
- 点击结果跳转到对应位置
- 高亮所有匹配项

#### 2.4.4 阅读模式组件

**组件位置**：`src/components/document/ReadingMode.vue`

**功能**：
- 字体大小调整
- 行距调整
- 主题切换（亮色/暗色）
- 阅读进度保存

### 2.5 实施步骤

1. **第一阶段（3天）**：PDF 预览
   - 实现 PDF 预览接口
   - 前端集成 PDF 查看器
   - 基础翻页和缩放功能

2. **第二阶段（2天）**：目录导航
   - 提取文档目录
   - 前端目录组件
   - 目录跳转功能

3. **第三阶段（2天）**：文档内搜索
   - 实现搜索接口
   - 前端搜索组件
   - 结果高亮和跳转

4. **第四阶段（1天）**：阅读模式
   - 阅读设置组件
   - 设置持久化

---

## 3. 批量操作

### 3.1 功能概述

支持批量上传、删除、移动文档和批量标签管理。

### 3.2 数据库设计

#### 3.2.1 批量操作任务表（batch_operations）

```sql
CREATE TABLE batch_operations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '用户ID',
    operation_type VARCHAR(50) NOT NULL COMMENT '操作类型：upload/delete/move/tag',
    status VARCHAR(50) DEFAULT 'pending' COMMENT '状态：pending/processing/completed/failed',
    total_count INT DEFAULT 0 COMMENT '总数量',
    success_count INT DEFAULT 0 COMMENT '成功数量',
    failed_count INT DEFAULT 0 COMMENT '失败数量',
    error_message TEXT COMMENT '错误信息',
    metadata JSON COMMENT '操作元数据',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX idx_user_status (user_id, status),
    INDEX idx_is_deleted (is_deleted),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='批量操作任务表';
```

### 3.3 后端 API 设计

#### 3.3.1 批量上传接口

**批量上传文档**
```
POST /api/v1/documents/batch/upload
Content-Type: multipart/form-data
Form Data:
  - files: File[] (多个文件)
  - knowledge_base_id: int (知识库ID)
  - category_id: int (可选，分类ID)
  - tags: string (可选，JSON 数组)
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "batch_upload_123",
    "total_count": 5,
    "uploaded_count": 5,
    "documents": [
      {
        "document_id": 1,
        "filename": "doc1.pdf",
        "status": "success"
      }
    ],
    "failed": []
  }
}
```

**实现逻辑**：
1. 接收多个文件
2. 逐个验证和上传
3. 返回上传结果
4. 异步处理文档（Celery 任务）

#### 3.3.2 批量删除接口

**批量删除文档**
```
POST /api/v1/documents/batch/delete
Request Body:
{
  "document_ids": [1, 2, 3]
}
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "deleted_count": 3,
    "failed_count": 0,
    "failed_ids": []
  }
}
```

**实现逻辑**：
1. 验证用户权限（数据隔离）
2. 批量删除文档记录
3. 异步删除 MinIO 文件
4. 异步删除 OpenSearch 索引

#### 3.3.3 批量移动接口

**批量移动文档**
```
POST /api/v1/documents/batch/move
Request Body:
{
  "document_ids": [1, 2, 3],
  "target_knowledge_base_id": 5,
  "target_category_id": 10  // 可选
}
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "moved_count": 3,
    "failed_count": 0,
    "failed_ids": []
  }
}
```

#### 3.3.4 批量标签接口

**批量添加标签**
```
POST /api/v1/documents/batch/tags/add
Request Body:
{
  "document_ids": [1, 2, 3],
  "tags": ["Python", "教程"]
}
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "updated_count": 3
  }
}
```

**批量删除标签**
```
POST /api/v1/documents/batch/tags/remove
Request Body:
{
  "document_ids": [1, 2, 3],
  "tags": ["Python"]
}
```

**批量替换标签**
```
POST /api/v1/documents/batch/tags/replace
Request Body:
{
  "document_ids": [1, 2, 3],
  "tags": ["新标签1", "新标签2"]
}
```

### 3.4 前端设计

#### 3.4.1 批量选择组件

**组件位置**：`src/components/common/BatchSelector.vue`

**功能**：
- 全选/取消全选
- 已选择数量显示
- 批量操作按钮组

#### 3.4.2 批量上传组件

**组件位置**：`src/components/document/BatchUpload.vue`

**功能**：
1. **拖拽上传区域**
   - 支持拖拽多个文件
   - 显示上传文件列表
   - 显示上传进度

2. **上传配置**
   - 选择知识库
   - 选择分类
   - 添加标签

3. **上传结果**
   - 显示成功/失败数量
   - 显示失败原因
   - 支持重试失败项

#### 3.4.3 批量操作工具栏

**组件位置**：`src/components/document/BatchActions.vue`

**功能**：
- 显示已选择数量
- 批量删除按钮
- 批量移动按钮
- 批量标签按钮
- 取消选择按钮

### 3.5 实施步骤

1. **第一阶段（2天）**：批量上传
   - 后端批量上传接口
   - 前端拖拽上传组件
   - 上传进度显示

2. **第二阶段（1天）**：批量删除
   - 后端批量删除接口
   - 前端批量选择组件
   - 确认对话框

3. **第三阶段（1天）**：批量移动和标签
   - 后端批量移动接口
   - 后端批量标签接口
   - 前端操作界面

---

## 4. 数据统计与分析

### 4.1 功能概述

提供个人数据统计和数据可视化，包括知识库统计、文档统计、使用统计和存储统计。

### 4.2 数据库设计

#### 4.2.1 用户统计表（user_statistics）

```sql
CREATE TABLE user_statistics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '用户ID',
    stat_date DATE NOT NULL COMMENT '统计日期',
    stat_type VARCHAR(50) NOT NULL COMMENT '统计类型：daily/weekly/monthly',
    
    -- 知识库统计
    knowledge_base_count INT DEFAULT 0 COMMENT '知识库数量',
    document_count INT DEFAULT 0 COMMENT '文档数量',
    total_file_size BIGINT DEFAULT 0 COMMENT '总文件大小（字节）',
    
    -- 使用统计
    search_count INT DEFAULT 0 COMMENT '搜索次数',
    qa_count INT DEFAULT 0 COMMENT '问答次数',
    upload_count INT DEFAULT 0 COMMENT '上传次数',
    
    -- 存储统计
    storage_used BIGINT DEFAULT 0 COMMENT '已用存储（字节）',
    storage_limit BIGINT DEFAULT 0 COMMENT '存储限制（字节）',
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    UNIQUE KEY uk_user_date_type (user_id, stat_date, stat_type),
    INDEX idx_user_date (user_id, stat_date DESC),
    INDEX idx_is_deleted (is_deleted),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户统计表';
```

#### 4.2.2 文档类型统计表（document_type_statistics）

```sql
CREATE TABLE document_type_statistics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '用户ID',
    file_type VARCHAR(50) NOT NULL COMMENT '文件类型',
    count INT DEFAULT 0 COMMENT '数量',
    total_size BIGINT DEFAULT 0 COMMENT '总大小',
    stat_date DATE NOT NULL COMMENT '统计日期',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX idx_user_date (user_id, stat_date DESC),
    INDEX idx_is_deleted (is_deleted),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文档类型统计表';
```

### 4.3 后端 API 设计

#### 4.3.1 个人数据统计接口

**获取个人数据统计**
```
GET /api/v1/statistics/personal
Query Parameters:
  - period: string = "all" (all/week/month/year)
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "knowledge_bases": {
      "total": 10,
      "active": 8,
      "total_documents": 150
    },
    "documents": {
      "total": 150,
      "by_type": {
        "pdf": 80,
        "docx": 50,
        "txt": 20
      },
      "by_status": {
        "processed": 140,
        "processing": 5,
        "failed": 5
      },
      "total_size": 1024000000  // 字节
    },
    "usage": {
      "total_searches": 500,
      "total_qa_sessions": 50,
      "total_uploads": 150,
      "last_active_date": "2025-01-23"
    },
    "storage": {
      "used": 1024000000,
      "limit": 10737418240,  // 10GB
      "percentage": 9.5
    }
  }
}
```

#### 4.3.2 趋势分析接口

**获取数据趋势**
```
GET /api/v1/statistics/trends
Query Parameters:
  - metric: string (document_count/search_count/upload_count)
  - period: string = "month" (week/month/year)
  - start_date: string (可选)
  - end_date: string (可选)
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "metric": "document_count",
    "period": "month",
    "data": [
      {"date": "2025-01-01", "value": 100},
      {"date": "2025-01-02", "value": 105},
      ...
    ],
    "trend": "increasing",  // increasing/decreasing/stable
    "growth_rate": 5.0  // 增长率（百分比）
  }
}
```

#### 4.3.3 知识库热力图接口

**获取知识库使用热力图**
```
GET /api/v1/statistics/knowledge-bases/heatmap
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "heatmap": [
      {
        "knowledge_base_id": 1,
        "name": "Python教程",
        "usage_count": 150,
        "document_count": 50,
        "last_used": "2025-01-23T10:00:00"
      }
    ]
  }
}
```

#### 4.3.4 搜索热词接口

**获取搜索热词**
```
GET /api/v1/statistics/search/hotwords
Query Parameters:
  - limit: int = 20
  - period: string = "week" (day/week/month)
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "hotwords": [
      {"keyword": "Python", "count": 45, "trend": "up"},
      {"keyword": "教程", "count": 32, "trend": "stable"}
    ]
  }
}
```

### 4.4 前端设计

#### 4.4.1 数据统计仪表盘

**组件位置**：`src/views/Statistics/index.vue`

**功能**：
1. **概览卡片**
   - 知识库数量
   - 文档总数
   - 总存储大小
   - 使用统计

2. **图表展示**
   - 文档增长趋势（折线图）
   - 文档类型分布（饼图）
   - 知识库使用热力图
   - 搜索热词云图

3. **数据表格**
   - 详细统计数据
   - 支持导出

#### 4.4.2 统计图表组件

**使用库**：`echarts` 或 `chart.js`

**组件位置**：`src/components/statistics/StatChart.vue`

**图表类型**：
- 折线图：趋势分析
- 柱状图：对比分析
- 饼图：分布分析
- 热力图：使用频率

### 4.5 定时任务设计

**Celery 定时任务**：每天凌晨统计前一天数据

```python
@celery_app.task
def calculate_daily_statistics():
    """计算每日统计数据"""
    # 1. 统计每个用户的数据
    # 2. 更新 user_statistics 表
    # 3. 更新 document_type_statistics 表
    pass
```

### 4.6 实施步骤

1. **第一阶段（2天）**：基础统计
   - 创建统计表
   - 实现统计接口
   - 前端概览卡片

2. **第二阶段（2天）**：趋势分析
   - 趋势数据接口
   - 前端图表组件
   - 数据可视化

3. **第三阶段（1天）**：热力图和热词
   - 热力图接口
   - 搜索热词接口
   - 前端展示

4. **第四阶段（1天）**：定时任务
   - Celery 定时任务
   - 数据聚合逻辑

---

## 5. 导出与备份

### 5.1 功能概述

支持导出知识库、文档和问答记录，支持多种格式（Markdown、PDF、JSON）。

### 5.2 数据库设计

#### 5.2.1 导出任务表（export_tasks）

```sql
CREATE TABLE export_tasks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL COMMENT '用户ID',
    export_type VARCHAR(50) NOT NULL COMMENT '导出类型：knowledge_base/document/qa_history',
    target_id INT COMMENT '目标ID（知识库ID/文档ID）',
    export_format VARCHAR(50) NOT NULL COMMENT '导出格式：markdown/pdf/json',
    status VARCHAR(50) DEFAULT 'pending' COMMENT '状态：pending/processing/completed/failed',
    file_path VARCHAR(500) COMMENT '导出文件路径',
    file_size BIGINT COMMENT '文件大小',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    completed_at DATETIME COMMENT '完成时间',
    is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX idx_user_status (user_id, status),
    INDEX idx_is_deleted (is_deleted),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='导出任务表';
```

### 5.3 后端 API 设计

#### 5.3.1 知识库导出接口

**导出知识库**
```
POST /api/v1/knowledge-bases/{kb_id}/export
Request Body:
{
  "format": "markdown",  // markdown/pdf/json
  "include_documents": true,  // 是否包含文档内容
  "include_chunks": false  // 是否包含文档块
}
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "export_123",
    "status": "processing",
    "estimated_time": 30  // 预计耗时（秒）
  }
}
```

**下载导出文件**
```
GET /api/v1/exports/{task_id}/download
Response:
  - 文件流（Content-Type: application/octet-stream）
  - 或重定向到 MinIO 下载链接
```

**查询导出任务状态**
```
GET /api/v1/exports/{task_id}
Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "export_123",
    "status": "completed",
    "file_path": "/exports/kb_1_20250123.md",
    "file_size": 1024000,
    "download_url": "/api/v1/exports/export_123/download"
  }
}
```

#### 5.3.2 文档导出接口

**导出单个文档**
```
POST /api/v1/documents/{doc_id}/export
Request Body:
{
  "format": "markdown",  // markdown/pdf/json
  "include_chunks": true,
  "include_images": false
}
```

**批量导出文档**
```
POST /api/v1/documents/batch/export
Request Body:
{
  "document_ids": [1, 2, 3],
  "format": "markdown"
}
```

#### 5.3.3 问答记录导出接口

**导出问答历史**
```
POST /api/v1/qa/history/export
Request Body:
{
  "format": "json",  // json/csv/markdown
  "session_id": 1,  // 可选，指定会话
  "start_date": "2025-01-01",  // 可选
  "end_date": "2025-01-31"  // 可选
}
```

### 5.4 导出格式设计

#### 5.4.1 Markdown 格式

```markdown
# 知识库名称

## 文档1

### 文档标题

文档内容...

### 文档块1

块内容...

---

## 文档2

...
```

#### 5.4.2 PDF 格式

- 使用 `reportlab` 或 `weasyprint` 生成 PDF
- 包含目录、页码
- 支持图片嵌入

#### 5.4.3 JSON 格式

```json
{
  "knowledge_base": {
    "id": 1,
    "name": "Python教程",
    "description": "..."
  },
  "documents": [
    {
      "id": 1,
      "title": "文档1",
      "content": "...",
      "chunks": [...]
    }
  ]
}
```

### 5.5 前端设计

#### 5.5.1 导出对话框组件

**组件位置**：`src/components/export/ExportDialog.vue`

**功能**：
- 选择导出格式
- 选择导出选项
- 显示导出进度
- 下载导出文件

#### 5.5.2 导出任务列表

**组件位置**：`src/components/export/ExportTasks.vue`

**功能**：
- 显示导出任务列表
- 显示任务状态
- 支持下载已完成的任务
- 支持取消进行中的任务

### 5.6 Celery 任务设计

```python
@celery_app.task
def export_knowledge_base_task(task_id: int, kb_id: int, format: str):
    """导出知识库任务"""
    # 1. 更新任务状态为 processing
    # 2. 查询知识库和文档数据
    # 3. 根据格式生成文件
    # 4. 保存到 MinIO
    # 5. 更新任务状态为 completed
    pass
```

### 5.7 实施步骤

1. **第一阶段（2天）**：知识库导出
   - 创建导出任务表
   - 实现 Markdown 导出
   - 前端导出对话框

2. **第二阶段（2天）**：文档导出
   - 单个文档导出
   - 批量文档导出
   - PDF 格式支持

3. **第三阶段（1天）**：问答记录导出
   - 问答历史导出接口
   - JSON/CSV 格式支持

4. **第四阶段（1天）**：优化和测试
   - 导出任务管理
   - 错误处理
   - 性能优化

---

## 6. 总体实施计划

### 6.1 时间安排

**总时长**：约 4-5 周

**第一周**：
- 搜索体验增强（搜索历史、建议、高亮）
- 批量操作（批量上传、删除）

**第二周**：
- 文档预览优化（PDF 预览、目录导航）
- 数据统计（基础统计、趋势分析）

**第三周**：
- 文档预览优化（文档内搜索、阅读模式）
- 导出功能（知识库导出、文档导出）

**第四周**：
- 数据统计（热力图、热词）
- 导出功能（问答记录导出）
- 测试和优化

### 6.2 技术依赖

**后端**：
- `PyPDF2` 或 `pdfplumber`：PDF 处理（Python）
- `python-docx`：Word 文档处理
- `openpyxl`：Excel 处理
- `reportlab` 或 `weasyprint`：PDF 生成
- `markdown`：Markdown 生成
- `libreoffice`（命令行工具）：Office 文档转 PDF（可选）

**注意**：
- `pdf.js` 是前端库，后端应使用 Python PDF 处理库
- 前端使用 `vue-pdf` 或 `pdf.js` 进行 PDF 预览

**前端**：
- `vue-pdf` 或 `pdf.js`：PDF 预览
- `echarts` 或 `chart.js`：图表展示
- `element-plus`：UI 组件

### 6.3 注意事项

1. **性能优化**：
   - 导出大文件使用异步任务
   - 搜索建议使用 Redis 缓存
   - 统计数据使用定时任务预计算

2. **用户体验**：
   - 所有异步操作显示进度
   - 错误信息清晰明确
   - 操作可撤销（如批量删除）

3. **数据安全**：
   - 导出文件包含用户认证
   - 批量操作验证用户权限
   - 统计数据按用户隔离

---

---

## 7. 设计检查清单

### 7.1 数据库设计检查

✅ **已修复**：
- 所有新表都包含 `created_at`、`updated_at`、`is_deleted` 字段（与 BaseModel 一致）
- 所有外键都使用 `ON DELETE CASCADE`
- 所有表都添加了必要的索引

### 7.2 API 设计检查

✅ **已确认**：
- API 响应格式与现有系统一致（`{"code": 0, "message": "ok", "data": {...}}`）
- 接口路径使用 `/api/v1/` 前缀
- 认证方式与现有接口一致（支持 query 参数或 header）

⚠️ **需要注意**：
- `/api/v1/search/history` 接口已存在，需要扩展而非新建
- `/api/v1/search/suggestions` 接口已存在，需要扩展响应格式
- `SearchRequest.filters` 字段已存在，只需扩展支持范围

### 7.3 与现有系统兼容性

✅ **兼容性检查**：
- 数据库表结构与 BaseModel 兼容
- API 响应格式与现有系统一致
- 字段命名遵循现有规范（snake_case）
- 用户认证和数据隔离已考虑

### 7.4 实施注意事项

1. **数据库迁移**：
   - 使用迁移脚本创建新表
   - 确保外键约束正确
   - 为现有数据初始化统计表

2. **API 扩展**：
   - 优先扩展现有接口，而非新建
   - 保持向后兼容性
   - 添加适当的版本控制

3. **性能考虑**：
   - 搜索历史表需要定期清理（保留最近 N 条）
   - 统计数据使用定时任务预计算
   - 导出大文件使用异步任务

4. **安全性**：
   - 所有接口都需要用户认证
   - 数据隔离验证（user_id 过滤）
   - 导出文件包含访问控制

---

**文档版本**：v1.1  
**创建日期**：2025-01-23  
**最后更新**：2025-01-23  
**检查状态**：✅ 已检查并修复兼容性问题

