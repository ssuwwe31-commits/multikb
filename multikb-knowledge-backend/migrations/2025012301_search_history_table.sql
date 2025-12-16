-- Migration: 搜索历史表
-- 文件：migrations/2025012301_search_history_table.sql
-- 创建日期：2025-01-23

USE `spx_knowledge`;

-- 搜索历史表
CREATE TABLE IF NOT EXISTS `search_history` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT 'ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `query_text` VARCHAR(500) NOT NULL COMMENT '搜索关键词',
    `search_type` VARCHAR(50) COMMENT '搜索类型：vector/keyword/hybrid/exact',
    `knowledge_base_id` INT COMMENT '知识库ID（可选）',
    `result_count` INT DEFAULT 0 COMMENT '结果数量',
    `search_time_ms` INT COMMENT '搜索耗时（毫秒）',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '搜索时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_user_created` (`user_id`, `created_at` DESC),
    INDEX `idx_query` (`query_text`(100)),
    INDEX `idx_is_deleted` (`is_deleted`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='搜索历史记录表';

-- 搜索热词表
CREATE TABLE IF NOT EXISTS `search_hotwords` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT 'ID',
    `keyword` VARCHAR(200) NOT NULL COMMENT '关键词',
    `search_count` INT DEFAULT 1 COMMENT '搜索次数',
    `last_searched_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '最后搜索时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '首次搜索时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_keyword` (`keyword`),
    INDEX `idx_count` (`search_count` DESC),
    INDEX `idx_last_searched` (`last_searched_at` DESC),
    INDEX `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='搜索热词统计表';
