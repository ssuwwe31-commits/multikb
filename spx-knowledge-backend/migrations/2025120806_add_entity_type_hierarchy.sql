-- 添加实体类型层级支持（最多3级分类）
-- 创建日期：2025-12-08
-- 说明：添加 parent_id 和 level 字段，支持实体类型的最多3级分类（level自动计算）

USE `spx_knowledge`;

-- ============================================
-- 1. 添加层级字段
-- ============================================
ALTER TABLE `entity_types`
ADD COLUMN `parent_id` INT NULL COMMENT '父类型ID（支持最多3级分类）' AFTER `is_enabled`,
ADD COLUMN `level` INT DEFAULT 1 COMMENT '层级深度（1=一级分类，2=二级分类，3=三级分类，最大3级，自动计算）' AFTER `parent_id`;

-- 添加外键约束
ALTER TABLE `entity_types`
ADD CONSTRAINT `fk_entity_type_parent` 
FOREIGN KEY (`parent_id`) REFERENCES `entity_types` (`id`) ON DELETE SET NULL;

-- 添加索引
ALTER TABLE `entity_types`
ADD INDEX `idx_parent` (`parent_id`),
ADD INDEX `idx_level` (`level`),
ADD INDEX `idx_parent_level` (`parent_id`, `level`);

-- ============================================
-- 2. 更新现有数据：设置默认层级为1
-- ============================================
UPDATE `entity_types` SET `level` = 1 WHERE `level` IS NULL OR `level` = 0;

-- ============================================
-- 3. 插入默认的一级分类实体类型
-- ============================================
INSERT INTO `entity_types` (`code`, `name`, `description`, `icon`, `color`, `tag_type`, `sort_order`, `is_system`, `is_enabled`, `parent_id`, `level`, `meta_data`) VALUES
('person', '人物', '个人、角色、用户等', 'user', '#FF6B6B', 'danger', 1, TRUE, TRUE, NULL, 1, '{"examples": ["张三", "Linus Torvalds"], "prompt_hint": "人物（如：张三、Linus Torvalds）"}'),
('location', '地点', '地理位置、场所、地址等', 'location', '#4ECDC4', 'success', 2, TRUE, TRUE, NULL, 1, '{"examples": ["北京", "GitHub"], "prompt_hint": "地点（如：北京、GitHub）"}'),
('concept', '概念', '抽象概念、理论、思想等', 'lightbulb', '#45B7D1', 'primary', 3, TRUE, TRUE, NULL, 1, '{"examples": ["异步编程", "面向对象"], "prompt_hint": "概念（如：异步编程、面向对象）"}'),
('product', '产品', '商品、服务、产品等', 'shopping', '#FFA07A', 'warning', 4, TRUE, TRUE, NULL, 1, '{"examples": ["MySQL", "Redis"], "prompt_hint": "产品（如：MySQL、Redis）"}'),
('technology', '技术', '技术、方法、技能等', 'cpu', '#98D8C8', 'info', 5, TRUE, TRUE, NULL, 1, '{"examples": ["Python", "FastAPI"], "prompt_hint": "技术（如：Python、FastAPI）"}'),
('event', '事件', '事件、活动、发生的事等', 'calendar', '#F7DC6F', '', 6, TRUE, TRUE, NULL, 1, '{"examples": ["Python 3.12发布"], "prompt_hint": "事件（如：Python 3.12发布）"}'),
('organization', '组织', '组织、机构、公司等', 'office-building', '#BB8FCE', 'success', 7, TRUE, TRUE, NULL, 1, '{"examples": ["Python Software Foundation"], "prompt_hint": "组织（如：Python Software Foundation）"}'),
('other', '其他', '其他未分类的实体', 'more', '#95A5A6', 'info', 8, TRUE, TRUE, NULL, 1, '{"examples": [], "prompt_hint": "其他"}')
ON DUPLICATE KEY UPDATE 
    `name`=VALUES(`name`), 
    `description`=VALUES(`description`),
    `level`=VALUES(`level`),
    `parent_id`=VALUES(`parent_id`);

-- ============================================
-- 4. 插入默认的二级分类实体类型（技术相关的子分类）
-- ============================================
-- 获取技术类型的ID（用于设置parent_id）
SET @technology_id = (SELECT `id` FROM `entity_types` WHERE `code` = 'technology' LIMIT 1);

