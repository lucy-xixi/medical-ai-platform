#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clinical RAG Assistant — 临床 RAG 智能助手

架构:
    User Question
         ↓
    Clinical RAG Assistant
         ↓
    ┌────────────────┬─────────────────┐
    Patient Data     Medical Knowledge
    (Warehouse)      (FAISS Vector DB)
         ↓                   ↓
         └──── Context Retrieval ────┘
                     ↓
               LLM Response

运行:
    python rag/clinical_rag.py
    python rag/clinical_rag.py "糖尿病患者HbA1c多少需要关注？"
    python rag/clinical_rag.py --interactive
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.context_builder import build_context
from rag.knowledge_retriever import retrieve_knowledge
from rag.llm_response import generate_response
from rag.logger import LOG_FILE, setup_logger
from rag.patient_retriever import retrieve_patient_data

logger = setup_logger("rag.assistant")


def ask(question: str, top_k: int = 3, verbose: bool = False) -> str:
    """
    Clinical RAG 主流程。

    Args:
        question: 用户问题
        top_k: 知识库检索数量
        verbose: 是否打印上下文摘要

    Returns:
        LLM 生成的回答
    """
    logger.info("========== Clinical RAG 开始 ==========")
    logger.info("用户问题: %s", question)

    # 1. 双路检索
    patient_data = retrieve_patient_data(question)
    knowledge = retrieve_knowledge(question, top_k=top_k)

    # 2. 上下文构建
    context = build_context(question, patient_data, knowledge)

    if verbose:
        print(context.build_context_summary())
        print()

    # 3. LLM 回答
    prompt = context.build_prompt()
    answer = generate_response(
        prompt,
        question=question,
        patient_text=patient_data.to_text(),
        knowledge_text=knowledge.to_text(),
    )

    logger.info("========== Clinical RAG 完成 ==========")
    return answer


def interactive_mode(top_k: int = 3) -> None:
    """交互式问答模式。"""
    print("=" * 60)
    print("Clinical RAG Assistant — 临床 RAG 智能助手")
    print("输入问题（输入 quit 退出）")
    print("=" * 60)

    while True:
        try:
            question = input("\n您的问题: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("再见。")
            break

        answer = ask(question, top_k=top_k, verbose=True)
        print("\n" + answer)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clinical RAG Assistant")
    parser.add_argument("question", nargs="*", help="用户问题")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--top-k", type=int, default=3, help="知识检索 Top K")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示检索上下文")
    args = parser.parse_args()

    logger.info("日志文件: %s", LOG_FILE)

    try:
        if args.interactive:
            interactive_mode(top_k=args.top_k)
            return 0

        question = " ".join(args.question) if args.question else "糖尿病患者HbA1c多少需要关注？"
        answer = ask(question, top_k=args.top_k, verbose=args.verbose)
        print("\n" + answer)
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        print("请先构建数据仓库与知识库:", file=sys.stderr)
        print("  python warehouse/build_warehouse.py", file=sys.stderr)
        print("  python knowledge_base/vector_store.py", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("RAG 失败: %s", exc)
        print(f"RAG failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
