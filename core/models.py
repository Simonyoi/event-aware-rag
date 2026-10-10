"""数据模型：Document / Chunk / Metric / Fact（Pydantic）。"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    financial_report = "financial_report"
    sales_data = "sales_data"
    competitor_news = "competitor_news"
    screenshot = "screenshot"
    other = "other"


class FileType(str, Enum):
    pdf = "pdf"
    csv = "csv"
    xlsx = "xlsx"
    png = "png"
    jpg = "jpg"
    jpeg = "jpeg"
    webp = "webp"
    txt = "txt"


class DocumentStatus(str, Enum):
    parsing = "parsing"
    indexed = "indexed"
    failed = "failed"


class Document(BaseModel):
    """一次上传的文件，带时间标签 period。"""

    doc_id: str
    file_name: str
    file_type: FileType
    source_type: SourceType
    period: str  # 时间标签，如 "2025Q2"
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    uploaded_at: datetime = Field(default_factory=datetime.now)
    status: DocumentStatus = DocumentStatus.parsing


class Chunk(BaseModel):
    """可检索的最小文本单元，继承 Document 的 period。"""

    chunk_id: str
    doc_id: str
    text: str
    period: str
    source_type: SourceType
    seq: int
    embedding: Optional[list[float]] = None  # 第 3 步由 embeddings 填充


class Metric(BaseModel):
    """数值指标，参与环比/同比计算。"""

    metric_id: str
    chunk_id: str
    doc_id: str
    period: str
    name: str  # 如 "留存率" "MRR" "付费用户数"
    value: float
    unit: str = ""  # 如 "%" "万元" "人"
    change: Optional[str] = None  # up / down / flat
    confidence: float = 1.0
    evidence: str = ""  # 原始文本片段，溯源用


class Fact(BaseModel):
    """非数值事实/事件，参与归因叙述。"""

    fact_id: str
    chunk_id: str
    doc_id: str
    period: str
    subject: str  # 如 "竞品X"
    predicate: str  # 如 "降价" "发布新品" "服务故障"
    object: str = ""
    confidence: float = 1.0
    evidence: str = ""
