-- Migration: add observability support tables
-- Apply this migration after deploying code that references the new models.

USE `spx_knowledge`;

-- 1. 集群接入配置表
CREATE TABLE IF NOT EXISTS `cluster_configs` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '集群配置ID',
    `name` VARCHAR(128) NOT NULL COMMENT '集群名称',
    `description` TEXT COMMENT '描述',
    `api_server` VARCHAR(255) NOT NULL COMMENT 'Kubernetes API Server 地址',
    `auth_type` VARCHAR(32) NOT NULL DEFAULT 'token' COMMENT '认证方式: token|kubeconfig|basic',
    `auth_token` MEDIUMTEXT COMMENT 'Bearer Token',
    `kubeconfig` LONGTEXT COMMENT 'kubeconfig 内容（加密存储）',
    `client_cert` LONGTEXT COMMENT '客户端证书（PEM）',
    `client_key` LONGTEXT COMMENT '客户端私钥（PEM）',
    `ca_cert` LONGTEXT COMMENT 'CA 证书（PEM）',
    `verify_ssl` BOOLEAN DEFAULT TRUE COMMENT '是否校验证书',
    `prometheus_url` VARCHAR(255) COMMENT 'Prometheus 地址',
    `prometheus_auth_type` VARCHAR(32) DEFAULT 'none' COMMENT 'Prometheus 认证方式',
    `prometheus_username` VARCHAR(128) COMMENT 'Prometheus 用户名',
    `prometheus_password` MEDIUMTEXT COMMENT 'Prometheus 密码/Token',
    `log_system` VARCHAR(64) COMMENT '日志系统类型: elk|loki|custom',
    `log_endpoint` VARCHAR(255) COMMENT '日志系统入口地址',
    `log_auth_type` VARCHAR(32) DEFAULT 'none' COMMENT '日志系统认证方式',
    `log_username` VARCHAR(128) COMMENT '日志系统用户名',
    `log_password` MEDIUMTEXT COMMENT '日志系统密码/Token',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `last_health_status` VARCHAR(32) DEFAULT 'unknown' COMMENT '最近一次健康检查状态',
    `last_health_message` TEXT COMMENT '健康检查结果描述',
    `last_health_checked_at` DATETIME COMMENT '最近一次健康检查时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cluster_name` (`name`),
    INDEX `idx_cluster_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='集群接入配置表';

-- 2. 资源快照表
CREATE TABLE IF NOT EXISTS `resource_snapshots` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '快照ID',
    `cluster_id` INT NOT NULL COMMENT '所属集群',
    `resource_type` VARCHAR(64) NOT NULL COMMENT '资源类型: Pod/Node/Deployment 等',
    `namespace` VARCHAR(255) COMMENT '命名空间',
    `resource_name` VARCHAR(255) COMMENT '资源名称',
    `snapshot` JSON NOT NULL COMMENT '资源快照内容(JSON)',
    `collected_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_snapshot_cluster_resource` (`cluster_id`, `resource_type`, `namespace`, `resource_name`),
    CONSTRAINT `fk_snapshot_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `cluster_configs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Kubernetes 资源快照';

-- 3. 诊断记录表
CREATE TABLE IF NOT EXISTS `diagnosis_records` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '诊断记录ID',
    `cluster_id` INT NOT NULL COMMENT '所属集群',
    `namespace` VARCHAR(255) COMMENT '命名空间',
    `resource_type` VARCHAR(64) COMMENT '资源类型',
    `resource_name` VARCHAR(255) COMMENT '资源名称',
    `trigger_source` VARCHAR(32) DEFAULT 'manual' COMMENT '触发来源: alert|manual|schedule',
    `trigger_payload` JSON COMMENT '触发上下文',
    `status` VARCHAR(32) DEFAULT 'pending' COMMENT '诊断状态: pending|pending_next|pending_human|running|completed|failed',
    `summary` TEXT COMMENT '概述',
    `conclusion` TEXT COMMENT '诊断结论',
    `confidence` DECIMAL(5,2) DEFAULT NULL COMMENT '置信度(0-1)',
    `metrics` JSON COMMENT '关键指标数据',
    `logs` JSON COMMENT '关键日志片段',
    `recommendations` JSON COMMENT '建议动作/知识条目',
    `knowledge_refs` JSON COMMENT '关联知识库条目',
    `started_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    PRIMARY KEY (`id`),
    INDEX `idx_diag_cluster` (`cluster_id`, `status`),
    INDEX `idx_diag_resource` (`cluster_id`, `resource_type`, `resource_name`),
    CONSTRAINT `fk_diagnosis_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `cluster_configs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='运维诊断记录';

-- End of migration.
