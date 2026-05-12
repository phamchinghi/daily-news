"""
Daily run script - được chạy bởi GitHub Actions mỗi sáng 7h Vietnam time.

Pipeline:
  1. Fetch N tin mới nhất từ feeds đã cấu hình
  2. Tóm tắt bằng Claude API (fallback nếu không có key)
  3. Render mỗi tin thành 1 ảnh card
  4. Đăng lên Facebook Page:
       - Bài đăng dạng album nhiều ảnh
       - Caption tổng hợp tiêu đề + link tin
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Cho phép chạy từ root
sys.path.insert(0, str(Path(__file__).parent))

from card_generator import NewsItem, render_card
from news_fetcher import fetch_article_image, fetch_feed
from publisher import FacebookPublisher
from summarizer import Summarizer, fallback_summary


# ---------------- Config ----------------

# Feeds bóng đá/thể thao — luôn lấy trước, đặt đầu album
SPORT_FEEDS = [
    "vnexpress_bongda",
    "vnexpress_thethao",
    "vnexpress_thoisu",
]

# Feeds tin tức chung — điền vào các slot còn lại
OTHER_FEEDS = [
    "vnexpress_thegioi",
    "vnexpress_kinhdoanh",
    "vnexpress_khoahoc",
    "vnexpress_sohoa",
    "vnexpress_giaitri",
    "vnexpress_phapluat",
    "vnexpress_gocnhin",
    "vnexpress_batdongsan",
    "vnexpress_suckhoe",
    "vnexpress_giaoduc",
    "vnexpress_doisong",
    "vnexpress_xe",
    "vnexpress_dulich",
    "vnexpress_thuGian",
]

MAX_CARDS = 20          # số card mỗi bài (Facebook hiển thị tốt 4-6 ảnh)
MAX_SPORT_CARDS = 2    # tối đa 1 card thể thao/bóng đá (đứng đầu album)
PER_FEED_LIMIT = 2     # lấy 2 tin / feed
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

VIETNAMESE_WEEKDAYS = {
    0: "THỨ HAI", 1: "THỨ BA", 2: "THỨ TƯ", 3: "THỨ NĂM",
    4: "THỨ SÁU", 5: "THỨ BẢY", 6: "CHỦ NHẬT",
}


_CATEGORY_HASHTAGS: dict[str, str] = {
    "bongda":     "#bongda #worldcup2026 #tructiepbongda",
    "thethao":    "#thethao #sportvietnam",
    "thoisu":     "#thoisu #tintucvietnam #chinhsach",
    "thegioi":    "#thegioi #tintucquocte",
    "kinhdoanh":  "#kinhdoanh #chungkhoan #kinhte",
    "khoahoc":    "#khoahoc #congnghe #science",
    "sohoa":      "#sohoa #congnghe #ai",
    "giaitri":    "#giaitri #showbiz #nghesivietnam",
    "phapluat":   "#phapluat #tintucphapluat",
    "suckhoe":    "#suckhoe #suckhoedoisong",
    "giaoduc":    "#giaoduc #tuyensinh",
    "doisong":    "#doisong #lifestyle",
    "xe":         "#xe #otovietnam #xedien",
    "dulich":     "#dulich #travel #vietnam",
    "batdongsan": "#batdongsan #nhadat",
}

def build_caption(items: list[tuple[NewsItem, str]]) -> str:
    """items: list of (NewsItem, link)."""
    now = datetime.now(VN_TZ)
    weekday = VIETNAMESE_WEEKDAYS[now.weekday()]
    date_str = now.strftime("%d/%m/%Y")

    header = f"📢 DIEM TIN SANG {weekday} | {date_str}\n\n"
    lines = ["Tin noi bat hom nay:\n"]
    for i, (item, link) in enumerate(items, 1):
        lines.append(f"{i}. {item.title}")
        if link:
            lines.append(f"   {link}\n")

    # Hashtag cơ bản + theo chuyên mục
    base_tags = "#odaycotintuc #tintuc #tinnoibat #vietnamnews"
    extra_tags = " ".join(
        _CATEGORY_HASHTAGS[it.category]
        for it, _ in items
        if it.category in _CATEGORY_HASHTAGS
    )
    hashtags = f"{base_tags} {extra_tags}".strip()

    cta = (
        "\n\nTheo doi trang de cap nhat tin tuc moi nhat moi sang!"
        "\nBan quan tam den tin nao nhat? Binh luan ben duoi nhe!"
    )

    return header + "\n".join(lines) + cta + "\n\n" + hashtags


def main() -> int:
    print(f"=== Daily run @ {datetime.now(VN_TZ).isoformat()} ===")

    # 1. Fetch — bóng đá/thể thao trước, sau đó tin tức chung
    def fetch_all(feeds: list[str]) -> list:
        results = []
        for feed in feeds:
            try:
                articles = fetch_feed(feed, limit=PER_FEED_LIMIT)
                print(f"[fetch] {feed}: {len(articles)} articles")
                results.extend(articles)
            except Exception as e:
                print(f"[fetch] {feed} FAILED: {e}")
        return results

    sport_articles = fetch_all(SPORT_FEEDS)
    other_articles = fetch_all(OTHER_FEEDS)

    # Lọc article có ảnh — sport trước (tối đa MAX_SPORT_CARDS), sau đó other
    def pick_with_image(articles: list, slots: int) -> list:
        picked = []
        for art in articles:
            if not art.image:
                art.image = fetch_article_image(art.link)
            if art.image:
                picked.append(art)
            if len(picked) >= slots:
                break
        return picked

    sport_valid = pick_with_image(sport_articles, MAX_SPORT_CARDS)
    other_valid = pick_with_image(other_articles, MAX_CARDS - len(sport_valid))
    valid = sport_valid + other_valid

    if not valid:
        print("[!] No articles with images. Abort.")
        return 1

    print(f"[*] Selected {len(valid)} articles")

    # 2. Summarize
    summarizer = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            summarizer = Summarizer()
            print("[*] Claude summarizer ready")
        except Exception as e:
            print(f"[!] Summarizer init failed: {e}")

    # 3. Render cards
    out_dir = Path("daily_output") / datetime.now(VN_TZ).strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[tuple[NewsItem, str, Path]] = []

    for i, art in enumerate(valid, 1):
        try:
            if summarizer:
                try:
                    summary = summarizer.summarize(art.title, art.summary)
                except Exception as e:
                    print(f"[render] {i} Claude failed, using RSS fallback: {e}")
                    summary = fallback_summary(art.summary)
            else:
                summary = fallback_summary(art.summary)

            item = NewsItem(
                title=art.title,
                summary=summary,
                image=art.image,
                source=art.source,
                category=art.category,
            )
            path = out_dir / f"{i:02d}.jpg"
            render_card(item, path)
            rendered.append((item, art.link, path))
            print(f"[render] {i}: {path}")
        except Exception as e:
            print(f"[render] {i} FAILED: {e}")

    if not rendered:
        print("[!] No cards rendered. Abort.")
        return 1

    # 4. Post Facebook
    if os.environ.get("DRY_RUN") == "1":
        print("[*] DRY_RUN=1, skip Facebook posting")
        for item, link, path in rendered:
            print(f"  would post: {path} - {item.title}")
        return 0

    try:
        pub = FacebookPublisher()
        pub.verify_token()
        caption = build_caption([(it, lk) for it, lk, _ in rendered])
        result = pub.post_multi_photo_album(
            image_paths=[str(p) for _, _, p in rendered],
            caption=caption,
        )
        print(f"[fb] Posted: {result}")
    except Exception as e:
        print(f"[fb] FAILED: {e}")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
