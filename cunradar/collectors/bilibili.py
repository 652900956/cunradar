"""Bilibili UP主视频采集器。

使用 B站官方 RSS 接口获取 UP 主视频更新：
  https://rss.bilibili.com/space/{uid}
"""

from datetime import datetime, timezone

import feedparser

from .base import BaseCollector, CollectedItem


class BilibiliCollector(BaseCollector):
    """Collect latest videos from a list of Bilibili creators via official RSS."""

    RSS_BASE = "https://rss.bilibili.com/space"

    def __init__(self, creators: list[dict]) -> None:
        self.creators = creators

    def collect(self) -> list[CollectedItem]:
        items: list[CollectedItem] = []
        for creator in self.creators:
            name = creator["name"]
            uid = creator["uid"]
            feed_url = f"{self.RSS_BASE}/{uid}"

            try:
                feed = feedparser.parse(feed_url)
            except Exception as e:
                print(f"  [Bilibili] Failed to fetch '{name}': {e}")
                continue

            if feed.bozo and not feed.entries:
                print(f"  [Bilibili] No entries for '{name}' (bad feed)")
                continue

            for entry in feed.entries:
                entry_id = entry.get("id") or entry.get("link", "")
                published = None
                if "published_parsed" in entry and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                items.append(CollectedItem(
                    source="bilibili",
                    source_name=name,
                    item_id=f"bili:{uid}:{entry_id}",
                    title=entry.get("title", "(no title)"),
                    url=entry.get("link", entry_id),
                    published=published,
                    description=entry.get("summary", ""),
                    extra={"uid": uid},
                ))

            print(f"  [Bilibili] '{name}': {len(feed.entries)} videos found")

        return items
