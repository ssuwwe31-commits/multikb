-- SPX Knowledge Base MySQL 初始化SQL
-- 创建数据库

CREATE DATABASE IF NOT EXISTS `spx_knowledge` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `spx_knowledge`;

-- ============================================
-- 1. 知识库分类表
-- ============================================
CREATE TABLE IF NOT EXISTS `knowledge_base_categories` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '分类ID',
    `name` VARCHAR(255) NOT NULL COMMENT '分类名称',
    `description` TEXT COMMENT '分类描述',
    `parent_id` INT NULL COMMENT '父分类ID',
    `sort_order` INT DEFAULT 0 COMMENT '排序',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    `level` INT DEFAULT 1 COMMENT '分类层级',
    `icon` VARCHAR(100) COMMENT '分类图标',
    `color` VARCHAR(20) COMMENT '分类颜色',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_category_parent_id` (`parent_id`),
    INDEX `idx_category_is_active` (`is_active`),
    CONSTRAINT `fk_category_parent` FOREIGN KEY (`parent_id`) REFERENCES `knowledge_base_categories` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库分类表';

-- ============================================
-- 2. 知识库表
-- ============================================
CREATE TABLE IF NOT EXISTS `knowledge_bases` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '知识库ID',
    `name` VARCHAR(255) NOT NULL COMMENT '知识库名称',
    `description` TEXT COMMENT '知识库描述',
    `category_id` INT NULL COMMENT '分类ID',
    `user_id` INT NULL COMMENT '用户ID（数据隔离/owner）',
    `visibility` VARCHAR(20) NOT NULL DEFAULT 'private' COMMENT '可见性: private/shared/public(预留)',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    `enable_auto_tagging` BOOLEAN DEFAULT TRUE COMMENT '是否启用自动标签/摘要（知识库级别配置）',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_kb_name` (`name`),
    INDEX `idx_kb_category_id` (`category_id`),
    INDEX `idx_kb_is_active` (`is_active`),
    CONSTRAINT `fk_kb_category` FOREIGN KEY (`category_id`) REFERENCES `knowledge_base_categories` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库表';

-- ============================================
-- 2.1. 知识库成员表（知识库共享功能）
-- ============================================
CREATE TABLE IF NOT EXISTS `knowledge_base_members` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `knowledge_base_id` INT NOT NULL COMMENT '知识库ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `role` VARCHAR(20) NOT NULL DEFAULT 'viewer' COMMENT '角色: owner/viewer/editor/admin',
    `invited_by` INT NULL COMMENT '邀请人ID',
    `invited_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '邀请时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_kb_member` (`knowledge_base_id`, `user_id`),
    CONSTRAINT `fk_kb_member_kb` FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_kb_member_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库成员表';

