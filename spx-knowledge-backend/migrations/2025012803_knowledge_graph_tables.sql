-- 知识图谱相关表
-- 创建日期：2025-01-28
-- 说明：创建知识图谱的实体表、关系表、关联表和任务表

USE `spx_knowledge`;

-- ============================================
-- 1. 知识图谱实体表
-- ============================================
CREATE TABLE IF NOT EXISTS `knowledge_graph_entities` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `knowledge_base_id` INT NOT NULL COMMENT '所属知识库ID',
    `user_id` INT NOT NULL COMMENT '创建用户ID',
    `name` VARCHAR(255) NOT NULL COMMENT '实体名称',
    `type` VARCHAR(50) NOT NULL COMMENT '实体类型: person/location/concept/product/technology/event/organization/other',
    `description` TEXT COMMENT '实体描述',
    `aliases` JSON COMMENT '实体别名列表，如: ["Python", "Python语言"]',
    `confidence` FLOAT DEFAULT 0.7 COMMENT '置信度分数（0-1），用于表示实体提取的可信度',
    `metadata` JSON COMMENT '扩展元数据，如: {"source": "doc_123", "extraction_method": "llm"}',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    `nebula_synced` BOOLEAN DEFAULT FALSE COMMENT '是否已同步到NebulaGraph',
    `nebula_synced_at` DATETIME COMMENT '同步到NebulaGraph的时间',
    `nebula_sync_error` TEXT COMMENT '同步错误信息（如果同步失败）',
    INDEX `idx_kb_name` (`knowledge_base_id`, `name`),
    INDEX `idx_type` (`type`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_is_deleted` (`is_deleted`),
    -- 组合索引优化：提高查询性能
    INDEX `idx_kb_deleted` (`knowledge_base_id`, `is_deleted`),
    INDEX `idx_type_deleted` (`type`, `is_deleted`),
    INDEX `idx_nebula_synced` (`nebula_synced`, `updated_at`) COMMENT '用于同步任务查询',
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    -- 唯一键约束：移除 is_deleted，避免逻辑删除后无法创建同名实体
    -- 注意：需要在应用层确保同一知识库下未删除的实体名称+类型唯一
    UNIQUE KEY `uk_kb_name_type` (`knowledge_base_id`, `name`, `type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识图谱实体表（主存储，用于列表查询、统计查询、关联查询）';

-- ============================================
-- 2. 知识图谱关系表
-- ============================================
CREATE TABLE IF NOT EXISTS `knowledge_graph_relationships` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `knowledge_base_id` INT NOT NULL COMMENT '所属知识库ID',
    `user_id` INT NOT NULL COMMENT '创建用户ID',
    `source_entity_id` INT NOT NULL COMMENT '源实体ID',
    `target_entity_id` INT NOT NULL COMMENT '目标实体ID',
    `relation_type` VARCHAR(50) NOT NULL COMMENT '关系类型: belongs_to/references/depends_on/compares/implements/related_to/part_of/has_part/created_by/occurs_in/other',
    `description` TEXT COMMENT '关系描述',
    `weight` FLOAT DEFAULT 0.5 COMMENT '关系权重（0-1），用于表示关系强度（基于共现频率、语义相似度等计算）',
    `confidence` FLOAT DEFAULT 0.7 COMMENT '置信度分数（0-1），用于表示关系提取的可信度',
    `metadata` JSON COMMENT '扩展元数据，如: {"source": "doc_123", "evidence": "文档片段", "extraction_method": "llm"}',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    `nebula_synced` BOOLEAN DEFAULT FALSE COMMENT '是否已同步到NebulaGraph',
    `nebula_synced_at` DATETIME COMMENT '同步到NebulaGraph的时间',
    `nebula_sync_error` TEXT COMMENT '同步错误信息（如果同步失败）',
    INDEX `idx_kb` (`knowledge_base_id`),
    INDEX `idx_source` (`source_entity_id`),
    INDEX `idx_target` (`target_entity_id`),
    INDEX `idx_relation_type` (`relation_type`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_is_deleted` (`is_deleted`),
    -- 组合索引优化：提高查询性能
    INDEX `idx_kb_deleted` (`knowledge_base_id`, `is_deleted`),
    INDEX `idx_source_deleted` (`source_entity_id`, `is_deleted`),
    INDEX `idx_target_deleted` (`target_entity_id`, `is_deleted`),
    INDEX `idx_nebula_synced` (`nebula_synced`, `updated_at`) COMMENT '用于同步任务查询',
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`source_entity_id`) REFERENCES `knowledge_graph_entities` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`target_entity_id`) REFERENCES `knowledge_graph_entities` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    -- 唯一键约束：移除 is_deleted，避免逻辑删除后无法创建同名关系
    -- 注意：需要在应用层确保未删除的关系唯一
    UNIQUE KEY `uk_source_target_relation` (`source_entity_id`, `target_entity_id`, `relation_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识图谱关系表（主存储，用于列表查询、统计查询）';

-- ============================================
-- 3. 实体-文档关联表
-- ============================================
CREATE TABLE IF NOT EXISTS `knowledge_graph_entity_documents` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `entity_id` INT NOT NULL COMMENT '实体ID',
    `document_id` INT NOT NULL COMMENT '文档ID',
    `chunk_id` INT COMMENT '文档块ID（可选）',
    `mentions_count` INT DEFAULT 1 COMMENT '提及次数',
    `first_mention_position` INT COMMENT '首次提及位置（字符偏移）',
    `metadata` JSON COMMENT '扩展元数据',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX `idx_entity` (`entity_id`),
    INDEX `idx_document` (`document_id`),
    INDEX `idx_chunk` (`chunk_id`),
    INDEX `idx_is_deleted` (`is_deleted`),
    FOREIGN KEY (`entity_id`) REFERENCES `knowledge_graph_entities` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`chunk_id`) REFERENCES `document_chunks` (`id`) ON DELETE SET NULL,
    UNIQUE KEY `uk_entity_document_chunk` (`entity_id`, `document_id`, `chunk_id`, `is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实体-文档关联表（记录实体在文档中的提及情况）';

-- ============================================
-- 4. 实体提取任务表
-- ============================================
CREATE TABLE IF NOT EXISTS `knowledge_graph_extraction_tasks` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `knowledge_base_id` INT NOT NULL COMMENT '知识库ID',
    `document_id` INT COMMENT '文档ID（可选，为空表示批量提取）',
    `status` VARCHAR(50) DEFAULT 'pending' COMMENT '状态: pending/processing/completed/failed',
    `total_entities` INT DEFAULT 0 COMMENT '提取的实体数量',
    `total_relationships` INT DEFAULT 0 COMMENT '提取的关系数量',
    `error_message` TEXT COMMENT '错误信息',
    `metadata` JSON COMMENT '扩展元数据',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX `idx_kb` (`knowledge_base_id`),
    INDEX `idx_document` (`document_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_is_deleted` (`is_deleted`),
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实体提取任务表';

