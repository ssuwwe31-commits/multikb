-- 重命名 entity_types 表的 metadata 列为 meta_data
-- 创建日期：2025-12-08
-- 说明：修复 SQLAlchemy 保留属性冲突，将 metadata 列重命名为 meta_data
-- 注意：如果表不存在或列不存在，此脚本会报错，这是正常的（说明已经使用新结构）

USE `spx_knowledge`;

-- ============================================
-- 重命名列
-- ============================================
-- 如果 entity_types 表存在且包含 metadata 列，则重命名为 meta_data
-- 如果表或列不存在，说明已经使用新结构，可以忽略错误

ALTER TABLE `entity_types` 
CHANGE COLUMN `metadata` `meta_data` JSON COMMENT '扩展元数据（如：提取提示词、示例等）';

