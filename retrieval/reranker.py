"""重排：DashScope gte-rerank。失败时返回 None，调用方退回相似度排序。"""
from __future__ import annotations

from http import HTTPStatus

import dashscope

import config


def rerank(query: str, documents: list[str]) -> list[float] | None:
    """返回与 documents 对齐的相关性分数（越高越相关）；失败返回 None。"""
    if not documents:
        return []
    try:
        resp = dashscope.TextReRank.call(
            model=config.RERANK_MODEL,
            query=query,
            documents=documents,
            top_n=len(documents),
            api_key=config.DASHSCOPE_API_KEY,
        )
        if resp.status_code == HTTPStatus.OK:
            scores = [0.0] * len(documents)
            for item in resp.output.results:
                scores[item.index] = item.relevance_score
            return scores
    except Exception:
        pass
    return None
