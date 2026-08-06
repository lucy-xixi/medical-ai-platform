# -*- coding: utf-8 -*-
"""
数据转换模块 (Transform)

对原始医疗数据进行清洗、标准化，并输出至 data/processed/。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

from etl.logger import setup_logger

logger = setup_logger("etl.transform")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# 标准化后的输出文件名
OUTPUT_FILES = {
    "patients": PROCESSED_DIR / "processed_patient.csv",
    "conditions": PROCESSED_DIR / "processed_condition.csv",
    "medications": PROCESSED_DIR / "processed_medication.csv",
}

# 性别标准化映射 (FHIR 风格: Male / Female)
GENDER_MAP = {
    "m": "Male",
    "male": "Male",
    "M": "Male",
    "Male": "Male",
    "男": "Male",
    "f": "Female",
    "female": "Female",
    "F": "Female",
    "Female": "Female",
    "女": "Female",
}

# 常见药物名称标准化（小写键 -> 标准写法）
DRUG_NAME_MAP = {
    "metformin": "Metformin",
    "METFORMIN": "Metformin",
    "amlodipine": "Amlodipine",
    "AMLODIPINE": "Amlodipine",
    "aspirin": "Aspirin",
    "ASPIRIN": "Aspirin",
    "atorvastatin": "Atorvastatin",
    "ATorvastatin": "Atorvastatin",
    "omeprazole": "Omeprazole",
    "OMEPRAZOLE": "Omeprazole",
    "ibuprofen": "Ibuprofen",
    "IBUPROFEN": "Ibuprofen",
    "insulin": "Insulin",
    "INSULIN": "Insulin",
    "二甲双胍": "Metformin",
    "氨氯地平": "Amlodipine",
}


def _normalize_date(series: pd.Series, column_name: str) -> pd.Series:
    """将日期列统一为 YYYY-MM-DD 格式（支持多种日期格式混用）。"""
    parsed = pd.to_datetime(series, errors="coerce", format="mixed")
    invalid_count = int(parsed.isna().sum())
    if invalid_count > 0:
        logger.warning("缺失值处理 | %s | 无效/缺失日期: %d 条，将填充为 NaT", column_name, invalid_count)
    return parsed.dt.strftime("%Y-%m-%d")


def _standardize_gender(value) -> str:
    """标准化性别字段。"""
    if pd.isna(value):
        return "Unknown"
    key = str(value).strip()
    return GENDER_MAP.get(key, GENDER_MAP.get(key.lower(), "Unknown"))


def _standardize_icd(code) -> str:
    """
    标准化 ICD-10 编码。

    示例: e11.9 -> E11.9, i10 -> I10
    """
    if pd.isna(code):
        return ""
    code = str(code).strip()
    if not code:
        return ""
    # 首字符字母大写，其余保持数字/字母/点号
    match = re.match(r"^([A-Za-z])(.*)$", code)
    if match:
        return match.group(1).upper() + match.group(2).upper()
    return code.upper()


def _standardize_drug_name(name) -> str:
    """标准化药品名称（首字母大写或查表映射）。"""
    if pd.isna(name):
        return ""
    name = str(name).strip()
    if not name:
        return ""
    if name in DRUG_NAME_MAP:
        return DRUG_NAME_MAP[name]
    if name.lower() in DRUG_NAME_MAP:
        return DRUG_NAME_MAP[name.lower()]
    # 默认 Title Case
    return name.title()


def transform_patients(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗患者数据:
        - 删除重复 patient_id
        - 缺失值处理
        - gender 标准化
        - birth_date 格式统一
    """
    original_count = len(df)
    result = df.copy()

    # 删除重复 patient_id
    dup_count = result.duplicated(subset=["patient_id"], keep="first").sum()
    result = result.drop_duplicates(subset=["patient_id"], keep="first")
    if dup_count > 0:
        logger.info("数据清洗 | patients | 删除重复 patient_id: %d 条", dup_count)

    # gender 标准化
    result["gender"] = result["gender"].apply(_standardize_gender)

    # race 缺失值填充
    race_missing = result["race"].isna().sum() if "race" in result.columns else 0
    if "race" not in result.columns:
        result["race"] = "unknown"
        logger.info("缺失值处理 | patients | race 列不存在，已填充默认值 unknown")
    else:
        result["race"] = result["race"].fillna("unknown").astype(str).str.strip()
        result.loc[result["race"] == "", "race"] = "unknown"
        if race_missing > 0:
            logger.info("缺失值处理 | patients | race 缺失填充: %d 条", race_missing)

    # birth_date 标准化
    gender_missing = result["gender"].eq("Unknown").sum()
    if gender_missing > 0:
        logger.info("缺失值处理 | patients | gender 无法识别/缺失: %d 条 -> Unknown", gender_missing)

    result["birth_date"] = _normalize_date(result["birth_date"], "birth_date")

    # 删除 birth_date 无效行
    before_drop = len(result)
    result = result.dropna(subset=["birth_date"])
    dropped = before_drop - len(result)
    if dropped > 0:
        logger.info("数据清洗 | patients | 删除 birth_date 无效行: %d 条", dropped)

    logger.info(
        "数据清洗 | patients | 原始: %d -> 清洗后: %d",
        original_count,
        len(result),
    )
    return result


