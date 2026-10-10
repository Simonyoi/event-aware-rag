"""全局配置：路径、模型名、连接信息。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = str(DATA_DIR / "chroma")
SQLITE_DB = str(DATA_DIR / "metadata.db")

# 确保运行时目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# DashScope（千问）OpenAI 兼容接口
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 模型
LLM_CHAT_MODEL = os.getenv("LLM_CHAT_MODEL", "qwen-plus")      # Agent 工具调用 + 指标抽取
LLM_REASON_MODEL = os.getenv("LLM_REASON_MODEL", "qwen-max")   # 对比归因报告
LLM_VISION_MODEL = os.getenv("LLM_VISION_MODEL", "qwen3-vl-plus")  # 图片理解
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))
RERANK_MODEL = os.getenv("RERANK_MODEL", "qwen3.7-text-rerank")

# Chroma
CHROMA_COLLECTION = "chunks"
