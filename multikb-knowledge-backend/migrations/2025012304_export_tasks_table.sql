-- Migration: 导出任务表
-- 文件：migrations/2025012304_export_tasks_table.sql
-- 创建日期：2025-01-23

USE `spx_knowledge`;

-- 导出任务表
CREATE TABLE IF NOT EXISTS `export_tasks` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT 'ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `export_type` VARCHAR(50) NOT NULL COMMENT '导出类型：knowledge_base/document/qa_history',
    `target_id` INT COMMENT '目标ID（知识库ID/文档ID）',
    `export_format` VARCHAR(50) NOT NULL COMMENT '导出格式：markdown/pdf/json',
    `status` VARCHAR(50) DEFAULT 'pending' COMMENT '状态：pending/processing/completed/failed',
    `file_path` VARCHAR(500) COMMENT '导出文件路径',
    `file_size` BIGINT COMMENT '文件大小',
    `error_message` TEXT COMMENT '错误信息',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_user_status` (`user_id`, `status`),
    INDEX `idx_is_deleted` (`is_deleted`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='导出任务表';
