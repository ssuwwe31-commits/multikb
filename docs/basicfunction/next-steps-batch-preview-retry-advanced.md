---
title: "批量上传 + 预览增强 + 失败重试 + 高级内容理解"设计方案
date: 2025-01-28
owner: platform-team
status: draft
---

# 1. 背景与目标

当前知识库已经实现单文档上传、解析、搜索等核心能力，但仍存在以下痛点：

1. **批量上传体验不足**：一次只能上传一个文件，用户需要重复操作，缺乏整体进度反馈。
2. **结构化数据预览较弱**：JSON/XML/CSV 等文件需要下载查看，不利于快速审阅。
3. **失败任务管理缺失**：文档/图片处理失败后只能在详情页逐个重试，效率低下。
4. **高级内容理解不足**：缺乏自动标签/摘要等智能化能力。

本设计旨在：
- 提供批量上传与进度展示能力。
- 为 JSON/XML/CSV 提供可视化预览。
- 建立统一的失败重试中心。
- 引入自动标签能力，提升内容理解与推荐效果。

# 2. 需求概述

| 功能 | 描述 | 关键收益 |
| ---- | ---- | -------- |
| 批量上传进度 | 支持批量文件/ZIP 上传到已有 `upload_document` 流程，实时展示整体与单文件进度 | 减少重复操作，提升上传体验 |
| JSON/XML/CSV 可视化预览 | 在 `Documents/detail.vue` 中增加树形/表格化渲染 | 快速查看结构化内容 |
| 失败重试中心 | 提供失败任务列表，可批量/自动重试 | 降低人工维护成本 |
| 自动标签/摘要 | 基于 LLM/Ollama 生成关键词与摘要 | 提升检索与列表信息量 |

# 3. 功能设计

## 3.1 批量上传与进度展示

### 3.1.1 使用场景
- 单次上传多个文件（拖拽或选择）。
- 上传 ZIP 自动解包并逐个走 `upload_document`。
- 需要查看整体进度、每个文件状态及错误信息。

### 3.1.2 设计方案
1. **前端 (`Documents/upload.vue`)**
   - 新增"批量上传"模式，可选文件列表或 ZIP。
   - 使用 `Upload` 组件的 `file-list` 渲染每个文件状态。
   - 引入进度面板：显示总进度（成功/失败/进行中计数）和单文件进度条。
   - 错误展示：对失败文件提供"查看日志"和"重试"按钮。
2. **后端**
   - **注意**：当前已有 `/api/v1/documents/batch-upload` 接口（基础实现），需要增强以下功能：
     - 支持 ZIP 文件自动解包。
     - 实现批次进度跟踪（批次表 + 状态接口）。
     - 实现实时进度通知（WebSocket 或轮询）。
   - **批量进度记录**：
     - 新建 `document_upload_batches` 表：
       | 字段 | 类型 | 含义 |
       | ---- | ---- | ---- |
       | id | INT | 批次 ID（主键） |
       | user_id | INT | 用户 ID（数据隔离） |
       | knowledge_base_id | INT | 知识库 ID |
       | total_files | INT | 总数 |
       | processed_files | INT | 已处理 |
       | success_files | INT | 成功数量 |
       | failed_files | INT | 失败数量 |
       | status | VARCHAR(50) | pending/processing/completed/failed/completed_with_errors |
       | error_summary | TEXT | 错误摘要（JSON 格式） |
       | created_at | DATETIME | 创建时间 |
       | updated_at | DATETIME | 更新时间 |
       - 索引：`idx_batch_user_id`, `idx_batch_kb_id`, `idx_batch_status`
     - 每个 `documents` 记录新增 `batch_id`（INT，外键），便于聚合。
   - **安全扫描与实时通知**：
     - **扫描节流**：批量任务默认串行提交到新的"扫描队列"（Celery queue: `security_scan`），限制并发，避免 ClamAV 同时处理过多文件。
     - **异步状态**：`documents.security_scan_status` 使用现有状态值（`pending`, `scanning`, `safe`, `infected`, `error`, `skipped`）。批量上传时：
       - 先写入 `pending`，由扫描 worker 异步更新为 `scanning` → `safe`/`infected`/`error`/`skipped`。
       - 扫描完成后（`safe` 或 `skipped`）再触发 `process_document_task`。
     - **通知接口**：
       - 轮询接口：`GET /api/v1/documents/batch/{batch_id}/status` 返回批次整体状态和每个文件的详细进度。
       - 响应格式：
         ```json
         {
           "batch_id": 123,
           "status": "processing",
           "total_files": 10,
           "processed_files": 5,
           "success_files": 4,
           "failed_files": 1,
           "files": [
             {
               "document_id": 1,
               "filename": "doc1.pdf",
               "status": "completed",  // 文档处理状态：uploaded/parsing/chunking/vectorizing/indexing/completed/failed
               "security_scan_status": "safe",  // 安全扫描状态：pending/scanning/safe/infected/error/skipped
               "processing_progress": 100,  // 处理进度 0-100
               "error_message": null  // 错误信息（如果有）
             }
           ]
         }
         ```
       - 可选：WebSocket 实时推送（后续迭代）。

