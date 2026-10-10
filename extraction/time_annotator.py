"""时间标注：从文件名/标题猜 period，或由用户上传时选择。"""
from __future__ import annotations

import re

_CN_Q = {"一": 1, "二": 2, "三": 3, "四": 4}


def guess_period(name: str | None) -> str | None:
    """从文件名/标题识别时间标签，统一为 YYYYQn 格式；识别不到返回 None。"""
    if not name:
        return None
    s = str(name).upper()

    # 2025Q2 / 2025 Q2 / 2025-Q2
    m = re.search(r"(20\d{2})\s*[-_]?\s*Q([1-4])", s)
    if m:
        return f"{m.group(1)}Q{m.group(2)}"

    # Q2 2025 / Q2-2025
    m = re.search(r"Q([1-4])\s*[-_]?\s*(20\d{2})", s)
    if m:
        return f"{m.group(2)}Q{m.group(1)}"

    # 2025-06 / 2025_06 / 2025年6 → 季度
    m = re.search(r"(20\d{2})[-_年]?(\d{1,2})", s)
    if m and 1 <= int(m.group(2)) <= 12:
        q = (int(m.group(2)) - 1) // 3 + 1
        return f"{m.group(1)}Q{q}"

    # 2025年第二季度
    m = re.search(r"(20\d{2})年?第?([一二三四])季度", s)
    if m and m.group(2) in _CN_Q:
        return f"{m.group(1)}Q{_CN_Q[m.group(2)]}"

    return None


def period_options(start_year: int = 2023, end_year: int = 2026) -> list[str]:
    """生成下拉选项，如 ['2023Q1', ..., '2026Q4']。"""
    return [f"{y}Q{q}" for y in range(start_year, end_year + 1) for q in range(1, 5)]
