"""PDF 解析：pypdf 抽文本 → 分块。"""
from __future__ import annotations

import uuid

from pypdf import PdfReader

from core.models import Chunk, SourceType
from .base import BaseParser, split_text


class PdfParser(BaseParser):
    def parse(
        self,
        file_path: str,
        doc_id: str,
        period: str,
        source_type: SourceType,
        **kwargs,
    ) -> list[Chunk]:
        reader = PdfReader(file_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        raw = "\n\n".join(pages)
        chunks: list[Chunk] = []
        for seq, text in enumerate(
            split_text(raw, max_len=kwargs.get("max_len", 1200), overlap=kwargs.get("overlap", 120))
        ):
            chunks.append(
                Chunk(
                    chunk_id=uuid.uuid4().hex[:16],
                    doc_id=doc_id,
                    text=text,
                    period=period,
                    source_type=source_type,
                    seq=seq,
                )
            )
        return chunks
