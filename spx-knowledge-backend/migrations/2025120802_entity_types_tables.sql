-- 实体类型动态配置管理相关表
-- 创建日期：2025-12-08
-- 说明：创建实体类型配置表和知识库实体类型关联表，支持动态管理实体类型

USE `spx_knowledge`;

-- ============================================
-- 1. 实体类型配置表
-- ============================================
CREATE TABLE IF NOT EXISTS `entity_types` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `code` VARCHAR(50) NOT NULL COMMENT '类型代码（唯一标识，如：person、location）',
    `name` VARCHAR(100) NOT NULL COMMENT '类型名称（中文标签，如：人物、地点）',
    `description` TEXT COMMENT '类型描述',
    `icon` VARCHAR(100) COMMENT '图标名称或URL',
    `color` VARCHAR(20) COMMENT '颜色代码（如：#FF6B6B）',
    `tag_type` VARCHAR(20) COMMENT '标签类型（用于前端显示，如：danger、success、primary）',
    `sort_order` INT DEFAULT 0 COMMENT '排序顺序（数字越小越靠前）',
    `is_system` BOOLEAN DEFAULT FALSE COMMENT '是否系统内置类型（系统类型不可删除）',
    `is_enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `meta_data` JSON COMMENT '扩展元数据（如：提取提示词、示例等）',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `is_deleted` BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    UNIQUE KEY `uk_code` (`code`),
    INDEX `idx_enabled` (`is_enabled`, `is_deleted`),
    INDEX `idx_sort` (`sort_order`, `is_enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实体类型配置表';

-- ============================================
-- 2. 知识库实体类型关联表
-- ============================================
CREATE TABLE IF NOT EXISTS `knowledge_base_entity_types` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `knowledge_base_id` INT NOT NULL COMMENT '知识库ID',
    `entity_type_id` INT NOT NULL COMMENT '实体类型ID',
    `is_enabled` BOOLEAN DEFAULT TRUE COMMENT '是否在该知识库中启用',
    `sort_order` INT DEFAULT 0 COMMENT '在该知识库中的排序顺序',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_kb_type` (`knowledge_base_id`, `entity_type_id`),
    INDEX `idx_kb` (`knowledge_base_id`, `is_enabled`),
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`entity_type_id`) REFERENCES `entity_types` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库实体类型关联表（支持知识库级别的类型配置）';

-- ============================================
-- 3. 插入默认实体类型数据
-- ============================================
INSERT INTO `entity_types` (`code`, `name`, `description`, `icon`, `color`, `tag_type`, `sort_order`, `is_system`, `is_enabled`, `meta_data`) VALUES
('person', '人物', '个人、角色、用户等', 'user', '#FF6B6B', 'danger', 1, TRUE, TRUE, '{"examples": ["张三", "Linus Torvalds"], "prompt_hint": "人物（如：张三、Linus Torvalds）"}'),
('location', '地点', '地理位置、场所、地址等', 'location', '#4ECDC4', 'success', 2, TRUE, TRUE, '{"examples": ["北京", "GitHub"], "prompt_hint": "地点（如：北京、GitHub）"}'),
('concept', '概念', '抽象概念、理论、思想等', 'lightbulb', '#45B7D1', 'primary', 3, TRUE, TRUE, '{"examples": ["异步编程", "面向对象"], "prompt_hint": "概念（如：异步编程、面向对象）"}'),
('product', '产品', '商品、服务、产品等', 'shopping', '#FFA07A', 'warning', 4, TRUE, TRUE, '{"examples": ["MySQL", "Redis"], "prompt_hint": "产品（如：MySQL、Redis）"}'),
('technology', '技术', '技术、方法、技能等', 'cpu', '#98D8C8', 'info', 5, TRUE, TRUE, '{"examples": ["Python", "FastAPI"], "prompt_hint": "技术（如：Python、FastAPI）"}'),
('event', '事件', '事件、活动、发生的事等', 'calendar', '#F7DC6F', '', 6, TRUE, TRUE, '{"examples": ["Python 3.12发布"], "prompt_hint": "事件（如：Python 3.12发布）"}'),
('organization', '组织', '组织、机构、公司等', 'office-building', '#BB8FCE', 'success', 7, TRUE, TRUE, '{"examples": ["Python Software Foundation"], "prompt_hint": "组织（如：Python Software Foundation）"}'),
('other', '其他', '其他未分类的实体', 'more', '#95A5A6', 'info', 8, TRUE, TRUE, '{"examples": [], "prompt_hint": "其他"}')
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `description`=VALUES(`description`);

-- ============================================
-- 4. 更新现有实体表的type字段注释（可选）
-- ============================================
ALTER TABLE `knowledge_graph_entities` 
MODIFY COLUMN `type` VARCHAR(50) NOT NULL COMMENT '实体类型（关联entity_types表的code字段）';