### 3.1.3 异常处理与架构补充
- **批次状态管理**：
  - `pending`：批次创建，等待处理。
  - `processing`：正在处理中（至少有一个文件在处理）。
  - `completed`：所有文件处理完成且全部成功。
  - `completed_with_errors`：所有文件处理完成，但有部分失败（`success_files > 0` 且 `failed_files > 0`）。
  - `failed`：批次处理失败（如 ZIP 解包失败、所有文件都失败）。
- **单文件失败处理**：单文件失败不影响其他文件，批次状态为 `completed_with_errors`。
- **ZIP 解包失败**：整体标记失败（`status = 'failed'`），返回错误原因。
- **扫描阶段失败**：批量任务在扫描阶段失败时，记录 `security_scan_result`，仍允许手动重试或跳过。
- **断点续传**（后续迭代）：记录已处理文件，重试时跳过。
- **扫描架构建议**：
  - 在 `FileValidationService` 保持同步扫描的基础上，为批量上传引入专用 Celery worker；HTTP 请求只负责排队上传文件，扫描结果通过任务回写。
  - 可选：部署独立的 ClamAV/扫描服务，通过 RPC 或消息队列串行调度，防止应用进程被占满。

## 3.2 JSON/XML/CSV 预览增强

### 3.2.1 文件类型检测
- **检测逻辑**：
  - 根据文件扩展名（`.json`, `.xml`, `.csv`）和 MIME 类型判断。
  - 对于 `.txt` 文件，尝试解析前 1KB 内容判断是否为 JSON/XML。
- **数据存储**：
  - 上传时在 `documents.metadata` 中记录 `structured_type` (`json`, `xml`, `csv`)。
  - 对 CSV 调用 `ExcelService.parse_csv_preview()` 生成前 N 行（默认 100 行）结构化数据，存储在 `metadata.preview_samples`。
  - 对 JSON/XML，解析并裁剪前 1MB 内容存储在 `metadata.preview_samples`。

### 3.2.2 前端展示 (`Documents/detail.vue`)
- **JSON/XML**
  - 引入树形视图组件（如 `vue-json-pretty`）。
  - 支持折叠/展开节点、复制路径。
  - XML 先转为 DOM 再渲染（保留属性/文本）。
- **CSV**
  - 使用 `el-table` 渲染前 N 行。
  - 支持下载原始文件。

### 3.2.3 服务器支持
- **API 接口**：`GET /api/v1/documents/{id}/structured-preview`
  - 返回样例数据：
    ```json
    {
      "type": "json",
      "content": {...},      // JSON 对象（裁剪，最大 1MB）
      "raw_snippet": "...",  // 原文片段（前 500 字符）
      "schema": {...},       // 可选 schema（JSON 结构分析）
      "total_size": 1024000, // 原始文件大小
      "preview_rows": 100    // 预览行数（CSV 专用）
    }
    ```
  - **实现逻辑**：
    - 优先从 `documents.metadata.preview_samples` 读取（已缓存）。
    - 如果不存在，实时解析并缓存（异步任务更新 metadata）。
    - 对于超大文件（>10MB），仅返回结构概览，不返回完整内容。

## 3.3 失败重试中心

### 3.3.1 数据来源
- `documents` 表 `status`, `error_message`.
- `document_images` 表 `status`, `error_message`.
- Celery 任务失败日志。

### 3.3.2 功能需求
- 后台（Web）页面展示：
  - 文档任务失败列表（分页、过滤：知识库、时间、错误类型）。
  - 图片/OCR 失败列表。
  - 批量操作：重新触发处理/重置状态。
- 自动重试策略：
  - 可配置重试次数、间隔。
  - 记录自动重试日志。

