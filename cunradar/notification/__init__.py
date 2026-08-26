"""多通道通知：飞书(Feishu) / 企业微信(WeCom) / 钉钉(DingTalk)。

统一入口 ``send_digest(notification_cfg, ...)`` 会遍历配置里所有通道，
把每日摘要推送到「已填写 webhook_url」的通道；未配置的通道自动跳过。
这样以后想加企业微信 / 钉钉，只需在 config.yaml 或 Secrets 里填对应
webhook 即可，无需改代码。
"""

import base64
import hashlib
import hmac
import time
import urllib.parse

import requests

from ..collectors.base import CollectedItem

# 飞书 post 富文本的安全上限（字符数），超出则截断
MAX_FEISHU_CHARS = 15000
# 企业微信 / 钉钉 markdown 较宽松，这里限制每个来源最多展示条数，避免超长
MAX_ITEMS_PER_SOURCE = 8

_SOURCE_LABELS = {
    "youtube": "\U0001F3AC YouTube",
    "bilibili": "\U0001F4FA B站",
    "rss": "\U0001F4DD 博客/RSS",
    "github": "\U0001F4BB GitHub",
    "github_trending": "\U0001F525 GitHub Trending",
}


def _group_items(items: list[CollectedItem]) -> dict:
    grouped: dict[str, list[CollectedItem]] = {}
    for item in items:
        grouped.setdefault(item.source, []).append(item)
    return grouped


# ─────────────────────────────── 飞书 ────────────────────────────────
def _build_feishu_signature(secret: str) -> tuple[str, str]:
    """飞书自定义机器人签名（timestamp + sign）。"""
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = base64.b64encode(hmac_code).decode("utf-8")
    return timestamp, sign


def _build_feishu_payload(
    date_str: str,
    items: list[CollectedItem],
    digest: str,
    html_url: str | None,
    configured_sources: list[str] | None,
) -> dict:
    grouped = _group_items(items)
    # post 内容：每行是「行内元素」列表
    content_lines: list[list[dict]] = []

    if digest:
        content_lines.append([{"tag": "text", "text": "── 今日技术动态 ──"}])
        for line in digest.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            content_lines.append([{"tag": "text", "text": line[:500]}])

    render_keys = configured_sources or list(grouped.keys())
    for source in render_keys:
        label = _SOURCE_LABELS.get(source, source)
        src_items = grouped.get(source)
        if not src_items:
            content_lines.append([{"tag": "text", "text": f"{label}：无新内容"}])
            continue
        content_lines.append([{"tag": "text", "text": f"{label}（{len(src_items)}）"}])
        for it in src_items[:MAX_ITEMS_PER_SOURCE]:
            content_lines.append(
                [{"tag": "a", "text": (it.title or "")[:120], "href": it.url or "#"}]
            )

    if html_url:
        content_lines.append([{"tag": "text", "text": "\U0001F310 完整日报"}])
        content_lines.append([{"tag": "a", "text": html_url, "href": html_url}])

    if not content_lines:
        content_lines = [[{"tag": "text", "text": "今日无新内容"}]]

    # 超长截断（从末尾丢行）
    def _line_len(line: list[dict]) -> int:
        return sum(len(e.get("text", "")) for e in line)

    total = sum(_line_len(ln) for ln in content_lines)
    if total > MAX_FEISHU_CHARS:
        trimmed: list[list[dict]] = []
        used = 0
        for ln in content_lines:
            if used + _line_len(ln) > MAX_FEISHU_CHARS and trimmed:
                break
            trimmed.append(ln)
            used += _line_len(ln)
        content_lines = trimmed
        content_lines.append([{"tag": "text", "text": "（内容过长已截断，请查看完整日报）"}])

    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"\U0001F4E1 CunRadar 每日资讯雷达 — {date_str}",
                    "content": content_lines,
                }
            }
        },
    }


