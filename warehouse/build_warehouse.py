#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医疗数据仓库构建脚本

从 OLTP 数据库 (database/hospital.db) 读取经 ETL 与质控处理后的数据，
转换并加载至星型模型数据仓库 (warehouse/warehouse.db)。

运行:
    python warehouse/build_warehouse.py
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import engine as source_engine
from warehouse.logger import LOG_FILE, setup_logger
from warehouse.models import (
    DimCondition,
    DimMedication,
    DimPatient,
    FactCondition,
    FactEncounter,
    FactMedication,
    FactObservation,
    WarehouseSessionLocal,
    init_warehouse_schema,
)

logger = setup_logger("warehouse.build")

BATCH_SIZE = 500


def calc_age_group(birth_date: date, reference: date | None = None) -> tuple[int, str]:
    """
    根据出生日期计算出生年份与年龄段。

    年龄段划分:
        0-17   → 0-17
        18-44  → 18-44
        45-64  → 45-64
        65+    → 65+
    """
    ref = reference or date.today()
    if isinstance(birth_date, str):
        birth_date = datetime.strptime(birth_date[:10], "%Y-%m-%d").date()
    elif isinstance(birth_date, datetime):
        birth_date = birth_date.date()

    birth_year = birth_date.year
    age = ref.year - birth_year - ((ref.month, ref.day) < (birth_date.month, birth_date.day))

    if age <= 17:
        group = "0-17"
    elif age <= 44:
        group = "18-44"
    elif age <= 64:
        group = "45-64"
    else:
        group = "65+"

    return birth_year, group


def load_source_data() -> Dict[str, pd.DataFrame]:
    """从 hospital.db 加载源表数据。"""
    logger.info("从 hospital.db 读取源数据...")
    tables = ["patients", "encounters", "conditions", "medications", "observations"]
    data = {}
    for table in tables:
        data[table] = pd.read_sql(f"SELECT * FROM {table}", source_engine)
        logger.info("源表 %s: %d 行", table, len(data[table]))
    return data


def build_dim_patient(session, patients_df: pd.DataFrame) -> Dict[int, int]:
    """
    构建患者维度表。

    Returns:
        patient_id → patient_key 映射字典
    """
    logger.info("构建 dim_patient...")
    id_map: Dict[int, int] = {}

    for _, row in patients_df.iterrows():
        patient_id = int(row["patient_id"])
        birth_year, age_group = calc_age_group(row["birth_date"])
        dim = DimPatient(
            patient_id=patient_id,
            gender=str(row["gender"]),
            birth_year=birth_year,
            age_group=age_group,
        )
        session.add(dim)
        session.flush()
        id_map[patient_id] = dim.patient_key

    logger.info("dim_patient 加载完成: %d 行", len(id_map))
    return id_map


def build_dim_condition(session, conditions_df: pd.DataFrame) -> Dict[tuple, int]:
    """构建诊断维度表，返回 (icd_code, condition_name) → condition_key 映射。"""
    logger.info("构建 dim_condition...")
    unique = conditions_df[["icd_code", "condition_name"]].drop_duplicates()
    key_map: Dict[tuple, int] = {}
    for _, row in unique.iterrows():
        dim = DimCondition(
            icd_code=str(row["icd_code"]),
            condition_name=str(row["condition_name"]),
        )
        session.add(dim)
        session.flush()
        key_map[(str(row["icd_code"]), str(row["condition_name"]))] = dim.condition_key
    logger.info("dim_condition 加载完成: %d 行", len(key_map))
    return key_map


def build_dim_medication(session, medications_df: pd.DataFrame) -> Dict[str, int]:
    """构建药品维度表，返回 drug_name → medication_key 映射。"""
    logger.info("构建 dim_medication...")
    key_map: Dict[str, int] = {}
    for drug_name in medications_df["drug_name"].drop_duplicates():
        dim = DimMedication(drug_name=str(drug_name))
        session.add(dim)
        session.flush()
        key_map[str(drug_name)] = dim.medication_key
    logger.info("dim_medication 加载完成: %d 行", len(key_map))
    return key_map


def build_fact_encounter(session, encounters_df: pd.DataFrame, patient_key_map: Dict[int, int]) -> int:
    """构建就诊事实表。"""
    logger.info("构建 fact_encounter...")
    mappings = []
    skipped = 0

    for _, row in encounters_df.iterrows():
        patient_id = int(row["patient_id"])
        patient_key = patient_key_map.get(patient_id)
        if patient_key is None:
            skipped += 1
            continue
        encounter_date = pd.to_datetime(row["encounter_date"])
        mappings.append(
            {
                "patient_key": patient_key,
                "encounter_date": encounter_date.to_pydatetime(),
                "encounter_type": str(row["encounter_type"]),
            }
        )

    for i in range(0, len(mappings), BATCH_SIZE):
        session.bulk_insert_mappings(FactEncounter, mappings[i : i + BATCH_SIZE])

    session.flush()
    if skipped:
        logger.warning("fact_encounter 跳过无效 patient_id: %d 行", skipped)
    logger.info("fact_encounter 加载完成: %d 行", len(mappings))
    return len(mappings)


