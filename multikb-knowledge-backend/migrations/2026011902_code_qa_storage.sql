-- ============================================
-- 代码问答数据存储表
-- 创建日期: 2026-01-19
-- ============================================

-- 1. 代码问答会话表
CREATE TABLE IF NOT EXISTS `code_qa_sessions` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '会话ID',
    `session_id` VARCHAR(100) NOT NULL UNIQUE COMMENT '会话UUID',
    `session_name` VARCHAR(200) COMMENT '会话名称（用户可编辑）',
    `repository_id` INT NOT NULL COMMENT '代码仓库ID',
    `user_id` VARCHAR(100) COMMENT '用户ID（可选）',
    `question_count` INT DEFAULT 0 COMMENT '问题数量',
    `last_question` VARCHAR(500) COMMENT '最后问题（摘要）',
    `last_answer_summary` VARCHAR(500) COMMENT '最后答案摘要',
    `last_activity_time` DATETIME COMMENT '最后活动时间',
    `status` VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/inactive/deleted',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_session_id` (`session_id`),
    INDEX `idx_qa_session_repo_id` (`repository_id`),
    INDEX `idx_qa_session_user_id` (`user_id`),
    INDEX `idx_qa_session_activity_time` (`last_activity_time`),
    INDEX `idx_qa_session_status` (`status`),
    FOREIGN KEY (`repository_id`) REFERENCES `code_repositories`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='代码问答会话表';

-- 2. 代码问答记录表
CREATE TABLE IF NOT EXISTS `code_qa_records` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
    `record_id` VARCHAR(100) NOT NULL UNIQUE COMMENT '记录UUID',
    `session_id` VARCHAR(100) NOT NULL COMMENT '会话ID',
    `repository_id` INT NOT NULL COMMENT '代码仓库ID（冗余，便于查询）',
    `question_summary` VARCHAR(500) NOT NULL COMMENT '问题摘要（前500字符）',
    `answer_summary` VARCHAR(500) COMMENT '答案摘要（前500字符）',
    `opensearch_doc_id` VARCHAR(100) COMMENT 'OpenSearch 文档ID',
    `source_count` INT DEFAULT 0 COMMENT '来源文件数量',
    `sources` JSON COMMENT '来源文件列表（JSON数组，存储文件路径）',
    `question_type` VARCHAR(50) COMMENT '问题类型：general/call_chain/architecture/diagram等',
    `processing_time` FLOAT COMMENT '处理时间（秒）',
    `token_usage` INT COMMENT 'Token使用量',
    `has_mermaid` BOOLEAN DEFAULT FALSE COMMENT '答案是否包含流程图',
    `has_code_snippets` BOOLEAN DEFAULT FALSE COMMENT '答案是否包含代码片段',
    `user_feedback` JSON COMMENT '用户反馈JSON（点赞/点踩/评分）',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_record_id` (`record_id`),
    INDEX `idx_qa_record_session_id` (`session_id`),
    INDEX `idx_qa_record_repo_id` (`repository_id`),
    INDEX `idx_qa_record_created_at` (`created_at`),
    INDEX `idx_qa_record_question_type` (`question_type`),
    FOREIGN KEY (`session_id`) REFERENCES `code_qa_sessions`(`session_id`) ON DELETE CASCADE,
    FOREIGN KEY (`repository_id`) REFERENCES `code_repositories`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='代码问答记录表';
