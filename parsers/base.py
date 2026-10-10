"""解析器统一接口 + 通用文本切分。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from core.models import Chunk, SourceType


class BaseParser(ABC):
    """所有解析器实现此接口：文件 → list[Chunk]。"""

    @abstractmethod
    def parse(
        self,
        file_path: str,
        doc_id: str,
        period: str,
        source_type: SourceType,
        **kwargs,
    ) -> list[Chunk]:
        ...


def split_text(text: str, max_len: int = 1200, overlap: int = 120) -> list[str]:
    """按固定窗口切分文本，带重叠。中文无空格，简单滑窗足够。"""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_len:
        return [text]
    out: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_len, len(text))
        out.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return out