def build_fact_observation(session, observations_df: pd.DataFrame, patient_key_map: Dict[int, int]) -> int:
    """构建观测事实表。"""
    logger.info("构建 fact_observation...")
    mappings = []
    skipped = 0

    for _, row in observations_df.iterrows():
        patient_id = int(row["patient_id"])
        patient_key = patient_key_map.get(patient_id)
        if patient_key is None:
            skipped += 1
            continue
        obs_date = pd.to_datetime(row["date"])
        mappings.append(
            {
                "patient_key": patient_key,
                "measurement_type": str(row["measurement_type"]),
                "value": Decimal(str(row["value"])),
                "unit": str(row["unit"]),
                "date": obs_date.to_pydatetime(),
            }
        )

    for i in range(0, len(mappings), BATCH_SIZE):
        session.bulk_insert_mappings(FactObservation, mappings[i : i + BATCH_SIZE])

    session.flush()
    if skipped:
        logger.warning("fact_observation 跳过无效 patient_id: %d 行", skipped)
    logger.info("fact_observation 加载完成: %d 行", len(mappings))
    return len(mappings)


def build_fact_condition(
    session,
    conditions_df: pd.DataFrame,
    patient_key_map: Dict[int, int],
    condition_key_map: Dict[tuple, int],
) -> int:
    """构建诊断事实表。"""
    logger.info("构建 fact_condition...")
    mappings = []
    skipped = 0
    for _, row in conditions_df.iterrows():
        patient_id = int(row["patient_id"])
        patient_key = patient_key_map.get(patient_id)
        cond_key = condition_key_map.get((str(row["icd_code"]), str(row["condition_name"])))
        if patient_key is None or cond_key is None:
            skipped += 1
            continue
        mappings.append({"patient_key": patient_key, "condition_key": cond_key})

    for i in range(0, len(mappings), BATCH_SIZE):
        session.bulk_insert_mappings(FactCondition, mappings[i : i + BATCH_SIZE])
    session.flush()
    if skipped:
        logger.warning("fact_condition 跳过无效记录: %d 行", skipped)
    logger.info("fact_condition 加载完成: %d 行", len(mappings))
    return len(mappings)


def build_fact_medication(
    session,
    medications_df: pd.DataFrame,
    patient_key_map: Dict[int, int],
    medication_key_map: Dict[str, int],
) -> int:
    """构建用药事实表。"""
    logger.info("构建 fact_medication...")
    mappings = []
    skipped = 0
    for _, row in medications_df.iterrows():
        patient_id = int(row["patient_id"])
        patient_key = patient_key_map.get(patient_id)
        med_key = medication_key_map.get(str(row["drug_name"]))
        if patient_key is None or med_key is None:
            skipped += 1
            continue
        mappings.append({"patient_key": patient_key, "medication_key": med_key})

    for i in range(0, len(mappings), BATCH_SIZE):
        session.bulk_insert_mappings(FactMedication, mappings[i : i + BATCH_SIZE])
    session.flush()
    if skipped:
        logger.warning("fact_medication 跳过无效记录: %d 行", skipped)
    logger.info("fact_medication 加载完成: %d 行", len(mappings))
    return len(mappings)


def build_warehouse() -> None:
    """执行完整数据仓库构建流程。"""
    logger.info("========== 数据仓库构建开始 ==========")
    logger.info("日志文件: %s", LOG_FILE)

    # 1. 创建表结构
    init_warehouse_schema(drop_existing=True)
    logger.info("warehouse.db 表结构已创建")

    # 2. 读取源数据
    source = load_source_data()

    # 3. 转换并加载
    session = WarehouseSessionLocal()
    try:
        patient_key_map = build_dim_patient(session, source["patients"])
        condition_key_map = build_dim_condition(session, source["conditions"])
        medication_key_map = build_dim_medication(session, source["medications"])
        build_fact_encounter(session, source["encounters"], patient_key_map)
        build_fact_observation(session, source["observations"], patient_key_map)
        build_fact_condition(session, source["conditions"], patient_key_map, condition_key_map)
        build_fact_medication(session, source["medications"], patient_key_map, medication_key_map)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    logger.info("========== 数据仓库构建完成 ==========")


def main() -> int:
    """命令行入口。"""
    try:
        build_warehouse()
        print("Healthcare data warehouse created successfully.")
        return 0
    except Exception as exc:
        logger.exception("数据仓库构建失败: %s", exc)
        print(f"Warehouse build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
