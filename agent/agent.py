"""Agentic 检索：LangChain create_react_agent（qwen-plus）+ 3 工具。"""
from __future__ import annotations

from langchain.agents import create_agent as _lc_create_agent
from langchain_core.messages import AIMessage

from agent.tools import make_tools
from core.llm import get_chat_llm
from core.storage import Storage

_SYSTEM = """你是一个「时序感知」的 SaaS 数据分析助手。知识库里的资料都带时间标签（如 2025Q2）。
回答关于「变化 / 对比 / 原因」的问题时：
1. 先确定要对比的时间片（如本季度 vs 上季度）；
2. 用 search_knowledge 检索相关事实（可指定 period 过滤）；
3. 用 compare_periods 或 compute_metric_change 获取指标数值与变化；
4. 综合证据，给出带依据的结论。
所有结论必须基于检索到的证据，不要臆造。"""


def create_agent(storage: Storage):
    """构建 Agent（LangChain 1.x create_agent）。"""
    llm = get_chat_llm(temperature=0.0)
    tools = make_tools(storage)
    return _lc_create_agent(llm, tools, system_prompt=_SYSTEM)


def extract_trace(messages) -> list[dict]:
    """从消息轨迹中提取工具调用序列（用于展示思考过程）。"""
    trace = []
    for m in messages:
        if isinstance(m, AIMessage):
            for tc in m.tool_calls or []:
                trace.append({"tool": tc["name"], "args": tc.get("args", {})})
    return trace


def run_agent(agent, question: str) -> dict:
    """执行 agent，返回最终答案与工具调用轨迹（用于展示思考过程）。"""
    result = agent.invoke({"messages": [("user", question)]})
    messages = result["messages"]
    answer = messages[-1].content if messages else ""
    return {"answer": answer, "trace": extract_trace(messages)}
