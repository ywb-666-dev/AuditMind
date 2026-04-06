-- 添加 detection_records 表缺失的新字段
-- 这些字段用于支持智能解析引擎、IPO对标和整改建议功能

-- 检查并添加 risk_evidence_locations 字段
SET @column_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'detection_records'
    AND COLUMN_NAME = 'risk_evidence_locations'
);

SET @sql = IF(@column_exists = 0,
    'ALTER TABLE detection_records ADD COLUMN risk_evidence_locations JSON NULL COMMENT "风险证据定位"',
    'SELECT "Column risk_evidence_locations already exists" AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加 suspicious_segments 字段
SET @column_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'detection_records'
    AND COLUMN_NAME = 'suspicious_segments'
);

SET @sql = IF(@column_exists = 0,
    'ALTER TABLE detection_records ADD COLUMN suspicious_segments JSON NULL COMMENT "可疑文本片段"',
    'SELECT "Column suspicious_segments already exists" AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加 ipo_comparison_results 字段
SET @column_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'detection_records'
    AND COLUMN_NAME = 'ipo_comparison_results'
);

SET @sql = IF(@column_exists = 0,
    'ALTER TABLE detection_records ADD COLUMN ipo_comparison_results JSON NULL COMMENT "IPO对标结果"',
    'SELECT "Column ipo_comparison_results already exists" AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并添加 remediation_suggestions 字段
SET @column_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'detection_records'
    AND COLUMN_NAME = 'remediation_suggestions'
);

SET @sql = IF(@column_exists = 0,
    'ALTER TABLE detection_records ADD COLUMN remediation_suggestions JSON NULL COMMENT "整改建议"',
    'SELECT "Column remediation_suggestions already exists" AS message'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 验证添加结果
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME = 'detection_records'
AND COLUMN_NAME IN ('risk_evidence_locations', 'suspicious_segments', 'ipo_comparison_results', 'remediation_suggestions')
ORDER BY ORDINAL_POSITION;
