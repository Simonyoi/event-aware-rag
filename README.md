# 时序感知多模态 RAG 决策助手

跨时间片对比归因的多模态 Agentic RAG。详见 [docs/design.md](docs/design.md)。

## 技术栈

Streamlit · LangChain · 千问 DashScope · Chroma · SQLite

## 快速开始（开发中）

```bash
pip install -r requirements.txt
cp .env.example .env   # 填入 DASHSCOPE_API_KEY
```

## 实现进度

- [x] 第 1 步：数据模型 + 目录结构
- [x] 第 2 步：多模态解析（PDF/表格/图片）+ 时间标注 + 指标抽取
- [x] 第 3 步：时序向量存储 + 混合检索 + rerank
- [x] 第 4 步：Agentic 检索（3 工具）
- [x] 第 5 步：对比归因 + 报告生成 + Streamlit 界面
- [x] 第 6 步：评估与优化（合成数据 + 黄金集 + 检索/生成指标）
