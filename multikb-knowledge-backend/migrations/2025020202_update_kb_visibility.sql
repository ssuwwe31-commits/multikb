-- 根据成员数量自动更新知识库的 visibility 字段
-- 如果有成员（除了owner），设置为 shared
-- 如果只有owner一个人，设置为 private

UPDATE `knowledge_bases` kb
SET `visibility` = CASE
    WHEN (
        SELECT COUNT(*) 
        FROM `knowledge_base_members` m 
        WHERE m.`knowledge_base_id` = kb.`id`
    ) > 1 THEN 'shared'
    ELSE 'private'
END
WHERE `is_deleted` = 0;
