-- 批量上传和失败重试相关表结构
-- 创建时间: 2025-01-28

USE `spx_knowledge`;

-- ============================================
-- 1. 文档上传批次表
-- ============================================
CREATE TABLE IF NOT EXISTS `document_upload_batches` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '批次ID',
    `user_id` INT COMMENT '用户ID（数据隔离）',
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
-- 2. 为 documents 表添加 batch_id 和 retry_count 字段
-- ============================================
ALTER TABLE `documents` 
ADD COLUMN `batch_id` INT NULL COMMENT '批次ID（外键）' AFTER `knowledge_base_id`,
ADD COLUMN `retry_count` INT DEFAULT 0 COMMENT '重试次数' AFTER `error_message`,
ADD INDEX `idx_doc_batch_id` (`batch_id`),
ADD CONSTRAINT `fk_doc_batch` FOREIGN KEY (`batch_id`) REFERENCES `document_upload_batches` (`id`) ON DELETE SET NULL;

-- ============================================
-- 3. 失败任务视图
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
