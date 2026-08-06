#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本向量化模块 (Embedding)

使用 sentence-transformers 将文档块转换为向量，保存 document_embeddings.npy。
若 sentence-transformers 导入失败，回退至 transformers 直接加载同一模型。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

# 避免 transformers 强制加载 torchvision（部分环境存在版本冲突）
os.environ.setdefault("TRANSFORMERS_NO_TORCHVISION", "1")

KB_ROOT = Path(__file__).resolve().parent
if str(KB_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(KB_ROOT.parent))

from knowledge_base.config import EMBEDDING_MODEL, EMBEDDINGS_NPY
from knowledge_base.document_processor import load_processed
from knowledge_base.logger import setup_logger

logger = setup_logger("knowledge_base.embedding")

_model = None
_backend = None


def _mean_pooling(model_output, attention_mask):
    """对 token embeddings 做 mean pooling。"""
    import torch

    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
        input_mask_expanded.sum(1), min=1e-9
    )


def _embed_with_transformers(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """通过 transformers 直接加载模型（回退方案）。"""
    import torch
    from transformers import AutoModel, AutoTokenizer

    logger.info("使用 transformers 回退加载: %s", EMBEDDING_MODEL)
    tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
    model = AutoModel.from_pretrained(EMBEDDING_MODEL)
    model.eval()

    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        encoded = tokenizer(batch, padding=True, truncation=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            output = model(**encoded)
            pooled = _mean_pooling(output, encoded["attention_mask"])
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
        all_embeddings.append(pooled.numpy())

    return np.vstack(all_embeddings).astype(np.float32)


def get_embedding_model():
    """懒加载 sentence-transformers 模型（支持中文）。"""
    global _model, _backend
    if _model is not None:
        return _model

    try:
        from sentence_transformers import SentenceTransformer

        logger.info("加载嵌入模型 (sentence-transformers): %s", EMBEDDING_MODEL)
        _model = SentenceTransformer(EMBEDDING_MODEL)
        _backend = "sentence_transformers"
        return _model
    except Exception as exc:
        logger.warning("sentence-transformers 加载失败，将使用 transformers 回退: %s", exc)
        _model = "transformers_fallback"
        _backend = "transformers"
        return _model


def embed_texts(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """
    将文本列表编码为向量矩阵。

    Returns:
        shape (n_texts, embedding_dim) 的 numpy 数组
    """
    logger.info("开始向量化 | 文本数: %d", len(texts))
    model = get_embedding_model()

    if _backend == "sentence_transformers":
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 10,
            normalize_embeddings=True,
        )
        return np.array(embeddings, dtype=np.float32)

    return _embed_with_transformers(texts, batch_size)


def embed_query(query: str) -> np.ndarray:
    """将单个查询问题编码为向量。"""
    return embed_texts([query], batch_size=1)


def build_embeddings(processed_path: Path | None = None) -> np.ndarray:
    """读取 processed_documents.json 并生成 embeddings。"""
    logger.info("========== 向量化开始 ==========")
    processed = load_processed(processed_path)
    texts = [item["text"] for item in processed]
    embeddings = embed_texts(texts)
    logger.info("向量化完成 | shape: %s", embeddings.shape)
    return embeddings


def save_embeddings(embeddings: np.ndarray, output_path: Path | None = None) -> Path:
    """保存 document_embeddings.npy。"""
    out = output_path or EMBEDDINGS_NPY
    np.save(out, embeddings)
    logger.info("已保存: %s", out)
    return out


def load_embeddings(input_path: Path | None = None) -> np.ndarray:
    """加载 document_embeddings.npy。"""
    path = input_path or EMBEDDINGS_NPY
    if not path.exists():
        raise FileNotFoundError(f"向量文件不存在: {path}，请先运行 embedding.py")
    return np.load(path)


def main() -> int:
    """命令行入口。"""
    try:
        embeddings = build_embeddings()
        save_embeddings(embeddings)
        print(f"Embeddings saved: {EMBEDDINGS_NPY.name} shape={embeddings.shape}")
        return 0
    except Exception as exc:
        logger.exception("向量化失败: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
