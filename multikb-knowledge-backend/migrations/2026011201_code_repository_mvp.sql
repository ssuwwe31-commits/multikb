-- 代码库知识库 MVP 版本
-- 创建日期：2026-01-12
-- 设计文档：code-repository-mvp-design.md

-- =============================================
-- 表1：code_repositories（代码仓库）
-- =============================================

CREATE TABLE IF NOT EXISTS `code_repositories` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `repo_url` VARCHAR(500) NOT NULL COMMENT 'GitHub仓库URL',
    `repo_name` VARCHAR(255) NOT NULL COMMENT '仓库名称（owner/repo）',
    `repo_type` VARCHAR(50) DEFAULT 'github' COMMENT '仓库类型',
    
    -- Git 信息
    `default_branch` VARCHAR(100) DEFAULT 'main',
    `last_commit_hash` VARCHAR(100),
    `last_commit_date` DATETIME,
    
    -- 克隆状态
    `local_path` VARCHAR(500) COMMENT '本地克隆路径（如：/data/code_repositories/1）',
    `clone_status` VARCHAR(50) DEFAULT 'pending' COMMENT 'pending/cloning/completed/failed',
    `clone_progress` FLOAT DEFAULT 0.0,
    
    -- 代码统计
    `total_files` INT DEFAULT 0,
    `total_lines` INT DEFAULT 0,
    `language_stats` JSON COMMENT '语言统计',
    
    -- 解析状态
    `parse_status` VARCHAR(50) DEFAULT 'pending',
    `parse_progress` FLOAT DEFAULT 0.0,
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_repo_name` (`repo_name`),
    INDEX `idx_clone_status` (`clone_status`),
    INDEX `idx_parse_status` (`parse_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='代码仓库表（MVP简化版）';

-- =============================================
-- 表2：code_analysis_cache（分析结果缓存）
-- =============================================

CREATE TABLE IF NOT EXISTS `code_analysis_cache` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `repository_id` INT NOT NULL,
    `cache_type` VARCHAR(50) NOT NULL COMMENT '缓存类型: structure/dependencies/summary/qa',
    `cache_key` VARCHAR(255) NOT NULL COMMENT '缓存键（如文件路径、问题hash）',
    `cache_data` JSON NOT NULL COMMENT '缓存数据',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `expires_at` DATETIME COMMENT '过期时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_repo_cache` (`repository_id`, `cache_type`, `cache_key`),
    INDEX `idx_repository_id` (`repository_id`),
    INDEX `idx_cache_type` (`cache_type`),
    INDEX `idx_expires_at` (`expires_at`),
    
    FOREIGN KEY (`repository_id`) REFERENCES `code_repositories`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='代码分析结果缓存表';

-- =============================================
-- 索引优化说明
-- =============================================
-- 1. uk_repo_name: 防止重复导入相同仓库
-- 2. idx_clone_status: 查询特定状态的仓库
-- 3. idx_parse_status: 查询解析状态
-- 4. uk_repo_cache: 防止重复缓存相同的分析结果
-- 5. idx_expires_at: 定期清理过期缓存

-- =============================================
-- 完成标记
-- =============================================
-- Migration completed: 2026-01-12
-- MVP Version: 1.0
