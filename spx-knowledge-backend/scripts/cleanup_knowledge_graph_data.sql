-- ============================================
-- 知识图谱数据清理脚本
-- 用途：清理所有知识图谱相关数据，用于重新生成图数据库
-- 使用前请确保已备份数据！
-- ============================================

USE `spx_knowledge`;

-- ============================================
-- 清理选项说明
-- ============================================
-- 1. 清理所有知识库的数据（推荐用于完全重建）
-- 2. 清理指定知识库的数据（按知识库ID清理）

-- ============================================
-- 选项1：清理所有知识库的知识图谱数据
-- ============================================

-- 步骤1：清理实体-文档关联表（必须先清理，因为有外键依赖）
TRUNCATE TABLE `knowledge_graph_entity_documents`;

-- 步骤2：清理关系表（必须先清理，因为有外键依赖）
TRUNCATE TABLE `knowledge_graph_relationships`;

-- 步骤3：清理实体表
TRUNCATE TABLE `knowledge_graph_entities`;

-- 步骤4：清理提取任务表（可选，保留任务历史可以不清理）
-- TRUNCATE TABLE `knowledge_graph_extraction_tasks`;

-- ============================================
-- 选项2：清理指定知识库的数据（替换 {KB_ID} 为实际知识库ID）
-- ============================================

-- 设置知识库ID（示例：知识库ID=4）
-- SET @kb_id = 4;

-- 步骤1：删除指定知识库的实体-文档关联记录
-- DELETE FROM `knowledge_graph_entity_documents`
-- WHERE `entity_id` IN (
--     SELECT `id` FROM `knowledge_graph_entities`
--     WHERE `knowledge_base_id` = @kb_id
-- );

-- 步骤2：删除指定知识库的关系记录
-- DELETE FROM `knowledge_graph_relationships`
-- WHERE `knowledge_base_id` = @kb_id;

-- 步骤3：删除指定知识库的实体记录
-- DELETE FROM `knowledge_graph_entities`
-- WHERE `knowledge_base_id` = @kb_id;

-- 步骤4：删除指定知识库的提取任务（可选）
-- DELETE FROM `knowledge_graph_extraction_tasks`
-- WHERE `knowledge_base_id` = @kb_id;

-- ============================================
-- 选项3：逻辑删除（标记为已删除，不物理删除）
-- ============================================

-- UPDATE `knowledge_graph_entity_documents` 
-- SET `is_deleted` = TRUE
-- WHERE `entity_id` IN (
--     SELECT `id` FROM `knowledge_graph_entities`
--     WHERE `knowledge_base_id` = @kb_id AND `is_deleted` = FALSE
-- );

-- UPDATE `knowledge_graph_relationships`
-- SET `is_deleted` = TRUE, `nebula_synced` = FALSE
-- WHERE `knowledge_base_id` = @kb_id AND `is_deleted` = FALSE;

-- UPDATE `knowledge_graph_entities`
-- SET `is_deleted` = TRUE, `nebula_synced` = FALSE
-- WHERE `knowledge_base_id` = @kb_id AND `is_deleted` = FALSE;

-- UPDATE `knowledge_graph_extraction_tasks`
-- SET `is_deleted` = TRUE
-- WHERE `knowledge_base_id` = @kb_id AND `is_deleted` = FALSE;

-- ============================================
-- 清理后需要执行的NebulaGraph清理操作
-- ============================================
-- 1. 使用清理API：POST /api/knowledge-graph/cleanup/orphaned-data?knowledge_base_id={KB_ID}
-- 2. 或者手动删除NebulaGraph空间（如果完全重建）：
--    DROP SPACE IF EXISTS kb_{KB_ID};

