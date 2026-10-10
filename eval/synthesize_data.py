"""合成数据生成器：生成带「已知变化点」的 SaaS 多季度数据。

文件按季度拆分、文件名带 period（如 _2025Q2），便于 guess_period 识别；
2025Q2 被注入「留存率下降 + 流失率上升 + 竞品 6 折促销 + 8 小时宕机」的因果故事，
从而让归因类问题的 ground truth 精确已知。
"""
from __future__ import annotations

import csv
from pathlib import Path

QUARTERS = ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2"]

# 指标：(数值, 单位)
METRICS_BY_QUARTER = {
    "2024Q1": {"付费用户数": (10000, "人"), "MRR": (900000, "元"), "ARPU": (90, "元"),
               "留存率": (85.0, "%"), "流失率": (3.4, "%"), "新增用户": (1500, "人"), "服务可用性": (99.96, "%")},
    "2024Q2": {"付费用户数": (11200, "人"), "MRR": (1019200, "元"), "ARPU": (91, "元"),
               "留存率": (84.6, "%"), "流失率": (3.6, "%"), "新增用户": (1600, "人"), "服务可用性": (99.95, "%")},
    "2024Q3": {"付费用户数": (12500, "人"), "MRR": (1150000, "元"), "ARPU": (92, "元"),
               "留存率": (84.2, "%"), "流失率": (3.8, "%"), "新增用户": (1700, "人"), "服务可用性": (99.97, "%")},
    "2024Q4": {"付费用户数": (14000, "人"), "MRR": (1302000, "元"), "ARPU": (93, "元"),
               "留存率": (83.8, "%"), "流失率": (4.0, "%"), "新增用户": (1800, "人"), "服务可用性": (99.94, "%")},
    "2025Q1": {"付费用户数": (15600, "人"), "MRR": (1466000, "元"), "ARPU": (94, "元"),
               "留存率": (82.5, "%"), "流失率": (4.3, "%"), "新增用户": (1900, "人"), "服务可用性": (99.95, "%")},
    "2025Q2": {"付费用户数": (15800, "人"), "MRR": (1501000, "元"), "ARPU": (95, "元"),
               "留存率": (74.1, "%"), "流失率": (7.5, "%"), "新增用户": (1100, "人"), "服务可用性": (97.2, "%")},
}

REPORTS = {
    "2024Q1": "云帆科技2024年第一季度财报摘要：付费用户数10000人，MRR达900000元，ARPU 90元。"
              "留存率85.0%，流失率3.4%，新增用户1500人。整体业务稳健增长，服务可用性99.96%。",
    "2024Q2": "云帆科技2024年第二季度财报摘要：付费用户数11200人，MRR达1019200元，ARPU 91元。"
              "留存率84.6%，流失率3.6%，新增用户1600人。服务可用性99.95%。",
    "2024Q3": "云帆科技2024年第三季度财报摘要：付费用户数12500人，MRR达1150000元，ARPU 92元。"
              "留存率84.2%，流失率3.8%，新增用户1700人。服务可用性99.97%。",
    "2024Q4": "云帆科技2024年第四季度财报摘要：付费用户数14000人，MRR达1302000元，ARPU 93元。"
              "留存率83.8%，流失率4.0%，新增用户1800人。服务可用性99.94%。",
    "2025Q1": "云帆科技2025年第一季度财报摘要：付费用户数15600人，MRR达1466000元，ARPU 94元。"
              "留存率82.5%，流失率4.3%，新增用户1900人。本季度公司将订阅价格涨价15%，留存率较上季度下滑。"
              "服务可用性99.95%。",
    "2025Q2": "云帆科技2025年第二季度财报摘要：付费用户数15800人，MRR达1501000元，ARPU 95元。"
              "留存率大幅下降至74.1%，流失率升至7.5%，新增用户仅1100人。"
              "主要原因是竞品星链CRM推出6折促销分流客户，且本季度发生一次8小时服务宕机，服务可用性降至97.2%。",
}

COMPETITOR_NEWS = {
    "2024Q1": "竞品动态：市场整体平稳，暂无重大竞品动作。",
    "2024Q2": "竞品动态：星链CRM发布新版本，主打团队协作功能。",
    "2024Q3": "竞品动态：多家竞品小幅调整定价，行业竞争温和。",
    "2024Q4": "竞品动态：行业进入年末促销季，竞品推出年度订阅折扣。",
    "2025Q1": "竞品动态：星链CRM完成新一轮融资，计划加大市场投放。",
    "2025Q2": "竞品动态：星链CRM宣布新用户6折促销，首年订阅半价，直指云帆科技核心客户群。",
}


def _write_retention_chart(output_dir: Path, period: str, quarters: list[str], retention: dict) -> Path | None:
    """生成留存率趋势图（截至指定季度），未装 matplotlib 则跳过。"""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    # 中文字体（Windows 常见字体，缺失则退回默认）
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "sans-serif"]
    plt.rcParams["axes.unicode_minus"] = False

    idx = quarters.index(period)
    xs = quarters[: idx + 1]
    ys = [retention[q] for q in xs]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(xs, ys, marker="o", color="#2563eb")
    ax.set_ylim(0, 100)
    ax.set_title(f"云帆科技 留存率趋势（截至 {period}）")
    ax.set_ylabel("留存率 %")
    for x, y in zip(xs, ys):
        ax.annotate(f"{y}", (x, y), textcoords="offset points", xytext=(0, 6), ha="center")
    fig.tight_layout()
    path = output_dir / f"云帆科技_留存率趋势_{period}.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def generate(output_dir: str | Path = "data/synthetic") -> list[Path]:
    """生成全部合成文件，返回文件路径列表。"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    retention = {q: METRICS_BY_QUARTER[q]["留存率"][0] for q in QUARTERS}

    files: list[Path] = []
    for q in QUARTERS:
        # 销售指标 CSV（长表：指标 / 数值 / 单位）
        csv_path = output_dir / f"云帆科技_销售数据_{q}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["指标", "数值", "单位"])
            for name, (value, unit) in METRICS_BY_QUARTER[q].items():
                w.writerow([name, value, unit])
        files.append(csv_path)

        # 财报叙述 txt
        report_path = output_dir / f"云帆科技_季度财报_{q}.txt"
        report_path.write_text(REPORTS[q], encoding="utf-8")
        files.append(report_path)

        # 竞品新闻 txt
        news_path = output_dir / f"竞品动态_{q}.txt"
        news_path.write_text(COMPETITOR_NEWS[q], encoding="utf-8")
        files.append(news_path)

        # 留存率趋势图 PNG
        chart_path = _write_retention_chart(output_dir, q, QUARTERS, retention)
        if chart_path:
            files.append(chart_path)

    return files


if __name__ == "__main__":
    generated = generate()
    print(f"已生成 {len(generated)} 个合成文件：")
    for p in generated:
        print(" -", p)
