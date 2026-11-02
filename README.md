# 时序感知的多模态 RAG：跨季度业务数据的对比归因

把不同季度的财报、销售表、竞品新闻和图表截图按季度对齐，回答「这一季和上一季比，哪个指标变了、可能是什么导致的」，答案里带可回溯的原文片段。

普通 RAG 解决的是「文档里有没有这句话」，这个项目要解决的是「两个时间点之间发生了什么变化」。

## 为什么不能直接问大模型

- 数据在本地文件里，模型没见过；
- 跨季度比数值，要的是确定的数和确定的区间，不是「大概」；
- 结论得能指回哪份文件的哪一段，否则没人敢用。

这是个个人项目，用来验证「时间对齐 + 结构化对比」这条路走不走得通，不是生产系统。

## 三个设计取舍

### 1. 时间标签放在文件级，不放进文本

时间归一化是最容易做错的一步：「去年前三季度」「Q2 后半段」「上一财年」都得落成区间。这里的做法是退化处理：上传时给文件打一个 `2025Q2`，chunk 继承这个字符串，检索时就是一次 metadata 等值过滤。

代价是粒度只到季度、且依赖人工确认；换来的是过滤确定、没有 NLP 误差。文件名能猜出季度的（`2025Q2`、`2025-06`、`2025年第二季度`）会自动预填。

### 2. 数值不进向量库

「Q2 的 MRR 比 Q1 涨了多少」是 `WHERE period=? AND name=?` 的精确查询，用相似度决定取哪条数值本身就不对。所以拆成两个存储：

| 存什么 | 存在哪 | 为什么 |
|---|---|---|
| chunk 文本、向量、period 元数据 | Chroma（cosine，1024 维） | 按语义找段落，period 做标量过滤 |
| document / metric / fact | SQLite | 环比同比、跨期对齐都是结构化查询 |

### 3. 只做对比归因，不做因果推断

LLM 做不了统计因果。报告里的原因条目是「假设 + 支持证据 + 反证 + 置信度」，置信度是模型自评，不是概率。这条约束写进了 prompt（`reasoning/attribution.py`），也写进了输出 schema。

## 数据流

```
上传 → 解析 → 分块 → 指标/事实抽取 → Chroma + SQLite
提问 → Agent → 归因报告（JSON）→ Streamlit 渲染
```

**解析**（`parsers/`）

- PDF：pypdf 抽文本，1200 字一块、120 字重叠；
- CSV / Excel：每 10 行一个块，块头带上表头（`表格「销售数据_2025Q2」。列：留存率、MRR…`），避免模型把列名和值对错位；
- 图片：压到 1280px 后交给 qwen3-vl-plus 描述，整张图一个 chunk。

**抽取**（`extraction/`）

每个 chunk 调一次 qwen-plus，结构化输出数值指标和事实三元组，写进 SQLite，同时留原文前 200 字作为 `evidence`，方便回查。

**检索**（`retrieval/`）

query 向量化 → Chroma 取 20 条（可选按 `period` / `source_type` 过滤）→ qwen3.7-text-rerank 重排 → 取 top 5。重排接口失败时退回余弦相似度。

**Agent**（`agent/`）

LangChain `create_agent` + qwen-plus，工具刻意只留三个：

| 工具 | 作用 |
|---|---|
| `search_knowledge(query, period, source_type, top_k)` | 语义检索，可限定时间片和来源 |
| `compare_periods(period_a, period_b, metric_name)` | 两期指标并排，算差值和变化率 |
| `compute_metric_change(metric_name, period, base)` | 环比 / 同比（`previous` / `yoy`） |

**报告**（`reasoning/`）

把工具输出拼成证据，交给 qwen-max 生成固定 schema 的 JSON：`answer / timeline / changes / causes / suggestions / evidence_refs`。前端逐段渲染，`causes` 里带 chunk_id 方便回查原文。

## 能力示例

| 类型 | 示例 |
|---|---|
| 事实查询 | 2025Q2 云帆科技的留存率是多少？ |
| 对比分析 | 2025Q2 相比 2025Q1，哪些指标变化最大？ |
| 归因分析 | 本季度留存率下降，结合竞品动态分析可能原因，并给三条建议 |

## 技术栈

