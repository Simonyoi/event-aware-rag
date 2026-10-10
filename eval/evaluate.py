"""评估：检索指标（Recall@k / MRR）+ 生成指标（gold 覆盖 / 忠实度 / 相关性）+ 根因分类。

说明：
- 检索评估只覆盖「事实 + 归因」两类（靠语义检索作答）；「对比」类由 SQLite 对比工具作答，
  不经过 hybrid_search，故不做检索 Recall，只在生成侧核对两个数值是否都被覆盖。
- 生成评估跑完整管线（Agent 取证 → 归因报告），用 qwen 做忠实度/相关性裁判。
"""
from __future__ import annotations

import sys
import statistics
from pathlib import Path

# 允许 `python eval/evaluate.py` 直接运行（把项目根加入 sys.path）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from core.llm import get_chat_llm
from reasoning import analyze, report_sections
from retrieval import hybrid_search

_SEARCH_BASED = ("fact", "attribution")


# ---------- 检索评估 ----------
def evaluate_retrieval(storage, questions, k: int = 5) -> dict:
    """对每题做检索，计算 gold 关键词的 Recall@k 与 MRR。"""
    per_q = []
    for q in questions:
        if q["category"] not in _SEARCH_BASED:
            continue
        try:
            results = hybrid_search(storage, q["question"], period=q.get("period"), top_k=k)
            texts = [r.text for r in results]
            gold = q["gold"]
            hits = sum(1 for t in gold if any(t in text for text in texts))
            recall = hits / len(gold) if gold else 1.0
            rank = next((i for i, text in enumerate(texts, 1) if any(t in text for t in gold)), None)
            mrr = 1 / rank if rank else 0.0
            per_q.append({**q, "recall": round(recall, 2), "mrr": round(mrr, 2)})
        except Exception as e:  # 单题失败不中断整体评估
            per_q.append({**q, "recall": 0.0, "mrr": 0.0, "error": str(e)[:120]})
    return _aggregate(per_q, "recall", "mrr")


# ---------- 生成评估 ----------
def _gold_coverage(answer: str, gold: list[str]) -> float:
    if not gold:
        return 1.0
    return sum(1 for t in gold if t in answer) / len(gold)


class JudgeScore(BaseModel):
    score: float = Field(description="0~1 分数")
    reason: str = ""


_FAITH = ChatPromptTemplate.from_messages(
    [
        ("system", "你是评估裁判。判断【回答】中的结论是否都有【证据】支撑、没有臆造。给 0~1 分数。"),
        ("human", "问题：{question}\n回答：{answer}\n证据：{contexts}"),
    ]
)

_REL = ChatPromptTemplate.from_messages(
    [
        ("system", "你是评估裁判。判断【回答】是否直接、完整地回应了【问题】。给 0~1 分数。"),
        ("human", "问题：{question}\n回答：{answer}"),
    ]
)


def judge_faithfulness(question: str, answer: str, contexts: str) -> float:
    llm = get_chat_llm().with_structured_output(JudgeScore, method="function_calling")
    return (_FAITH | llm).invoke(
        {"question": question, "answer": answer, "contexts": contexts}
    ).score


def judge_relevancy(question: str, answer: str) -> float:
    llm = get_chat_llm().with_structured_output(JudgeScore, method="function_calling")
    return (_REL | llm).invoke({"question": question, "answer": answer}).score


def evaluate_generation(storage, agent, questions) -> dict:
    """跑完整管线，评估答案的 gold 覆盖、忠实度、相关性。"""
    per_q = []
    for q in questions:
        try:
            report = analyze(agent, q["question"])
            answer = "".join(report_sections(report))
            contexts = " ".join(
                r.text for r in hybrid_search(storage, q["question"], period=q.get("period"), top_k=5)
            )
            per_q.append(
                {
                    **q,
                    "coverage": round(_gold_coverage(answer, q["gold"]), 2),
                    "faithfulness": round(judge_faithfulness(q["question"], answer, contexts), 2),
                    "relevancy": round(judge_relevancy(q["question"], answer), 2),
                }
            )
        except Exception as e:  # 单题失败不中断整体评估
            per_q.append(
                {**q, "coverage": 0.0, "faithfulness": 0.0, "relevancy": 0.0, "error": str(e)[:120]}
            )
    return _aggregate(per_q, "coverage", "faithfulness", "relevancy")


# ---------- 汇总 / 根因 ----------
def _aggregate(per_q: list[dict], *metrics: str) -> dict:
    by_cat: dict[str, list[dict]] = {}
    for q in per_q:
        by_cat.setdefault(q["category"], []).append(q)
    summary = {}
    for cat, items in by_cat.items():
        ok = [i for i in items if "error" not in i]
        summary[cat] = {m: (round(statistics.mean(i[m] for i in ok), 3) if ok else None) for m in metrics}
    ok_all = [i for i in per_q if "error" not in i]
    if ok_all:
        summary["overall"] = {m: round(statistics.mean(i[m] for i in ok_all), 3) for m in metrics}
    return {"per_question": per_q, "summary": summary}


