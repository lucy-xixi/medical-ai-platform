-- ============================================================================
-- 医疗数据平台 - MySQL 数据库结构
-- 设计参考: FHIR R4 (Patient, Encounter, Condition, Medication, Observation)
-- 适用场景: 医院信息中心 EHR 模拟数据平台
-- ============================================================================

-- 创建数据库（若已存在则跳过）
CREATE DATABASE IF NOT EXISTS medical_platform
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE medical_platform;

-- ----------------------------------------------------------------------------
-- 患者表 (对应 FHIR Patient 资源)
-- 存储患者人口统计学基本信息
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    patient_id   INT UNSIGNED    NOT NULL AUTO_INCREMENT COMMENT '患者唯一标识 (FHIR: Patient.id)',
    gender       ENUM('male', 'female', 'other', 'unknown') NOT NULL COMMENT '性别 (FHIR: Patient.gender)',
    birth_date   DATE            NOT NULL COMMENT '出生日期 (FHIR: Patient.birthDate)',
    race         VARCHAR(64)     NOT NULL DEFAULT 'unknown' COMMENT '种族/民族 (FHIR: Patient.extension - race)',
    created_at   TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at   TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    PRIMARY KEY (patient_id),
    INDEX idx_patients_birth_date (birth_date),
    INDEX idx_patients_gender (gender)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='患者基本信息表';

-- ----------------------------------------------------------------------------
-- 就诊表 (对应 FHIR Encounter 资源)
-- 记录患者每次门诊、住院、急诊等就诊事件
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS encounters (
    encounter_id   INT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '就诊唯一标识 (FHIR: Encounter.id)',
    patient_id     INT UNSIGNED  NOT NULL COMMENT '关联患者 ID (FHIR: Encounter.subject)',
    encounter_date DATETIME      NOT NULL COMMENT '就诊日期时间 (FHIR: Encounter.period.start)',
    encounter_type ENUM(
        'outpatient',   -- 门诊 (ambulatory)
        'inpatient',    -- 住院 (inpatient encounter)
        'emergency',    -- 急诊 (emergency)
        'telehealth'    -- 远程诊疗
    ) NOT NULL COMMENT '就诊类型 (FHIR: Encounter.class)',
    created_at     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    PRIMARY KEY (encounter_id),
    INDEX idx_encounters_patient_id (patient_id),
    INDEX idx_encounters_date (encounter_date),
    INDEX idx_encounters_type (encounter_type),
    CONSTRAINT fk_encounters_patient
        FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='患者就诊记录表';

-- ----------------------------------------------------------------------------
-- 诊断/疾病表 (对应 FHIR Condition 资源)
-- 存储患者诊断信息，使用 ICD-10 编码
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conditions (
    condition_id   INT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '诊断唯一标识 (FHIR: Condition.id)',
    patient_id     INT UNSIGNED  NOT NULL COMMENT '关联患者 ID (FHIR: Condition.subject)',
    icd_code       VARCHAR(16)   NOT NULL COMMENT 'ICD-10 诊断编码 (FHIR: Condition.code.coding)',
    condition_name VARCHAR(256)  NOT NULL COMMENT '诊断名称 (FHIR: Condition.code.text)',
    onset_date     DATE          NOT NULL COMMENT '发病/诊断日期 (FHIR: Condition.onsetDateTime)',
    created_at     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    PRIMARY KEY (condition_id),
    INDEX idx_conditions_patient_id (patient_id),
    INDEX idx_conditions_icd_code (icd_code),
    INDEX idx_conditions_onset_date (onset_date),
    CONSTRAINT fk_conditions_patient
        FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='患者诊断/疾病表';

-- ----------------------------------------------------------------------------
-- 用药表 (对应 FHIR MedicationStatement / MedicationRequest 资源)
-- 记录患者用药信息及起止时间
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS medications (
    medication_id INT UNSIGNED   NOT NULL AUTO_INCREMENT COMMENT '用药记录唯一标识 (FHIR: MedicationStatement.id)',
    patient_id    INT UNSIGNED   NOT NULL COMMENT '关联患者 ID (FHIR: MedicationStatement.subject)',
    drug_name     VARCHAR(256)   NOT NULL COMMENT '药品名称 (FHIR: MedicationStatement.medicationCodeableConcept)',
    start_date    DATE           NOT NULL COMMENT '用药开始日期 (FHIR: MedicationStatement.effectivePeriod.start)',
    end_date      DATE           NULL COMMENT '用药结束日期，NULL 表示仍在用药 (FHIR: effectivePeriod.end)',
    created_at    TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    PRIMARY KEY (medication_id),
    INDEX idx_medications_patient_id (patient_id),
    INDEX idx_medications_drug_name (drug_name),
    INDEX idx_medications_start_date (start_date),
    CONSTRAINT fk_medications_patient
        FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_medications_date_range
        CHECK (end_date IS NULL OR end_date >= start_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='患者用药记录表';

-- ----------------------------------------------------------------------------
-- 观测/检验表 (对应 FHIR Observation 资源)
-- 存储生命体征、实验室检验等量化测量结果
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS observations (
    observation_id   INT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '观测唯一标识 (FHIR: Observation.id)',
    patient_id       INT UNSIGNED  NOT NULL COMMENT '关联患者 ID (FHIR: Observation.subject)',
    measurement_type VARCHAR(64)   NOT NULL COMMENT '测量类型，如血压、血糖 (FHIR: Observation.code)',
    value            DECIMAL(12, 4) NOT NULL COMMENT '测量数值 (FHIR: Observation.valueQuantity.value)',
    unit             VARCHAR(32)   NOT NULL COMMENT '测量单位 (FHIR: Observation.valueQuantity.unit)',
    observation_date DATETIME      NOT NULL COMMENT '观测日期时间 (FHIR: Observation.effectiveDateTime)',
    created_at       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    PRIMARY KEY (observation_id),
    INDEX idx_observations_patient_id (patient_id),
    INDEX idx_observations_type (measurement_type),
    INDEX idx_observations_date (observation_date),
    CONSTRAINT fk_observations_patient
        FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='患者观测/检验结果表';
