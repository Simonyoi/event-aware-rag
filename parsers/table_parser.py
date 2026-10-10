"""表格解析：pandas 读取，按「表头语义 + 结构化记录」转文本块。"""
from __future__ import annotations

import uuid
from pathlib import Path

import pandas as pd

from core.models import Chunk, SourceType
from .base import BaseParser


class TableParser(BaseParser):
    """CSV / Excel。每行转成「列名=值」的结构化记录，保留表头上下文，避免 LLM 误解数值含义。"""

    def parse(
        self,
        file_path: str,
        doc_id: str,
        period: str,
        source_type: SourceType,
        **kwargs,
    ) -> list[Chunk]:
        title = kwargs.get("title") or Path(file_path).stem
        if str(file_path).lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        columns = [str(c) for c in df.columns]
        header = f"表格「{title}」（{period}）。列：{'、'.join(columns)}"
        rows_per_chunk = kwargs.get("rows_per_chunk", 10)

        chunks: list[Chunk] = []
        buf: list[str] = []
        seq = 0

        def flush() -> None:
            nonlocal buf, seq
            if buf:
                text = header + "\n" + "\n".join(buf)
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
                seq += 1
                buf = []

        for _, row in df.iterrows():
            cells = [f"{c}={row[c]}" for c in columns if pd.notna(row[c])]
            if not cells:
                continue
            buf.append("；".join(cells))
            if len(buf) >= rows_per_chunk:
                flush()

        flush()
        return chunks
