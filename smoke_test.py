"""端到端冒烟测试：入库少量合成数据 → 提问 → 检查报告与工具轨迹。"""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agent import create_agent
from core.ingest import ingest_file
from core.models import SourceType
from core.storage import Storage
from extraction import guess_period
from reasoning import analyze, report_sections


def main() -> None:
    storage = Storage()
    storage.clear_all()

    files = [
        ("data/synthetic/云帆科技_销售数据_2025Q1.csv", SourceType.sales_data),
        ("data/synthetic/云帆科技_季度财报_2025Q1.txt", SourceType.financial_report),
        ("data/synthetic/竞品动态_2025Q1.txt", SourceType.competitor_news),
        ("data/synthetic/云帆科技_销售数据_2025Q2.csv", SourceType.sales_data),
        ("data/synthetic/云帆科技_季度财报_2025Q2.txt", SourceType.financial_report),
        ("data/synthetic/竞品动态_2025Q2.txt", SourceType.competitor_news),
        ("data/synthetic/云帆科技_留存率趋势_2025Q2.png", SourceType.screenshot),
    ]

    for path, source in files:
        period = guess_period(path) or "2025Q2"
        print(f"入库 {path} ({period}) …")
        summary = ingest_file(storage, path, period, source)
        print("   ->", summary)

    print("\n已入库文档:", [(d.file_name, d.period) for d in storage.get_documents()])
    print("已抽取指标数:", len(storage.query_metrics()))
    print("已抽取事实数:", len(storage.query_facts()))

    agent = create_agent(storage)
    question = "2025Q2 云帆科技留存率下降的可能原因是什么？"
    print(f"\n提问：{question}")
    report = analyze(agent, question)

    print("\n=== 工具调用轨迹 ===")
    for t in report.get("_trace", []):
        print(f"  {t['tool']}: {t['args']}")

    print("\n=== 报告 ===")
    print("".join(report_sections(report)))


if __name__ == "__main__":
    main()
