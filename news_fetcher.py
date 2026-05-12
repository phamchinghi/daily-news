"""
News aggregator - lấy tin từ RSS feeds các báo Việt Nam.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup


# VnExpress RSS feeds - tất cả chuyên mục
FEEDS = {
    # Tin tổng hợp
    "vnexpress_home":       "https://vnexpress.net/rss/tin-moi-nhat.rss",
    # Thể thao & Bóng đá (ưu tiên đầu album)
    "vnexpress_bongda":     "https://vnexpress.net/rss/bong-da.rss",
    "vnexpress_thethao":    "https://vnexpress.net/rss/the-thao.rss",
    # Thời sự
    "vnexpress_thoisu":     "https://vnexpress.net/rss/thoi-su.rss",
    # Thế giới
    "vnexpress_thegioi":    "https://vnexpress.net/rss/the-gioi.rss",
    # Kinh doanh
    "vnexpress_kinhdoanh":  "https://vnexpress.net/rss/kinh-doanh.rss",
    # Khoa học công nghệ
    "vnexpress_khoahoc":    "https://vnexpress.net/rss/khoa-hoc.rss",
    "vnexpress_sohoa":      "https://vnexpress.net/rss/so-hoa.rss",
    # Giải trí
    "vnexpress_giaitri":    "https://vnexpress.net/rss/giai-tri.rss",
    # Pháp luật
    "vnexpress_phapluat":   "https://vnexpress.net/rss/phap-luat.rss",
    # Góc nhìn
    "vnexpress_gocnhin":    "https://vnexpress.net/rss/goc-nhin.rss",
    # Bất động sản
    "vnexpress_batdongsan": "https://vnexpress.net/rss/bat-dong-san.rss",
    # Sức khỏe
    "vnexpress_suckhoe":    "https://vnexpress.net/rss/suc-khoe.rss",
    # Giáo dục
    "vnexpress_giaoduc":    "https://vnexpress.net/rss/giao-duc.rss",
    # Đời sống
    "vnexpress_doisong":    "https://vnexpress.net/rss/doi-song.rss",
    # Xe
    "vnexpress_xe":         "https://vnexpress.net/rss/xe.rss",
    # Du lịch
    "vnexpress_dulich":     "https://vnexpress.net/rss/du-lich.rss",
    # Ý kiến
    "vnexpress_ykien":      "https://vnexpress.net/rss/y-kien.rss",
    # Tâm sự
    "vnexpress_tamsu":      "https://vnexpress.net/rss/tam-su.rss",
    # Thư giãn
    "vnexpress_thuGian":    "https://vnexpress.net/rss/thu-gian.rss",
}


@dataclass
class RawArticle:
    title: str
    link: str
    summary: str            # mô tả từ RSS (có thể có HTML)
    image: Optional[str]
    source: str             # vd "vnexpress.net"
    category: str = ""


def _first_image_from_html(html: str) -> Optional[str]:
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    img = soup.find("img")
    if img and img.get("src"):
        return img["src"]
    return None


def _clean_html(html: str) -> str:
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _domain_of(url: str) -> str:
    m = re.search(r"https?://([^/]+)/", url + "/")
    return m.group(1).replace("www.", "") if m else ""


def fetch_feed(feed_key: str, limit: int = 5) -> list[RawArticle]:
    url = FEEDS[feed_key]
    parsed = feedparser.parse(url)
    articles: list[RawArticle] = []

    for entry in parsed.entries[:limit]:
        # Ảnh: thử media_content, enclosure, hoặc tìm <img> trong summary
        image = None
        if hasattr(entry, "media_content") and entry.media_content:
            image = entry.media_content[0].get("url")
        if not image and hasattr(entry, "enclosures") and entry.enclosures:
            image = entry.enclosures[0].get("href") or entry.enclosures[0].get("url")
        if not image:
            image = _first_image_from_html(entry.get("summary", ""))

        articles.append(RawArticle(
            title=entry.get("title", "").strip(),
            link=entry.get("link", ""),
            summary=_clean_html(entry.get("summary", "")),
            image=image,
            source=_domain_of(entry.get("link", "")),
            category=feed_key.split("_", 1)[-1] if "_" in feed_key else "",
        ))
    return articles


def fetch_article_image(url: str) -> Optional[str]:
    """Fallback: scrape og:image từ bài viết nếu RSS không có ảnh."""
    try:
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (compatible; NewsCardBot/1.0)"
        })
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]
    except Exception:
        return None
    return None


if __name__ == "__main__":
    items = fetch_feed("vnexpress_health", limit=3)
    for it in items:
        print(f"- {it.title}")
        print(f"  {it.link}")
        print(f"  image: {it.image}")
        print(f"  summary: {it.summary[:120]}...")
        print()
