"""
Helper: đổi short-lived user token thành long-lived Page token (never expire).

Chạy 1 lần để lấy token, lưu vào GitHub Secrets:

    python scripts/get_page_token.py \\
        --app-id YOUR_APP_ID \\
        --app-secret YOUR_APP_SECRET \\
        --user-token SHORT_LIVED_USER_TOKEN

Output là Page Access Token mà bạn paste vào secret FB_PAGE_ACCESS_TOKEN.
"""
from __future__ import annotations

import argparse
import sys

import requests

GRAPH_API = "https://graph.facebook.com/v25.0"


def exchange_for_long_lived(app_id: str, app_secret: str, user_token: str) -> str:
    """Step 1: short-lived user token -> long-lived user token (~60 ngày)."""
    resp = requests.get(
        f"{GRAPH_API}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": user_token,
        },
        timeout=10,
    )
    if not resp.ok:
        raise SystemExit(
            f"Facebook trả về lỗi {resp.status_code}: {resp.text}\n"
            "Kiểm tra: --app-secret phải là 32-ký-tự hex từ App Dashboard "
            "(KHÔNG phải token EAA...), --user-token phải là short-lived user token thật."
        )
    return resp.json()["access_token"]


def get_pages(long_lived_user_token: str) -> list[dict]:
    """Step 2: list pages user quản lý + page tokens (never expire)."""
    resp = requests.get(
        f"{GRAPH_API}/me/accounts",
        params={
            "access_token": long_lived_user_token,
            "fields": "id,name,access_token",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["data"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--app-id", required=True)
    p.add_argument("--app-secret", required=True)
    p.add_argument("--user-token", required=True,
                   help="Short-lived user token từ Graph API Explorer")
    args = p.parse_args()

    print("[1/2] Exchanging for long-lived user token...")
    ll_token = exchange_for_long_lived(args.app_id, args.app_secret, args.user_token)
    print(f"      Long-lived user token: {ll_token[:20]}...")

    print("[2/2] Fetching page tokens...")
    pages = get_pages(ll_token)
    if not pages:
        print("No pages found. Make sure your user has admin role on at least 1 page.")
        sys.exit(1)

    print(f"\nFound {len(pages)} page(s):")
    for page in pages:
        print(f"\n  Page: {page['name']}")
        print(f"  ID:   {page['id']}")
        print(f"  Token (never expires): {page['access_token']}")

    print("\n>>> Lưu các giá trị này vào GitHub Secrets:")
    print(f"    FB_PAGE_ID           = {pages[0]['id']}")
    print(f"    FB_PAGE_ACCESS_TOKEN = {pages[0]['access_token']}")


if __name__ == "__main__":
    main()
