"""
News Card Generator - style Ở Đây Có Tin Tức.

Layout: 1200x1600 (3:4)
- Ảnh tin tức: ~54% trên (1200×860)
- Accent bar đỏ: 8px
- Panel navy: ~45% còn lại
  + Category badge (top-left, trên ảnh)
  + Brand watermark (top-right, trên ảnh, stroke trắng)
  + Tiêu đề: bold white, 68px, max 3 dòng
  + Mô tả: light blue, 34px, max 4 dòng
  + Source: vàng, bottom-right
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont


# ── Palette (từ avatar kênh) ──────────────────────────────────────

CARD_W, CARD_H = 1200, 1600
IMG_H          = 860

NAVY           = (13,  27, 110)    # #0D1B6E  – panel chính
RED            = (227, 30,  36)    # #E31E24  – accent / badge breaking
YELLOW         = (245, 184,  0)    # #F5B800  – tagline / source
WHITE          = (255, 255, 255)
TEXT_DESC      = (176, 196, 222)   # #B0C4DE  – mô tả (light steel blue)
STROKE_DARK    = (0,   0,  30)     # stroke cho text trên ảnh

ACCENT_BAR_H   = 8
PADDING_X      = 64
TITLE_TOP      = IMG_H + ACCENT_BAR_H + 60
TITLE_SIZE     = 68
TITLE_LINE_H   = 86
DESC_SIZE      = 34
DESC_LINE_H    = 50
DESC_GAP       = 38

BADGE_PAD_X    = 18
BADGE_PAD_Y    = 10
BADGE_FONT_SZ  = 28
BADGE_RADIUS   = 6
BADGE_TOP      = 40
BADGE_LEFT     = PADDING_X

BRAND_SIZE     = 34

# category key → (label, badge_color)
CATEGORY_STYLE: dict[str, tuple[str, tuple]] = {
    "bongda":      ("BONG DA",        RED),
    "thethao":     ("THE THAO",       RED),
    "thoisu":      ("THOI SU",        RED),
    "thegioi":     ("THE GIOI",       (0,  80, 180)),
    "kinhdoanh":   ("KINH TE",        (0,  80, 180)),
    "khoahoc":     ("KHOA HOC",       (0,  80, 180)),
    "sohoa":       ("CONG NGHE",      (0,  80, 180)),
    "giaitri":     ("GIAI TRI",       (180, 60,  0)),
    "phapluat":    ("PHAP LUAT",      (0,  80, 180)),
    "gocnhin":     ("GOC NHIN",       (0,  80, 180)),
    "batdongsan":  ("BAT DONG SAN",   (0,  80, 180)),
    "suckhoe":     ("SUC KHOE",       (190,  0, 60)),
    "giaoduc":     ("GIAO DUC",       (0,  80, 180)),
    "doisong":     ("DOI SONG",       (140, 90,  0)),
    "xe":          ("XE",             (0,  80, 180)),
    "dulich":      ("DU LICH",        (0, 130, 100)),
    "ykien":       ("Y KIEN",         (0,  80, 180)),
    "tamsu":       ("TAM SU",         (100, 50, 130)),
    "thuGian":     ("THU GIAN",       (80, 120,  0)),
    "home":        ("TIN MOI",        RED),
}


@dataclass
class NewsItem:
    title: str
    summary: str
    image: str | Path
    source: str   = ""
    brand: str    = "O Day Co Tin Tuc"
    category: str = ""


# ── Font loading ──────────────────────────────────────────────────

FONT_DIR = Path(__file__).parent / "fonts"

def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        FONT_DIR / ("BeVietnamPro-Bold.ttf" if bold else "BeVietnamPro-Regular.ttf"),
        FONT_DIR / ("Inter-Bold.ttf"        if bold else "Inter-Regular.ttf"),
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(str(p), size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# ── Text helpers ──────────────────────────────────────────────────

def _wrap_text(draw, text, font, max_width, max_lines):
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) == max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines:
        consumed = " ".join(lines)
        if text[len(consumed):].strip():
            last = lines[-1]
            while draw.textlength(last + "...", font=font) > max_width and last:
                last = last[:-1]
            lines[-1] = last + "..."
    return lines


def _stroke_text(draw, pos, text, font, fill, stroke=STROKE_DARK, sw=2):
    """Draw text với viền đen mỏng để dễ đọc trên ảnh sáng."""
    x, y = pos
    for dx in range(-sw, sw + 1):
        for dy in range(-sw, sw + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=stroke)
    draw.text(pos, text, font=font, fill=fill)


# ── Image helpers ─────────────────────────────────────────────────

def _load_image(src: str | Path) -> Image.Image:
    if isinstance(src, str) and src.startswith(("http://", "https://")):
        resp = requests.get(src, timeout=15)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")
    return Image.open(src).convert("RGB")


def _cover_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    if src_w / src_h > target_w / target_h:
        new_w = int(src_h * target_w / target_h)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w * target_h / target_w)
        top = (src_h - new_h) // 2
        img = img.crop((0, top, src_w, top + new_h))
    return img.resize((target_w, target_h), Image.LANCZOS)


# ── Main render ───────────────────────────────────────────────────

def render_card(item: NewsItem, output_path: str | Path) -> Path:
    # Canvas nền navy
    canvas = Image.new("RGB", (CARD_W, CARD_H), NAVY)

    # 1. Ảnh tin tức (top)
    photo = _cover_crop(_load_image(item.image), CARD_W, IMG_H)
    canvas.paste(photo, (0, 0))
    draw = ImageDraw.Draw(canvas)

    # 2. Brand watermark (top-right, trên ảnh)
    brand_font = _load_font(BRAND_SIZE, bold=True)
    brand_w = draw.textlength(item.brand, font=brand_font)
    _stroke_text(draw, (CARD_W - PADDING_X - brand_w, 36), item.brand, brand_font, WHITE)

    # 3. Category badge (top-left, trên ảnh)
    cat_key = item.category.lower()
    label, badge_color = CATEGORY_STYLE.get(cat_key, ("TIN TUC", RED))
    badge_font = _load_font(BADGE_FONT_SZ, bold=True)
    label_w = draw.textlength(label, font=badge_font)
    badge_rect = [
        BADGE_LEFT,
        BADGE_TOP,
        BADGE_LEFT + label_w + BADGE_PAD_X * 2,
        BADGE_TOP + BADGE_FONT_SZ + BADGE_PAD_Y * 2,
    ]
    draw.rounded_rectangle(badge_rect, radius=BADGE_RADIUS, fill=badge_color)
    draw.text(
        (BADGE_LEFT + BADGE_PAD_X, BADGE_TOP + BADGE_PAD_Y),
        label, font=badge_font, fill=WHITE,
    )

    # 4. Red accent bar (giữa ảnh và panel)
    draw.rectangle([0, IMG_H, CARD_W, IMG_H + ACCENT_BAR_H], fill=RED)

    # 5. Tiêu đề (white, bold)
    title_font = _load_font(TITLE_SIZE, bold=True)
    title_lines = _wrap_text(draw, item.title, title_font, CARD_W - 2 * PADDING_X, 3)
    y = TITLE_TOP
    for line in title_lines:
        draw.text((PADDING_X, y), line, font=title_font, fill=WHITE)
        y += TITLE_LINE_H

    # 6. Mô tả (light steel blue)
    y += DESC_GAP
    desc_font = _load_font(DESC_SIZE)
    desc_lines = _wrap_text(draw, item.summary, desc_font, CARD_W - 2 * PADDING_X, 4)
    for line in desc_lines:
        draw.text((PADDING_X, y), line, font=desc_font, fill=TEXT_DESC)
        y += DESC_LINE_H

    # 7. Source (yellow, bottom-right)
    if item.source:
        src_font = _load_font(26)
        src_w = draw.textlength(item.source, font=src_font)
        draw.text(
            (CARD_W - PADDING_X - src_w, CARD_H - 56),
            item.source, font=src_font, fill=YELLOW,
        )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "JPEG", quality=92)
    return out


if __name__ == "__main__":
    demo = NewsItem(
        title="Hantavirus - benh de nham voi cum nhung chuyen nang nhanh",
        summary=(
            "Nguoi mac Hantavirus co the chi sot nhe, dau co nhu cum "
            "nhung sau do nhanh chong roi vao suy ho hap cap, phu phoi, "
            "tut huyet ap va soc tim."
        ),
        image="https://images.unsplash.com/photo-1584634731339-252c581abfc5?w=1600",
        source="vnexpress.net",
        category="suckhoe",
    )
    path = render_card(demo, "output/demo.jpg")
    print(f"Saved: {path}")
