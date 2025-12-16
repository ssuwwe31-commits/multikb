-- 为知识库添加自动标签配置字段
-- 创建时间: 2025-01-28

USE `spx_knowledge`;

-- 为 knowledge_bases 表添加 enable_auto_tagging 字段
ALTER TABLE `knowledge_bases` 
ADD COLUMN `enable_auto_tagging` BOOLEAN DEFAULT TRUE COMMENT '是否启用自动标签/摘要（知识库级别配置）' AFTER `is_active`;

-- 更新现有知识库，默认启用自动标签
UPDATE `knowledge_bases` 
SET `enable_auto_tagging` = TRUE 
WHERE `enable_auto_tagging` IS NULL;
