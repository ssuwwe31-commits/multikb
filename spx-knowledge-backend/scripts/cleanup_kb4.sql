-- 清理知识库4的知识图谱数据
USE `spx_knowledge`;

-- 步骤1：删除实体-文档关联记录
DELETE FROM `knowledge_graph_entity_documents`
WHERE `entity_id` IN (
    SELECT `id` FROM `knowledge_graph_entities`
    WHERE `knowledge_base_id` = 4 AND `is_deleted` = FALSE
);

-- 步骤2：删除关系记录
DELETE FROM `knowledge_graph_relationships`
WHERE `knowledge_base_id` = 4 AND `is_deleted` = FALSE;

-- 步骤3：删除实体记录
DELETE FROM `knowledge_graph_entities`
WHERE `knowledge_base_id` = 4 AND `is_deleted` = FALSE;

-- 步骤4：删除提取任务记录
DELETE FROM `knowledge_graph_extraction_tasks`
WHERE `knowledge_base_id` = 4 AND `is_deleted` = FALSE;

-- 显示清理结果
SELECT '清理完成' AS status;

