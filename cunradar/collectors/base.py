"""Base collector interface."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CollectedItem:
    """A single piece of content collected from any source."""

    source: str               # e.g. "youtube", "bilibili", "rss", "github"
    source_name: str          # human-readable name of the channel/feed/repo
    item_id: str              # unique ID for deduplication
    title: str                # content title
    url: str                  # link to the content
    published: datetime | None = None  # publication time
    description: str = ""     # short summary / excerpt
    extra: dict = field(default_factory=dict)  # source-specific extra data


class BaseCollector:
    """Base class for all collectors."""

    def collect(self) -> list[CollectedItem]:
        """Fetch new content from the source.

        Returns:
            A list of ``CollectedItem`` objects discovered.
        """
        raise NotImplementedError