def transform_conditions(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗诊断数据:
        - ICD 编码标准化
        - condition_name 去空格
        - 缺失值处理
    """
    original_count = len(df)
    result = df.copy()

    # ICD 编码标准化
    result["icd_code"] = result["icd_code"].apply(_standardize_icd)

    # condition_name 去首尾空格
    result["condition_name"] = result["condition_name"].fillna("").astype(str).str.strip()

    # onset_date 标准化
    result["onset_date"] = _normalize_date(result["onset_date"], "onset_date")

    # 缺失值处理：删除关键字段缺失行
    before_drop = len(result)
    result = result.dropna(subset=["patient_id", "icd_code", "onset_date"])
    result = result[result["condition_name"] != ""]
    dropped = before_drop - len(result)
    if dropped > 0:
        logger.info("数据清洗 | conditions | 删除关键字段缺失行: %d 条", dropped)

    icd_missing = (result["icd_code"] == "").sum()
    if icd_missing > 0:
        result = result[result["icd_code"] != ""]

    logger.info(
        "数据清洗 | conditions | 原始: %d -> 清洗后: %d",
        original_count,
        len(result),
    )
    return result


def transform_medications(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗用药数据:
        - drug_name 标准化
        - 日期格式转换
    """
    original_count = len(df)
    result = df.copy()

    # drug_name 标准化
    result["drug_name"] = result["drug_name"].apply(_standardize_drug_name)

    # 日期标准化
    result["start_date"] = _normalize_date(result["start_date"], "start_date")
    result["end_date"] = _normalize_date(result["end_date"], "end_date")
    # 空 end_date 表示仍在用药
    result["end_date"] = result["end_date"].replace("NaT", "")
    result["end_date"] = result["end_date"].fillna("")

    # 缺失值处理
    before_drop = len(result)
    result = result.dropna(subset=["patient_id", "drug_name", "start_date"])
    result = result[result["drug_name"] != ""]
    dropped = before_drop - len(result)
    if dropped > 0:
        logger.info("数据清洗 | medications | 删除关键字段缺失行: %d 条", dropped)

    logger.info(
        "数据清洗 | medications | 原始: %d -> 清洗后: %d",
        original_count,
        len(result),
    )
    return result


def save_processed(data: Dict[str, pd.DataFrame]) -> Dict[str, Path]:
    """将清洗后的数据写入 data/processed/ 目录。"""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    saved: Dict[str, Path] = {}
    for key, df in data.items():
        output_path = OUTPUT_FILES[key]
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info("文件输出 | %s | 路径: %s | 行数: %d", key, output_path, len(df))
        saved[key] = output_path

    return saved


def transform_all(raw_data: Dict[str, pd.DataFrame]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Path]]:
    """
    执行全部 Transform 流程。

    Returns:
        (清洗后的 DataFrame 字典, 输出文件路径字典)
    """
    logger.info("========== Transform 阶段开始 ==========")

    processed = {
        "patients": transform_patients(raw_data["patients"]),
        "conditions": transform_conditions(raw_data["conditions"]),
        "medications": transform_medications(raw_data["medications"]),
    }

    output_paths = save_processed(processed)
    logger.info("Transform 完成")
    return processed, output_paths