### 3.3.3 实现方案
1. **后端**
   - **数据模型**：使用 SQL 视图 `v_failure_tasks` 整合 `documents` 和 `document_images`：
     ```sql
     CREATE VIEW v_failure_tasks AS
     SELECT 
       id, 'document' AS task_type, original_filename AS filename,
       status, error_message, updated_at AS last_processed_at,
       knowledge_base_id, user_id, 0 AS retry_count, NULL AS document_id
     FROM documents
     WHERE status = 'failed' AND is_deleted = FALSE
     UNION ALL
     SELECT 
       di.id, 'image' AS task_type, di.image_path AS filename,
       di.status, di.error_message, di.last_processed_at,
       d.knowledge_base_id, d.user_id, di.retry_count, di.document_id
     FROM document_images di
     INNER JOIN documents d ON di.document_id = d.id
     WHERE di.status = 'failed' AND di.is_deleted = FALSE;
     ```
     - **注意**：视图需要包含 `document_id` 字段，以便图片任务可以关联到文档；同时需要 JOIN `documents` 表获取 `knowledge_base_id` 和 `user_id`。
   - **API 接口**：
     - `GET /api/v1/tasks/failures?type=document|image&knowledge_base_id=...&page=1&size=20`
     - `POST /api/v1/tasks/failures/{id}/retry`（需要 `task_type` 参数）
     - `POST /api/v1/tasks/failures/batch-retry`（请求体：`{"task_ids": [1,2,3], "task_type": "document"}`）
   - **重试逻辑**：
     - 文档：调用 `DocumentService.reprocess_document(doc_id)`（重置状态为 `reprocessing`，触发 `process_document_task`）。
     - 图片：调用 `ImageService.process_image_sync(image_id)`（同步处理，包含 OCR、向量化、索引；注意：`document_images` 表已有 `retry_count` 字段）。
     - 更新 `retry_count` 字段：
       - `document_images` 表已有 `retry_count` 字段。
       - `documents` 表需要新增 `retry_count` 字段（INT，默认 0）。
2. **前端**
   - 新增"失败任务中心"页面（`Tasks/failures.vue`）。
   - 列表字段：类型、文件名、知识库、错误信息、最后处理时间、重试次数、操作人。
   - 行内操作：查看详情/重新处理/批量重试。
   - 支持筛选：任务类型、知识库、时间范围、错误类型（通过错误信息关键词匹配）。

## 3.4 高级内容理解

### 3.4.1 文档自动标签/摘要

#### 流程
1. **触发时机**：在 `process_document_task` 完成所有 chunk 生成和向量化后，但在索引建立之前（即 `status` 从 `vectorizing` 转为 `indexing` 之前）。
   - **注意**：如果自动标签/摘要生成失败，不应阻塞文档处理流程，应记录错误但继续索引建立。
2. **内容提取**：
   - 收集所有 chunk 的文本内容（限制总长度，如 10000 字符）。
   - 调用 `OllamaService.generate_text()` 或 `OllamaService.chat()`：
     - Prompt 示例：「请为以下文档内容提取 5 个中文关键词，并生成 2 句摘要。内容：{text_content}」
     - 返回结构：`{"keywords": ["关键词1", "关键词2", ...], "summary": "摘要文本" }`
3. **结果存储**：
   - `documents.metadata.auto_keywords`（数组）
   - `documents.metadata.auto_summary`（字符串）
   - 可选：为每个 chunk 也生成关键词，存储在 `document_chunks.metadata.auto_keywords`（仅对重要 chunk，如标题块）。
4. **前端展示**：
   - 列表页（`Documents/index.vue`）新增"AI 标签"列，显示前 3 个关键词。
   - 详情页（`Documents/detail.vue`）展示摘要卡片，可折叠。
   - 支持手动触发重新生成（调用 `POST /api/v1/documents/{id}/regenerate-summary`）。

#### 配置
- 支持按知识库开启/关闭。
- 可选择模型（默认 `OLLAMA_MODEL`，可切换到在线 LLM）。



# 4. 系统影响与改动点

| 模块 | 影响说明 |
| ---- | -------- |
| 后端 API | 新增/增强：批量上传（ZIP 支持、批次状态）、预览（结构化数据）、失败任务（列表/重试）、自动标签/摘要（生成/重新生成） |
| 数据库 | 新增表：`document_upload_batches`；新增视图：`v_failure_tasks`；修改表：`documents`（新增 `batch_id` INT, `retry_count` INT DEFAULT 0），`document_images`（已有 `retry_count` 字段，无需修改） |
| 处理流程 | `process_document_task` 增加：自动标签/摘要生成（向量化后、索引前，可选，失败不阻塞） |
| 前端 | 上传页（批量上传 UI、进度展示）、详情页（结构化预览、AI 标签/摘要）、失败任务中心（新页面）、列表页（AI 标签列） |
| 配置 | 新增配置项：`ENABLE_AUTO_TAGGING`（自动标签开关）、`AUTO_TAGGING_MODEL`（标签生成模型）、`BATCH_UPLOAD_MAX_FILES`（批量上传最大文件数）、`BATCH_UPLOAD_MAX_SIZE`（批量上传最大总大小）、`STRUCTURED_PREVIEW_MAX_SIZE`（结构化预览最大文件大小） |

