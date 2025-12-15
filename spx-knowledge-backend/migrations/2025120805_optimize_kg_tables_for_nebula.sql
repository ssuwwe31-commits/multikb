-- 优化知识图谱表结构，适配NebulaGraph优先存储策略
-- 创建日期：2025-12-08
-- 说明：MySQL表仅存储索引信息，完整数据优先存储在NebulaGraph

USE `spx_knowledge`;

-- ============================================
-- 1. 优化实体表：更新字段注释，明确用途
-- ============================================

-- 更新表注释
ALTER TABLE `knowledge_graph_entities` 
COMMENT='知识图谱实体表（索引存储，完整数据优先存储在NebulaGraph）';

-- 更新字段注释，明确哪些字段仅用于索引
ALTER TABLE `knowledge_graph_entities`
MODIFY COLUMN `description` TEXT COMMENT '实体描述（索引字段，完整数据在NebulaGraph，可为空）',
MODIFY COLUMN `aliases` JSON COMMENT '实体别名列表（索引字段，完整数据在NebulaGraph，可为空）',
MODIFY COLUMN `confidence` FLOAT DEFAULT 0.7 COMMENT '置信度分数（0-1），用于排序和筛选',
MODIFY COLUMN `metadata` JSON COMMENT '扩展元数据（索引字段，完整数据在NebulaGraph，可为空）',
MODIFY COLUMN `nebula_synced` BOOLEAN DEFAULT FALSE COMMENT '是否已同步到NebulaGraph（true=数据在NebulaGraph，false=数据在MySQL）',
MODIFY COLUMN `nebula_synced_at` DATETIME COMMENT '同步到NebulaGraph的时间',
MODIFY COLUMN `nebula_sync_error` TEXT COMMENT '同步错误信息（如果同步失败）';

-- ============================================
-- 2. 优化关系表：更新字段注释，明确用途
-- ============================================

-- 更新表注释
ALTER TABLE `knowledge_graph_relationships` 
COMMENT='知识图谱关系表（索引存储，完整数据优先存储在NebulaGraph）';

-- 更新字段注释
ALTER TABLE `knowledge_graph_relationships`
MODIFY COLUMN `description` TEXT COMMENT '关系描述（索引字段，完整数据在NebulaGraph，可为空）',
MODIFY COLUMN `weight` FLOAT DEFAULT 0.5 COMMENT '关系权重（0-1），用于排序和筛选',
MODIFY COLUMN `confidence` FLOAT DEFAULT 0.7 COMMENT '置信度分数（0-1），用于排序和筛选',
MODIFY COLUMN `metadata` JSON COMMENT '扩展元数据（索引字段，完整数据在NebulaGraph，可为空）',
MODIFY COLUMN `nebula_synced` BOOLEAN DEFAULT FALSE COMMENT '是否已同步到NebulaGraph（true=数据在NebulaGraph，false=数据在MySQL）',
MODIFY COLUMN `nebula_synced_at` DATETIME COMMENT '同步到NebulaGraph的时间',
MODIFY COLUMN `nebula_sync_error` TEXT COMMENT '同步错误信息（如果同步失败）';

-- ============================================
-- 3. 添加存储位置标记字段（可选，用于追踪数据存储位置）
-- ============================================

-- 检查是否已有 stored_in 字段（在metadata中）
-- 如果需要在metadata外单独标记，可以添加：
-- ALTER TABLE `knowledge_graph_entities` 
-- ADD COLUMN `stored_in` VARCHAR(20) DEFAULT 'mysql' COMMENT '数据存储位置: nebula/mysql' AFTER `nebula_synced`;

-- ALTER TABLE `knowledge_graph_relationships` 
-- ADD COLUMN `stored_in` VARCHAR(20) DEFAULT 'mysql' COMMENT '数据存储位置: nebula/mysql' AFTER `nebula_synced`;

-- ============================================
-- 4. 优化索引：确保索引覆盖常用查询场景
-- ============================================

-- 实体表索引已足够，无需修改
-- 关系表索引已足够，无需修改

-- ============================================
-- 5. 数据迁移说明（可选）
-- ============================================

-- 如果已有数据，可以运行以下查询来标记数据存储位置：
-- UPDATE `knowledge_graph_entities` 
-- SET `metadata` = JSON_SET(COALESCE(`metadata`, '{}'), '$.stored_in', 'mysql')
-- WHERE `nebula_synced` = FALSE OR `nebula_synced` IS NULL;

-- UPDATE `knowledge_graph_entities` 
-- SET `metadata` = JSON_SET(COALESCE(`metadata`, '{}'), '$.stored_in', 'nebula')
-- WHERE `nebula_synced` = TRUE;

