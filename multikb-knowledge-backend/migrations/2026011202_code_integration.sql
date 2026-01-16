-- ============================================
-- 代码库深度集成迁移脚本
-- 版本：v2.0
-- 日期：2026-01-12
-- 说明：将代码分析功能深度集成到知识库系统
-- ============================================

-- ============================================
-- 第一步：扩展现有表（不影响现有数据）
-- ============================================

-- 扩展 code_repositories 表，添加知识库关联
ALTER TABLE `code_repositories` 
ADD COLUMN `knowledge_base_id` INT NULL COMMENT '关联的知识库ID（可选）' AFTER `id`,
ADD COLUMN `kb_document_id` INT NULL COMMENT '对应的知识库文档ID（自动创建）' AFTER `knowledge_base_id`,
ADD COLUMN `description` TEXT COMMENT '仓库描述' AFTER `repo_name`,
ADD COLUMN `readme_content` LONGTEXT COMMENT 'README内容' AFTER `description`,
ADD COLUMN `tags` JSON COMMENT '标签' AFTER `readme_content`,
ADD COLUMN `visibility` ENUM('public', 'private', 'internal') DEFAULT 'private' COMMENT '可见性' AFTER `tags`;

-- 添加索引
ALTER TABLE `code_repositories`
ADD INDEX `idx_kb` (`knowledge_base_id`);

-- 添加外键约束（删除知识库时，代码仓库保留但解除关联）
ALTER TABLE `code_repositories`
ADD CONSTRAINT `fk_code_repo_kb` 
    FOREIGN KEY (`knowledge_base_id`) 
    REFERENCES `knowledge_bases` (`id`) 
    ON DELETE SET NULL;

-- ============================================
-- 第二步：创建新表
-- ============================================

-- 表1：code_files（代码文件表）
CREATE TABLE IF NOT EXISTS `code_files` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '文件ID',
    `repository_id` INT NOT NULL COMMENT '仓库ID',
    `knowledge_base_id` INT NULL COMMENT '知识库ID（冗余，便于查询）',
    
    -- 文件信息
    `file_path` VARCHAR(1000) NOT NULL COMMENT '文件路径（相对路径）',
    `file_name` VARCHAR(255) NOT NULL COMMENT '文件名',
    `file_type` VARCHAR(50) COMMENT '文件类型',
    `language` VARCHAR(50) COMMENT '编程语言',
    
    -- 内容信息
    `content_hash` VARCHAR(64) COMMENT 'SHA256哈希（用于检测变更）',
    `lines_of_code` INT COMMENT '代码行数',
    `file_size` BIGINT COMMENT '文件大小（字节）',
    
    -- 分析结果
    `symbols_count` INT DEFAULT 0 COMMENT '符号数量',
    `imports_count` INT DEFAULT 0 COMMENT '导入数量',
    `complexity_score` FLOAT COMMENT '平均复杂度',
    
    -- 向量化
    `opensearch_doc_id` VARCHAR(100) COMMENT 'OpenSearch文档ID',
    `vector_indexed` BOOLEAN DEFAULT FALSE COMMENT '是否已向量化',
    `vector_updated_at` DATETIME COMMENT '向量更新时间',
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` BOOLEAN DEFAULT FALSE,
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_repo_path` (`repository_id`, `file_path`(255)),
    INDEX `idx_kb` (`knowledge_base_id`),
    INDEX `idx_language` (`language`),
    INDEX `idx_vector_indexed` (`vector_indexed`),
    INDEX `idx_hash` (`content_hash`),
    CONSTRAINT `fk_file_repo` 
        FOREIGN KEY (`repository_id`) 
        REFERENCES `code_repositories` (`id`) 
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='代码文件表';

