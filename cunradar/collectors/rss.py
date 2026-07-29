"""Generic RSS/Atom/JSON Feed collector."""

from datetime import datetime, timezone

import feedparser

from .base import BaseCollector, CollectedItem


class RSSCollector(BaseCollector):
    """Collect articles from a list of RSS/Atom/JSON feeds."""

    def __init__(self, feeds: list[dict]) -> None:
        self.feeds = feeds

    def collect(self) -> list[CollectedItem]:
        items: list[CollectedItem] = []
        for feed_cfg in self.feeds:
            name = feed_cfg["name"]
            url = feed_cfg["url"]

            try:
                parsed = feedparser.parse(url)
            except Exception as e:
                print(f"  [RSS] Failed to fetch '{name}': {e}")
                continue

            if parsed.bozo and not parsed.entries:
                print(f"  [RSS] No entries for '{name}' (bad feed)")
                continue

            for entry in parsed.entries:
                entry_id = entry.get("id") or entry.get("link", "")
                published = None
                if "published_parsed" in entry and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                # Prefer the feed title, fall back to link digest
                items.append(CollectedItem(
                    source="rss",
                    source_name=name,
                    item_id=f"rss:{entry_id}",
                    title=entry.get("title", "(no title)"),
                    url=entry.get("link", entry_id),
                    published=published,
                    description=entry.get("summary", ""),
                    extra={},
                ))

            print(f"  [RSS] '{name}': {len(parsed.entries)} articles found")

        return items
