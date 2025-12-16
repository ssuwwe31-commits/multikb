-- 为历史数据设置安全扫描字段的默认值
-- 历史数据由于在添加安全扫描功能之前上传，无法进行扫描
-- 因此设置为 'pending' 状态和 'none' 方法

UPDATE `documents` 
SET 
    `security_scan_status` = 'pending',
    `security_scan_method` = 'none',
    `security_scan_result` = JSON_OBJECT(
        'virus_scan', NULL,
        'script_scan', NULL,
        'threats_found', JSON_ARRAY(),
        'scan_timestamp', NULL,
        'is_historical_data', true
    ),
    `security_scan_timestamp` = NULL
WHERE 
    `security_scan_status` IS NULL 
    OR `security_scan_status` = 'pending'
    AND (`security_scan_method` IS NULL OR `security_scan_method` = 'none')
    AND `security_scan_result` IS NULL;
