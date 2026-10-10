# 时序感知多模态 RAG 决策助手 — 设计文档

> 定位：不只「Chat with your PDF」，而是「Chat with 你跨时间的业务数据」——把散落在不同季度财报、月度销售表、竞品新闻里的信息按时间轴对齐，让 AI 做跨时间片对比归因。

## 技术栈

| 层 | 选型 |
|---|---|
| 界面 | Streamlit（`st.file_uploader` 上传、`st.write_stream` 流式） |
| 框架 | LangChain（Agent 用 `create_react_agent`，避开已弃用的 AgentExecutor） |
| 模型 | 千问 DashScope（OpenAI 兼容接口） |
| 向量库 | Chroma（嵌入式，Windows 原生） |
| 结构化存储 | SQLite |

模型映射：`qwen-plus`（Agent 工具调用 + 指标抽取）、`qwen-max`（对比归因报告）、`qwen-vl-plus`（图片理解）、`text-embedding-v3`（向量）、`gte-rerank`（重排）。

## 数据模型

```
Document (源文件) 1 ──< N Chunk (检索块) 1 ──< N Metric (数值指标)
                                        └────< N Fact (事实断言)
```

- **Document** = 一次上传文件，带时间标签 `period`（如 `2025Q2`）。
- **Chunk** = 可检索最小文本单元，继承 Document 的 period。
- **Metric** = 数值指标（参与环比/同比计算）。
- **Fact** = 非数值事实/事件（参与归因叙述）。

### Chroma collection `chunks`

| 字段 | 说明 |
|---|---|
| ids | chunk_id（主键） |
| embeddings | 向量（cosine，dim=1024） |
| documents | 文本内容 |
| metadatas | `{doc_id, period, source_type, seq}`，period/source_type 支持 where 过滤 |

### SQLite 表

- `documents`：doc_id / file_name / file_type / source_type / period / period_start / period_end / uploaded_at / status
- `metrics`：metric_id / chunk_id / doc_id / period / name / value / unit / change / confidence / evidence
- `facts`：fact_id / chunk_id / doc_id / period / subject / predicate / object / confidence / evidence

### 报告 JSON（对比归因输出）

```json
{
  "question": "…",
  "timeline": [{"period": "2025Q2", "facts": ["…"], "metrics": [{"name": "留存率", "value": 74.1}]}],
  "changes": [{"metric": "留存率", "a": 82.5, "b": 74.1, "change_pct": -10.2, "direction": "down"}],
  "causes": [{"cause": "…", "confidence": 0.78, "supporting_evidence": ["chunk_id"], "counter_evidence": []}],
  "suggestions": [{"suggestion": "…", "rationale": "…"}],
  "evidence_refs": [{"chunk_id": "…", "snippet": "…"}]
}
```

## 目录结构

```
app.py / config.py / requirements.txt / .env.example / .gitignore / README.md
core/        数据模型 + LLM/embedding 封装 + 存储
parsers/     多模态解析（PDF/表格/图片）
extraction/  指标抽取 + 时间标注
retrieval/   混合检索（时间过滤 + 语义 + rerank）
agent/       LangChain create_react_agent + 3 工具
reasoning/   对比归因报告生成
eval/        合成数据 + 黄金集 + 评估
data/        运行时数据（gitignore）
docs/        文档
```

## 模块 I/O 与调用关系

```
入库：upload → time_annotator(period) → parsers(→Chunk) → metric_extractor(→Metric/Fact)
      → embeddings(chunk) → storage.write(Chroma + SQLite)

查询：question → agent(create_react_agent)
      ├─ tool1 hybrid_search(query, period, top_k) → [Chunk]
      ├─ tool2 compare(metric, period_a, period_b) → [Metric] + 差异
      ├─ tool3 compute(metric, periods) → 环比/同比
      └─ attribution(检索结果 + metrics, qwen-max) → JSON 报告 → st.write_stream
```

## 关键设计决策

1. **向量库只存 chunk，指标/事实放 SQLite**：跨时间片对比与环比是「按 period + 指标名」的精确查询，不是语义查询，SQLite 更快更简单。
2. **period 放文件级，不靠文本抽取**：时间标签上传时确定，chunk 继承，把最难的「时间归一化」降级成字符串字段。
3. **Metric 与 Fact 分开**：数值指标参与计算，事实断言用于归因叙述，字段结构不同。
4. **定位「对比归因」而非「因果推理」**：LLM 做不了真因果，输出为「假设 + 证据 + 置信度」。