def classify_failures(retrieval: dict, generation: dict) -> list[dict]:
    """根因分类：检索失败 vs 生成失败 vs 两者。"""
    r_map = {q["id"]: q for q in retrieval["per_question"]}
    failures = []
    for g in generation["per_question"]:
        if "error" in g:
            continue
        recall = r_map.get(g["id"], {}).get("recall", 1.0)
        coverage = g["coverage"]
        if recall >= 1.0 and coverage >= 1.0:
            continue
        if recall < 1.0 and coverage < 1.0:
            kind = "检索+生成均失败"
        elif recall < 1.0:
            kind = "检索失败（证据未召回）"
        else:
            kind = "生成失败（证据已召回但未利用）"
        failures.append(
            {"id": g["id"], "question": g["question"], "kind": kind,
             "recall": recall, "coverage": coverage}
        )
    return failures


def print_report(retrieval: dict, generation: dict, failures: list[dict]) -> None:
    def _show(title: str, summary: dict) -> None:
        print(f"\n== {title} ==")
        for cat, m in summary.items():
            print(f"  {cat:12s} " + "  ".join(f"{k}={v}" for k, v in m.items()))

    _show("检索指标 (Recall@k / MRR)", retrieval["summary"])
    _show("生成指标 (覆盖 / 忠实度 / 相关性)", generation["summary"])
    print(f"\n== 失败案例（{len(failures)}）==")
    for f in failures:
        print(f"  [{f['kind']}] {f['question']}  (recall={f['recall']}, coverage={f['coverage']})")

    errors = [q for q in generation["per_question"] if "error" in q]
    if errors:
        print(f"\n== 出错题目（{len(errors)}，已从均值剔除）==")
        for e in errors:
            print(f"  [{e['id']}] {e['question']} -> {e['error']}")


# ---------- 入口 ----------
def _source_from_name(name: str):
    from core.models import SourceType

    if "销售" in name:
        return SourceType.sales_data
    if "财报" in name:
        return SourceType.financial_report
    if "竞品" in name:
        return SourceType.competitor_news
    if "趋势" in name or name.endswith(".png"):
        return SourceType.screenshot
    return SourceType.other


def _sample_questions(questions: list[dict], limit: int | None) -> list[dict]:
    """跨类别均衡抽样（归因/事实/对比 轮询取），保证小样本有代表性。"""
    if limit is None or limit >= len(questions):
        return questions
    buckets: dict[str, list[dict]] = {"attribution": [], "fact": [], "compare": []}
    for q in questions:
        buckets[q["category"]].append(q)
    out: list[dict] = []
    i = 0
    while len(out) < limit:
        progress = False
        for cat in ("attribution", "fact", "compare"):
            if i < len(buckets[cat]) and len(out) < limit:
                out.append(buckets[cat][i])
                progress = True
        if not progress:
            break
        i += 1
    return out


def main(limit: int | None = None, skip_ingest: bool = False) -> None:
    """生成合成数据 → 清空入库 → 跑检索/生成评估 → 打印汇总。

    limit：只跑 N 题（跨类别均衡抽样）；skip_ingest：复用已入库数据，跳过生成与入库。
    """
    from agent import create_agent
    from core.ingest import ingest_file
    from core.storage import Storage
    from eval.golden_set import QUESTIONS
    from eval.synthesize_data import generate
    from extraction import guess_period

    questions = _sample_questions(QUESTIONS, limit)
    print(f"本次评估题数：{len(questions)}")

    storage = Storage()
    if skip_ingest:
        print("跳过入库，复用现有知识库…")
    else:
        files = generate()
        print(f"已生成 {len(files)} 个合成文件")
        storage.clear_all()
        for f in files:
            period = guess_period(f.name) or "2025Q2"
            ingest_file(storage, str(f), period, _source_from_name(f.name))
        print("入库完成，开始评估…")

    agent = create_agent(storage)
    retrieval = evaluate_retrieval(storage, questions)
    generation = evaluate_generation(storage, agent, questions)
    failures = classify_failures(retrieval, generation)
    print_report(retrieval, generation, failures)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG 评估")
    parser.add_argument("--limit", type=int, default=None, help="只跑 N 题（跨类别均衡抽样）")
    parser.add_argument("--skip-ingest", action="store_true", help="复用已入库数据，跳过生成与入库")
    args = parser.parse_args()
    main(limit=args.limit, skip_ingest=args.skip_ingest)
