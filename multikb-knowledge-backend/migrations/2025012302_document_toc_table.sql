-- Migration: 文档目录表
-- 文件：migrations/2025012302_document_toc_table.sql
-- 创建日期：2025-01-23

USE `spx_knowledge`;

-- 文档目录表
CREATE TABLE IF NOT EXISTS `document_toc` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT 'ID',
    `document_id` INT NOT NULL COMMENT '文档ID',
    `level` INT NOT NULL COMMENT '目录级别（1-6）',
    `title` VARCHAR(500) NOT NULL COMMENT '标题',
    `page_number` INT COMMENT '页码',
    `position` INT COMMENT '位置（用于排序）',
    `parent_id` INT COMMENT '父级目录ID',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_document` (`document_id`),
    INDEX `idx_parent` (`parent_id`),
    INDEX `idx_is_deleted` (`is_deleted`),
    FOREIGN KEY (`document_id`) REFERENCES `documents`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档目录表';