def send_feishu(
    webhook_url: str,
    secret: str | None,
    date_str: str,
    items: list[CollectedItem],
    digest: str,
    html_url: str | None,
    configured_sources: list[str] | None,
) -> bool:
    payload = _build_feishu_payload(date_str, items, digest, html_url, configured_sources)
    if secret:
        ts, sign = _build_feishu_signature(secret)
        payload["timestamp"] = ts
        payload["sign"] = sign
    try:
        resp = requests.post(webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code", 0) != 0:
            print(f"  [Feishu] API 返回错误: {data}")
            return False
        print(f"  [Feishu] 推送成功（{len(payload['content']['post']['zh_cn']['content'])} 行）")
        return True
    except Exception as e:
        print(f"  [Feishu] 推送失败: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"  [Feishu] 响应: {e.response.text[:500]}")
        return False


# ─────────────── 通用 Markdown（企业微信 / 钉钉 共用） ───────────────
def _build_markdown(
    date_str: str,
    items: list[CollectedItem],
    digest: str,
    html_url: str | None,
    configured_sources: list[str] | None,
) -> str:
    """生成企业微信 / 钉钉都兼容的 markdown 文本。

    两家的 markdown 均支持 # 标题、**加粗**、[文字](链接)、> 引用、换行。
    """
    grouped = _group_items(items)
    parts: list[str] = [f"# \U0001F4E1 CunRadar 每日资讯雷达 — {date_str}", ""]

    if digest:
        parts.append("**── 今日技术动态 ──**")
        parts.append(digest.strip())
        parts.append("")

    render_keys = configured_sources or list(grouped.keys())
    for source in render_keys:
        label = _SOURCE_LABELS.get(source, source)
        src_items = grouped.get(source)
        if not src_items:
            parts.append(f"- {label}：无新内容")
            continue
        parts.append(f"**{label}（{len(src_items)}）**")
        for it in src_items[:MAX_ITEMS_PER_SOURCE]:
            title = (it.title or "").replace("|", "/").replace("\n", " ")[:120]
            url = it.url or "#"
            parts.append(f"- [{title}]({url})")

    if html_url:
        parts.append("")
        parts.append(f"\U0001F310 [完整日报]({html_url})")

    if not (digest or items):
        parts.append("")
        parts.append("今日无新内容")

    return "\n".join(parts)


# ─────────────────────────────── 企业微信 ───────────────────────────────
def send_wecom(
    webhook_url: str,
    date_str: str,
    items: list[CollectedItem],
    digest: str,
    html_url: str | None,
    configured_sources: list[str] | None,
) -> bool:
    text = _build_markdown(date_str, items, digest, html_url, configured_sources)
    payload = {"msgtype": "markdown", "markdown": {"content": text}}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # 企业微信返回 {"errcode":0,"errmsg":"ok"}
        if data.get("errcode", 0) != 0:
            print(f"  [WeCom] API 返回错误: {data}")
            return False
        print("  [WeCom] 推送成功")
        return True
    except Exception as e:
        print(f"  [WeCom] 推送失败: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"  [WeCom] 响应: {e.response.text[:500]}")
        return False


# ─────────────────────────────── 钉钉 ───────────────────────────────
def _build_dingtalk_sign(secret: str) -> tuple[str, str]:
    """钉钉自定义机器人加签：timestamp(ms) + sign（需 URL encode）。"""
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = base64.b64encode(hmac_code).decode("utf-8")
    sign = urllib.parse.quote_plus(sign)
    return timestamp, sign


def send_dingtalk(
    webhook_url: str,
    secret: str | None,
    date_str: str,
    items: list[CollectedItem],
    digest: str,
    html_url: str | None,
    configured_sources: list[str] | None,
) -> bool:
    text = _build_markdown(date_str, items, digest, html_url, configured_sources)
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"\U0001F4E1 CunRadar 每日资讯雷达 — {date_str}",
            "text": text,
        },
    }
    url = webhook_url
    if secret:
        ts, sign = _build_dingtalk_sign(secret)
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}timestamp={ts}&sign={sign}"
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # 钉钉返回 {"errcode":0,"errmsg":"ok"}
        if data.get("errcode", 0) != 0:
            print(f"  [DingTalk] API 返回错误: {data}")
            return False
        print("  [DingTalk] 推送成功")
        return True
    except Exception as e:
        print(f"  [DingTalk] 推送失败: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"  [DingTalk] 响应: {e.response.text[:500]}")
        return False


# ───────────────────────────── 统一入口 ─────────────────────────────
def send_digest(
    notification_cfg: dict,
    date_str: str,
    items: list[CollectedItem],
    digest: str,
    html_url: str | None = None,
    configured_sources: list[str] | None = None,
) -> bool:
    """按配置把摘要推送到所有已启用的通道。

    Args:
        notification_cfg: config.yaml 里的 ``notification`` 段。
            形如 {"feishu": {...}, "wecom": {...}, "dingtalk": {...}}，
            只有含 ``webhook_url`` 的通道才会推送。
        ...
    Returns:
        ``True`` 表示至少有一个通道推送成功（或至少配置了一个通道）。
        若没有任何通道配置 webhook_url，返回 False（视为跳过）。
    """
    any_configured = False
    any_ok = False

    fs = notification_cfg.get("feishu") or {}
    if fs.get("webhook_url"):
        any_configured = True
        print("  [Feishu] 推送中...")
        if send_feishu(
            fs["webhook_url"], fs.get("secret") or None,
            date_str, items, digest, html_url, configured_sources,
        ):
            any_ok = True

    wx = notification_cfg.get("wecom") or {}
    if wx.get("webhook_url"):
        any_configured = True
        print("  [WeCom] 推送中...")
        if send_wecom(
            wx["webhook_url"], date_str, items, digest, html_url, configured_sources
        ):
            any_ok = True

    dt = notification_cfg.get("dingtalk") or {}
    if dt.get("webhook_url"):
        any_configured = True
        print("  [DingTalk] 推送中...")
        if send_dingtalk(
            dt["webhook_url"], dt.get("secret") or None,
            date_str, items, digest, html_url, configured_sources,
        ):
            any_ok = True

    if not any_configured:
        print("  [Notify] 未配置任何通道的 webhook_url，跳过推送")

    return any_configured and any_ok
