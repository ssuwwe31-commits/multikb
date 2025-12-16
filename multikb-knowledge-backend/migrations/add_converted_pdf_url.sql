-- 迁移脚本：为documents表添加converted_pdf_url字段
-- 用于存储DOCX等Office文档转换后的PDF文件路径（MinIO对象键）

-- 如果字段不存在，则添加
SET @dbname = DATABASE();
SET @tablename = "documents";
SET @columnname = "converted_pdf_url";
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE
            (table_name = @tablename)
            AND (table_schema = @dbname)
            AND (column_name = @columnname)
    ) > 0,
    "SELECT 'Column already exists.' AS result;",
    CONCAT("ALTER TABLE ", @tablename, " ADD COLUMN ", @columnname, " VARCHAR(500) COMMENT '转换后的PDF文件路径（MinIO对象键），用于预览' AFTER `file_path`;")
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;