# 5. 迭代建议

| 阶段 | 内容 |
| ---- | ---- |
| Phase 1 | 批量上传 + 失败重试中心（与当前痛点最直接） |
| Phase 2 | JSON/XML/CSV 预览 + 自动标签/摘要 |
| Phase 3 | 性能优化、监控告警、断点续传等增强特性 |

# 6. 风险与缓解

| 风险 | 说明 | 缓解措施 |
| ---- | ---- | -------- |
| 批量上传导致 Celery 压力激增 | 短时间提交大量任务 | 设置批次并发上限（如每批次最多 10 个文件同时处理），使用专用队列（`security_scan`）串行扫描，调度节流 |
| LLM 成本与延迟 | 自动标签/摘要依赖模型调用 | 支持本地模型（Ollama）、缓存结果（相同内容不重复生成）、离线任务（异步处理，不阻塞主流程）、设置超时和重试 |
| 可观测性缺失 | 新流程较多，难以追踪问题 | 接入 Prometheus 指标（批次处理时间、失败率、LLM 调用延迟），增加日志结构化输出（JSON 格式，包含 trace_id），添加健康检查接口 |
| 结构化预览性能 | 大文件解析可能耗时 | 限制预览大小（默认 1MB），使用缓存（Redis），异步生成预览数据 |

# 7. 当前实现状态

## 7.1 已实现功能
- **基础批量上传**：`/api/v1/documents/batch-upload` 接口已存在，支持多文件上传，但缺少批次跟踪和 ZIP 支持。
- **文档处理流程**：`process_document_task` 已完整实现，支持多种文档类型（PDF、DOCX、TXT、MD、HTML、Excel、PPTX）。
- **安全扫描**：`security_scan_status` 字段已实现，支持 `pending`, `scanning`, `safe`, `infected`, `error`, `skipped` 状态。
- **文档重试**：`DocumentService.reprocess_document()` 已实现，支持手动重试。

## 7.2 待实现功能
- **批量上传增强**：批次表、ZIP 解包、进度跟踪、实时通知。
- **结构化预览**：JSON/XML/CSV 预览接口和前端展示。
- **失败重试中心**：统一的任务失败列表、批量重试、自动重试策略。
- **自动标签/摘要**：LLM 调用、结果存储、前端展示。

## 7.3 实现注意事项
1. **数据库迁移**：新增表和字段需要编写迁移脚本，注意外键约束和索引优化。
2. **向后兼容**：现有 API 接口保持兼容，新功能通过新接口或扩展现有接口实现。
3. **性能考虑**：批量操作需要限制并发和资源使用，避免影响系统稳定性。
4. **错误处理**：所有新功能需要完善的错误处理和日志记录。
5. **测试覆盖**：新增功能需要单元测试和集成测试，特别是批量操作和异步任务。

# 8. 结论

通过上述功能，系统可在上传体验、结构化预览、任务维护以及内容智能化方面获得全面升级，为知识库建设提供更高效、更智能的基础能力。推荐按照"批量上传 + 失败重试 → 结构化预览 → 自动标签/摘要"顺序实施。

**实施优先级建议**：
1. **Phase 1（高优先级）**：批量上传增强（批次跟踪、ZIP 支持）、失败重试中心（统一管理、批量操作）
2. **Phase 2（中优先级）**：结构化预览（JSON/XML/CSV）、自动标签/摘要（提升用户体验）
3. **Phase 3（后续迭代）**：性能优化、监控告警、断点续传等增强特性

# 9. 后续迭代功能（暂不实现）

## 9.1 文档关联分析

**状态**：暂不实现，保留设计供后续迭代参考。

### 功能概述
根据 chunk 元数据构建文档间的相似/引用关系，在详情页推荐相关文档。

### 设计要点
1. **相似度计算**：使用 chunk 向量计算相似文档（基于 OpenSearch 向量搜索）。
2. **引用关系解析**：解析 chunk 文本中的文档引用模式（如 "见文档 #123"、"参考文档ID:456"）。
3. **结构化数据引用**：对 HTML/JSON/XML chunk 中的链接进行引用映射。

### 存储结构
- 新增 `document_relations` 表存储文档关系（similar/reference/citation）。

### 前端展示
- 详情页新增"相关文档"卡片，列出前 5 条相关文档。

**注意**：此功能设计保留在文档中，但不在当前实施计划内。

