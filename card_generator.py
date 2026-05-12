"""
News Card Generator - tạo ảnh news card theo style Ở Đây Có Tin Tức.

Layout: 1200x1600 (3:4)
- Ảnh trên: chiếm ~55% chiều cao (1200x880)
- Khối vàng dưới: chiếm ~45% (1200x720)
  + Tiêu đề: bold, ~64-72px, max 3 dòng
  + Mô tả: regular, ~36px, max 3 dòng
- Watermark "Ở Đây Có Tin Tức" góc trên phải (trắng, in đè ảnh)
- Source góc dưới phải (xám đậm)
"""

from __future__ import annotations

import io
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont


# ---------------- Config ----------------

CARD_W, CARD_H = 1200, 1600
IMG_H = 880                # phần ảnh phía trên
YELLOW = (255, 193, 7)     # #FFC107
TEXT_DARK = (17, 17, 17)
TEXT_MUTED = (60, 60, 60)
WATERMARK_COLOR = (255, 255, 255)
SOURCE_COLOR = (90, 90, 90)

PADDING_X = 60
TITLE_TOP = IMG_H + 60
TITLE_SIZE = 72
TITLE_LINE_H = 88
DESC_SIZE = 36
DESC_LINE_H = 52
DESC_GAP = 40              # khoảng cách tiêu đề -> mô tả

# ---------------- Data ----------------

@dataclass
class NewsItem:
    title: str
    summary: str
    image: str | Path        # URL hoặc local path
    source: str = ""         # vd: "vnexpress.net - Sức khỏe"
    brand: str = "Ở Đây Có Tin Tức"


# ---------------- Font loading ----------------

# Be Vietnam Pro hỗ trợ dấu tiếng Việt rất tốt. Nếu chưa có,
# fonts/ sẽ rỗng và code fallback sang DejaVuSans (có sẵn trên Ubuntu).

FONT_DIR = Path(__file__).parent / "fonts"

def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates_bold = [
        FONT_DIR / "BeVietnamPro-Bold.ttf",
        FONT_DIR / "Inter-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    candidates_regular = [
        FONT_DIR / "BeVietnamPro-Regular.ttf",
        FONT_DIR / "Inter-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in (candidates_bold if bold else candidates_regular):
        try:
            return ImageFont.truetype(str(p), size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# ---------------- Text wrapping ----------------

def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    max_lines: int,
) -> list[str]:
    """Wrap text theo pixel width thật (chính xác hơn textwrap theo ký tự)."""
    words = text.split()
    lines: list[str] = []
    current = ""

    for word in words:
        trial = f"{current} {word}".strip()
        w = draw.textlength(trial, font=font)
        if w <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) == max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)

    # Truncate dòng cuối nếu vẫn còn chữ thừa
    if len(lines) == max_lines:
        consumed = " ".join(lines)
        remaining = text[len(consumed):].strip()
        if remaining:
            last = lines[-1]
            ellipsis = "…"
            while draw.textlength(last + ellipsis, font=font) > max_width and last:
                last = last[:-1]
            lines[-1] = last + ellipsis
    return lines


# ---------------- Image helpers ----------------

def _load_image(src: str | Path) -> Image.Image:
    if isinstance(src, str) and src.startswith(("http://", "https://")):
        resp = requests.get(src, timeout=15)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")
    return Image.open(src).convert("RGB")


def _cover_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Crop kiểu CSS object-fit: cover."""
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    tgt_ratio = target_w / target_h
    if src_ratio > tgt_ratio:
        # Source rộng hơn -> crop 2 bên
        new_w = int(src_h * tgt_ratio)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w / tgt_ratio)
        top = (src_h - new_h) // 2
        img = img.crop((0, top, src_w, top + new_h))
    return img.resize((target_w, target_h), Image.LANCZOS)


# ---------------- Main render ----------------

def render_card(item: NewsItem, output_path: str | Path) -> Path:
    canvas = Image.new("RGB", (CARD_W, CARD_H), YELLOW)

    # 1. Ảnh trên
    photo = _load_image(item.image)
    photo = _cover_crop(photo, CARD_W, IMG_H)
    canvas.paste(photo, (0, 0))

    draw = ImageDraw.Draw(canvas)

    # 2. Watermark brand góc phải trên (đè lên ảnh)
    brand_font = _load_font(36, bold=True)
    brand_w = draw.textlength(item.brand, font=brand_font)
    draw.text(
        (CARD_W - PADDING_X - brand_w, 40),
        item.brand,
        font=brand_font,
        fill=WATERMARK_COLOR,
    )

    # 3. Tiêu đề
    title_font = _load_font(TITLE_SIZE, bold=True)
    title_lines = _wrap_text(
        draw, item.title, title_font,
        max_width=CARD_W - 2 * PADDING_X,
        max_lines=3,
    )
    y = TITLE_TOP
    for line in title_lines:
        draw.text((PADDING_X, y), line, font=title_font, fill=TEXT_DARK)
        y += TITLE_LINE_H

    # 4. Mô tả - bắt đầu sau tiêu đề + khoảng cách
    y += DESC_GAP
    desc_font = _load_font(DESC_SIZE, bold=False)
    desc_lines = _wrap_text(
        draw, item.summary, desc_font,
        max_width=CARD_W - 2 * PADDING_X,
        max_lines=4,
    )
    for line in desc_lines:
        draw.text((PADDING_X, y), line, font=desc_font, fill=TEXT_MUTED)
        y += DESC_LINE_H

    # 5. Source góc phải dưới
    if item.source:
        src_font = _load_font(28, bold=False)
        src_w = draw.textlength(item.source, font=src_font)
        draw.text(
            (CARD_W - PADDING_X - src_w, CARD_H - 60),
            item.source,
            font=src_font,
            fill=SOURCE_COLOR,
        )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "JPEG", quality=92)
    return out


if __name__ == "__main__":
    # Demo nhanh
    demo = NewsItem(
        title="Hantavirus - bệnh dễ nhầm với cúm nhưng chuyển nặng nhanh",
        summary=(
            "Người mắc Hantavirus có thể chỉ sốt nhẹ, đau cơ như cúm "
            "nhưng sau đó nhanh chóng rơi vào suy hô hấp cấp, phù phổi, "
            "tụt huyết áp và sốc tim."
        ),
        image="https://images.unsplash.com/photo-1584634731339-252c581abfc5?w=1600",
        source="vnexpress.net - Sức khỏe",
    )
    path = render_card(demo, "output/demo.jpg")
    print(f"Saved: {path}")
