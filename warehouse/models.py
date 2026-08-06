# -*- coding: utf-8 -*-
"""
数据仓库星型模型 (Star Schema)

维度表 (Dimension):
    dim_patient    — 患者维度
    dim_condition  — 诊断维度
    dim_medication — 药品维度

事实表 (Fact):
    fact_encounter    — 就诊事实
    fact_observation  — 观测/检验事实
    fact_condition    — 诊断事实（患者-诊断关联）
    fact_medication   — 用药事实（患者-药品关联）
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

WAREHOUSE_DIR = Path(__file__).resolve().parent
WAREHOUSE_DB_FILE = WAREHOUSE_DIR / "warehouse.db"


class WarehouseBase(DeclarativeBase):
    """数据仓库声明式基类。"""


def get_warehouse_engine():
    """创建指向 warehouse.db 的 SQLAlchemy Engine。"""
    url = f"sqlite:///{WAREHOUSE_DB_FILE.as_posix()}"
    engine = create_engine(url, echo=False, future=True, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


warehouse_engine = get_warehouse_engine()
WarehouseSessionLocal = sessionmaker(
    bind=warehouse_engine, autocommit=False, autoflush=False, expire_on_commit=False
)


class DimPatient(WarehouseBase):
    """
    患者维度表

    存储患者人口统计学属性，支持按性别、年龄段分析。
    """

    __tablename__ = "dim_patient"
    __table_args__ = {"comment": "患者维度表"}

    patient_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="患者维度代理键")
    patient_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True, comment="业务系统患者 ID")
    gender: Mapped[str] = mapped_column(String(16), nullable=False, comment="性别")
    birth_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="出生年份")
    age_group: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="年龄段分组")


class DimCondition(WarehouseBase):
    """
    诊断维度表

    存储 ICD 编码与诊断名称，用于疾病分布分析。
    """

    __tablename__ = "dim_condition"
    __table_args__ = {"comment": "诊断维度表"}

    condition_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="诊断维度代理键")
    icd_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="ICD-10 编码")
    condition_name: Mapped[str] = mapped_column(String(256), nullable=False, comment="诊断名称")


class DimMedication(WarehouseBase):
    """
    药品维度表

    存储药品名称，用于用药分析。
    """

    __tablename__ = "dim_medication"
    __table_args__ = {"comment": "药品维度表"}

    medication_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="药品维度代理键")
    drug_name: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, index=True, comment="药品名称")


class FactEncounter(WarehouseBase):
    """
    就诊事实表

    记录每次就诊事件，关联患者维度。
    """

    __tablename__ = "fact_encounter"
    __table_args__ = (
        Index("idx_fact_encounter_date", "encounter_date"),
        Index("idx_fact_encounter_type", "encounter_type"),
        {"comment": "就诊事实表"},
    )

    encounter_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="就诊事实代理键")
    patient_key: Mapped[int] = mapped_column(
        ForeignKey("dim_patient.patient_key"), nullable=False, index=True, comment="患者维度外键"
    )
    encounter_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="就诊日期时间")
    encounter_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="就诊类型")


class FactObservation(WarehouseBase):
    """
    观测/检验事实表

    记录量化测量结果，关联患者维度。
    """

    __tablename__ = "fact_observation"
    __table_args__ = (
        Index("idx_fact_observation_type", "measurement_type"),
        Index("idx_fact_observation_date", "date"),
        {"comment": "观测/检验事实表"},
    )

    observation_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="观测事实代理键")
    patient_key: Mapped[int] = mapped_column(
        ForeignKey("dim_patient.patient_key"), nullable=False, index=True, comment="患者维度外键"
    )
    measurement_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="测量类型")
    value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, comment="测量数值")
    unit: Mapped[str] = mapped_column(String(32), nullable=False, comment="测量单位")
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="观测日期时间")


class FactCondition(WarehouseBase):
    """
    诊断事实表

    记录患者与诊断的关联，支持疾病分布与患病人数统计。
    """

    __tablename__ = "fact_condition"
    __table_args__ = (
        Index("idx_fact_condition_patient", "patient_key"),
        Index("idx_fact_condition_condition", "condition_key"),
        {"comment": "诊断事实表"},
    )

    condition_fact_key: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="诊断事实代理键"
    )
    patient_key: Mapped[int] = mapped_column(
        ForeignKey("dim_patient.patient_key"), nullable=False, comment="患者维度外键"
    )
    condition_key: Mapped[int] = mapped_column(
        ForeignKey("dim_condition.condition_key"), nullable=False, comment="诊断维度外键"
    )


class FactMedication(WarehouseBase):
    """
    用药事实表

    记录患者与药品的关联，支持用药频次与分布分析。
    """

    __tablename__ = "fact_medication"
    __table_args__ = (
        Index("idx_fact_medication_patient", "patient_key"),
        Index("idx_fact_medication_drug", "medication_key"),
        {"comment": "用药事实表"},
    )

    medication_fact_key: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="用药事实代理键"
    )
    patient_key: Mapped[int] = mapped_column(
        ForeignKey("dim_patient.patient_key"), nullable=False, comment="患者维度外键"
    )
    medication_key: Mapped[int] = mapped_column(
        ForeignKey("dim_medication.medication_key"), nullable=False, comment="药品维度外键"
    )


def init_warehouse_schema(drop_existing: bool = True) -> None:
    """创建或重建数据仓库表结构。"""
    if drop_existing:
        WarehouseBase.metadata.drop_all(bind=warehouse_engine)
    WarehouseBase.metadata.create_all(bind=warehouse_engine)
