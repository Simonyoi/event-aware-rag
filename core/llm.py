"""千问 DashScope 的 LLM 封装（走 OpenAI 兼容接口）。"""
from __future__ import annotations

from langchain_openai import ChatOpenAI

import config


def _require_key() -> None:
    if not config.DASHSCOPE_API_KEY:
        raise RuntimeError(
            "未配置 DASHSCOPE_API_KEY：请在项目根目录复制 .env.example 为 .env 并填入真实 Key。"
        )


def get_chat_llm(model: str | None = None, temperature: float = 0.0) -> ChatOpenAI:
    """qwen-plus：Agent 工具调用、指标抽取。"""
    _require_key()
    return ChatOpenAI(
        model=model or config.LLM_CHAT_MODEL,
        base_url=config.DASHSCOPE_BASE_URL,
        api_key=config.DASHSCOPE_API_KEY,
        temperature=temperature,
    )


def get_reason_llm(model: str | None = None, temperature: float = 0.2) -> ChatOpenAI:
    """qwen-max：对比归因报告生成。"""
    _require_key()
    return ChatOpenAI(
        model=model or config.LLM_REASON_MODEL,
        base_url=config.DASHSCOPE_BASE_URL,
        api_key=config.DASHSCOPE_API_KEY,
        temperature=temperature,
    )


def get_vision_llm(model: str | None = None) -> ChatOpenAI:
    """qwen-vl-plus：图片理解。"""
    _require_key()
    return ChatOpenAI(
        model=model or config.LLM_VISION_MODEL,
        base_url=config.DASHSCOPE_BASE_URL,
        api_key=config.DASHSCOPE_API_KEY,
        temperature=0.0,
    )