-- 表2：code_symbols（代码符号表：函数、类等）
CREATE TABLE IF NOT EXISTS `code_symbols` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '符号ID',
    `file_id` INT NOT NULL COMMENT '文件ID',
    `repository_id` INT NOT NULL COMMENT '仓库ID（冗余）',
    `knowledge_base_id` INT NULL COMMENT '知识库ID（冗余）',
    
    -- 符号信息
    `symbol_type` VARCHAR(50) NOT NULL COMMENT '符号类型: function/class/method/variable',
    `symbol_name` VARCHAR(255) NOT NULL COMMENT '符号名称',
    `qualified_name` VARCHAR(500) COMMENT '完整限定名',
    `signature` TEXT COMMENT '函数签名/类声明',
    
    -- 位置信息
    `start_line` INT COMMENT '起始行号',
    `end_line` INT COMMENT '结束行号',
    
    -- 文档
    `docstring` TEXT COMMENT '文档字符串',
    `parameters` JSON COMMENT '参数列表',
    `return_type` VARCHAR(100) COMMENT '返回类型',
    
    -- 关系
    `parent_symbol_id` INT NULL COMMENT '父符号ID',
    `modifiers` JSON COMMENT '修饰符（public/private/static）',
    
    -- 复杂度
    `complexity_score` FLOAT COMMENT '圈复杂度',
    `lines_count` INT COMMENT '代码行数',
    
    -- 向量化
    `opensearch_doc_id` VARCHAR(100) COMMENT 'OpenSearch文档ID',
    `vector_indexed` BOOLEAN DEFAULT FALSE,
    `vector_updated_at` DATETIME COMMENT '向量更新时间',
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` BOOLEAN DEFAULT FALSE,
    
    PRIMARY KEY (`id`),
    INDEX `idx_file` (`file_id`),
    INDEX `idx_repo` (`repository_id`),
    INDEX `idx_kb` (`knowledge_base_id`),
    INDEX `idx_type` (`symbol_type`),
    INDEX `idx_name` (`symbol_name`),
    INDEX `idx_parent` (`parent_symbol_id`),
    INDEX `idx_vector_indexed` (`vector_indexed`),
    CONSTRAINT `fk_symbol_file` 
        FOREIGN KEY (`file_id`) 
        REFERENCES `code_files` (`id`) 
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='代码符号表（函数、类等）';

-- 表3：code_dependencies（代码依赖关系表）
CREATE TABLE IF NOT EXISTS `code_dependencies` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `repository_id` INT NOT NULL,
    
    -- 源和目标
    `source_file_id` INT NOT NULL COMMENT '源文件ID',
    `source_symbol_id` INT NULL COMMENT '源符号ID（可选）',
    `target_file_id` INT NOT NULL COMMENT '目标文件ID',
    `target_symbol_id` INT NULL COMMENT '目标符号ID（可选）',
    
    -- 依赖信息
    `dependency_type` VARCHAR(50) NOT NULL COMMENT 'import/call/inherit/implement/reference',
    `import_statement` TEXT COMMENT 'import语句原文',
    `line_number` INT COMMENT '行号',
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_deleted` BOOLEAN DEFAULT FALSE,
    
    PRIMARY KEY (`id`),
    INDEX `idx_repo` (`repository_id`),
    INDEX `idx_source_file` (`source_file_id`),
    INDEX `idx_target_file` (`target_file_id`),
    INDEX `idx_dep_type` (`dependency_type`),
    CONSTRAINT `fk_dep_source` 
        FOREIGN KEY (`source_file_id`) 
        REFERENCES `code_files` (`id`) 
        ON DELETE CASCADE,
    CONSTRAINT `fk_dep_target` 
        FOREIGN KEY (`target_file_id`) 
        REFERENCES `code_files` (`id`) 
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='代码依赖关系表';

-- 表4：code_kb_mappings（代码-文档映射表）
CREATE TABLE IF NOT EXISTS `code_kb_mappings` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `knowledge_base_id` INT NOT NULL COMMENT '知识库ID',
    `document_id` INT NULL COMMENT '文档ID',
    `code_file_id` INT NULL COMMENT '代码文件ID',
    `code_symbol_id` INT NULL COMMENT '代码符号ID',
    
    -- 映射类型
    `mapping_type` VARCHAR(50) NOT NULL COMMENT 'reference/implements/explains/example',
    `mapping_context` TEXT COMMENT '映射上下文（如：文档中引用代码的段落）',
    
    -- 双向关联强度
    `confidence_score` FLOAT DEFAULT 1.0 COMMENT '关联置信度',
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `created_by` INT COMMENT '创建用户ID',
    
    PRIMARY KEY (`id`),
    INDEX `idx_kb` (`knowledge_base_id`),
    INDEX `idx_doc` (`document_id`),
    INDEX `idx_code_file` (`code_file_id`),
    INDEX `idx_code_symbol` (`code_symbol_id`),
    INDEX `idx_mapping_type` (`mapping_type`),
    CONSTRAINT `fk_mapping_kb` 
        FOREIGN KEY (`knowledge_base_id`) 
        REFERENCES `knowledge_bases` (`id`) 
        ON DELETE CASCADE,
    CONSTRAINT `fk_mapping_doc` 
        FOREIGN KEY (`document_id`) 
        REFERENCES `documents` (`id`) 
        ON DELETE CASCADE,
    CONSTRAINT `fk_mapping_file` 
        FOREIGN KEY (`code_file_id`) 
        REFERENCES `code_files` (`id`) 
        ON DELETE CASCADE,
    CONSTRAINT `fk_mapping_symbol` 
        FOREIGN KEY (`code_symbol_id`) 
        REFERENCES `code_symbols` (`id`) 
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='代码与文档映射关系表';

-- ============================================
-- 第三步：数据迁移（可选）
-- ============================================

-- 注意：如果已有代码仓库数据，需要根据实际情况调整

-- 示例：为现有代码仓库创建默认知识库（如果需要）
-- INSERT INTO `knowledge_bases` (`kb_name`, `description`, `creator_id`, `is_public`)
-- SELECT 
--     CONCAT('代码库: ', repo_name),
--     CONCAT('自动创建的代码库知识库：', repo_url),
--     1, -- 系统用户
--     FALSE
-- FROM `code_repositories`
-- WHERE `knowledge_base_id` IS NULL;

-- 关联代码仓库到新创建的知识库（如果需要）
-- UPDATE `code_repositories` cr
-- JOIN `knowledge_bases` kb ON kb.kb_name = CONCAT('代码库: ', cr.repo_name)
-- SET cr.knowledge_base_id = kb.id
-- WHERE cr.knowledge_base_id IS NULL;

-- ============================================
-- 完成！
-- ============================================

-- 验证查询
SELECT 'Migration completed successfully!' AS status;

-- 显示新增表
SELECT 
    TABLE_NAME, 
    TABLE_ROWS, 
    CREATE_TIME,
    TABLE_COMMENT
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME IN ('code_files', 'code_symbols', 'code_dependencies', 'code_kb_mappings')
ORDER BY TABLE_NAME;

-- 显示 code_repositories 表的新字段
SELECT 
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'code_repositories'
  AND COLUMN_NAME IN ('knowledge_base_id', 'kb_document_id', 'description', 'readme_content', 'tags', 'visibility')
ORDER BY ORDINAL_POSITION;
