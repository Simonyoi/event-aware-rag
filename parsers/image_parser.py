"""图片解析：qwen-vl 生成结构化文本描述（图表类型 + 关键数据点 + 可见文字）。"""
from __future__ import annotations

import base64
import io
import uuid

from langchain_core.messages import HumanMessage
from PIL import Image

from core.llm import get_vision_llm
from core.models import Chunk, SourceType
from .base import BaseParser

_PROMPT = (
    "请描述这张图片/图表的内容：图表类型、关键数据点、趋势，以及所有可见文字。"
    "用简洁中文，突出可量化的数字和变化。"
)


class ImageParser(BaseParser):
    def parse(
        self,
        file_path: str,
        doc_id: str,
        period: str,
        source_type: SourceType,
        **kwargs,
    ) -> list[Chunk]:
        with open(file_path, "rb") as f:
            raw = f.read()

        # 压缩到合理尺寸，统一转 PNG 再 base64，避免超大图
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img.thumbnail((1280, 1280))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        msg = HumanMessage(
            content=[
                {"type": "text", "text": kwargs.get("prompt") or _PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                },
            ]
        )
        resp = get_vision_llm().invoke([msg])
        text = resp.content if isinstance(resp.content, str) else str(resp.content)

        return [
            Chunk(
                chunk_id=uuid.uuid4().hex[:16],
                doc_id=doc_id,
                text=text,
                period=period,
                source_type=source_type,
                seq=0,
            )
        ]
