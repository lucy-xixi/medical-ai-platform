# -*- coding: utf-8 -*-
"""临床知识库路径常量（均相对于 knowledge_base/ 目录）。"""

from pathlib import Path

KB_ROOT = Path(__file__).resolve().parent

DOCUMENTS_DIR = KB_ROOT / "documents"
PROCESSED_JSON = KB_ROOT / "processed_documents.json"
EMBEDDINGS_NPY = KB_ROOT / "document_embeddings.npy"
VECTOR_STORE_DIR = KB_ROOT / "vector_store"
FAISS_INDEX = VECTOR_STORE_DIR / "faiss.index"
METADATA_JSON = VECTOR_STORE_DIR / "metadata.json"

# 文本切分参数
CHUNK_SIZE_MIN = 500
CHUNK_SIZE_MAX = 800
CHUNK_OVERLAP = 100

# 嵌入模型
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# 检索默认 Top K
DEFAULT_TOP_K = 3
