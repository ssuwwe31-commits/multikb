-- Migration: Fix resource_events table schema
-- Add missing updated_at and is_deleted columns to match BaseModel

USE `spx_knowledge`;

-- Add updated_at and is_deleted columns to resource_events
ALTER TABLE `resource_events`
    ADD COLUMN `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间' AFTER `created_at`,
    ADD COLUMN `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除' AFTER `updated_at`;

-- Update existing records to set is_deleted = false
UPDATE `resource_events` SET `is_deleted` = FALSE WHERE `is_deleted` IS NULL;
