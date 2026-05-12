"""
CLI - tổng hợp tin tức + tạo ảnh card hàng loạt.

Cách dùng:
    # Tạo card từ 5 tin VnExpress sức khỏe
    python main.py --feed vnexpress_health --limit 5

    # Dùng API tóm tắt (cần ANTHROPIC_API_KEY)
    python main.py --feed vnexpress_home --limit 4 --use-ai

    # Tạo 1 card từ input thủ công
    python main.py --manual \\
        --title "Hantavirus..." \\
        --summary "Người mắc..." \\
        --image https://... \\
        --source "vnexpress.net - Sức khỏe"
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from card_generator import NewsItem, render_card
from news_fetcher import FEEDS, fetch_article_image, fetch_feed
from summarizer import Summarizer, fallback_summary


def _slug(text: str, maxlen: int = 50) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text[:maxlen]


def run_feed(feed_key: str, limit: int, use_ai: bool, outdir: Path) -> None:
    print(f"[*] Fetching feed: {feed_key}")
    articles = fetch_feed(feed_key, limit=limit)
    print(f"[*] Got {len(articles)} articles")

    summarizer = Summarizer() if use_ai else None

    for i, art in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] {art.title}")

        # Đảm bảo có ảnh
        image = art.image
        if not image:
            print("    -> no image in RSS, scraping og:image...")
            image = fetch_article_image(art.link)
        if not image:
            print("    !! skip: no image")
            continue

        # Tóm tắt
        if summarizer:
            try:
                summary = summarizer.summarize(art.title, art.summary)
            except Exception as e:
                print(f"    AI failed ({e}), fallback")
                summary = fallback_summary(art.summary)
        else:
            summary = fallback_summary(art.summary)

        item = NewsItem(
            title=art.title,
            summary=summary,
            image=image,
            source=f"{art.source} - {art.category}" if art.category else art.source,
        )

        out_path = outdir / f"{i:02d}-{_slug(art.title)}.jpg"
        try:
            render_card(item, out_path)
            print(f"    -> saved {out_path}")
        except Exception as e:
            print(f"    !! render failed: {e}")


def run_manual(args, outdir: Path) -> None:
    item = NewsItem(
        title=args.title,
        summary=args.summary,
        image=args.image,
        source=args.source or "",
    )
    out_path = outdir / f"{_slug(args.title)}.jpg"
    render_card(item, out_path)
    print(f"Saved: {out_path}")


def main():
    p = argparse.ArgumentParser(description="News Card Generator (J2TEAM style)")
    p.add_argument("--outdir", default="output", help="Output directory")

    # Mode feed
    p.add_argument("--feed", choices=list(FEEDS.keys()), help="RSS feed key")
    p.add_argument("--limit", type=int, default=4)
    p.add_argument("--use-ai", action="store_true",
                   help="Use Claude API for summarization")

    # Mode manual
    p.add_argument("--manual", action="store_true")
    p.add_argument("--title")
    p.add_argument("--summary")
    p.add_argument("--image")
    p.add_argument("--source")

    args = p.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.manual:
        if not (args.title and args.summary and args.image):
            print("Manual mode needs --title, --summary, --image", file=sys.stderr)
            sys.exit(1)
        run_manual(args, outdir)
    elif args.feed:
        run_feed(args.feed, args.limit, args.use_ai, outdir)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
