"""对比归因引擎：收集 Agent 证据 → qwen-max 生成结构化 JSON 报告。"""
from __future__ import annotations

import json
from typing import Optional

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from agent.agent import extract_trace
from core.llm import get_reason_llm


# ---------- 报告 Schema ----------
class TimelineMetric(BaseModel):
    name: str
    value: float


class TimelineItem(BaseModel):
    period: str
    facts: list[str] = Field(default_factory=list)
    metrics: list[TimelineMetric] = Field(default_factory=list)


class Change(BaseModel):
    metric: str
    a: float
    b: float
    change_pct: Optional[float] = None
    direction: str = "flat"


class Cause(BaseModel):
    cause: str
    confidence: float = Field(description="0~1 置信度")
    supporting_evidence: list[str] = Field(default_factory=list)
    counter_evidence: list[str] = Field(default_factory=list)


class Suggestion(BaseModel):
    suggestion: str
    rationale: str = ""


class EvidenceRef(BaseModel):
    chunk_id: str
    snippet: str = ""


class Report(BaseModel):
    question: str
    answer: str = Field(description="对用户问题的直接、简洁回答")
    timeline: list[TimelineItem] = Field(default_factory=list)
    changes: list[Change] = Field(default_factory=list)
    causes: list[Cause] = Field(default_factory=list)
    suggestions: list[Suggestion] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


_SYSTEM = """你是资深 SaaS 数据分析师。基于给定的【证据】回答用户问题，输出结构化分析报告。
要求：
1. 先用 answer 字段直接、简洁地回答用户问题；
2. 识别证据中不同时间片的变化（changes）；
3. 每个可能原因给出置信度（0~1）与支持/反对证据的 chunk_id；
4. 给出最多 3 条可执行建议；
5. 这是「相关性与证据链」分析，不是统计因果；证据不足时降低置信度并说明，不要臆造。"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM),
        ("human", "用户问题：{question}\n\n证据：\n{evidence}"),
    ]
)


def collect_evidence(messages) -> dict:
    """从 Agent 消息轨迹中收集工具输出，作为归因证据。"""
    name_by_id = {}
    for m in messages:
        if isinstance(m, AIMessage):
            for tc in m.tool_calls or []:
                name_by_id[tc["id"]] = tc["name"]

    evidence = {"search_results": [], "comparisons": []}
    for m in messages:
        if isinstance(m, ToolMessage):
            name = name_by_id.get(m.tool_call_id, "")
            try:
                data = json.loads(m.content)
            except (json.JSONDecodeError, TypeError):
                continue
            if name == "search_knowledge" and isinstance(data, list):
                evidence["search_results"].extend(data)
            elif isinstance(data, dict):
                evidence["comparisons"].append(data)
    return evidence


def generate_report(question: str, evidence: dict) -> dict:
    """qwen-max 生成结构化报告。"""
    structured = get_reason_llm().with_structured_output(Report, method="function_calling")
    report: Report = (_PROMPT | structured).invoke(
        {"question": question, "evidence": json.dumps(evidence, ensure_ascii=False)}
    )
    return report.model_dump()


def analyze(agent, question: str) -> dict:
    """两步：Agent 检索取证 → 归因引擎生成报告。附带 _trace（思考过程）。"""
    result = agent.invoke({"messages": [("user", question)]})
    messages = result["messages"]
    evidence = collect_evidence(messages)
    report = generate_report(question, evidence)
    report["_trace"] = extract_trace(messages)
    return report


# ---------- Markdown 渲染（供 st.write_stream 流式输出） ----------
_DIR = {"up": "↑", "down": "↓", "flat": "→"}


def report_sections(report: dict):
    """把报告切成 markdown 片段逐段 yield，配合 st.write_stream 流式渲染。"""
    yield "### 📊 分析报告\n\n"
    if report.get("answer"):
        yield f"**{report['answer']}**\n\n"
    if report.get("changes"):
        lines = ["| 指标 | 期初 | 期末 | 变化率 | 方向 |", "|---|---|---|---|---|"]
        for c in report["changes"]:
            pct = f"{c.get('change_pct')}%" if c.get("change_pct") is not None else "—"
            lines.append(
                f"| {c.get('metric','')} | {c.get('a','')} | {c.get('b','')} | {pct} | "
                f"{_DIR.get(c.get('direction',''), '')} |"
            )
        yield "#### 📈 指标变化\n" + "\n".join(lines) + "\n\n"
    if report.get("timeline"):
        yield "#### 🗓 时间线\n"
        for t in report["timeline"]:
            facts = "；".join(t.get("facts", []))
            yield f"- **{t.get('period','')}**：{facts}\n"
        yield "\n"
    if report.get("causes"):
        yield "#### 🎯 可能原因（假设 + 置信度）\n"
        for c in report["causes"]:
            yield f"- **{c.get('cause','')}**（置信度 {c.get('confidence', 0)}）\n"
            if c.get("supporting_evidence"):
                yield f"  - 支持：{', '.join(c['supporting_evidence'])}\n"
            if c.get("counter_evidence"):
                yield f"  - 反对：{', '.join(c['counter_evidence'])}\n"
        yield "\n"
    if report.get("suggestions"):
        yield "#### 💡 建议\n"
        for i, s in enumerate(report["suggestions"], 1):
            rationale = f"：{s.get('rationale','')}" if s.get("rationale") else ""
            yield f"{i}. **{s.get('suggestion','')}**{rationale}\n"
        yield "\n"
    if report.get("evidence_refs"):
        yield "#### 📎 证据引用\n"
        for r in report["evidence_refs"]:
            yield f"- `{r.get('chunk_id','')}`：{(r.get('snippet','') or '')[:120]}\n"
