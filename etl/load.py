# -*- coding: utf-8 -*-
"""
数据加载模块 (Load)

将清洗后的 CSV 数据批量写入 SQLite 数据库 (database/hospital.db)。
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import init_db, session_scope
from database.models import Condition, Medication, Patient
from etl.logger import setup_logger

logger = setup_logger("etl.load")

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
BATCH_SIZE = 500

PROCESSED_FILES = {
    "patients": PROCESSED_DIR / "processed_patient.csv",
    "conditions": PROCESSED_DIR / "processed_condition.csv",
    "medications": PROCESSED_DIR / "processed_medication.csv",
}


def _parse_date(value: str):
    """将 YYYY-MM-DD 字符串转为 date 对象。"""
    if pd.isna(value) or value == "" or value == "NaT":
        return None
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _load_patients(session, df: pd.DataFrame) -> int:
    """批量加载患者数据，支持指定 patient_id（upsert）。"""
    count = 0
    for _, row in df.iterrows():
        patient_id = int(row["patient_id"])
        existing = session.get(Patient, patient_id)
        if existing:
            existing.gender = row["gender"]
            existing.birth_date = _parse_date(row["birth_date"])
            existing.race = row.get("race", "unknown")
        else:
            session.add(
                Patient(
                    patient_id=patient_id,
                    gender=row["gender"],
                    birth_date=_parse_date(row["birth_date"]),
                    race=row.get("race", "unknown"),
                )
            )
        count += 1
    session.flush()
    logger.info("数据加载 | patients | 插入/更新: %d 条", count)
    return count


def _load_conditions(session, df: pd.DataFrame, valid_patient_ids: set[int]) -> int:
    """批量加载诊断数据（仅加载有效 patient_id）。"""
    mappings = []
    skipped = 0
    for _, row in df.iterrows():
        patient_id = int(row["patient_id"])
        if patient_id not in valid_patient_ids:
            skipped += 1
            continue
        mappings.append(
            {
                "patient_id": patient_id,
                "icd_code": row["icd_code"],
                "condition_name": row["condition_name"],
                "onset_date": _parse_date(row["onset_date"]),
            }
        )

    if skipped > 0:
        logger.warning("数据加载 | conditions | 跳过无效 patient_id: %d 条", skipped)

    for i in range(0, len(mappings), BATCH_SIZE):
        batch = mappings[i : i + BATCH_SIZE]
        session.bulk_insert_mappings(Condition, batch)

    session.flush()
    logger.info("数据加载 | conditions | 插入: %d 条", len(mappings))
    return len(mappings)


def _load_medications(session, df: pd.DataFrame, valid_patient_ids: set[int]) -> int:
    """批量加载用药数据（仅加载有效 patient_id）。"""
    mappings = []
    skipped = 0
    for _, row in df.iterrows():
        patient_id = int(row["patient_id"])
        if patient_id not in valid_patient_ids:
            skipped += 1
            continue
        end_date = _parse_date(row.get("end_date"))
        mappings.append(
            {
                "patient_id": patient_id,
                "drug_name": row["drug_name"],
                "start_date": _parse_date(row["start_date"]),
                "end_date": end_date,
            }
        )

    if skipped > 0:
        logger.warning("数据加载 | medications | 跳过无效 patient_id: %d 条", skipped)

    for i in range(0, len(mappings), BATCH_SIZE):
        batch = mappings[i : i + BATCH_SIZE]
        session.bulk_insert_mappings(Medication, batch)

    session.flush()
    logger.info("数据加载 | medications | 插入: %d 条", len(mappings))
    return len(mappings)


def load_from_dataframes(processed: Dict[str, pd.DataFrame]) -> Dict[str, int]:
    """
    将清洗后的 DataFrame 写入数据库。

    Returns:
        各表插入/更新数量
    """
    logger.info("========== Load 阶段开始 ==========")

    init_db(drop_existing=False)

    results = {"patients": 0, "conditions": 0, "medications": 0}

    with session_scope() as session:
        results["patients"] = _load_patients(session, processed["patients"])
        valid_patient_ids = set(processed["patients"]["patient_id"].astype(int).tolist())
        results["conditions"] = _load_conditions(session, processed["conditions"], valid_patient_ids)
        results["medications"] = _load_medications(session, processed["medications"], valid_patient_ids)

    logger.info(
        "Load 完成 | patients=%d, conditions=%d, medications=%d",
        results["patients"],
        results["conditions"],
        results["medications"],
    )
    return results


def load_from_csv() -> Dict[str, int]:
    """从 data/processed/ 读取 CSV 并加载至数据库。"""
    processed = {}
    for key, path in PROCESSED_FILES.items():
        if not path.exists():
            raise FileNotFoundError(f"处理后文件不存在: {path}")
        processed[key] = pd.read_csv(path, dtype=str, keep_default_na=True)
        logger.info("读取处理后文件 | %s | 行数: %d", path.name, len(processed[key]))

    return load_from_dataframes(processed)


def load_all(processed: Dict[str, pd.DataFrame]) -> Dict[str, int]:
    """Load 阶段入口。"""
    return load_from_dataframes(processed)
