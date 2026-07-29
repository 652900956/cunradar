"""Bilibili UP主视频采集器。

使用 B站官方 API 获取 UP 主视频更新：
  https://api.bilibili.com/x/space/arc/search?mid={uid}

需要添加 Referer / User-Agent 等请求头以绕过风控。
"""

from datetime import datetime, timezone

import requests

from .base import BaseCollector, CollectedItem


class BilibiliCollector(BaseCollector):
    """Collect latest videos from a list of Bilibili creators via official API."""

    API_BASE = "https://api.bilibili.com/x/space/arc/search"

    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://space.bilibili.com/",
        "Origin": "https://space.bilibili.com",
        "Accept": "application/json, text/plain, */*",
    }

    def __init__(self, creators: list[dict]) -> None:
        self.creators = creators

    def collect(self) -> list[CollectedItem]:
        items: list[CollectedItem] = []
        for creator in self.creators:
            name = creator["name"]
            uid = creator["uid"]

            try:
                resp = requests.get(
                    self.API_BASE,
                    params={"mid": uid, "ps": 10, "pn": 1},
                    headers={**self._HEADERS, "Referer": f"https://space.bilibili.com/{uid}"},
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"  [Bilibili] Failed to fetch '{name}': {e}")
                continue

            if data.get("code") != 0:
                print(f"  [Bilibili] API error for '{name}': code={data.get('code')}, msg={data.get('message', '')}")
                continue

            vlist = data.get("data", {}).get("list", {}).get("vlist", [])
            if not vlist:
                print(f"  [Bilibili] No video list for '{name}'")
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

        return items
