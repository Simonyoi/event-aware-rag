"""多模态解析：按扩展名分发到对应解析器。"""
from __future__ import annotations

import uuid
from pathlib import Path

from core.models import Chunk, SourceType
from .image_parser import ImageParser
from .pdf_parser import PdfParser
from .table_parser import TableParser

_PARSERS = {
    "pdf": PdfParser(),
    "csv": TableParser(),
    "xlsx": TableParser(),
    "xls": TableParser(),
    "png": ImageParser(),
    "jpg": ImageParser(),
    "jpeg": ImageParser(),
    "webp": ImageParser(),
}


def parse_file(
    file_path: str,
    doc_id: str,
    period: str,
    source_type: SourceType,
    **kwargs,
) -> list[Chunk]:
    """按文件扩展名分发解析。"""
    ext = Path(file_path).suffix.lower().lstrip(".")
    parser = _PARSERS.get(ext)
    if parser is None:
        # 未知类型回退为纯文本读取
        text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        return [
            Chunk(
                chunk_id=uuid.uuid4().hex[:16],
                doc_id=doc_id,
                text=text,
                period=period,
                source_type=source_type,
                seq=0,
            )
        ]
    return parser.parse(file_path, doc_id, period, source_type, **kwargs)


__all__ = ["parse_file"]
