"""
Summarizer - dùng Claude API tóm tắt bài báo thành 2-3 câu tiếng Việt.

Yêu cầu: pip install anthropic
Cần biến môi trường ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import os
from typing import Optional

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None  # type: ignore


SYSTEM_PROMPT = """Bạn là biên tập viên tóm tắt tin tức tiếng Việt.
Nhiệm vụ: tóm tắt bài báo thành 2-3 câu, tối đa 240 ký tự.
Yêu cầu:
- Văn phong báo chí, trung lập, ngắn gọn.
- Giữ thông tin chính: ai/cái gì, ở đâu, hệ quả.
- Không thêm bình luận, không dùng "Bài báo nói rằng...".
- Trả về DUY NHẤT phần tóm tắt, không có tiền tố."""


class Summarizer:
    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        if Anthropic is None:
            raise ImportError("pip install anthropic")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Set ANTHROPIC_API_KEY environment variable")
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def summarize(self, title: str, content: str) -> str:
        user_msg = f"Tiêu đề: {title}\n\nNội dung: {content}\n\nTóm tắt:"
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        return resp.content[0].text.strip()


def fallback_summary(text: str, max_chars: int = 240) -> str:
    """Khi không có API key: cắt ngắn từ summary RSS."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    # Cắt tại dấu chấm gần nhất
    cut = text[:max_chars].rsplit(".", 1)[0]
    return cut + "." if cut else text[:max_chars] + "…"


if __name__ == "__main__":
    sample = (
        "Hà Nội - Bộ Y tế xác nhận một ca mắc Hantavirus tại bệnh viện Bạch Mai. "
        "Bệnh nhân nam 34 tuổi, vào viện với triệu chứng sốt cao, đau cơ, "
        "sau đó suy hô hấp nhanh chóng và được chuyển vào khoa hồi sức tích cực."
    )
    print(fallback_summary(sample, 200))
