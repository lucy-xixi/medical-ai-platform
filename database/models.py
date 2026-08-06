# -*- coding: utf-8 -*-
"""
医疗数据 ORM 模型

设计参考 FHIR R4 资源:
    Patient, Encounter, Condition, MedicationStatement, Observation
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类，供所有 ORM 模型继承。"""


class Patient(Base):
    """
    患者表 — 对应 FHIR Patient 资源

    存储患者人口统计学基本信息（性别、出生日期、民族等）。
    """

    __tablename__ = "patients"
    __table_args__ = {"comment": "患者基本信息表 (FHIR: Patient)"}

    patient_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="患者唯一标识")
    gender: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="性别 (FHIR: Patient.gender)")
    birth_date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment="出生日期 (FHIR: Patient.birthDate)")
    race: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown", comment="种族/民族 (FHIR: Patient.extension)")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), comment="记录创建时间"
    )

    encounters: Mapped[List["Encounter"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    conditions: Mapped[List["Condition"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    medications: Mapped[List["Medication"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    observations: Mapped[List["Observation"]] = relationship(back_populates="patient", cascade="all, delete-orphan")


class Encounter(Base):
    """
    就诊表 — 对应 FHIR Encounter 资源

    记录门诊、住院、急诊等就诊事件。
    """

    __tablename__ = "encounters"
    __table_args__ = (
        Index("idx_encounters_patient_date", "patient_id", "encounter_date"),
        {"comment": "患者就诊记录表 (FHIR: Encounter)"},
    )

    encounter_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="就诊唯一标识")
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True, comment="关联患者 ID"
    )
    encounter_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True, comment="就诊日期时间 (FHIR: Encounter.period.start)"
    )
    encounter_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True, comment="就诊类型: outpatient/inpatient/emergency/telehealth"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), comment="记录创建时间"
    )

    patient: Mapped["Patient"] = relationship(back_populates="encounters")


class Condition(Base):
    """
    诊断/疾病表 — 对应 FHIR Condition 资源

    使用 ICD-10 编码存储患者诊断信息。
    """

    __tablename__ = "conditions"
    __table_args__ = (
        Index("idx_conditions_patient_icd", "patient_id", "icd_code"),
        {"comment": "患者诊断/疾病表 (FHIR: Condition)"},
    )

    condition_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="诊断唯一标识")
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True, comment="关联患者 ID"
    )
    icd_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="ICD-10 诊断编码")
    condition_name: Mapped[str] = mapped_column(String(256), nullable=False, comment="诊断名称")
    onset_date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment="发病/诊断日期")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), comment="记录创建时间"
    )

    patient: Mapped["Patient"] = relationship(back_populates="conditions")


class Medication(Base):
    """
    用药表 — 对应 FHIR MedicationStatement 资源

    记录患者用药名称及有效时间区间。
    """

    __tablename__ = "medications"
    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="chk_medications_date_range"),
        {"comment": "患者用药记录表 (FHIR: MedicationStatement)"},
    )

    medication_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="用药记录唯一标识")
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True, comment="关联患者 ID"
    )
    drug_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True, comment="药品名称")
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment="用药开始日期")
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, comment="用药结束日期，NULL 表示仍在用药")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), comment="记录创建时间"
    )

    patient: Mapped["Patient"] = relationship(back_populates="medications")


class Observation(Base):
    """
    观测/检验表 — 对应 FHIR Observation 资源

    存储生命体征、实验室检验等量化测量结果。
    """

    __tablename__ = "observations"
    __table_args__ = (
        Index("idx_observations_patient_type", "patient_id", "measurement_type"),
        {"comment": "患者观测/检验结果表 (FHIR: Observation)"},
    )

    observation_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="观测唯一标识")
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True, comment="关联患者 ID"
    )
    measurement_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="测量类型 (FHIR: Observation.code)"
    )
    value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, comment="测量数值")
    unit: Mapped[str] = mapped_column(String(32), nullable=False, comment="测量单位")
    date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True, comment="观测日期时间 (FHIR: Observation.effectiveDateTime)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), comment="记录创建时间"
    )

    patient: Mapped["Patient"] = relationship(back_populates="observations")
