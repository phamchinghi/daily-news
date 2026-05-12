"""
Facebook publisher - đăng ảnh kèm caption lên Facebook Page.

Yêu cầu:
  - PAGE_ID:           ID của Facebook Page
  - PAGE_ACCESS_TOKEN: Long-lived Page Access Token (never expire)
  - Permission `pages_manage_posts` đã được app review approve.

2 mode đăng:
  1. post_single_photo(): 1 ảnh + caption
  2. post_multi_photo_album(): nhiều ảnh dưới dạng album (giống J2TEAM)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Sequence

import requests


GRAPH_API_VERSION = "v25.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class FacebookPublisher:
    def __init__(self, page_id: str | None = None, access_token: str | None = None):
        self.page_id = page_id or os.environ.get("FB_PAGE_ID")
        self.access_token = access_token or os.environ.get("FB_PAGE_ACCESS_TOKEN")
        if not (self.page_id and self.access_token):
            raise RuntimeError(
                "Set FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN environment variables"
            )

    # ----- Single photo -----

    def post_single_photo(
        self,
        image_path: str | Path,
        caption: str,
        published: bool = True,
    ) -> dict:
        """Đăng 1 ảnh với caption. Trả về dict chứa post id."""
        url = f"{GRAPH_API_BASE}/{self.page_id}/photos"
        with open(image_path, "rb") as f:
            resp = requests.post(
                url,
                files={"source": f},
                data={
                    "caption": caption,
                    "published": "true" if published else "false",
                    "access_token": self.access_token,
                },
                timeout=60,
            )
        resp.raise_for_status()
        return resp.json()

    # ----- Multi-photo album -----

    def _upload_unpublished(self, image_path: str | Path) -> str:
        """Upload 1 ảnh dạng unpublished, trả về media_fbid để ghép album."""
        url = f"{GRAPH_API_BASE}/{self.page_id}/photos"
        with open(image_path, "rb") as f:
            resp = requests.post(
                url,
                files={"source": f},
                data={
                    "published": "false",
                    "access_token": self.access_token,
                },
                timeout=60,
            )
        resp.raise_for_status()
        return resp.json()["id"]

    def post_multi_photo_album(
        self,
        image_paths: Sequence[str | Path],
        caption: str,
    ) -> dict:
        """Đăng nhiều ảnh dạng album (giống bài J2TEAM grid)."""
        if not image_paths:
            raise ValueError("image_paths is empty")

        media_ids = [self._upload_unpublished(p) for p in image_paths]
        attached = [{"media_fbid": mid} for mid in media_ids]

        url = f"{GRAPH_API_BASE}/{self.page_id}/feed"
        resp = requests.post(
            url,
            data={
                "message": caption,
                "attached_media": json.dumps(attached),
                "access_token": self.access_token,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()

    # ----- Helper -----

    def verify_token(self) -> dict:
        """Check token còn hợp lệ và quyền hạn."""
        url = f"{GRAPH_API_BASE}/me"
        resp = requests.get(
            url,
            params={"access_token": self.access_token, "fields": "id,name"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    # Test verify token (không đăng gì)
    pub = FacebookPublisher()
    info = pub.verify_token()
    print(f"Token OK. Page: {info}")
