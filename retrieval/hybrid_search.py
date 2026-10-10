"""混合检索：时间过滤 + 语义相似度 + 重排。"""
from __future__ import annotations

from pydantic import BaseModel

from core.embeddings import embed_query
from core.storage import Storage
from retrieval.reranker import rerank


class SearchResult(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    period: str
    source_type: str
    score: float


def hybrid_search(
    storage: Storage,
    query: str,
    period: str | list[str] | None = None,
    source_type: str | None = None,
    top_k: int = 5,
    recall_k: int = 20,
) -> list[SearchResult]:
    """时间过滤 + 语义召回（recall_k）→ 重排 → 返回 top_k。"""
    q_emb = embed_query(query)
    hits = storage.search(q_emb, period=period, source_type=source_type, limit=recall_k)
    if not hits:
        return []

    texts = [h["text"] for h in hits]
    scores = rerank(query, texts)
    if scores is None:
        # 重排失败 → 退回余弦相似度（1 - distance，越大越相关）
        scores = [1 - (h["distance"] or 0) for h in hits]

    ranked = sorted(zip(hits, scores), key=lambda x: x[1], reverse=True)[:top_k]
    return [
        SearchResult(
            chunk_id=h["chunk_id"],
            doc_id=h["doc_id"],
            text=h["text"],
            period=h["period"],
            source_type=h["source_type"],
            score=round(s, 4),
        )
        for h, s in ranked
    ]
