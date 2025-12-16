-- Migration: Fix resource_sync_states table schema
-- Add missing created_at and is_deleted columns to match BaseModel

USE `spx_knowledge`;

-- Add created_at and is_deleted columns to resource_sync_states
ALTER TABLE `resource_sync_states`
    ADD COLUMN `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间' AFTER `resource_version`,
    ADD COLUMN `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除' AFTER `created_at`;

-- Update existing records to set is_deleted = false
UPDATE `resource_sync_states` SET `is_deleted` = FALSE WHERE `is_deleted` IS NULL;