- 界面：Streamlit
- Agent：LangChain 1.x `create_agent`
- 模型：DashScope 通义千问，qwen-plus 做工具调用和指标抽取，qwen-max 写报告，qwen3-vl-plus 读图
- 向量：text-embedding-v3（1024 维）+ Chroma。选 Chroma 的直接原因是 Milvus Lite 在 Windows 上装不上，而 Chroma 嵌入式、免 Docker，metadata 过滤也够用
- 重排：qwen3.7-text-rerank
- 结构化存储：SQLite

## 快速开始

```bash
git clone https://github.com/Simonyoi/event-aware-rag.git
cd event-aware-rag

python -m venv .venv
.venv\Scripts\activate          # Windows；macOS/Linux 用 source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env            # 填入 DASHSCOPE_API_KEY
streamlit run app.py            # http://localhost:8501
```

Python 3.10+，实测环境 3.11。

生成演示数据（可选）：

```bash
python eval/synthesize_data.py
# 输出 6 个季度（2024Q1–2025Q2）的合成 SaaS 数据：CSV、财报、竞品新闻、留存率走势图。
# 其中 2025Q2 埋了「竞品促销 + 服务宕机 → 留存率下降」的故事，用来验证归因链路。
# 文件名自带 2025Q2 这类时间标签，上传时会自动识别。
```

端到端冒烟测试（会真实调用模型，产生费用）：

```bash
python smoke_test.py
```

## 项目结构

```
app.py            Streamlit 入口：上传、时间标注、提问、渲染报告
config.py         路径、模型名、Key
smoke_test.py     端到端冒烟：入库 7 个文件 → 提问 → 打印工具轨迹和报告
core/             数据模型、LLM/embedding 封装、Chroma+SQLite 存储、入库编排
parsers/          PDF / 表格 / 图片解析，统一输出 Chunk
extraction/       指标与事实抽取、时间标注
retrieval/        时间过滤 + 语义召回 + 重排
agent/            LangChain Agent 与 3 个工具
reasoning/        归因报告生成与 Markdown 渲染
eval/             合成数据、30 题评估集、评估脚本
docs/design.md    设计文档（含数据模型和报告 schema）
```

## 评估

30 题，事实 / 对比 / 归因各 10 题，每题带一组「答案里必须出现」的 gold 关键串。

- 检索：Recall@5、MRR。只对事实和归因两类算 —— 对比类由 SQLite 工具作答，不经过 `hybrid_search`。
- 生成：gold 覆盖、忠实度、相关性，qwen 当裁判打 0~1 分。
- 失败归因：按每题的 recall 和 coverage，把失败切成「检索没召回」「召回了但没用上」「两者都」。

```bash
python -m eval.evaluate                          # 全量 30 题，会重新生成数据并清库
python -m eval.evaluate --limit 5 --skip-ingest  # 5 题快跑，复用已入库数据
```

这组数字只能当回归护栏，不能当效果证明：数据是 `eval/synthesize_data.py` 合成的，gold 是照着同一份数据写的，裁判和被测评的模型还同族。要证明有用，得换真实财报、人工标注、再和 baseline 比一次。目前没做。

## 已知局限

1. 时间标签只到文件级，而且靠上传时人工确认。一份年报同时讲四个季度时，只能整体归到一个 period。
2. 指标由 LLM 从 chunk 里抽，没有人工校对。同名指标在多个文件里出现时按平均值处理，口径不一致时这就是错的。
3. 重排失败会静默退回余弦相似度，日志里看不出来，出问题不好定位。
4. 重复上传同一个文件会重复入库、重复抽取，没有去重。
5. 没有多轮对话记忆。追问「那上季度呢」接不上上一轮的时间片。
6. 单机单用户，没有鉴权，没有并发控制；SQLite 连接是 `check_same_thread=False`，多会话下没有加锁。
7. 依赖没有锁版本，`requirements.txt` 只写了包名。

## 接下来

- 指标冲突消解：同名指标按来源优先级取值，而不是平均；冲突时在报告里显式标出来。
- 真实语料评估：拿公开财报做一套 50 题人工标注集，和「纯语义检索 + 长上下文」的 baseline 对比。
- 对话记忆：把上一轮的时间片和指标带进下一轮的工具参数。

## License

MIT
