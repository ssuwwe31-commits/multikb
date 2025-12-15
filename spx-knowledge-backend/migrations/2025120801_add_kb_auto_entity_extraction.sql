-- 添加知识库自动实体提取配置字段
-- 创建日期：2025-12-08
-- 说明：为知识库添加 enable_auto_entity_extraction 字段，用于控制是否自动提取实体

USE `spx_knowledge`;

-- ============================================
-- 添加 enable_auto_entity_extraction 字段
-- ============================================
ALTER TABLE `knowledge_bases`
ADD COLUMN `enable_auto_entity_extraction` BOOLEAN DEFAULT TRUE COMMENT '是否启用自动实体提取（知识库级别配置）' AFTER `enable_auto_tagging`;

-- 更新现有记录，默认启用自动实体提取
UPDATE `knowledge_bases` SET `enable_auto_entity_extraction` = TRUE WHERE `enable_auto_entity_extraction` IS NULL;

