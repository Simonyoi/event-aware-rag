"""Streamlit 界面：上传（选时间/来源）→ 入库 → 提问 → 流式报告。"""
from __future__ import annotations

import uuid

import streamlit as st

import config
from agent import create_agent
from core.ingest import ingest_file
from core.models import SourceType
from core.storage import Storage
from extraction import guess_period, period_options
from reasoning import analyze, report_sections

st.set_page_config(page_title="时序感知多模态 RAG 决策助手", layout="wide")


@st.cache_resource
def get_storage() -> Storage:
    return Storage()


@st.cache_resource
def get_agent():
    return create_agent(get_storage())


storage = get_storage()
agent = get_agent()

st.title("📈 时序感知多模态 RAG 决策助手")
st.caption("上传带时间标签的业务资料（财报 / 销售 / 竞品新闻 / 截图），做跨时间片对比归因")

# ---------- 侧栏：上传 ----------
with st.sidebar:
    st.header("📤 上传资料")
    if not config.DASHSCOPE_API_KEY:
        st.warning("未检测到 DASHSCOPE_API_KEY：请复制 .env.example 为 .env 并填入 Key。")

    uploaded = st.file_uploader(
        "选择文件（PDF/CSV/Excel/图片）",
        type=["pdf", "csv", "xlsx", "xls", "png", "jpg", "jpeg", "webp", "txt"],
        accept_multiple_files=True,
    )

    periods = period_options()
    file_meta: list[tuple] = []  # (UploadedFile, period, source)
    if uploaded:
        for uf in uploaded:
            with st.expander(uf.name, expanded=False):
                guessed = guess_period(uf.name)
                idx = periods.index(guessed) if guessed in periods else None
                period = st.selectbox("时间标签", periods, index=idx, key=f"period_{uf.name}")
                source = st.selectbox(
                    "来源类型", [s.value for s in SourceType], key=f"source_{uf.name}"
                )
                st.caption(f"文件名识别到：{guessed or '无'}")
                file_meta.append((uf, period, source))

    if st.button("入库并索引", disabled=not uploaded):
        for uf, period, source in file_meta:
            save_path = config.UPLOAD_DIR / f"{uuid.uuid4().hex[:8]}_{uf.name}"
            save_path.write_bytes(uf.getbuffer())
            with st.status(f"正在解析 {uf.name} …"):
                summary = ingest_file(storage, str(save_path), period, SourceType(source))
                st.write(summary)
        st.success("入库完成")

# ---------- 主区：对话 ----------
st.header("💬 提问")
docs = storage.get_documents()
if docs:
    st.caption(f"知识库已入库 {len(docs)} 个文件")
    with st.expander("已入库文件"):
        for d in docs:
            st.write(f"- [{d.period}] {d.file_name}（{d.source_type.value}，{d.status.value}）")
else:
    st.info("先在左侧上传资料并入库，再提问。")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("例如：本季度留存率下降的可能原因？")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    if not docs:
        st.warning("知识库为空，请先在左侧上传资料并入库。")
    else:
        with st.chat_message("assistant"):
            with st.spinner("检索与分析中…"):
                report = analyze(agent, question)
            st.write_stream(report_sections(report))
            trace = report.get("_trace", [])
            if trace:
                with st.expander("🧠 思考过程（工具调用轨迹）"):
                    for i, t in enumerate(trace, 1):
                        st.write(f"{i}. 调用 `{t['tool']}`：`{t['args']}`")

    st.session_state.messages.append(
        {"role": "assistant", "content": "".join(report_sections(report))}
    )
