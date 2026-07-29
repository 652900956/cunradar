"""Bilibili UP主视频采集器。

使用 B站官方 API 获取 UP 主视频更新。
绕过风控的关键步骤：
  1. 先访问空间主页获取 Cookie（buvid3）
  2. 间隔一定时间后再调用 API
  3. 使用 retry 应对频率限制
"""

import time
from datetime import datetime, timezone

import requests

from .base import BaseCollector, CollectedItem


class BilibiliCollector(BaseCollector):
    """Collect latest videos from a list of Bilibili creators via official API."""

    API_BASE = "https://api.bilibili.com/x/space/arc/search"
    MAX_RETRIES = 3
    RETRY_DELAYS = [3, 5, 10]  # seconds between retries

    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    def __init__(self, creators: list[dict]) -> None:
        self.creators = creators
        # One session per collector (shared across all creators)
        self._session = requests.Session()

    def _ensure_cookies(self, uid: int | str) -> None:
        """Visit space page to obtain session cookies (buvid3 etc.)."""
        print(f"  [Bilibili] Getting session cookies (space.bilibili.com/{uid})")
        try:
            self._session.get(
                f"https://space.bilibili.com/{uid}",
                headers={
                    "User-Agent": self._HEADERS["User-Agent"],
                    "Accept-Language": "zh-CN,zh;q=0.9",
                },
                timeout=15,
            )
        except Exception as e:
            # Non-critical; just log
            print(f"  [Bilibili] Cookie fetch warning: {e}")

    def _fetch_videos(self, uid: int | str) -> dict | None:
        """Try to fetch video list from old API. Returns JSON dict or None."""
        url = f"{self.API_BASE}?mid={uid}&ps=10&pn=1"
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = self._session.get(
                    url,
                    headers={
                        **self._HEADERS,
                        "Referer": f"https://space.bilibili.com/{uid}",
                    },
                    timeout=15,
                )
                data = resp.json()
            except Exception as e:
                print(f"  [Bilibili] Request error (attempt {attempt + 1}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAYS[attempt])
                continue

            code = data.get("code")
            msg = data.get("message", "")

            if code == 0:
                return data

            if code == -799:
                # Rate limited — wait and retry
                delay = self.RETRY_DELAYS[attempt]
                print(f"  [Bilibili] Rate limited (-799), retrying in {delay}s...")
                time.sleep(delay)
                continue

            # Other errors — not recoverable
            print(f"  [Bilibili] API error: code={code}, msg={msg}")
            return None

        print(f"  [Bilibili] All {self.MAX_RETRIES} attempts exhausted for uid={uid}")
        return None

    def collect(self) -> list[CollectedItem]:
        items: list[CollectedItem] = []

        for creator in self.creators:
            name = creator["name"]
            uid = creator["uid"]

            print(f"  [Bilibili] '{name}' (uid={uid})")

            # Step 1: Get fresh cookies from space page
            self._ensure_cookies(uid)
            time.sleep(2)  # Critical: delay between cookie fetch and API call

            # Step 2: Attempt to fetch videos
            data = self._fetch_videos(uid)

            if not data:
                print(f"  [Bilibili] '{name}': skipped (fetch failed)")
                continue

            vlist = data.get("data", {}).get("list", {}).get("vlist", [])
            if not vlist:
                print(f"  [Bilibili] '{name}': No videos found")
                continue

            for v in vlist:
                aid = v.get("aid")
                published = None
                ts = v.get("created")
                if ts:
                    published = datetime.fromtimestamp(ts, tz=timezone.utc)

                items.append(CollectedItem(
                    source="bilibili",
                    source_name=name,
                    item_id=f"bili:{uid}:{aid}",
                    title=v.get("title", "(no title)"),
                    url=f"https://www.bilibili.com/video/av{aid}",
                    published=published,
                    description=v.get("description", ""),
                    extra={"uid": uid, "aid": aid},
                ))

            print(f"  [Bilibili] '{name}': {len(vlist)} videos found")

            # Step 3: Delay between creators to avoid rate limiting
            if creator != self.creators[-1]:
                time.sleep(3)

        return items