-- ============================================
-- 3.1. 文档上传批次表
-- ============================================
CREATE TABLE IF NOT EXISTS `document_upload_batches` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '批次ID',
    `user_id` INT NULL COMMENT '用户ID（数据隔离）',
    `knowledge_base_id` INT NOT NULL COMMENT '知识库ID',
    `total_files` INT NOT NULL DEFAULT 0 COMMENT '总文件数',
    `processed_files` INT NOT NULL DEFAULT 0 COMMENT '已处理文件数',
    `success_files` INT NOT NULL DEFAULT 0 COMMENT '成功文件数',
    `failed_files` INT NOT NULL DEFAULT 0 COMMENT '失败文件数',
    `status` VARCHAR(50) NOT NULL DEFAULT 'pending' COMMENT '批次状态: pending/processing/completed/failed/completed_with_errors',
    `error_summary` TEXT COMMENT '错误摘要（JSON格式）',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_batch_user_id` (`user_id`),
    INDEX `idx_batch_kb_id` (`knowledge_base_id`),
    INDEX `idx_batch_status` (`status`),
    CONSTRAINT `fk_batch_kb` FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档上传批次表';

-- ============================================
-- 3.2. 失败任务视图
-- ============================================
CREATE OR REPLACE VIEW `v_failure_tasks` AS
SELECT 
    id, 
    'document' AS task_type, 
    original_filename AS filename,
    status, 
    error_message, 
    updated_at AS last_processed_at,
    knowledge_base_id, 
    user_id, 
    COALESCE(retry_count, 0) AS retry_count, 
    NULL AS document_id
FROM documents
WHERE status = 'failed' AND is_deleted = FALSE
UNION ALL
SELECT 
    di.id, 
    'image' AS task_type, 
    di.image_path AS filename,
    di.status, 
    di.error_message, 
    di.last_processed_at,
    d.knowledge_base_id, 
    d.user_id, 
    COALESCE(di.retry_count, 0) AS retry_count, 
    di.document_id
FROM document_images di
INNER JOIN documents d ON di.document_id = d.id
WHERE di.status = 'failed' AND di.is_deleted = FALSE;

-- ============================================
-- 3. 文档表
-- ============================================
CREATE TABLE IF NOT EXISTS `documents` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '文档ID',
    `original_filename` VARCHAR(255) NOT NULL COMMENT '原始文件名',
    `file_type` VARCHAR(50) COMMENT '文件类型',
    `file_size` INT COMMENT '文件大小',
    `file_hash` VARCHAR(64) COMMENT '文件哈希',
    `file_path` VARCHAR(500) COMMENT '文件路径',
    `converted_pdf_url` VARCHAR(500) COMMENT '转换后的PDF文件路径（MinIO对象键），用于预览',
    `knowledge_base_id` INT NOT NULL COMMENT '知识库ID',
    `batch_id` INT NULL COMMENT '所属批量上传批次ID',
    `category_id` INT NULL COMMENT '分类ID',
    `user_id` INT NULL COMMENT '用户ID（数据隔离）',
    `tags` JSON COMMENT '标签列表JSON',
    `metadata` JSON COMMENT '元数据JSON',
    `status` VARCHAR(50) DEFAULT 'uploaded' COMMENT '处理状态',
    `processing_progress` FLOAT DEFAULT 0.0 COMMENT '处理进度',
    `error_message` TEXT COMMENT '错误信息',
    `retry_count` INT DEFAULT 0 COMMENT '任务重试次数',
    `last_modified_at` DATETIME COMMENT '最后修改时间',
    `modification_count` INT DEFAULT 0 COMMENT '修改次数',
    `last_modified_by` VARCHAR(100) COMMENT '最后修改者',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_doc_knowledge_base_id` (`knowledge_base_id`),
    INDEX `idx_doc_batch_id` (`batch_id`),
    INDEX `idx_doc_category_id` (`category_id`),
    INDEX `idx_doc_status` (`status`),
    INDEX `idx_doc_file_hash` (`file_hash`),
    CONSTRAINT `fk_doc_kb` FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_doc_batch` FOREIGN KEY (`batch_id`) REFERENCES `document_upload_batches` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_doc_category` FOREIGN KEY (`category_id`) REFERENCES `knowledge_base_categories` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档表';

-- ============================================
-- 4. 文档分块表
-- ============================================
CREATE TABLE IF NOT EXISTS `document_chunks` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '分块ID',
    `document_id` INT NOT NULL COMMENT '文档ID',
    `content` TEXT NULL COMMENT '分块内容',
    `chunk_index` INT NOT NULL COMMENT '分块索引',
    `chunk_type` VARCHAR(50) DEFAULT 'text' COMMENT '分块类型',
    `metadata` TEXT COMMENT '元数据JSON',
    `version` INT DEFAULT 1 COMMENT '版本号',
    `chunk_version_id` INT NULL COMMENT '当前块版本ID',
    `last_modified_at` DATETIME COMMENT '最后修改时间',
    `modification_count` INT DEFAULT 0 COMMENT '修改次数',
    `last_modified_by` VARCHAR(100) COMMENT '最后修改者',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_chunk_document_id` (`document_id`),
    INDEX `idx_chunk_index` (`document_id`, `chunk_index`),
    INDEX `idx_chunk_version_id` (`chunk_version_id`),
    CONSTRAINT `fk_chunk_doc` FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档分块表';

-- ============================================
-- 5. 分块版本表
-- ============================================
CREATE TABLE IF NOT EXISTS `chunk_versions` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '版本ID',
    `chunk_id` INT NOT NULL COMMENT '分块ID',
    `version_number` INT NOT NULL COMMENT '版本号',
    `content` TEXT NOT NULL COMMENT '版本内容',
    `metadata` TEXT COMMENT '版本元数据JSON',
    `modified_by` VARCHAR(100) COMMENT '修改者',
    `version_comment` TEXT COMMENT '版本注释',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_chunk_ver_chunk_id` (`chunk_id`),
    INDEX `idx_chunk_ver_version` (`chunk_id`, `version_number`),
    CONSTRAINT `fk_version_chunk` FOREIGN KEY (`chunk_id`) REFERENCES `document_chunks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分块版本表';

-- ============================================
-- 6. 文档版本表
-- ============================================
CREATE TABLE IF NOT EXISTS `document_versions` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '版本ID',
    `document_id` INT NOT NULL COMMENT '文档ID',
    `version_number` INT NOT NULL COMMENT '版本号',
    `version_type` VARCHAR(50) DEFAULT 'auto' COMMENT '版本类型',
    `description` TEXT COMMENT '版本描述',
    `file_path` VARCHAR(500) NOT NULL COMMENT '文件路径',
    `file_size` INT COMMENT '文件大小',
    `file_hash` VARCHAR(64) COMMENT '文件哈希',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_doc_ver_document_id` (`document_id`),
    INDEX `idx_doc_ver_version` (`document_id`, `version_number`),
    CONSTRAINT `fk_doc_ver_doc` FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档版本表';

