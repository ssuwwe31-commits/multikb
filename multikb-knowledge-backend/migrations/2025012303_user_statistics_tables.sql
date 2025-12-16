-- Migration: 用户统计表
-- 文件：migrations/2025012303_user_statistics_tables.sql
-- 创建日期：2025-01-23

USE `spx_knowledge`;

-- 用户统计表
CREATE TABLE IF NOT EXISTS `user_statistics` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT 'ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `stat_date` DATE NOT NULL COMMENT '统计日期',
    `stat_type` VARCHAR(50) NOT NULL COMMENT '统计类型：daily/weekly/monthly',
    
    -- 知识库统计
    `knowledge_base_count` INT DEFAULT 0 COMMENT '知识库数量',
    `document_count` INT DEFAULT 0 COMMENT '文档数量',
    `total_file_size` BIGINT DEFAULT 0 COMMENT '总文件大小（字节）',
    
    -- 使用统计
    `search_count` INT DEFAULT 0 COMMENT '搜索次数',
    `qa_count` INT DEFAULT 0 COMMENT '问答次数',
    `upload_count` INT DEFAULT 0 COMMENT '上传次数',
    
    -- 存储统计
    `storage_used` BIGINT DEFAULT 0 COMMENT '已用存储（字节）',
    `storage_limit` BIGINT DEFAULT 0 COMMENT '存储限制（字节）',
    
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_date_type` (`user_id`, `stat_date`, `stat_type`),
    INDEX `idx_user_date` (`user_id`, `stat_date` DESC),
    INDEX `idx_is_deleted` (`is_deleted`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户统计表';

-- 文档类型统计表
CREATE TABLE IF NOT EXISTS `document_type_statistics` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT 'ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `file_type` VARCHAR(50) NOT NULL COMMENT '文件类型',
    `count` INT DEFAULT 0 COMMENT '数量',
    `total_size` BIGINT DEFAULT 0 COMMENT '总大小',
    `stat_date` DATE NOT NULL COMMENT '统计日期',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_user_date` (`user_id`, `stat_date` DESC),
    INDEX `idx_is_deleted` (`is_deleted`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档类型统计表';
