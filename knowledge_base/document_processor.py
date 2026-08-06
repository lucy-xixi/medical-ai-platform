#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档预处理模块 (Document Processor)

对采集的临床知识文本进行清洗、切分，输出 processed_documents.json。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import List

KB_ROOT = Path(__file__).resolve().parent
if str(KB_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(KB_ROOT.parent))

from knowledge_base.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE_MAX,
    CHUNK_SIZE_MIN,
    PROCESSED_JSON,
)
from knowledge_base.ingestion import DocumentRecord, ingest_documents
from knowledge_base.logger import setup_logger

logger = setup_logger("knowledge_base.processor")


def clean_text(text: str) -> str:
    """
    文本清洗：去除多余空白、特殊控制字符，统一换行。
    """
    # 去除 BOM 及控制字符
    text = text.replace("\ufeff", "")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    # 统一换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 合并多余空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 去除行首尾空白
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def split_into_chunks(
    text: str,
    chunk_min: int = CHUNK_SIZE_MIN,
    chunk_max: int = CHUNK_SIZE_MAX,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """
    将文本切分为 500～800 字符的块，重叠 100 字符。

    优先按段落边界切分，保证语义完整性。
    """
    chunks: List[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_max, text_len)

        # 若剩余不足最小块长，直接取至末尾
        if text_len - start <= chunk_max:
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        # 在 [chunk_min, chunk_max] 窗口内寻找最佳断点（段落或句号）
        search_start = start + chunk_min
        search_end = end
        window = text[search_start:search_end]

        break_pos = -1
        for sep in ["\n\n", "。", "；", "\n", "，"]:
            pos = window.rfind(sep)
            if pos != -1:
                break_pos = search_start + pos + len(sep)
                break

        if break_pos == -1 or break_pos <= start:
            break_pos = end

        chunk = text[start:break_pos].strip()
        if chunk:
            chunks.append(chunk)

        # 下一块起点（保留 overlap）
        start = max(break_pos - overlap, start + 1)

    return chunks


def process_documents(document_list: List[DocumentRecord]) -> List[dict]:
    """
    处理全部文档，生成带 id 的 chunk 列表。

    Returns:
        [{"id": 1, "text": "...", "source": "xxx.txt"}, ...]
    """
    logger.info("========== 文档预处理开始 ==========")
    processed: List[dict] = []
    chunk_id = 1

    for doc in document_list:
        cleaned = clean_text(doc["content"])
        chunks = split_into_chunks(cleaned)
        logger.info("切分 | %s | 原始: %d 字符 -> %d 块", doc["filename"], len(cleaned), len(chunks))

        for chunk in chunks:
            processed.append(
                {
                    "id": chunk_id,
                    "text": chunk,
                    "source": doc["filename"],
                }
            )
            chunk_id += 1

    logger.info("文档预处理完成 | 总块数: %d", len(processed))
    return processed


def save_processed(processed: List[dict], output_path: Path | None = None) -> Path:
    """保存 processed_documents.json。"""
    out = output_path or PROCESSED_JSON
    out.write_text(json.dumps(processed, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("已保存: %s", out)
    return out


def load_processed(input_path: Path | None = None) -> List[dict]:
    """加载 processed_documents.json。"""
    path = input_path or PROCESSED_JSON
    if not path.exists():
        raise FileNotFoundError(f"预处理文件不存在: {path}，请先运行 document_processor.py")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    """命令行入口。"""
    try:
        docs = ingest_documents()
        processed = process_documents(docs)
        save_processed(processed)
        print(f"Processed {len(processed)} chunks -> {PROCESSED_JSON.name}")
        return 0
    except Exception as exc:
        logger.exception("文档预处理失败: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
