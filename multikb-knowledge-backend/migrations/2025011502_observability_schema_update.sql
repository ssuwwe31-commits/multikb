-- Migration: observability schema enhancement
USE `spx_knowledge`;

-- cluster_configs add credential reference column
ALTER TABLE `cluster_configs`
    ADD COLUMN `credential_ref` VARCHAR(255) NULL COMMENT '外部凭证引用' AFTER `log_password`;

-- resource_snapshots enhancements
ALTER TABLE `resource_snapshots`
    ADD COLUMN `resource_uid` VARCHAR(128) NOT NULL COMMENT '资源UID' AFTER `cluster_id`,
    ADD COLUMN `labels` JSON NULL COMMENT '资源标签' AFTER `resource_name`,
    ADD COLUMN `annotations` JSON NULL COMMENT '资源注解' AFTER `labels`,
    ADD COLUMN `spec` JSON NULL COMMENT '资源规格' AFTER `annotations`,
    ADD COLUMN `status` JSON NULL COMMENT '资源状态' AFTER `spec`,
    ADD COLUMN `resource_version` VARCHAR(64) NULL COMMENT '资源版本号' AFTER `status`,
    MODIFY COLUMN `resource_name` VARCHAR(255) NOT NULL COMMENT '资源名称';

ALTER TABLE `resource_snapshots`
    ADD UNIQUE INDEX `uk_snapshot_uid` (`cluster_id`, `resource_uid`);

-- diagnosis_records enhancements
ALTER TABLE `diagnosis_records`
    ADD COLUMN `symptoms` JSON NULL COMMENT '症状摘要' AFTER `trigger_payload`,
    ADD COLUMN `events` JSON NULL COMMENT '诊断事件时间线' AFTER `logs`,
    ADD COLUMN `feedback` JSON NULL COMMENT '用户反馈' AFTER `events`,
    ADD COLUMN `knowledge_source` VARCHAR(32) NULL COMMENT '知识来源' AFTER `recommendations`,
    MODIFY COLUMN `status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT '诊断状态: pending|pending_next|pending_human|running|completed|failed';

-- resource sync state table
CREATE TABLE IF NOT EXISTS `resource_sync_states` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `cluster_id` INT NOT NULL COMMENT '集群ID',
    `resource_type` VARCHAR(64) NOT NULL COMMENT '资源类型',
    `namespace` VARCHAR(255) NULL COMMENT '命名空间',
    `resource_version` VARCHAR(64) NULL COMMENT '最新资源版本',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_sync_state` (`cluster_id`, `resource_type`, `namespace`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资源同步状态';

-- resource events table
CREATE TABLE IF NOT EXISTS `resource_events` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '事件ID',
    `cluster_id` INT NOT NULL COMMENT '集群ID',
    `resource_type` VARCHAR(64) NOT NULL COMMENT '资源类型',
    `namespace` VARCHAR(255) NULL COMMENT '命名空间',
    `resource_uid` VARCHAR(128) NOT NULL COMMENT '资源UID',
    `event_type` VARCHAR(32) NOT NULL COMMENT '事件类型: created|updated|deleted',
    `diff` JSON NULL COMMENT '变更摘要',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_resource_event` (`cluster_id`, `resource_type`, `namespace`, `resource_uid`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资源变更事件';
