"""Agent 工具集：语义检索 / 跨时间片对比 / 指标计算。"""
from __future__ import annotations

import json
from collections import defaultdict

from langchain_core.tools import tool

from core.storage import Storage
from retrieval import hybrid_search


def prev_period(period: str) -> str:
    """上一季度：2025Q1 → 2024Q4。"""
    year, q = int(period[:4]), int(period[5])
    if q == 1:
        return f"{year - 1}Q4"
    return f"{year}Q{q - 1}"


def yoy_period(period: str) -> str:
    """去年同季度：2025Q2 → 2024Q2。"""
    return f"{int(period[:4]) - 1}{period[4:]}"


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _diff_metrics(
    storage: Storage, metric_name: str, period_a: str, period_b: str
) -> dict:
    """对比两期指标与事实，计算变化量/变化率。"""
    metrics_a = storage.query_metrics(period=period_a, name=metric_name or None)
    metrics_b = storage.query_metrics(period=period_b, name=metric_name or None)
    facts_a = storage.query_facts(period=period_a)
    facts_b = storage.query_facts(period=period_b)

    ga: dict[str, list[float]] = defaultdict(list)
    gb: dict[str, list[float]] = defaultdict(list)
    units: dict[str, str] = {}
    for m in metrics_a:
        ga[m.name].append(m.value)
        units[m.name] = m.unit
    for m in metrics_b:
        gb[m.name].append(m.value)
        units.setdefault(m.name, m.unit)

    rows = []
    for name in sorted(set(ga) | set(gb)):
        a = _avg(ga[name])
        b = _avg(gb[name])
        diff = b - a
        pct = (diff / a * 100) if a else None
        direction = "flat" if diff == 0 else ("up" if diff > 0 else "down")
        rows.append(
            {
                "name": name,
                "unit": units.get(name, ""),
                "period_a_value": round(a, 4),
                "period_b_value": round(b, 4),
                "diff": round(diff, 4),
                "change_pct": round(pct, 2) if pct is not None else None,
                "direction": direction,
            }
        )

    return {
        "period_a": period_a,
        "period_b": period_b,
        "metrics": rows,
        "facts_a": [
            {"subject": f.subject, "predicate": f.predicate, "object": f.object}
            for f in facts_a
        ],
        "facts_b": [
            {"subject": f.subject, "predicate": f.predicate, "object": f.object}
            for f in facts_b
        ],
    }


def make_tools(storage: Storage) -> list:
    """构造 3 个工具，绑定到给定 storage 实例。"""

    @tool
    def search_knowledge(
        query: str, period: str = "", source_type: str = "", top_k: int = 5
    ) -> str:
        """在知识库中做语义检索，可选按时间片(period，如 2025Q2)和来源(source_type)过滤。
        用于查找事实、文本片段、竞品动态、财报描述等。返回相关文本块列表。"""
        results = hybrid_search(
            storage,
            query,
            period=period or None,
            source_type=source_type or None,
            top_k=top_k,
        )
        return json.dumps([r.model_dump() for r in results], ensure_ascii=False)

    @tool
    def compare_periods(period_a: str, period_b: str, metric_name: str = "") -> str:
        """对比两个时间片的指标数值与事实（如 period_a=2025Q1, period_b=2025Q2）。
        metric_name 留空则对比所有指标。返回各指标两期数值、变化量与变化率，以及两期事实。"""
        return json.dumps(
            _diff_metrics(storage, metric_name, period_a, period_b), ensure_ascii=False
        )

    @tool
    def compute_metric_change(metric_name: str, period: str, base: str = "previous") -> str:
        """计算某指标在指定时间片的环比或同比。
        period 如 2025Q2；base 取 "previous"（环比，相对上一季度）或 "yoy"（同比，相对去年同季度）。"""
        base_period = prev_period(period) if base == "previous" else yoy_period(period)
        return json.dumps(
            _diff_metrics(storage, metric_name, base_period, period), ensure_ascii=False
        )

    return [search_knowledge, compare_periods, compute_metric_change]
