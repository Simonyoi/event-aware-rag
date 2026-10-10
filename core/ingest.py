"""入库链路编排：解析 → 抽取 → 向量化 → 入库。"""
from __future__ import annotations

import uuid
from pathlib import Path

from core.embeddings import embed_texts
from core.models import Document, DocumentStatus, FileType, SourceType
from core.storage import Storage
from extraction import extract
from parsers import parse_file

_EXT_TO_FILETYPE = {
    ".pdf": FileType.pdf,
    ".csv": FileType.csv,
    ".xlsx": FileType.xlsx,
    ".xls": FileType.xlsx,
    ".png": FileType.png,
    ".jpg": FileType.jpg,
    ".jpeg": FileType.jpeg,
    ".webp": FileType.webp,
    ".txt": FileType.txt,
}


def _file_type(path: str) -> FileType:
    return _EXT_TO_FILETYPE.get(Path(path).suffix.lower(), FileType.txt)


def ingest_file(
    storage: Storage,
    file_path: str,
    period: str,
    source_type: SourceType,
    doc_id: str | None = None,
    title: str | None = None,
) -> dict:
    """解析单个文件并入库（文档/块/指标/事实），返回摘要统计。"""
    doc_id = doc_id or uuid.uuid4().hex[:16]
    doc = Document(
        doc_id=doc_id,
        file_name=Path(file_path).name,
        file_type=_file_type(file_path),
        source_type=source_type,
        period=period,
        status=DocumentStatus.parsing,
    )
    storage.insert_document(doc)

    chunks = parse_file(file_path, doc_id, period, source_type, title=title)
    if not chunks:
        storage.update_document_status(doc_id, DocumentStatus.failed)
        return {"doc_id": doc_id, "chunks": 0, "metrics": 0, "facts": 0, "status": "failed"}

    embeddings = embed_texts([c.text for c in chunks])
    for c, emb in zip(chunks, embeddings):
        c.embedding = emb
    storage.insert_chunks(chunks)

    metrics: list = []
    facts: list = []
    for c in chunks:
        ms, fs = extract(c)
        metrics += ms
        facts += fs
    storage.insert_metrics(metrics)
    storage.insert_facts(facts)

    storage.update_document_status(doc_id, DocumentStatus.indexed)
    return {
        "doc_id": doc_id,
        "chunks": len(chunks),
        "metrics": len(metrics),
        "facts": len(facts),
        "status": "indexed",
    }
