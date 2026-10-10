"""30 题黄金集：事实 / 对比 / 归因 各 10 题，带 ground truth 关键串。

字段：
- category: fact(事实查询) / compare(对比分析) / attribution(归因分析)
- period:   检索时的时间过滤（单季度）；None 表示跨时间片、不过滤
- gold:     最终答案必须包含的关键串（用于覆盖度评估；检索 Recall 复用）
"""
from __future__ import annotations

QUESTIONS: list[dict] = [
    # ---------- 事实查询 ----------
    {"id": "fact_01", "category": "fact", "period": "2025Q2",
     "question": "2025Q2 云帆科技的留存率是多少？", "gold": ["74.1"]},
    {"id": "fact_02", "category": "fact", "period": "2025Q2",
     "question": "2025Q2 云帆科技的付费用户数是多少？", "gold": ["15800"]},
    {"id": "fact_03", "category": "fact", "period": "2025Q1",
     "question": "2025Q1 云帆科技的 MRR 是多少？", "gold": ["1466000"]},
    {"id": "fact_04", "category": "fact", "period": "2025Q2",
     "question": "2025Q2 云帆科技的服务可用性是多少？", "gold": ["97.2"]},
    {"id": "fact_05", "category": "fact", "period": "2025Q1",
     "question": "2025Q1 云帆科技的流失率是多少？", "gold": ["4.3"]},
    {"id": "fact_06", "category": "fact", "period": "2025Q2",
     "question": "2025Q2 云帆科技的新增用户数是多少？", "gold": ["1100"]},
    {"id": "fact_07", "category": "fact", "period": "2024Q1",
     "question": "2024Q1 云帆科技的 ARPU 是多少？", "gold": ["90"]},
    {"id": "fact_08", "category": "fact", "period": "2025Q2",
     "question": "2025Q2 竞品星链CRM 采取了什么营销动作？", "gold": ["促销"]},
    {"id": "fact_09", "category": "fact", "period": "2025Q2",
     "question": "2025Q2 云帆科技发生了什么技术故障？", "gold": ["宕机"]},
    {"id": "fact_10", "category": "fact", "period": "2024Q4",
     "question": "2024Q4 云帆科技的付费用户数是多少？", "gold": ["14000"]},

    # ---------- 对比分析 ----------
    {"id": "cmp_01", "category": "compare", "period": None,
     "question": "2025Q2 相比 2025Q1，云帆科技的留存率变化了多少？", "gold": ["82.5", "74.1"]},
    {"id": "cmp_02", "category": "compare", "period": None,
     "question": "2025Q1 相比 2024Q1，MRR 增长了多少？", "gold": ["900000", "1466000"]},
    {"id": "cmp_03", "category": "compare", "period": None,
     "question": "2025Q2 相比 2025Q1，流失率如何变化？", "gold": ["4.3", "7.5"]},
    {"id": "cmp_04", "category": "compare", "period": None,
     "question": "2025Q2 新增用户相比 2025Q1 变化了多少？", "gold": ["1900", "1100"]},
    {"id": "cmp_05", "category": "compare", "period": None,
     "question": "2025Q2 服务可用性环比变化多少？", "gold": ["99.95", "97.2"]},
    {"id": "cmp_06", "category": "compare", "period": None,
     "question": "2024Q4 相比 2024Q3，付费用户数变化多少？", "gold": ["12500", "14000"]},
    {"id": "cmp_07", "category": "compare", "period": None,
     "question": "2025Q2 MRR 环比增速是多少？", "gold": ["1466000", "1501000"]},
    {"id": "cmp_08", "category": "compare", "period": None,
     "question": "2024Q3 相比 2024Q2，ARPU 变化多少？", "gold": ["91", "92"]},
    {"id": "cmp_09", "category": "compare", "period": None,
     "question": "2025Q2 留存率同比（相对 2024Q2）变化多少？", "gold": ["84.6", "74.1"]},
    {"id": "cmp_10", "category": "compare", "period": None,
     "question": "2025Q2 相比 2025Q1，付费用户数增长多少？", "gold": ["15600", "15800"]},

    # ---------- 归因分析 ----------
    {"id": "att_01", "category": "attribution", "period": None,
     "question": "2025Q2 云帆科技留存率下降的可能原因是什么？", "gold": ["竞品", "宕机"]},
    {"id": "att_02", "category": "attribution", "period": None,
     "question": "2025Q2 服务可用性下降的原因是什么？", "gold": ["宕机"]},
    {"id": "att_03", "category": "attribution", "period": None,
     "question": "2025Q2 新增用户减少与什么因素有关？", "gold": ["竞品", "促销"]},
    {"id": "att_04", "category": "attribution", "period": None,
     "question": "2025Q2 流失率上升与哪些事件相关？", "gold": ["竞品", "宕机"]},
    {"id": "att_05", "category": "attribution", "period": None,
     "question": "结合竞品动态，分析 2025Q2 业绩承压的原因？", "gold": ["促销", "宕机"]},
    {"id": "att_06", "category": "attribution", "period": None,
     "question": "为什么 2025Q1 涨价后 2025Q2 流失加剧？", "gold": ["涨价", "竞品"]},
    {"id": "att_07", "category": "attribution", "period": None,
     "question": "2025Q2 MRR 增速放缓的可能原因？", "gold": ["新增用户", "流失率"]},
    {"id": "att_08", "category": "attribution", "period": None,
     "question": "云帆科技 2025Q2 面临的主要风险是什么？", "gold": ["竞品", "宕机"]},
    {"id": "att_09", "category": "attribution", "period": None,
     "question": "竞品降价对云帆科技留存率的影响是什么？", "gold": ["下降"]},
    {"id": "att_10", "category": "attribution", "period": None,
     "question": "分析 2025Q2 用户流失加剧与竞品促销的关联？", "gold": ["竞品", "流失"]},
]


def by_category(category: str) -> list[dict]:
    return [q for q in QUESTIONS if q["category"] == category]
