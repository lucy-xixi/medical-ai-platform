# -*- coding: utf-8 -*-
"""
患者数据检索器

从数据仓库 warehouse.db 检索结构化临床与运营数据（只读）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

import pandas as pd

from rag.logger import setup_logger
from warehouse.models import warehouse_engine

logger = setup_logger("rag.patient_retriever")


@dataclass
class PatientDataContext:
    """患者数据检索结果。"""

    snippets: List[str] = field(default_factory=list)
    source: str = "warehouse/warehouse.db"

    def to_text(self) -> str:
        if not self.snippets:
            return "（未检索到相关结构化患者数据）"
        return "\n".join(f"- {s}" for s in self.snippets)


def _query(sql: str) -> pd.DataFrame:
    """执行只读 SQL 查询。"""
    return pd.read_sql(sql, warehouse_engine)


def _match_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(kw in text for kw in keywords)


def retrieve_patient_data(question: str) -> PatientDataContext:
    """
    根据用户问题从数据仓库检索相关患者/临床统计数据。

    支持意图：
        - 患者总数 / 人口统计
        - 疾病分布 / Top 疾病
        - 用药排名
        - 实验室指标（HbA1c、血压、肌酐）
        - 医院 KPI
        - 指定 patient_id 信息
    """
    logger.info("检索患者数据 | 问题: %s", question)
    ctx = PatientDataContext()
    q = question.lower()

    try:
        # 患者总数与性别分布
        if _match_any(q, ("患者", "病人", "patient", "总数", "多少人", "人口")):
            total = _query("SELECT COUNT(*) AS cnt FROM dim_patient").iloc[0]["cnt"]
            gender = _query(
                """
                SELECT gender, COUNT(*) AS cnt
                FROM dim_patient
                GROUP BY gender
                ORDER BY cnt DESC
                """
            )
            gender_text = ", ".join(f"{r['gender']}:{r['cnt']}" for _, r in gender.iterrows())
            ctx.snippets.append(f"患者总数: {total}；性别分布: {gender_text}")

            age = _query(
                """
                SELECT age_group, COUNT(*) AS cnt
                FROM dim_patient
                GROUP BY age_group
                ORDER BY age_group
                """
            )
            age_text = ", ".join(f"{r['age_group']}:{r['cnt']}" for _, r in age.iterrows())
            ctx.snippets.append(f"年龄分组: {age_text}")

        # 疾病 / 诊断
        if _match_any(q, ("疾病", "诊断", "icd", "病", "糖尿病", "高血压", "disease", "condition")):
            top_diseases = _query(
                """
                SELECT dc.condition_name, dc.icd_code, COUNT(DISTINCT fc.patient_key) AS patient_count
                FROM fact_condition fc
                JOIN dim_condition dc ON fc.condition_key = dc.condition_key
                GROUP BY dc.condition_name, dc.icd_code
                ORDER BY patient_count DESC
                LIMIT 5
                """
            )
            for _, row in top_diseases.iterrows():
                ctx.snippets.append(
                    f"疾病「{row['condition_name']}」(ICD:{row['icd_code']}) 患者数: {row['patient_count']}"
                )

        # 用药
        if _match_any(q, ("药", "用药", "medication", "drug", "metformin", "二甲双胍", "胰岛素")):
            top_meds = _query(
                """
                SELECT dm.drug_name, COUNT(*) AS usage_count,
                       COUNT(DISTINCT fm.patient_key) AS patient_count
                FROM fact_medication fm
                JOIN dim_medication dm ON fm.medication_key = dm.medication_key
                GROUP BY dm.drug_name
                ORDER BY usage_count DESC
                LIMIT 5
                """
            )
            for _, row in top_meds.iterrows():
                ctx.snippets.append(
                    f"药物「{row['drug_name']}」使用次数: {row['usage_count']}，涉及患者: {row['patient_count']}"
                )

        # 实验室 / 观测指标
        if _match_any(q, ("hba1c", "糖化", "血压", "blood pressure", "肌酐", "creatinine", "实验室", "指标", "检验")):
            lab_types = [
                ("hba1c", "HbA1c"),
                ("systolic_blood_pressure", "收缩压"),
                ("diastolic_blood_pressure", "舒张压"),
                ("creatinine", "肌酐"),
            ]
            for mtype, label in lab_types:
                if mtype.replace("_", " ") in q or label.lower() in q or mtype in q:
                    stats = _query(
                        f"""
                        SELECT COUNT(*) AS cnt,
                               ROUND(AVG(value), 2) AS avg_val,
                               ROUND(MIN(value), 2) AS min_val,
                               ROUND(MAX(value), 2) AS max_val
                        FROM fact_observation
                        WHERE measurement_type = '{mtype}'
                        """
                    )
                    if stats.iloc[0]["cnt"] > 0:
                        r = stats.iloc[0]
                        ctx.snippets.append(
                            f"{label} 统计 (n={int(r['cnt'])}): 均值={r['avg_val']}, "
                            f"范围=[{r['min_val']}, {r['max_val']}]"
                        )

        # 就诊 / KPI
        if _match_any(q, ("就诊", "encounter", "kpi", "运营", "门诊", "住院")):
            kpi = _query(
                """
                SELECT
                    (SELECT COUNT(*) FROM dim_patient) AS patients,
                    (SELECT COUNT(*) FROM fact_encounter) AS encounters,
                    (SELECT COUNT(*) FROM fact_condition) AS conditions,
                    (SELECT COUNT(*) FROM fact_medication) AS medications,
                    (SELECT COUNT(*) FROM fact_observation) AS observations
                """
            ).iloc[0]
            ctx.snippets.append(
                f"医院 KPI: 患者={kpi['patients']}, 就诊={kpi['encounters']}, "
                f"诊断记录={kpi['conditions']}, 用药记录={kpi['medications']}, "
                f"检验记录={kpi['observations']}"
            )

            enc_types = _query(
                """
                SELECT encounter_type, COUNT(*) AS cnt
                FROM fact_encounter
                GROUP BY encounter_type
                ORDER BY cnt DESC
                """
            )
            enc_text = ", ".join(f"{r['encounter_type']}:{r['cnt']}" for _, r in enc_types.iterrows())
            ctx.snippets.append(f"就诊类型分布: {enc_text}")

        # 指定 patient_id
        pid_match = re.search(r"(?:patient[_\s]?id|患者\s*id|患者编号)\s*[:：]?\s*(\d+)", q, re.I)
        if not pid_match:
            pid_match = re.search(r"\b(\d{4,6})\b", question)
        if pid_match:
            pid = int(pid_match.group(1))
            patient = _query(f"SELECT * FROM dim_patient WHERE patient_id = {pid}")
            if not patient.empty:
                p = patient.iloc[0]
                ctx.snippets.append(
                    f"患者 ID={pid}: 性别={p['gender']}, 出生年={p['birth_year']}, 年龄段={p['age_group']}"
                )
                conditions = _query(
                    f"""
                    SELECT dc.condition_name, dc.icd_code
                    FROM fact_condition fc
                    JOIN dim_condition dc ON fc.condition_key = dc.condition_key
                    JOIN dim_patient dp ON fc.patient_key = dp.patient_key
                    WHERE dp.patient_id = {pid}
                    LIMIT 5
                    """
                )
                if not conditions.empty:
                    conds = "; ".join(f"{r['condition_name']}({r['icd_code']})" for _, r in conditions.iterrows())
                    ctx.snippets.append(f"该患者诊断: {conds}")

        # 若无明确意图，返回基础 KPI 摘要
        if not ctx.snippets:
            total = _query("SELECT COUNT(*) AS cnt FROM dim_patient").iloc[0]["cnt"]
            ctx.snippets.append(f"数据仓库患者总数: {total}")
            top1 = _query(
                """
                SELECT dc.condition_name, COUNT(DISTINCT fc.patient_key) AS cnt
                FROM fact_condition fc
                JOIN dim_condition dc ON fc.condition_key = dc.condition_key
                GROUP BY dc.condition_name
                ORDER BY cnt DESC LIMIT 1
                """
            )
            if not top1.empty:
                ctx.snippets.append(f"最常见诊断: {top1.iloc[0]['condition_name']} ({top1.iloc[0]['cnt']} 人)")

    except Exception as exc:
        logger.warning("患者数据检索异常: %s", exc)
        ctx.snippets.append(f"（患者数据检索失败: {exc}）")

    logger.info("患者数据检索完成 | 片段数: %d", len(ctx.snippets))
    return ctx
