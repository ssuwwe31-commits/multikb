-- 行业模板实体类型初始化
-- 创建日期：2025-12-08
-- 说明：创建行业模板中定义的行业特定实体类型

USE `spx_knowledge`;

-- ============================================
-- 技术文档行业特定类型
-- ============================================
INSERT INTO `entity_types` (`code`, `name`, `description`, `icon`, `color`, `tag_type`, `sort_order`, `is_system`, `is_enabled`, `meta_data`) VALUES
('framework', '框架', '软件开发框架', 'grid', '#4ECDC4', 'success', 10, FALSE, TRUE, '{"template": "technology", "prompt_hint": "框架（如：React、Vue、Django）"}'),
('standard', '标准', '技术标准、规范', 'document', '#45B7D1', 'primary', 11, FALSE, TRUE, '{"template": "technology", "prompt_hint": "标准（如：HTTP、REST、JSON）"}'),
('method', '方法', '技术方法、算法', 'tools', '#FFA07A', 'warning', 12, FALSE, TRUE, '{"template": "technology", "prompt_hint": "方法（如：敏捷开发、TDD）"}'),
('document', '文档', '技术文档、规范文档', 'document', '#95A5A6', 'info', 13, FALSE, TRUE, '{"template": "technology", "prompt_hint": "文档（如：API文档、设计文档）"}')
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `description`=VALUES(`description`);

-- ============================================
-- 医疗健康行业特定类型
-- ============================================
INSERT INTO `entity_types` (`code`, `name`, `description`, `icon`, `color`, `tag_type`, `sort_order`, `is_system`, `is_enabled`, `meta_data`) VALUES
('disease', '疾病', '疾病、病症', 'warning', '#FF6B6B', 'danger', 20, FALSE, TRUE, '{"template": "medical", "parent_type": "concept", "prompt_hint": "疾病（如：高血压、糖尿病）"}'),
('drug', '药物', '药品、药物', 'medicine-box', '#4ECDC4', 'success', 21, FALSE, TRUE, '{"template": "medical", "parent_type": "product", "prompt_hint": "药物（如：阿司匹林、青霉素）"}'),
('treatment', '治疗方法', '治疗方案、治疗方法', 'first-aid-kit', '#45B7D1', 'primary', 22, FALSE, TRUE, '{"template": "medical", "parent_type": "method", "prompt_hint": "治疗方法（如：手术治疗、药物治疗）"}')
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `description`=VALUES(`description`);

-- ============================================
-- 法律行业特定类型
-- ============================================
INSERT INTO `entity_types` (`code`, `name`, `description`, `icon`, `color`, `tag_type`, `sort_order`, `is_system`, `is_enabled`, `meta_data`) VALUES
('law', '法律', '法律法规、法律条文', 'document', '#4ECDC4', 'success', 30, FALSE, TRUE, '{"template": "legal", "parent_type": "document", "prompt_hint": "法律（如：民法典、刑法）"}'),
('case', '案例', '法律案例、判例', 'folder-opened', '#45B7D1', 'primary', 31, FALSE, TRUE, '{"template": "legal", "parent_type": "event", "prompt_hint": "案例（如：XX诉XX案）"}')
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `description`=VALUES(`description`);

-- ============================================
-- 金融行业特定类型
-- ============================================
INSERT INTO `entity_types` (`code`, `name`, `description`, `icon`, `color`, `tag_type`, `sort_order`, `is_system`, `is_enabled`, `meta_data`) VALUES
('financial_product', '金融产品', '金融产品、理财产品', 'wallet', '#4ECDC4', 'success', 40, FALSE, TRUE, '{"template": "finance", "parent_type": "product", "prompt_hint": "金融产品（如：股票、基金、保险）"}'),
('market', '市场', '金融市场、市场', 'trend-charts', '#45B7D1', 'primary', 41, FALSE, TRUE, '{"template": "finance", "parent_type": "concept", "prompt_hint": "市场（如：股票市场、债券市场）"}')
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `description`=VALUES(`description`);

-- ============================================
-- 教育行业特定类型
-- ============================================
INSERT INTO `entity_types` (`code`, `name`, `description`, `icon`, `color`, `tag_type`, `sort_order`, `is_system`, `is_enabled`, `meta_data`) VALUES
('course', '课程', '课程、课程内容', 'reading', '#4ECDC4', 'success', 50, FALSE, TRUE, '{"template": "education", "parent_type": "concept", "prompt_hint": "课程（如：高等数学、数据结构）"}'),
('subject', '学科', '学科、专业', 'notebook', '#45B7D1', 'primary', 51, FALSE, TRUE, '{"template": "education", "parent_type": "concept", "prompt_hint": "学科（如：计算机科学、数学）"}')
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `description`=VALUES(`description`);
