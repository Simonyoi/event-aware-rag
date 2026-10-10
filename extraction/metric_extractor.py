"""指标/事实抽取：qwen-plus 结构化输出（JSON Schema），从 chunk 抽取 Metric 与 Fact。"""
from __future__ import annotations

import uuid
from typing import Literal, Optional

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from core.llm import get_chat_llm
from core.models import Chunk, Fact, Metric


class MetricSchema(BaseModel):
    name: str = Field(description="指标名，如 留存率、MRR、付费用户数")
    value: float = Field(description="数值")
    unit: str = Field("", description="单位，如 %、万元、人")
    change: Optional[Literal["up", "down", "flat"]] = Field(
        None, description="变化方向，仅当文本明确提到时填写"
    )
    confidence: float = Field(1.0, description="抽取置信度 0~1")


class FactSchema(BaseModel):
    subject: str = Field(description="主体，如 竞品X、公司、市场")
    predicate: str = Field(description="动作或变化，如 降价、发布新品、服务故障")
    object: str = Field("", description="客体")
    confidence: float = Field(1.0, description="抽取置信度 0~1")


class ExtractionSchema(BaseModel):
    metrics: list[MetricSchema] = Field(default_factory=list)
    facts: list[FactSchema] = Field(default_factory=list)


_SYSTEM = (
    "你是数据抽取助手。从给定文本中抽取「数值指标」和「事实/事件」。"
    "只抽取文本中明确出现的内容，不要臆造；数值要保留单位。"
)

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM),
        ("human", "文本：\n{text}\n\n时间标签：{period}"),
    ]
)


def extract(chunk: Chunk) -> tuple[list[Metric], list[Fact]]:
    """抽取一个 chunk 中的指标与事实。返回 (metrics, facts)。"""
    structured_llm = get_chat_llm().with_structured_output(ExtractionSchema, method="function_calling")
    result: ExtractionSchema = (_PROMPT | structured_llm).invoke(
        {"text": chunk.text, "period": chunk.period}
    )

    metrics = [
        Metric(
            metric_id=uuid.uuid4().hex[:12],
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            period=chunk.period,
            name=m.name,
            value=m.value,
            unit=m.unit,
            change=m.change,
            confidence=m.confidence,
            evidence=chunk.text[:200],
        )
        for m in result.metrics
    ]
    facts = [
        Fact(
            fact_id=uuid.uuid4().hex[:12],
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            period=chunk.period,
            subject=f.subject,
            predicate=f.predicate,
            object=f.object,
            confidence=f.confidence,
            evidence=chunk.text[:200],
        )
        for f in result.facts
    ]
    return metrics, facts
