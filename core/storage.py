"""存储层：Chroma（向量 + 时间过滤）+ SQLite（结构化元数据）。"""
from __future__ import annotations

import sqlite3

import chromadb

import config
from core.models import Chunk, Document, DocumentStatus, Fact, Metric

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    file_name TEXT,
    file_type TEXT,
    source_type TEXT,
    period TEXT,
    period_start TEXT,
    period_end TEXT,
    uploaded_at TEXT,
    status TEXT
);
CREATE TABLE IF NOT EXISTS metrics (
    metric_id TEXT PRIMARY KEY,
    chunk_id TEXT,
    doc_id TEXT,
    period TEXT,
    name TEXT,
    value REAL,
    unit TEXT,
    change TEXT,
    confidence REAL,
    evidence TEXT
);
CREATE TABLE IF NOT EXISTS facts (
    fact_id TEXT PRIMARY KEY,
    chunk_id TEXT,
    doc_id TEXT,
    period TEXT,
    subject TEXT,
    predicate TEXT,
    object TEXT,
    confidence REAL,
    evidence TEXT
);
CREATE INDEX IF NOT EXISTS idx_metrics_period ON metrics(period);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name);
CREATE INDEX IF NOT EXISTS idx_facts_period ON facts(period);
"""


def build_where(period: str | list[str] | None = None, source_type: str | None = None):
    """构造 Chroma metadata 过滤条件（时间标量过滤）。"""
    conds: list[dict] = []
    if period:
        if isinstance(period, (list, tuple)):
            conds.append({"period": {"$in": list(period)}})
        else:
            conds.append({"period": period})
    if source_type:
        conds.append({"source_type": source_type})
    if not conds:
        return None
    if len(conds) == 1:
        return conds[0]
    return {"$and": conds}


class Storage:
    """统一读写入口：向量进 Chroma，结构化元数据进 SQLite。"""

    def __init__(self) -> None:
        self.conn = sqlite3.connect(config.SQLITE_DB, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA_SQL)
        self.conn.commit()
        self.chroma = chromadb.PersistentClient(path=config.CHROMA_DIR)
        self.collection = self.chroma.get_or_create_collection(
            name=config.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    # ---------- Chroma（向量） ----------
    def insert_chunks(self, chunks: list[Chunk]) -> None:
        valid = [c for c in chunks if c.embedding is not None]
        if not valid:
            return
        self.collection.add(
            ids=[c.chunk_id for c in valid],
            embeddings=[c.embedding for c in valid],
            documents=[c.text for c in valid],
            metadatas=[
                {
                    "doc_id": c.doc_id,
                    "period": c.period,
                    "source_type": c.source_type.value,
                    "seq": c.seq,
                }
                for c in valid
            ],
        )

    def search(
        self,
        query_embedding: list[float],
        period: str | list[str] | None = None,
        source_type: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """按向量 + 时间/来源过滤检索。返回 dict 列表，distance 越小越相关（cosine）。"""
        where = build_where(period, source_type)
        kwargs = dict(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )
        if where:
            kwargs["where"] = where
        res = self.collection.query(**kwargs)

        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]

        out: list[dict] = []
        for i, cid in enumerate(ids):
            meta = metas[i] or {}
            out.append(
                {
                    "chunk_id": cid,
                    "doc_id": meta.get("doc_id", ""),
                    "text": docs[i] if i < len(docs) else "",
                    "period": meta.get("period", ""),
                    "source_type": meta.get("source_type", ""),
                    "distance": dists[i] if i < len(dists) else None,
                }
            )
        return out

    # ---------- SQLite ----------
    def insert_document(self, doc: Document) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO documents (doc_id, file_name, file_type, source_type, period, "
            "period_start, period_end, uploaded_at, status) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                doc.doc_id,
                doc.file_name,
                doc.file_type.value,
                doc.source_type.value,
                doc.period,
                doc.period_start.isoformat() if doc.period_start else None,
                doc.period_end.isoformat() if doc.period_end else None,
                doc.uploaded_at.isoformat(),
                doc.status.value,
            ),
        )
        self.conn.commit()

    def update_document_status(self, doc_id: str, status: DocumentStatus) -> None:
        self.conn.execute("UPDATE documents SET status = ? WHERE doc_id = ?", (status.value, doc_id))
        self.conn.commit()

    def insert_metrics(self, metrics: list[Metric]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO metrics (metric_id, chunk_id, doc_id, period, name, value, "
            "unit, change, confidence, evidence) VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                (m.metric_id, m.chunk_id, m.doc_id, m.period, m.name, m.value, m.unit, m.change,
                 m.confidence, m.evidence)
                for m in metrics
            ],
        )
        self.conn.commit()

    def insert_facts(self, facts: list[Fact]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO facts (fact_id, chunk_id, doc_id, period, subject, predicate, "
            "object, confidence, evidence) VALUES (?,?,?,?,?,?,?,?,?)",
            [
                (f.fact_id, f.chunk_id, f.doc_id, f.period, f.subject, f.predicate, f.object,
                 f.confidence, f.evidence)
                for f in facts
            ],
        )
        self.conn.commit()

    # ---------- 查询 ----------
    def query_metrics(self, period: str | None = None, name: str | None = None) -> list[Metric]:
        sql, params = "SELECT * FROM metrics WHERE 1=1", []
        if period:
            sql += " AND period = ?"
            params.append(period)
        if name:
            sql += " AND name = ?"
            params.append(name)
        return [Metric(**dict(r)) for r in self.conn.execute(sql, params).fetchall()]

    def query_facts(self, period: str | None = None) -> list[Fact]:
        sql, params = "SELECT * FROM facts WHERE 1=1", []
        if period:
            sql += " AND period = ?"
            params.append(period)
        return [Fact(**dict(r)) for r in self.conn.execute(sql, params).fetchall()]

    def get_documents(self) -> list[Document]:
        rows = self.conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
        return [Document(**dict(r)) for r in rows]

    def clear_all(self) -> None:
        """清空全部数据（评估/重置用）。"""
        try:
            self.chroma.delete_collection(config.CHROMA_COLLECTION)
        except Exception:
            pass
        self.collection = self.chroma.get_or_create_collection(
            name=config.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        for table in ("documents", "metrics", "facts"):
            self.conn.execute(f"DELETE FROM {table}")
        self.conn.commit()
