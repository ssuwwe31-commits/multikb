-- Migration: 为文档目录表添加分块关联字段
-- 文件：migrations/2025012401_add_toc_chunk_link.sql
-- 创建日期：2025-01-24

USE `spx_knowledge`;

-- 添加字段用于关联目录项和分块
ALTER TABLE `document_toc` 
ADD COLUMN `element_index` INT COMMENT '元素索引（在文档中的位置）' AFTER `position`,
ADD COLUMN `paragraph_index` INT COMMENT '段落索引（Word文档）' AFTER `element_index`,
ADD COLUMN `start_chunk_id` INT COMMENT '起始分块ID（该目录项对应的第一个分块）' AFTER `paragraph_index`,
ADD INDEX `idx_element_index` (`document_id`, `element_index`),
ADD INDEX `idx_start_chunk` (`start_chunk_id`);
