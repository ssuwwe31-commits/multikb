-- 为 code_analysis_cache 表添加 MinIO 支持
-- 创建日期：2026-01-19
-- 目的：支持将大文件存储到 MinIO，MySQL 只存储路径

-- 添加 MinIO 路径字段
ALTER TABLE `code_analysis_cache` 
ADD COLUMN `minio_path` VARCHAR(500) NULL COMMENT 'MinIO 对象路径（如果数据存储在 MinIO）' AFTER `cache_key`,
ADD COLUMN `file_size` BIGINT NULL COMMENT '文件大小（字节）' AFTER `minio_path`,
ADD COLUMN `is_compressed` BOOLEAN DEFAULT FALSE COMMENT '是否压缩' AFTER `file_size`;

-- 修改 cache_data 字段为可选（如果存储在 MinIO，此字段可以为 NULL）
ALTER TABLE `code_analysis_cache` 
MODIFY COLUMN `cache_data` JSON NULL COMMENT '缓存数据（小数据直接存储，大数据存储在 MinIO）';

-- 添加索引（可选，用于查询优化）
CREATE INDEX `idx_minio_path` ON `code_analysis_cache` (`minio_path`(255));

-- 完成标记
-- Migration completed: 2026-01-19
-- Version: 1.0
