-- 添加 is_deleted 字段到代码相关表
-- 日期: 2026-01-12
-- 描述: 为代码仓库相关表添加软删除标记字段，与 BaseModel 保持一致

-- 1. code_repositories 表
ALTER TABLE `code_repositories` 
ADD COLUMN `is_deleted` TINYINT(1) DEFAULT 0 COMMENT '是否已删除（软删除）' AFTER `updated_at`;

-- 2. code_files 表
ALTER TABLE `code_files` 
ADD COLUMN `is_deleted` TINYINT(1) DEFAULT 0 COMMENT '是否已删除（软删除）' AFTER `updated_at`;

-- 3. code_symbols 表
ALTER TABLE `code_symbols` 
ADD COLUMN `is_deleted` TINYINT(1) DEFAULT 0 COMMENT '是否已删除（软删除）' AFTER `updated_at`;

-- 4. code_dependencies 表
ALTER TABLE `code_dependencies` 
ADD COLUMN `is_deleted` TINYINT(1) DEFAULT 0 COMMENT '是否已删除（软删除）' AFTER `updated_at`;

-- 5. code_analysis_cache 表
ALTER TABLE `code_analysis_cache` 
ADD COLUMN `is_deleted` TINYINT(1) DEFAULT 0 COMMENT '是否已删除（软删除）' AFTER `expires_at`;

-- 6. code_kb_mappings 表
ALTER TABLE `code_kb_mappings` 
ADD COLUMN `is_deleted` TINYINT(1) DEFAULT 0 COMMENT '是否已删除（软删除）' AFTER `updated_at`;

-- 添加索引以优化软删除查询
ALTER TABLE `code_repositories` ADD INDEX `idx_is_deleted` (`is_deleted`);
ALTER TABLE `code_files` ADD INDEX `idx_is_deleted` (`is_deleted`);
ALTER TABLE `code_symbols` ADD INDEX `idx_is_deleted` (`is_deleted`);
