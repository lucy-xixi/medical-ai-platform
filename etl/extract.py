# -*- coding: utf-8 -*-
"""
数据抽取模块 (Extract)

从 data/raw/ 目录读取原始 CSV 医疗数据文件。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from etl.logger import setup_logger

logger = setup_logger("etl.extract")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# 原始数据文件映射
RAW_FILES = {
    "patients": RAW_DIR / "patients.csv",
    "conditions": RAW_DIR / "conditions.csv",
    "medications": RAW_DIR / "medications.csv",
}


def _read_csv(file_path: Path, name: str) -> pd.DataFrame:
    """
    读取单个 CSV 文件，检查存在性并记录日志。

    Args:
        file_path: CSV 文件路径
        name: 数据集名称（用于日志）

    Returns:
        读取的 DataFrame

    Raises:
        FileNotFoundError: 文件不存在
    """
    if not file_path.exists():
        msg = f"原始数据文件不存在: {file_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    df = pd.read_csv(file_path, dtype=str, keep_default_na=True)
    logger.info("文件读取成功 | %s | 路径: %s | 行数: %d", name, file_path, len(df))
    return df


def extract_patients() -> pd.DataFrame:
    """抽取患者原始数据。"""
    return _read_csv(RAW_FILES["patients"], "patients")


def extract_conditions() -> pd.DataFrame:
    """抽取诊断原始数据。"""
    return _read_csv(RAW_FILES["conditions"], "conditions")


def extract_medications() -> pd.DataFrame:
    """抽取用药原始数据。"""
    return _read_csv(RAW_FILES["medications"], "medications")


def extract_all() -> Dict[str, pd.DataFrame]:
    """
    抽取全部原始医疗数据。

    Returns:
        包含 patients / conditions / medications 三个 DataFrame 的字典
    """
    logger.info("========== Extract 阶段开始 ==========")

    data = {
        "patients": extract_patients(),
        "conditions": extract_conditions(),
        "medications": extract_medications(),
    }

    total = sum(len(df) for df in data.values())
    logger.info("Extract 完成 | 合计读取 %d 行", total)
    return data
