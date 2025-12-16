-- Migration: 为实体类型表添加 user_id 字段
-- 文件：migrations/2025120901_add_user_id_to_entity_types.sql
-- 创建日期：2025-12-09
-- 说明：支持用户创建属于自己的实体类型模板

USE `spx_knowledge`;

-- 为 entity_types 表添加 user_id 字段（如果不存在）
SET @dbname = DATABASE();
SET @tablename = 'entity_types';
SET @columnname = 'user_id';

SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (COLUMN_NAME = @columnname)
    ) > 0,
    'SELECT 1 AS result',
    CONCAT('ALTER TABLE `', @tablename, '` ADD COLUMN `', @columnname, '` INT NULL COMMENT ''创建用户ID（系统类型为NULL，用户自定义类型关联创建者）'' AFTER `is_enabled`;')
));

PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加索引
SET @indexname = 'idx_entity_type_user_id';
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (INDEX_NAME = @indexname)
    ) > 0,
    'SELECT 1 AS result',
    CONCAT('ALTER TABLE `', @tablename, '` ADD INDEX `', @indexname, '` (`user_id`);')
));

PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 添加外键约束
SET @constraintname = 'fk_entity_type_user';
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (CONSTRAINT_NAME = @constraintname)
    ) > 0,
    'SELECT 1 AS result',
    CONCAT('ALTER TABLE `', @tablename, '` ADD CONSTRAINT `', @constraintname, '` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;')
));

PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 为已有数据设置 user_id（系统类型保持 NULL，用户创建的类型需要手动关联）
-- 注意：这里不自动设置，因为无法区分哪些是用户创建的

