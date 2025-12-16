-- 添加安全扫描相关字段到 documents 表
-- 用于记录 ClamAV 扫描结果和状态

ALTER TABLE `documents` 
ADD COLUMN `security_scan_status` VARCHAR(50) DEFAULT 'pending' COMMENT '安全扫描状态: pending(待扫描), scanning(扫描中), safe(安全), infected(感染), error(错误), skipped(跳过)' AFTER `status`,
ADD COLUMN `security_scan_method` VARCHAR(50) COMMENT '扫描方法: clamav(ClamAV扫描), pattern_only(仅模式匹配), none(未扫描)' AFTER `security_scan_status`,
ADD COLUMN `security_scan_result` JSON COMMENT '安全扫描结果JSON: {virus_scan: {...}, script_scan: {...}, threats: [...], scan_timestamp: "..."}' AFTER `security_scan_method`,
ADD COLUMN `security_scan_timestamp` DATETIME COMMENT '安全扫描时间' AFTER `security_scan_result`;

-- 添加索引以便查询
CREATE INDEX `idx_doc_security_scan_status` ON `documents` (`security_scan_status`);
