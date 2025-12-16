-- Migration: 修复 qa_sessions 表的 user_id 字段类型
-- 文件：migrations/2025012002_fix_qa_sessions_user_id.sql
-- 创建日期：2024-01-20

USE `spx_knowledge`;

-- 修复 qa_sessions 表的 user_id 字段类型（从 VARCHAR(100) 改为 INT）
-- 注意：如果表中已有数据，需要先处理数据迁移

-- 1. 检查并修改字段类型
SET @dbname = DATABASE();
SET @tablename = 'qa_sessions';
SET @columnname = 'user_id';

-- 检查当前字段类型
SET @current_type = (
    SELECT DATA_TYPE 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = @dbname 
    AND TABLE_NAME = @tablename 
    AND COLUMN_NAME = @columnname
);

-- 如果字段类型不是 INT，则修改
SET @preparedStatement = (SELECT IF(
    @current_type = 'varchar' OR @current_type = 'char' OR @current_type = 'text',
    CONCAT('ALTER TABLE `', @tablename, '` MODIFY COLUMN `', @columnname, '` INT NULL COMMENT ''用户ID'';'),
    'SELECT 1 AS result'
));
PREPARE alterIfNeeded FROM @preparedStatement;
EXECUTE alterIfNeeded;
DEALLOCATE PREPARE alterIfNeeded;

-- 2. 添加外键约束（如果不存在）
SET @constraintname = 'fk_qa_session_user';
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (CONSTRAINT_NAME = @constraintname)
    ) > 0,
    'SELECT 1 AS result',
    CONCAT('ALTER TABLE `', @tablename, '` ADD CONSTRAINT `', @constraintname, '` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;
