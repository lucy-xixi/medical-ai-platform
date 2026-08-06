#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Synthetic EHR 数据初始化脚本

运行:
    python database/init_data.py

生成 database/hospital.db 及指定数量的测试数据。
"""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from faker import Faker
from sqlalchemy import func, select

# 确保从项目根目录可导入 database 包
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import DEFAULT_DB_FILE, get_database_url, init_db, session_scope
from database.models import Condition, Encounter, Medication, Observation, Patient

# ---------------------------------------------------------------------------
# 数据量配置
# ---------------------------------------------------------------------------
PATIENT_COUNT = 1000
ENCOUNTER_COUNT = 5000
CONDITION_COUNT = 3000
MEDICATION_COUNT = 3000
OBSERVATION_COUNT = 10000
BATCH_SIZE = 500

# ---------------------------------------------------------------------------
# EHR 参考数据
# ---------------------------------------------------------------------------
GENDERS = ["male", "female"]
GENDER_WEIGHTS = [0.48, 0.52]

RACES = ["汉族", "回族", "满族", "蒙古族", "藏族", "维吾尔族", "苗族", "壮族", "其他"]

ENCOUNTER_TYPES = ["outpatient", "inpatient", "emergency", "telehealth"]
ENCOUNTER_TYPE_WEIGHTS = [0.55, 0.25, 0.15, 0.05]

CONDITIONS_CATALOG = [
    ("E11.9", "2型糖尿病，未伴有并发症"),
    ("I10", "原发性高血压"),
    ("J06.9", "急性上呼吸道感染，未特指"),
    ("J18.9", "肺炎，未特指"),
    ("I25.10", "动脉粥样硬化性心脏病"),
    ("N18.3", "慢性肾脏病，3期"),
    ("M54.5", "下背痛"),
    ("K21.0", "胃食管反流病伴食管炎"),
    ("E78.5", "高脂血症，未特指"),
    ("F32.9", "抑郁发作，未特指"),
    ("C34.90", "支气管或肺恶性肿瘤，未特指"),
    ("G43.909", "偏头痛，未特指"),
    ("I63.9", "脑梗死，未特指"),
    ("J44.9", "慢性阻塞性肺病，未特指"),
    ("K80.20", "胆囊结石，不伴有胆囊炎"),
]

MEDICATIONS_CATALOG = [
    "二甲双胍", "氨氯地平", "阿托伐他汀", "阿司匹林", "奥美拉唑",
    "布洛芬", "左氧氟沙星", "胰岛素", "缬沙坦", "美托洛尔",
    "氯吡格雷", "格列美脲", "瑞舒伐他汀", "厄贝沙坦", "头孢曲松",
    "氨溴索", "蒙脱石散", "硝苯地平", "叶酸", "维生素D",
]

OBSERVATION_TYPES = [
    ("systolic_blood_pressure", 90, 180, "mmHg"),
    ("diastolic_blood_pressure", 60, 110, "mmHg"),
    ("heart_rate", 55, 120, "beats/min"),
    ("body_weight", 45, 110, "kg"),
    ("body_height", 150, 190, "cm"),
    ("fasting_glucose", 4.0, 15.0, "mmol/L"),
    ("hba1c", 5.0, 12.0, "%"),
    ("total_cholesterol", 3.0, 8.0, "mmol/L"),
    ("creatinine", 40, 200, "umol/L"),
    ("hemoglobin", 90, 180, "g/L"),
]

fake = Faker("zh_CN")
Faker.seed(42)
random.seed(42)


def _random_birth_date(min_age: int = 1, max_age: int = 90) -> date:
    """生成随机出生日期。"""
    age = random.randint(min_age, max_age)
    return fake.date_of_birth(minimum_age=age, maximum_age=age)


def _random_datetime(years_back: int = 3):
    """生成近 N 年内的随机 datetime。"""
    start = date.today() - timedelta(days=365 * years_back)
    end = date.today()
    return fake.date_time_between(start_date=start, end_date=end)


def _random_date(years_back: int = 10) -> date:
    """生成近 N 年内的随机 date。"""
    start = date.today() - timedelta(days=365 * years_back)
    end = date.today()
    return fake.date_between(start_date=start, end_date=end)


def generate_patients(count: int) -> list[Patient]:
    """使用 Faker 生成患者数据。"""
    patients = []
    for _ in range(count):
        patients.append(
            Patient(
                gender=random.choices(GENDERS, weights=GENDER_WEIGHTS, k=1)[0],
                birth_date=_random_birth_date(),
                race=random.choice(RACES),
            )
        )
    return patients


def generate_encounters(patient_ids: list[int], count: int) -> list[Encounter]:
    """生成指定数量的就诊记录。"""
    encounters = []
    for _ in range(count):
        encounters.append(
            Encounter(
                patient_id=random.choice(patient_ids),
                encounter_date=_random_datetime(years_back=3),
                encounter_type=random.choices(ENCOUNTER_TYPES, weights=ENCOUNTER_TYPE_WEIGHTS, k=1)[0],
            )
        )
    return encounters


def generate_conditions(patient_ids: list[int], count: int) -> list[Condition]:
    """生成指定数量的诊断记录。"""
    conditions = []
    for _ in range(count):
        icd_code, condition_name = random.choice(CONDITIONS_CATALOG)
        conditions.append(
            Condition(
                patient_id=random.choice(patient_ids),
                icd_code=icd_code,
                condition_name=condition_name,
                onset_date=_random_date(years_back=10),
            )
        )
    return conditions


def generate_medications(patient_ids: list[int], count: int) -> list[Medication]:
    """生成指定数量的用药记录。"""
    medications = []
    for _ in range(count):
        start = _random_date(years_back=5)
        end = None if random.random() < 0.3 else start + timedelta(days=random.randint(7, 365))
        medications.append(
            Medication(
                patient_id=random.choice(patient_ids),
                drug_name=random.choice(MEDICATIONS_CATALOG),
                start_date=start,
                end_date=end,
            )
        )
    return medications


def generate_observations(patient_ids: list[int], count: int) -> list[Observation]:
    """生成指定数量的观测/检验记录。"""
    observations = []
    for _ in range(count):
        mtype, low, high, unit = random.choice(OBSERVATION_TYPES)
        if isinstance(low, int) and isinstance(high, int):
            value = Decimal(str(random.randint(low, high)))
        else:
            value = Decimal(str(round(random.uniform(low, high), 2)))

        observations.append(
            Observation(
                patient_id=random.choice(patient_ids),
                measurement_type=mtype,
                value=value,
                unit=unit,
                date=_random_datetime(years_back=2),
            )
        )
    return observations


def bulk_insert(session, objects: list, label: str) -> int:
    """分批 bulk_save_objects 提升插入性能。"""
    total = len(objects)
    for i in range(0, total, BATCH_SIZE):
        batch = objects[i : i + BATCH_SIZE]
        session.bulk_save_objects(batch)
        session.flush()
    print(f"  {label}: {total}")
    return total


def print_summary(session) -> None:
    """打印各表记录数。"""
    tables = [
        ("patients", Patient),
        ("encounters", Encounter),
        ("conditions", Condition),
        ("medications", Medication),
        ("observations", Observation),
    ]
    print("\n--- Insert Summary ---")
    for name, model in tables:
        count = session.scalar(select(func.count()).select_from(model))
        print(f"  {name}: {count}")


def main() -> int:
    """主入口：建表 → 生成数据 → 插入 → 统计。"""
    print("=" * 60)
    print("Medical Data Intelligence Platform - Database Init")
    print("=" * 60)
    print(f"Database URL: {get_database_url()}")
    print(f"Database file: {DEFAULT_DB_FILE}")

    init_db(drop_existing=True)

    with session_scope() as session:
        print("\nGenerating Synthetic EHR data...")

        patients = generate_patients(PATIENT_COUNT)
        bulk_insert(session, patients, "patients")

        # 刷新以获取自增 patient_id
        session.flush()
        patient_ids = list(session.scalars(select(Patient.patient_id)).all())

        bulk_insert(session, generate_encounters(patient_ids, ENCOUNTER_COUNT), "encounters")
        bulk_insert(session, generate_conditions(patient_ids, CONDITION_COUNT), "conditions")
        bulk_insert(session, generate_medications(patient_ids, MEDICATION_COUNT), "medications")
        bulk_insert(session, generate_observations(patient_ids, OBSERVATION_COUNT), "observations")

        print_summary(session)

    print("\nDatabase initialization completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
