[README.md](https://github.com/user-attachments/files/33289443/README.md)
# 📈 时序感知多模态 Agentic RAG 决策助手

> 不只「Chat with your PDF」，而是「Chat with 你**跨时间**的业务数据」。
> 把散落在不同季度财报、月度销售表、竞品新闻、产品截图里的信息按时间轴对齐，让 AI 回答「**为什么**」——本季度留存率为什么下降，并给出带证据引用的建议。

## ✨ 与普通 RAG 的四个不同

| 普通 RAG | 本项目 |
|---|---|
| 静态文档问答 | **时序感知**：知识带时间标签，支持跨时间片检索 |
| 只读 PDF | **多模态**：PDF / 表格（CSV·Excel）/ 图片（图表）三类输入 |
| 固定「检索 → 生成」 | **Agentic**：LLM 自主决定检索什么、何时对比、何时计算 |
| 给答案 | **对比归因**：找变化点 → 生成假设 → 证据链 + 置信度 + 建议 |

## 🧠 系统架构

```
上传 → 解析(PDF/表格/图片) → 指标/事实抽取 → 向量化(Chroma) + 结构化(SQLite)
提问 → Agent(3 工具) → 对比归因报告(JSON) → 流式渲染
```

- **入库链路**：`time_annotator(period)` → `parsers(→Chunk)` → `metric_extractor(→Metric/Fact)` → `embeddings` → `storage(Chroma + SQLite)`
- **查询链路**：`question` → `Agent` → `{search_knowledge / compare_periods / compute_metric_change}` → 归因引擎 → 报告

## 🛠 技术栈

| 层 | 选型 |
|---|---|
| 界面 | Streamlit |
| 框架 | LangChain（`create_agent`） |
| 模型 | 千问 DashScope：qwen-plus（Agent/抽取）· qwen-max（归因）· qwen3-vl-plus（图片） |
| 向量库 | Chroma（嵌入式，Windows 原生） |
| 结构化存储 | SQLite |
| Embedding / Rerank | text-embedding-v3 / qwen3.7-text-rerank |

## 🚀 快速开始

```bash
# 1. 克隆
git clone https://github.com/Simonyoi/event-aware-rag.git
cd event-aware-rag

# 2. 建虚拟环境（Python 3.10+，本项目用 3.11 验证）
python -m venv .venv
.venv\Scripts\activate          # Windows

# 3. 装依赖
pip install -r requirements.txt

# 4. 配置 API Key（阿里云百炼 DashScope）
cp .env.example .env            # 把 DASHSCOPE_API_KEY=sk-xxxx 换成真实 Key

# 5. 运行
streamlit run app.py            # 浏览器打开 http://localhost:8501
```

### 生成演示数据（可选）

```bash
python eval/synthesize_data.py
# 生成 6 个季度的合成 SaaS 数据（CSV / 财报 / 竞品新闻 / 留存率图表），
# 其中 2025Q2 埋入了「留存率下降 + 竞品促销 + 服务宕机」的因果故事，便于验证归因。
# 上传 data/synthetic/ 里的文件即可体验（文件名已带 2025Q2 等时间标签，自动识别）。
```

## 🎯 三类问题（能力演示）

| 类型 | 示例 |
|---|---|
| 事实查询 | 「2025Q2 云帆科技的留存率是多少？」 |
| 对比分析 | 「2025Q2 相比 2025Q1，哪些指标变化最大？」 |
| 归因分析 | 「本季度留存率下降，结合竞品动态，分析可能原因并给 3 条建议」 |

## 📁 项目结构

```
app.py            Streamlit 入口
config.py         配置（模型名 / 路径 / Key）
core/             数据模型 · LLM/embedding 封装 · 存储(Chroma+SQLite) · 入库编排
parsers/          PDF / 表格 / 图片 解析
extraction/       指标/事实抽取 + 时间标注
retrieval/        混合检索（时间过滤 + 语义 + rerank）
agent/            LangChain create_agent + 3 工具
reasoning/        对比归因报告生成（JSON 带证据引用）
eval/             合成数据生成器 + 30 题黄金集 + 评估
docs/design.md    设计文档
```

## 📊 评估

- **检索**：Recall@k / MRR（时间过滤 + 语义召回 + 重排）
- **生成**：gold 覆盖度 / 忠实度 / 相关性（qwen 裁判）
- **失败根因分类**：检索失败 vs 生成失败

```bash
python -m eval.evaluate                          # 全量 30 题
python -m eval.evaluate --limit 5 --skip-ingest  # 快速 5 题（复用已入库数据）
```

## 🔧 关键设计取舍

1. **对比归因，而非「因果推理」**：LLM 无法做统计因果。本项目输出「假设 + 证据 + 置信度」，诚实且可检验。
2. **时间标签在文件级，而非文本抽取**：把最难的时间归一化降级为一个字符串字段，时间过滤 = 纯标量过滤，零 NLP 风险。
3. **Chroma 而非 Milvus**：Milvus Lite 不支持 Windows；Chroma 嵌入式、免 Docker，且保留 metadata 过滤能力。
4. **向量库只存 chunk，指标/事实进 SQLite**：跨时间片对比与环比是「按 period + 指标名」的精确查询，SQLite 更快更简单。

## 📄 License

MIT
