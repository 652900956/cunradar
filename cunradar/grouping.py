"""按「来源 → 发帖人(博主) → 内容」三级分组。

把所有采集到的 CollectedItem 组织成：
    dict[source] -> dict[source_name] -> list[CollectedItem]

- 外层 key 是来源类型（youtube / bilibili / rss / github / github_trending）
- 内层 key 是具体发帖人 / 博主 / 频道 / 仓库名（item.source_name）
- 顺序保持「先来源、后博主」的插入顺序：来源按收集/配置顺序，
  同一来源内的博主按内容出现顺序（即配置顺序）。
"""

from collections import OrderedDict

from .collectors.base import CollectedItem


def group_by_uploader(items: list[CollectedItem]) -> "OrderedDict[str, OrderedDict[str, list[CollectedItem]]]":
    """把 items 按 来源 → 博主 嵌套分组，保持插入顺序。"""
    grouped: "OrderedDict[str, OrderedDict[str, list[CollectedItem]]]" = OrderedDict()
    for item in items:
        by_author = grouped.setdefault(item.source, OrderedDict())
        by_author.setdefault(item.source_name, []).append(item)
    return grouped


def count_items(grouped: "OrderedDict[str, OrderedDict[str, list[CollectedItem]]]") -> int:
    """统计分组后的总条目数。"""
    return sum(len(items) for by_author in grouped.values() for items in by_author.values())
