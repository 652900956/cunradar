"""Telegram bot notification — HTML parse mode, titles as clickable links."""

from ..collectors.base import CollectedItem

import requests

MAX_LEN = 4096

_SOURCE_LABELS = {
    "youtube": "🎬 YouTube",
    "bilibili": "📺 B站",
    "rss": "📝 博客/RSS",
    "github": "💻 GitHub",
    "github_trending": "🔥 GitHub Trending",
}


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send_digest(
    bot_token: str,
    chat_id: str,
    date_str: str,
    items: list[CollectedItem],
    digest: str,
    html_url: str | None = None,
    configured_sources: list[str] | None = None,
) -> bool:
    """Send the daily digest in HTML parse mode.

    Args:
        bot_token: Telegram Bot API token.
        chat_id: Target chat/channel ID.
        date_str: Date string.
        items: New items collected today.
        digest: AI-generated digest text.
        html_url: Link to the full HTML report.
        configured_sources: All source types the user has configured.
            If provided, empty sources are shown as "无新内容",
            matching the HTML report.

    Returns:
        ``True`` on success.
    """
    # Group items by source
    grouped: dict[str, list[CollectedItem]] = {}
    for item in items:
        grouped.setdefault(item.source, []).append(item)

    # ── Build HTML message ──
    parts: list[str] = [f"<b>📡 CunRadar Daily — {date_str}</b>", ""]

    # AI digest first (same order as HTML report)
    if digest:
        parts.append("<b>── 今日技术动态 ──</b>")
        parts.append("")
        import re

        for line in digest.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Escape HTML first, then convert **bold** to <b>bold</b>
            line = _esc(line)
            line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
            if line.startswith("#"):
                parts.append(f"<b>{line.lstrip('# ')}</b>")
            else:
                parts.append(line)
        parts.append("")

    # Determine which sources to render
    if configured_sources:
        render_keys = configured_sources
    else:
        render_keys = list(grouped.keys())

    for source in render_keys:
        label = _SOURCE_LABELS.get(source, source)
        src_items = grouped.get(source)
        if not src_items:
            parts.append(f"<b>{label}</b>")
            parts.append("  无新内容")
            parts.append("")
            continue

        parts.append(f"<b>{label} ({len(src_items)})</b>")
        for it in src_items:
            title = _esc(it.title[:120])
            url = it.url
            parts.append(f"  • <a href='{url}'>{title}</a>")
        parts.append("")

    # Link to full report
    if html_url:
        parts.append(f'🌐 <a href="{html_url}">完整日报</a>')

    text = "\n".join(parts)

    # ── Trim to 4096 ──
    if len(text) > MAX_LEN:
        text = _trim_html(text, render_keys, grouped, digest, html_url, date_str)

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        print(f"  [Telegram] Digest sent successfully ({len(text)} chars)")
        return True
    except Exception as e:
        print(f"  [Telegram] Failed to send: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"  [Telegram] Response: {e.response.text[:500]}")
        return False


def _trim_html(
    text: str,
    render_keys: list[str],
    grouped: dict[str, list[CollectedItem]],
    digest: str,
    html_url: str | None,
    date_str: str,
) -> str:
    """Trim HTML message to 4096 chars by dropping items from the last section."""
    header = f"<b>📡 CunRadar Daily — {date_str}</b>\n"
    result = header

    # Digest first (same order as HTML report and main flow)
    if digest:
        remaining = MAX_LEN - len(result) - 50
        d = digest.strip()[:remaining]
        result += f"<b>── 今日技术动态 ──</b>\n\n{_esc(d)}\n"

    for source in render_keys:
        label = _SOURCE_LABELS.get(source, source)
        src_items = grouped.get(source)

        if not src_items:
            sec = f"<b>{label}</b>\n  无新内容\n\n"
            candidate = result + sec
            if len(candidate) > MAX_LEN - 200:
                break
            result += sec
            continue

        sec = f"<b>{label} ({len(src_items)})</b>\n"
        for it in src_items:
            line = f"  • <a href='{it.url}'>{_esc(it.title[:120])}</a>\n"
            candidate = result + sec + line
            if len(candidate) > MAX_LEN - 200:
                break
            sec += line
        if len(result + sec) > MAX_LEN - 200:
            break
        result += sec + "\n"

    if html_url:
        link = f"\n🌐 <a href='{html_url}'>完整日报</a>"
        if len(result) + len(link) <= MAX_LEN:
            result += link

    return result[:MAX_LEN]
