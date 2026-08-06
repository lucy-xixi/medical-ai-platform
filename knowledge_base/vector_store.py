#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量索引模块 (Vector Store)

使用 FAISS 建立向量索引并持久化保存。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import faiss
import numpy as np

KB_ROOT = Path(__file__).resolve().parent
if str(KB_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(KB_ROOT.parent))

from knowledge_base.config import FAISS_INDEX, METADATA_JSON, VECTOR_STORE_DIR
from knowledge_base.document_processor import load_processed
from knowledge_base.embedding import build_embeddings, load_embeddings
from knowledge_base.logger import setup_logger

logger = setup_logger("knowledge_base.vector_store")


def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    """
    创建 FAISS 索引（内积检索，向量已归一化等价于余弦相似度）。
    """
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    logger.info("FAISS 索引创建完成 | 向量数: %d | 维度: %d", index.ntotal, dim)
    return index


def save_index(index: faiss.Index, processed: list[dict]) -> None:
    """保存 faiss.index 及 metadata.json。"""
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(FAISS_INDEX))

    metadata = {
        "total_chunks": len(processed),
        "embedding_dim": index.d,
        "chunks": processed,
    }
    METADATA_JSON.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("已保存索引: %s", FAISS_INDEX)
    logger.info("已保存元数据: %s", METADATA_JSON)


def load_index() -> tuple[faiss.Index, list[dict]]:
    """加载 FAISS 索引与 chunk 元数据。"""
    if not FAISS_INDEX.exists():
        raise FileNotFoundError(f"FAISS 索引不存在: {FAISS_INDEX}，请先运行 vector_store.py")
    index = faiss.read_index(str(FAISS_INDEX))
    metadata = json.loads(METADATA_JSON.read_text(encoding="utf-8"))
    chunks = metadata["chunks"]
    return index, chunks


def build_and_save_vector_store() -> faiss.Index:
    """完整构建向量库。"""
    logger.info("========== 向量库构建开始 ==========")
    processed = load_processed()

    from knowledge_base.config import EMBEDDINGS_NPY

    if EMBEDDINGS_NPY.exists():
        embeddings = load_embeddings()
    else:
        embeddings = build_embeddings()

    index = build_faiss_index(embeddings)
    save_index(index, processed)
    logger.info("========== 向量库构建完成 ==========")
    return index


def main() -> int:
    """命令行入口。"""
    try:
        build_and_save_vector_store()
        print("Clinical Knowledge Base created successfully.")
        return 0
    except Exception as exc:
        logger.exception("向量库构建失败: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
