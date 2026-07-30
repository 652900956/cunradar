"""Bilibili UP主视频采集器。

使用 B站搜索 API + curl_cffi 模拟浏览器TLS指纹获取视频更新。

curl_cffi 会模拟 Chrome 浏览器的 TLS 握手特征，
绕过 B站 WAF 对 Python requests 库的拦截。
"""

import re
import time
from datetime import datetime, timezone

from curl_cffi import requests as curl_requests

from .base import BaseCollector, CollectedItem


class BilibiliCollector(BaseCollector):
    """Collect latest videos from a list of Bilibili creators via search API."""

    SEARCH_API = "https://api.bilibili.com/x/web-interface/search/type"

    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    _TAG_RE = re.compile(r"<[^>]+>")

    def __init__(self, creators: list[dict]) -> None:
        self.creators = creators
        self._session = curl_requests.Session()

    @staticmethod
    def _clean_title(title: str) -> str:
        """Remove HTML tags (e.g. <em class=\"keyword\">) from title."""
        return BilibiliCollector._TAG_RE.sub("", title)

    def _search_videos(self, name: str, uid: int | str) -> list[dict]:
        """Search videos by UP主 name, then filter by UID for precision."""
        params = {
            "search_type": "video",
            "keyword": name,
            "page": 1,
            "order": "pubdate",
        }
        try:
            resp = self._session.get(
                self.SEARCH_API,
                params=params,
                headers={
                    **self._HEADERS,
                    "Referer": "https://search.bilibili.com/",
                },
                impersonate="chrome120",
                timeout=15,
            )
            data = resp.json()
        except Exception as e:
            print(f"  [Bilibili] Search request failed for '{name}': {e}")
            return []

        if data.get("code") != 0:
            print(f"  [Bilibili] Search API error for '{name}': code={data.get('code')}, msg={data.get('message', '')}")
            return []

        results = data.get("data", {}).get("result", [])
        if not results:
            print(f"  [Bilibili] No search results for '{name}'")
            return []

        # Filter by UID to ensure only this creator's videos
        uid_str = str(uid)
        filtered = [v for v in results if str(v.get("mid", "")) == uid_str]

        if not filtered:
            print(f"  [Bilibili] '{name}': found {len(results)} results, but none matched uid={uid}")
            for v in results[:3]:
                print(f"    - author={v.get('author','?')}, mid={v.get('mid','?')}")
        else:
            print(f"  [Bilibili] '{name}': {len(filtered)} videos found via search")

        return filtered

    def collect(self) -> list[CollectedItem]:
        items: list[CollectedItem] = []

        for creator in self.creators:
            name = creator.get("name", "")
            uid = creator.get("uid", "")

            if not name or not uid:
                continue

            print(f"  [Bilibili] '{name}' (uid={uid})")

            videos = self._search_videos(name, uid)

            for v in videos:
                aid = v.get("aid")
                published = None
                ts = v.get("pubdate")
                if ts:
                    published = datetime.fromtimestamp(int(ts), tz=timezone.utc)

                items.append(CollectedItem(
                    source="bilibili",
                    source_name=name,
                    item_id=f"bili:{uid}:{aid}",
                    title=self._clean_title(v.get("title", "")),
                    url=f"https://www.bilibili.com/video/av{aid}",
                    published=published,
                    description=v.get("description", ""),
                    extra={"uid": uid, "aid": aid},
                ))

            if videos:
                print(f"  [Bilibili] '{name}': {len(videos)} videos collected")

            # Small delay between creators
            if creator != self.creators[-1]:
                time.sleep(2)

        return items
