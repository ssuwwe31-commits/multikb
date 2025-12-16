-- Migration: diagnosis reasoning iterations and memories
USE `spx_knowledge`;

-- diagnosis iterations table
CREATE TABLE IF NOT EXISTS `diagnosis_iterations` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '迭代ID',
    `diagnosis_id` INT NOT NULL COMMENT '所属诊断记录',
    `iteration_no` INT NOT NULL COMMENT '迭代序号',
    `stage` VARCHAR(64) NULL COMMENT '迭代阶段',
    `status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT '迭代状态',
    `reasoning_prompt` TEXT NULL COMMENT '推理提示',
    `reasoning_summary` TEXT NULL COMMENT '推理摘要',
    `reasoning_output` JSON NULL COMMENT '推理原始输出',
    `action_plan` JSON NULL COMMENT '执行计划',
    `action_result` JSON NULL COMMENT '执行结果',
    `metadata` JSON NULL COMMENT '扩展信息',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_diagnosis_iteration` (`diagnosis_id`, `iteration_no`),
    KEY `idx_iteration_diagnosis` (`diagnosis_id`, `status`),
    CONSTRAINT `fk_iteration_diagnosis` FOREIGN KEY (`diagnosis_id`)
        REFERENCES `diagnosis_records` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='诊断迭代记录';

-- diagnosis memories table
CREATE TABLE IF NOT EXISTS `diagnosis_memories` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '记忆ID',
    `diagnosis_id` INT NOT NULL COMMENT '所属诊断记录',
    `iteration_id` INT NULL COMMENT '关联迭代ID',
    `iteration_no` INT NULL COMMENT '迭代序号',
    `memory_type` VARCHAR(32) NOT NULL COMMENT '记忆类型: symptom|metric|log|fact|hypothesis|conclusion|action|feedback',
    `summary` TEXT NULL COMMENT '摘要',
    `content` JSON NULL COMMENT '内容详情',
    `metadata` JSON NULL COMMENT '附加信息',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_memory_diagnosis` (`diagnosis_id`, `memory_type`),
    KEY `idx_memory_iteration` (`iteration_id`),
    CONSTRAINT `fk_memory_diagnosis` FOREIGN KEY (`diagnosis_id`)
        REFERENCES `diagnosis_records` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_memory_iteration` FOREIGN KEY (`iteration_id`)
        REFERENCES `diagnosis_iterations` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='诊断上下文记忆';
