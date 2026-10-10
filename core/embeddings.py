"""Embedding：DashScope text-embedding-v3（批量调用）。"""
from __future__ import annotations

from http import HTTPStatus

import dashscope

import config

_BATCH_SIZE = 10  # 单次批量条数（保守值，避免超限）


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量向量化，返回与输入顺序一致的向量列表。"""
    if not texts:
        return []
    if not config.DASHSCOPE_API_KEY:
        raise RuntimeError(
            "未配置 DASHSCOPE_API_KEY：请在项目根目录复制 .env.example 为 .env 并填入真实 Key。"
        )
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        resp = dashscope.TextEmbedding.call(
            model=config.EMBEDDING_MODEL,
            input=batch,
            dimension=config.EMBEDDING_DIM,
            api_key=config.DASHSCOPE_API_KEY,
        )
        if resp.status_code != HTTPStatus.OK:
            raise RuntimeError(f"embedding 失败：{getattr(resp, 'message', resp)}")
        items = sorted(resp.output["embeddings"], key=lambda e: e.get("text_index", 0))
        out.extend(item["embedding"] for item in items)
    return out


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
