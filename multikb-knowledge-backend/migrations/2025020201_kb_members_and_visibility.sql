-- 创建知识库成员表 & 为知识库增加 visibility 字段

CREATE TABLE IF NOT EXISTS `knowledge_base_members` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `knowledge_base_id` INT NOT NULL COMMENT '知识库ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `role` VARCHAR(20) NOT NULL DEFAULT 'viewer' COMMENT '角色: owner/viewer/editor/admin',
    `invited_by` INT NULL COMMENT '邀请人ID',
    `invited_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '邀请时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_kb_member` (`knowledge_base_id`, `user_id`),
    CONSTRAINT `fk_kb_member_kb` FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_kb_member_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) COMMENT='知识库成员表';

-- 为 knowledge_bases 增加 visibility 字段（若不存在）
-- MySQL 不支持 IF NOT EXISTS，使用存储过程检查
SET @dbname = DATABASE();
SET @tablename = 'knowledge_bases';
SET @columnname = 'visibility';
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (COLUMN_NAME = @columnname)
    ) > 0,
    'SELECT 1 AS result',
    CONCAT('ALTER TABLE `', @tablename, '` ADD COLUMN `', @columnname, '` VARCHAR(20) NOT NULL DEFAULT ''private'' COMMENT ''可见性: private/shared/public'' AFTER `user_id`;')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 为已有数据设置默认 visibility（兼容旧版本）
UPDATE `knowledge_bases`
SET `visibility` = 'private'
WHERE `visibility` IS NULL;

-- 回填已有知识库的 owner 成员记录（兼容旧版本）
-- 为每个已有知识库的 owner（user_id）创建一条成员记录
INSERT INTO `knowledge_base_members` (`knowledge_base_id`, `user_id`, `role`, `invited_by`, `invited_at`)
SELECT 
    `id` AS `knowledge_base_id`,
    `user_id`,
    'owner' AS `role`,
    `user_id` AS `invited_by`,
    `created_at` AS `invited_at`
FROM `knowledge_bases`
WHERE `is_deleted` = 0
  AND `user_id` IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM `knowledge_base_members` m
      WHERE m.`knowledge_base_id` = `knowledge_bases`.`id`
        AND m.`user_id` = `knowledge_bases`.`user_id`
  );