-- ============================================
-- 7. 文档图片表
-- ============================================
CREATE TABLE IF NOT EXISTS `document_images` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '图片ID',
    `document_id` INT NOT NULL COMMENT '文档ID',
    `image_path` VARCHAR(500) NOT NULL COMMENT '图片路径',
    `thumbnail_path` VARCHAR(500) COMMENT '缩略图路径',
    `image_type` VARCHAR(50) COMMENT '图片类型',
    `file_size` INT COMMENT '图片大小',
    `width` INT COMMENT '宽度',
    `height` INT COMMENT '高度',
    `sha256_hash` VARCHAR(64) COMMENT '图片哈希',
    `ocr_text` TEXT COMMENT 'OCR识别文本',
    `metadata` TEXT COMMENT '元数据JSON',
    `vector_model` VARCHAR(50) COMMENT '向量模型',
    `vector_dim` INT COMMENT '向量维度',
    `status` VARCHAR(50) DEFAULT 'pending' COMMENT '处理状态',
    `retry_count` INT DEFAULT 0 COMMENT '重试次数',
    `last_processed_at` DATETIME NULL COMMENT '最近处理时间',
    `error_message` TEXT COMMENT '错误信息',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_image_sha256` (`sha256_hash`),
    INDEX `idx_image_document_id` (`document_id`),
    INDEX `idx_image_status` (`status`),
    CONSTRAINT `fk_image_doc` FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档图片表';

-- ============================================
-- 8. 问答会话表
-- ============================================
CREATE TABLE IF NOT EXISTS `qa_sessions` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '会话ID',
    `session_id` VARCHAR(100) NOT NULL UNIQUE COMMENT '会话UUID',
    `session_name` VARCHAR(200) COMMENT '会话名称',
    `knowledge_base_id` INT NOT NULL COMMENT '知识库ID',
    `user_id` VARCHAR(100) COMMENT '用户ID',
    `query_method` VARCHAR(50) DEFAULT 'hybrid' COMMENT '查询方式',
    `search_config` JSON COMMENT '搜索配置JSON',
    `llm_config` JSON COMMENT 'LLM配置JSON',
    `question_count` INT DEFAULT 0 COMMENT '问题数量',
    `last_question` TEXT COMMENT '最后问题',
    `last_activity_time` DATETIME COMMENT '最后活动时间',
    `status` VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/inactive/deleted',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_session_id` (`session_id`),
    INDEX `idx_qa_session_kb_id` (`knowledge_base_id`),
    INDEX `idx_qa_session_user_id` (`user_id`),
    INDEX `idx_qa_session_activity_time` (`last_activity_time`),
    INDEX `idx_qa_session_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='问答会话表';

-- ============================================
-- 9. 问答记录表
-- ============================================
CREATE TABLE IF NOT EXISTS `qa_questions` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
    `question_id` VARCHAR(100) NOT NULL UNIQUE COMMENT '问题UUID',
    `session_id` VARCHAR(100) NOT NULL COMMENT '会话ID',
    `question_content` TEXT NOT NULL COMMENT '问题内容',
    `answer_content` TEXT COMMENT '答案内容',
    `source_info` JSON COMMENT '来源信息JSON',
    `processing_info` JSON COMMENT '处理信息JSON',
    `similarity_score` FLOAT COMMENT '相似度分数',
    `answer_quality` VARCHAR(20) COMMENT '答案质量',
    `user_feedback` JSON COMMENT '用户反馈JSON',
    `input_type` VARCHAR(50) DEFAULT 'text' COMMENT '输入类型：text/image/multimodal',
    `processing_time` FLOAT COMMENT '处理时间（秒）',
    `token_usage` INT COMMENT 'Token使用量',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_question_id` (`question_id`),
    INDEX `idx_qa_question_session_id` (`session_id`),
    INDEX `idx_qa_question_similarity` (`similarity_score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='问答记录表';

-- ============================================
-- 10. 问答统计表
-- ============================================
CREATE TABLE IF NOT EXISTS `qa_statistics` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '统计ID',
    `knowledge_base_id` INT NOT NULL COMMENT '知识库ID',
    `date` DATETIME NOT NULL COMMENT '统计日期',
    `total_questions` INT DEFAULT 0 COMMENT '总问题数',
    `answered_questions` INT DEFAULT 0 COMMENT '已回答数',
    `unanswered_questions` INT DEFAULT 0 COMMENT '未回答数',
    `avg_similarity_score` FLOAT COMMENT '平均相似度分数',
    `avg_response_time` FLOAT COMMENT '平均响应时间',
    `hot_questions` JSON COMMENT '热门问题JSON',
    `query_method_stats` JSON COMMENT '查询方式统计JSON',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_qa_stats_kb_id` (`knowledge_base_id`),
    INDEX `idx_qa_stats_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='问答统计表';

-- ============================================
-- 10.1 外部搜索记录表
-- ============================================
CREATE TABLE IF NOT EXISTS `qa_external_searches` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
    `question` TEXT NOT NULL COMMENT '用户原始问题',
    `search_query` TEXT COMMENT '发送到SearxNG的查询语句',
    `session_id` VARCHAR(100) COMMENT '会话ID',
    `user_id` VARCHAR(100) COMMENT '用户ID',
    `summary` TEXT COMMENT '模型总结',
    `results` JSON COMMENT '外部搜索结果JSON',
    `trigger_metadata` JSON COMMENT '触发元数据',
    `from_cache` BOOLEAN DEFAULT FALSE COMMENT '是否命中缓存',
    `latency` FLOAT COMMENT '耗时（秒）',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_external_session` (`session_id`),
    INDEX `idx_external_user` (`user_id`),
    INDEX `idx_external_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='外部搜索记录表';

-- ============================================
-- 11. Celery任务表
-- ============================================
CREATE TABLE IF NOT EXISTS `celery_tasks` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '任务ID',
    `task_id` VARCHAR(100) NOT NULL UNIQUE COMMENT 'Celery任务ID',
    `task_name` VARCHAR(100) NOT NULL COMMENT '任务名称',
    `status` VARCHAR(50) DEFAULT 'pending' COMMENT '任务状态',
    `progress` FLOAT DEFAULT 0.0 COMMENT '任务进度',
    `result` TEXT COMMENT '任务结果',
    `error_message` TEXT COMMENT '错误信息',
    `started_at` DATETIME COMMENT '开始时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_task_id` (`task_id`),
    INDEX `idx_celery_task_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Celery任务表';

-- ============================================
-- 12. 系统配置表
-- ============================================
CREATE TABLE IF NOT EXISTS `system_configs` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '配置ID',
    `key` VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
    `value` TEXT COMMENT '配置值',
    `description` TEXT COMMENT '配置描述',
    `config_type` VARCHAR(50) DEFAULT 'string' COMMENT '配置类型',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_config_key` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- ============================================
-- 13. 操作日志表
-- ============================================
CREATE TABLE IF NOT EXISTS `operation_logs` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
    `operation_type` VARCHAR(50) NOT NULL COMMENT '操作类型',
    `operation_description` TEXT COMMENT '操作描述',
    `user_id` INT COMMENT '用户ID',
    `resource_type` VARCHAR(50) COMMENT '资源类型',
    `resource_id` INT COMMENT '资源ID',
    `ip_address` VARCHAR(50) COMMENT 'IP地址',
    `user_agent` TEXT COMMENT '用户代理',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_op_log_user_id` (`user_id`),
    INDEX `idx_op_log_type` (`operation_type`),
    INDEX `idx_op_log_resource` (`resource_type`, `resource_id`),
    INDEX `idx_op_log_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='操作日志表';

-- ============================================
-- 14. 分块关系表（父子/顺序关系）
-- ============================================
CREATE TABLE IF NOT EXISTS `chunk_relations` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '关系ID',
    `document_id` INT NOT NULL COMMENT '文档ID',
    `relation_type` VARCHAR(32) NOT NULL COMMENT '关系类型: parent_child|sequence',
    `parent_chunk_id` VARCHAR(64) NULL COMMENT '父块ID',
    `child_chunk_id` VARCHAR(64) NULL COMMENT '子块ID/顺序中的后继',
    `order_in_parent` INT NULL COMMENT '子块在父块内的顺序',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_rel_doc_parent_order` (`document_id`, `parent_chunk_id`, `order_in_parent`),
    INDEX `idx_rel_doc_type` (`document_id`, `relation_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档分块关系表';

-- ============================================
-- 15. 文档表格表（表格JSON懒加载）
-- ============================================
CREATE TABLE IF NOT EXISTS `document_tables` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `table_uid` VARCHAR(64) NOT NULL UNIQUE COMMENT '表格唯一UID（UUID）',
    `table_group_uid` VARCHAR(64) NOT NULL COMMENT '整表分组UID（同一张大表的所有分片共享）',
    `document_id` INT NOT NULL COMMENT '文档ID',
    `element_index` INT NULL COMMENT '文档顺序索引',
    `n_rows` INT DEFAULT 0 COMMENT '行数',
    `n_cols` INT DEFAULT 0 COMMENT '列数',
    `headers_json` MEDIUMTEXT COMMENT '表头JSON',
    `cells_json` LONGTEXT COMMENT '单元格JSON（必要时可gzip存储）',
    `spans_json` MEDIUMTEXT COMMENT '合并单元格JSON',
    `stats_json` MEDIUMTEXT COMMENT '列类型与统计信息JSON',
    `part_index` INT DEFAULT 0 COMMENT '分片索引',
    `part_count` INT DEFAULT 1 COMMENT '总分片数',
    `row_range` VARCHAR(50) NULL COMMENT '此分片覆盖的行范围',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_doc_tables_doc_id` (`document_id`),
    INDEX `idx_doc_tables_uid` (`table_uid`),
    INDEX `idx_doc_tables_group` (`document_id`, `table_group_uid`, `part_index`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档表格存储表';

-- ============================================
-- 16. 集群配置表（K8s/监控/日志接入）
-- ============================================
CREATE TABLE IF NOT EXISTS `cluster_configs` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '集群配置ID',
    `name` VARCHAR(128) NOT NULL COMMENT '集群名称',
    `description` TEXT COMMENT '描述',
    `api_server` VARCHAR(255) NOT NULL COMMENT 'Kubernetes API Server 地址',
    `auth_type` VARCHAR(32) NOT NULL DEFAULT 'token' COMMENT '认证方式: token|kubeconfig|basic',
    `auth_token` MEDIUMTEXT COMMENT 'Bearer Token',
    `kubeconfig` LONGTEXT COMMENT 'kubeconfig 内容（加密存储）',
    `client_cert` LONGTEXT COMMENT '客户端证书（PEM）',
    `client_key` LONGTEXT COMMENT '客户端私钥（PEM）',
    `ca_cert` LONGTEXT COMMENT 'CA 证书（PEM）',
    `verify_ssl` BOOLEAN DEFAULT TRUE COMMENT '是否校验证书',
    `prometheus_url` VARCHAR(255) COMMENT 'Prometheus 地址',
    `prometheus_auth_type` VARCHAR(32) DEFAULT 'none' COMMENT 'Prometheus 认证方式',
    `prometheus_username` VARCHAR(128) COMMENT 'Prometheus 用户名',
    `prometheus_password` MEDIUMTEXT COMMENT 'Prometheus 密码/Token',
    `log_system` VARCHAR(64) COMMENT '日志系统类型: elk|loki|custom',
    `log_endpoint` VARCHAR(255) COMMENT '日志系统入口地址',
    `log_auth_type` VARCHAR(32) DEFAULT 'none' COMMENT '日志系统认证方式',
    `log_username` VARCHAR(128) COMMENT '日志系统用户名',
    `log_password` MEDIUMTEXT COMMENT '日志系统密码/Token',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `last_health_status` VARCHAR(32) DEFAULT 'unknown' COMMENT '最近一次健康检查状态',
    `last_health_message` TEXT COMMENT '健康检查结果描述',
    `last_health_checked_at` DATETIME COMMENT '最近一次健康检查时间',
    `credential_ref` VARCHAR(255) NULL COMMENT '外部凭证引用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cluster_name` (`name`),
    INDEX `idx_cluster_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='集群接入配置表';

-- ============================================
-- 17. 资源快照表（缓存关键K8s资源）
-- ============================================
CREATE TABLE IF NOT EXISTS `resource_snapshots` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '快照ID',
    `cluster_id` INT NOT NULL COMMENT '所属集群',
    `resource_uid` VARCHAR(128) NOT NULL COMMENT '资源UID',
    `resource_type` VARCHAR(64) NOT NULL COMMENT '资源类型: Pod/Node/Deployment 等',
    `namespace` VARCHAR(255) COMMENT '命名空间',
    `resource_name` VARCHAR(255) NOT NULL COMMENT '资源名称',
    `labels` JSON COMMENT '资源标签',
    `annotations` JSON COMMENT '资源注解',
    `spec` JSON COMMENT '资源规格',
    `status` JSON COMMENT '资源状态',
    `resource_version` VARCHAR(64) COMMENT '资源版本号',
    `snapshot` JSON NOT NULL COMMENT '资源快照内容(JSON)',
    `collected_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_snapshot_uid` (`cluster_id`, `resource_uid`),
    INDEX `idx_snapshot_cluster_resource` (`cluster_id`, `resource_type`, `namespace`, `resource_name`),
    CONSTRAINT `fk_snapshot_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `cluster_configs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Kubernetes 资源快照';

-- ============================================
-- 18. 诊断记录表
-- ============================================
CREATE TABLE IF NOT EXISTS `diagnosis_records` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '诊断记录ID',
    `cluster_id` INT NOT NULL COMMENT '所属集群',
    `namespace` VARCHAR(255) COMMENT '命名空间',
    `resource_type` VARCHAR(64) COMMENT '资源类型',
    `resource_name` VARCHAR(255) COMMENT '资源名称',
    `trigger_source` VARCHAR(32) DEFAULT 'manual' COMMENT '触发来源: alert|manual|schedule',
    `trigger_payload` JSON COMMENT '触发上下文',
    `symptoms` JSON COMMENT '症状摘要',
    `status` VARCHAR(32) DEFAULT 'pending' COMMENT '诊断状态: pending|running|completed|failed',
    `summary` TEXT COMMENT '概述',
    `conclusion` TEXT COMMENT '诊断结论',
    `confidence` DECIMAL(5,2) DEFAULT NULL COMMENT '置信度(0-1)',
    `metrics` JSON COMMENT '关键指标数据',
    `logs` JSON COMMENT '关键日志片段',
    `recommendations` JSON COMMENT '建议动作/知识条目',
    `events` JSON COMMENT '诊断事件时间线',
    `feedback` JSON COMMENT '用户反馈',
    `knowledge_refs` JSON COMMENT '关联知识库条目',
    `knowledge_source` VARCHAR(32) COMMENT '知识来源',
    `started_at` DATETIME COMMENT '开始时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_diag_cluster` (`cluster_id`, `status`),
    INDEX `idx_diag_resource` (`cluster_id`, `resource_type`, `resource_name`),
    CONSTRAINT `fk_diagnosis_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `cluster_configs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='运维诊断记录';

-- ============================================
-- 19. 资源同步状态表
-- ============================================
CREATE TABLE IF NOT EXISTS `resource_sync_states` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `cluster_id` INT NOT NULL COMMENT '集群ID',
    `resource_type` VARCHAR(64) NOT NULL COMMENT '资源类型',
    `namespace` VARCHAR(255) NULL COMMENT '命名空间',
    `resource_version` VARCHAR(64) NULL COMMENT '最新资源版本',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_sync_state` (`cluster_id`, `resource_type`, `namespace`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资源同步状态';

-- ============================================
-- 20. 资源事件表
-- ============================================
CREATE TABLE IF NOT EXISTS `resource_events` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '事件ID',
    `cluster_id` INT NOT NULL COMMENT '集群ID',
    `resource_type` VARCHAR(64) NOT NULL COMMENT '资源类型',
    `namespace` VARCHAR(255) NULL COMMENT '命名空间',
    `resource_uid` VARCHAR(128) NOT NULL COMMENT '资源UID',
    `event_type` VARCHAR(32) NOT NULL COMMENT '事件类型: created|updated|deleted',
    `diff` JSON NULL COMMENT '变更摘要',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_resource_event` (`cluster_id`, `resource_type`, `namespace`, `resource_uid`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资源变更事件';

-- ============================================
-- 21. 诊断迭代表
-- ============================================
CREATE TABLE IF NOT EXISTS `diagnosis_iterations` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '迭代ID',
    `diagnosis_id` INT NOT NULL COMMENT '所属诊断记录',
    `iteration_no` INT NOT NULL COMMENT '迭代序号',
    `stage` VARCHAR(64) COMMENT '迭代阶段',
    `status` VARCHAR(32) DEFAULT 'pending' COMMENT '迭代状态: pending|running|completed|failed',
    `reasoning_prompt` TEXT COMMENT '推理提示词',
    `reasoning_summary` TEXT COMMENT '推理摘要',
    `reasoning_output` JSON COMMENT '推理原始输出',
    `action_plan` JSON COMMENT '执行计划',
    `action_result` JSON COMMENT '执行结果',
    `metadata` JSON COMMENT '扩展信息',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_diagnosis_iteration` (`diagnosis_id`, `iteration_no`),
    INDEX `idx_iteration_diagnosis` (`diagnosis_id`, `status`),
    CONSTRAINT `fk_iteration_diagnosis` FOREIGN KEY (`diagnosis_id`) REFERENCES `diagnosis_records` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='诊断迭代记录';

-- ============================================
-- 22. 诊断记忆表
-- ============================================
CREATE TABLE IF NOT EXISTS `diagnosis_memories` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '记忆ID',
    `diagnosis_id` INT NOT NULL COMMENT '所属诊断记录',
    `iteration_id` INT NULL COMMENT '关联迭代ID',
    `iteration_no` INT NULL COMMENT '迭代序号',
    `memory_type` VARCHAR(32) NOT NULL COMMENT '记忆类型: symptom|metric|log|fact|hypothesis|conclusion|action|feedback',
    `summary` TEXT COMMENT '记忆摘要',
    `content` JSON COMMENT '记忆详情',
    `metadata` JSON COMMENT '附加信息',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_memory_diagnosis` (`diagnosis_id`, `memory_type`),
    INDEX `idx_memory_iteration` (`iteration_id`),
    CONSTRAINT `fk_memory_diagnosis` FOREIGN KEY (`diagnosis_id`) REFERENCES `diagnosis_records` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_memory_iteration` FOREIGN KEY (`iteration_id`) REFERENCES `diagnosis_iterations` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='诊断上下文记忆';

-- ============================================
-- 21. 知识图谱相关表
-- ============================================

-- 21.1 知识图谱实体表
CREATE TABLE IF NOT EXISTS `knowledge_graph_entities` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `knowledge_base_id` INT NOT NULL COMMENT '所属知识库ID',
    `user_id` INT NOT NULL COMMENT '创建用户ID',
    `name` VARCHAR(255) NOT NULL COMMENT '实体名称',
    `type` VARCHAR(50) NOT NULL COMMENT '实体类型: person/location/concept/product/technology/event/organization/other',
    `description` TEXT COMMENT '实体描述',
    `aliases` JSON COMMENT '实体别名列表，如: ["Python", "Python语言"]',
    `confidence` FLOAT DEFAULT 0.7 COMMENT '置信度分数（0-1），用于表示实体提取的可信度',
    `metadata` JSON COMMENT '扩展元数据，如: {"source": "doc_123", "extraction_method": "llm"}',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    `nebula_synced` BOOLEAN DEFAULT FALSE COMMENT '是否已同步到NebulaGraph',
    `nebula_synced_at` DATETIME COMMENT '同步到NebulaGraph的时间',
    `nebula_sync_error` TEXT COMMENT '同步错误信息（如果同步失败）',
    INDEX `idx_kb_name` (`knowledge_base_id`, `name`),
    INDEX `idx_type` (`type`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_is_deleted` (`is_deleted`),
    INDEX `idx_kb_deleted` (`knowledge_base_id`, `is_deleted`),
    INDEX `idx_type_deleted` (`type`, `is_deleted`),
    INDEX `idx_nebula_synced` (`nebula_synced`, `updated_at`) COMMENT '用于同步任务查询',
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    UNIQUE KEY `uk_kb_name_type` (`knowledge_base_id`, `name`, `type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识图谱实体表（主存储，用于列表查询、统计查询、关联查询）';

-- 21.2 知识图谱关系表
CREATE TABLE IF NOT EXISTS `knowledge_graph_relationships` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `knowledge_base_id` INT NOT NULL COMMENT '所属知识库ID',
    `user_id` INT NOT NULL COMMENT '创建用户ID',
    `source_entity_id` INT NOT NULL COMMENT '源实体ID',
    `target_entity_id` INT NOT NULL COMMENT '目标实体ID',
    `relation_type` VARCHAR(50) NOT NULL COMMENT '关系类型: belongs_to/references/depends_on/compares/implements/related_to/part_of/has_part/created_by/occurs_in/other',
    `description` TEXT COMMENT '关系描述',
    `weight` FLOAT DEFAULT 0.5 COMMENT '关系权重（0-1），用于表示关系强度（基于共现频率、语义相似度等计算）',
    `confidence` FLOAT DEFAULT 0.7 COMMENT '置信度分数（0-1），用于表示关系提取的可信度',
    `metadata` JSON COMMENT '扩展元数据，如: {"source": "doc_123", "evidence": "文档片段", "extraction_method": "llm"}',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    `nebula_synced` BOOLEAN DEFAULT FALSE COMMENT '是否已同步到NebulaGraph',
    `nebula_synced_at` DATETIME COMMENT '同步到NebulaGraph的时间',
    `nebula_sync_error` TEXT COMMENT '同步错误信息（如果同步失败）',
    INDEX `idx_kb` (`knowledge_base_id`),
    INDEX `idx_source` (`source_entity_id`),
    INDEX `idx_target` (`target_entity_id`),
    INDEX `idx_relation_type` (`relation_type`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_is_deleted` (`is_deleted`),
    INDEX `idx_kb_deleted` (`knowledge_base_id`, `is_deleted`),
    INDEX `idx_source_deleted` (`source_entity_id`, `is_deleted`),
    INDEX `idx_target_deleted` (`target_entity_id`, `is_deleted`),
    INDEX `idx_nebula_synced` (`nebula_synced`, `updated_at`) COMMENT '用于同步任务查询',
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`source_entity_id`) REFERENCES `knowledge_graph_entities` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`target_entity_id`) REFERENCES `knowledge_graph_entities` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    UNIQUE KEY `uk_source_target_relation` (`source_entity_id`, `target_entity_id`, `relation_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识图谱关系表（主存储，用于列表查询、统计查询）';

-- 21.3 实体-文档关联表
CREATE TABLE IF NOT EXISTS `knowledge_graph_entity_documents` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `entity_id` INT NOT NULL COMMENT '实体ID',
    `document_id` INT NOT NULL COMMENT '文档ID',
    `chunk_id` INT COMMENT '文档块ID（可选）',
    `mentions_count` INT DEFAULT 1 COMMENT '提及次数',
    `first_mention_position` INT COMMENT '首次提及位置（字符偏移）',
    `metadata` JSON COMMENT '扩展元数据',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX `idx_entity` (`entity_id`),
    INDEX `idx_document` (`document_id`),
    INDEX `idx_chunk` (`chunk_id`),
    INDEX `idx_is_deleted` (`is_deleted`),
    FOREIGN KEY (`entity_id`) REFERENCES `knowledge_graph_entities` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`chunk_id`) REFERENCES `document_chunks` (`id`) ON DELETE SET NULL,
    UNIQUE KEY `uk_entity_document_chunk` (`entity_id`, `document_id`, `chunk_id`, `is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实体-文档关联表（记录实体在文档中的提及情况）';

-- 21.4 实体提取任务表
CREATE TABLE IF NOT EXISTS `knowledge_graph_extraction_tasks` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `knowledge_base_id` INT NOT NULL COMMENT '知识库ID',
    `document_id` INT COMMENT '文档ID（可选，为空表示批量提取）',
    `status` VARCHAR(50) DEFAULT 'pending' COMMENT '状态: pending/processing/completed/failed',
    `total_entities` INT DEFAULT 0 COMMENT '提取的实体数量',
    `total_relationships` INT DEFAULT 0 COMMENT '提取的关系数量',
    `error_message` TEXT COMMENT '错误信息',
    `metadata` JSON COMMENT '扩展元数据',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX `idx_kb` (`knowledge_base_id`),
    INDEX `idx_document` (`document_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_is_deleted` (`is_deleted`),
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实体提取任务表';

-- ============================================
-- 初始化完成
-- ============================================
SELECT 'SPX Knowledge Base 数据库初始化完成！' AS message;