-- 插入技术的二级分类
INSERT INTO `entity_types` (`code`, `name`, `description`, `icon`, `color`, `tag_type`, `sort_order`, `is_system`, `is_enabled`, `parent_id`, `level`, `meta_data`) VALUES
('programming_language', '编程语言', '编程语言，如：Python、Java、JavaScript等', 'code', '#4ECDC4', 'success', 1, TRUE, TRUE, @technology_id, 2, '{"examples": ["Python", "Java", "JavaScript"], "prompt_hint": "编程语言（如：Python、Java、JavaScript）"}'),
('framework', '框架', '软件开发框架，如：Django、Spring、React等', 'grid', '#45B7D1', 'primary', 2, TRUE, TRUE, @technology_id, 2, '{"examples": ["Django", "Spring", "React"], "prompt_hint": "框架（如：Django、Spring、React）"}'),
('library', '库', '软件库、工具库，如：NumPy、Pandas、Lodash等', 'collection', '#98D8C8', 'info', 3, TRUE, TRUE, @technology_id, 2, '{"examples": ["NumPy", "Pandas", "Lodash"], "prompt_hint": "库（如：NumPy、Pandas、Lodash）"}'),
('tool', '工具', '开发工具、软件工具，如：Git、Docker、VS Code等', 'tools', '#FFA07A', 'warning', 4, TRUE, TRUE, @technology_id, 2, '{"examples": ["Git", "Docker", "VS Code"], "prompt_hint": "工具（如：Git、Docker、VS Code）"}'),
('platform', '平台', '技术平台、云平台，如：AWS、Azure、Kubernetes等', 'platform', '#BB8FCE', 'success', 5, TRUE, TRUE, @technology_id, 2, '{"examples": ["AWS", "Azure", "Kubernetes"], "prompt_hint": "平台（如：AWS、Azure、Kubernetes）"}'),
('protocol', '协议', '网络协议、通信协议，如：HTTP、TCP/IP、WebSocket等', 'connection', '#F7DC6F', '', 6, TRUE, TRUE, @technology_id, 2, '{"examples": ["HTTP", "TCP/IP", "WebSocket"], "prompt_hint": "协议（如：HTTP、TCP/IP、WebSocket）"}'),
('standard', '标准', '技术标准、规范，如：RESTful、GraphQL、OpenAPI等', 'document', '#95A5A6', 'info', 7, TRUE, TRUE, @technology_id, 2, '{"examples": ["RESTful", "GraphQL", "OpenAPI"], "prompt_hint": "标准（如：RESTful、GraphQL、OpenAPI）"}'),
('method', '方法', '技术方法、算法、设计模式等', 'lightbulb', '#FF6B6B', 'danger', 8, TRUE, TRUE, @technology_id, 2, '{"examples": ["设计模式", "算法", "最佳实践"], "prompt_hint": "方法（如：设计模式、算法、最佳实践）"}')
ON DUPLICATE KEY UPDATE 
    `name`=VALUES(`name`), 
    `description`=VALUES(`description`),
    `level`=VALUES(`level`),
    `parent_id`=VALUES(`parent_id`);

-- ============================================
-- 5. 插入其他一级分类的二级分类（可选）
-- ============================================

-- 产品的二级分类
SET @product_id = (SELECT `id` FROM `entity_types` WHERE `code` = 'product' LIMIT 1);
INSERT INTO `entity_types` (`code`, `name`, `description`, `icon`, `color`, `tag_type`, `sort_order`, `is_system`, `is_enabled`, `parent_id`, `level`, `meta_data`) VALUES
('software', '软件', '软件产品，如：MySQL、Redis、Nginx等', 'monitor', '#4ECDC4', 'success', 1, TRUE, TRUE, @product_id, 2, '{"examples": ["MySQL", "Redis", "Nginx"], "prompt_hint": "软件（如：MySQL、Redis、Nginx）"}'),
('service', '服务', '服务产品、SaaS服务等', 'service', '#45B7D1', 'primary', 2, TRUE, TRUE, @product_id, 2, '{"examples": ["AWS S3", "GitHub Actions"], "prompt_hint": "服务（如：AWS S3、GitHub Actions）"}')
ON DUPLICATE KEY UPDATE 
    `name`=VALUES(`name`), 
    `description`=VALUES(`description`),
    `level`=VALUES(`level`),
    `parent_id`=VALUES(`parent_id`);

-- 概念的二级分类
SET @concept_id = (SELECT `id` FROM `entity_types` WHERE `code` = 'concept' LIMIT 1);
INSERT INTO `entity_types` (`code`, `name`, `description`, `icon`, `color`, `tag_type`, `sort_order`, `is_system`, `is_enabled`, `parent_id`, `level`, `meta_data`) VALUES
('design_pattern', '设计模式', '设计模式、架构模式等', 'grid', '#4ECDC4', 'success', 1, TRUE, TRUE, @concept_id, 2, '{"examples": ["单例模式", "工厂模式"], "prompt_hint": "设计模式（如：单例模式、工厂模式）"}'),
('principle', '原则', '设计原则、开发原则等', 'document', '#45B7D1', 'primary', 2, TRUE, TRUE, @concept_id, 2, '{"examples": ["SOLID原则", "DRY原则"], "prompt_hint": "原则（如：SOLID原则、DRY原则）"}')
ON DUPLICATE KEY UPDATE 
    `name`=VALUES(`name`), 
    `description`=VALUES(`description`),
    `level`=VALUES(`level`),
    `parent_id`=VALUES(`parent_id`);

