"""AI daily digest generator — OpenAI-compatible, multi-provider.

Built-in presets (all OpenAI-compatible chat-completions endpoints):
  - deepseek : DeepSeek V4-Flash（付费；2026-07-24 起旧名 deepseek-chat/reasoner 已停用，统一为 deepseek-v4-flash，思考模式用 thinking 参数开启）
  - zhipu    : 智谱 GLM-4.7-Flash（免费）
  - hunyuan  : 腾讯混元 Lite（免费；更好的免费档 hunyuan-turbos-latest）
  - qwen     : 通义千问 Qwen3.7 Flash（便宜；若报错改用 qwen3.6-flash / qwen-turbo）

选择供应商：config.ai.provider 或环境变量 AI_PROVIDER
覆盖 key/base/model：环境变量 AI_API_KEY / AI_BASE_URL / AI_MODEL（优先级最高）
"""

import os
from datetime import datetime, timezone

import requests

from ..collectors.base import CollectedItem


# 内置供应商预设。
# 注意：api_base 已包含版本前缀，代码统一在其后拼接 /chat/completions，
# 各家前缀不同（DeepSeek /v1、智谱 /v4、混元 /v1、Qwen /v1），因此分别写全。
PROVIDER_PRESETS = {
    "deepseek": {
        "api_base": "https://api.deepseek.com/v1",
        "model": "deepseek-v4-flash",
        "thinking": "enabled",
        "note": "DeepSeek V4-Flash（2026-07-24 起 deepseek-chat/reasoner 已停用，统一映射到此模型；思考模式需显式开启）",
    },
    "zhipu": {
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4.7-flash",
        "note": "智谱 GLM-4.7-Flash，免费",
    },
    "hunyuan": {
        "api_base": "https://api.hunyuan.cloud.tencent.com/v1",
        "model": "hunyuan-lite",
        "note": "腾讯混元 Lite，免费（更好的免费档：hunyuan-turbos-latest）",
    },
    "qwen": {
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3.7-flash",
        "note": "通义千问 Qwen3.7 Flash，便宜（若报错改用 qwen3.6-flash / qwen-turbo）",
    },
}


AI_SYSTEM_PROMPT = """You are CunRadar's AI digest writer. Your job is to take today's
collection of updates from various sources and produce a concise,
well-organized daily digest in Chinese.

Rules:
1. Group related items by topic when possible.
2. Keep each item description to 1-2 sentences.
3. Focus on WHAT changed and WHY it matters.
4. If an item is from GitHub, note the repo name.
5. If an item is a video, note the creator name.
6. Output in MARKDOWN format with clear section headers.
7. Be factual and concise - no fluff or marketing language.
8. Total output should be 200-500 characters.
9. If there are very few updates (0-3 items), still write a short digest."""


def build_user_prompt(items: list[CollectedItem], date_str: str) -> str:
    """Build the user prompt from collected items."""
    lines = [f"Today's date: {date_str}", "", "Updates collected today:"]
    for i, item in enumerate(items, 1):
        source_tag = item.source.upper()
        published = item.published.strftime("%H:%M UTC") if item.published else "unknown time"
        lines.append(f"{i}. [{source_tag}] {item.title}")
        lines.append(f"   From: {item.source_name} | {published}")
        if item.description:
            desc = item.description[:200].replace("\n", " ")
            lines.append(f"   {desc}")
        lines.append("")
    return "\n".join(lines)


def resolve_ai_config(config: dict | None) -> dict:
    """Resolve which provider / key / base / model to use.

    Priority: environment variables > config.ai.* > provider preset.
    """
    ai_cfg = (config or {}).get("ai", {})
    provider = os.environ.get("AI_PROVIDER") or ai_cfg.get("provider", "deepseek")
    preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["deepseek"])
    api_key = (
        ai_cfg.get("api_key")
        or os.environ.get("AI_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY", "")
    )
    api_base = (
        os.environ.get("AI_BASE_URL")
        or ai_cfg.get("api_base")
        or preset["api_base"]
    )
    model = os.environ.get("AI_MODEL") or ai_cfg.get("model") or preset["model"]
    # thinking 模式：仅 DeepSeek V4 系列支持；默认开启（对应原 deepseek-reasoner 的思考模式）
    thinking = (
        os.environ.get("AI_THINKING")        # 取值 enabled / disabled
        or ai_cfg.get("thinking")
        or preset.get("thinking", "")
    )
    return {
        "provider": provider,
        "api_key": api_key,
        "api_base": api_base,
        "model": model,
        "thinking": thinking,
        "timeout": ai_cfg.get("timeout", 120),
    }


def generate_digest(
    items: list[CollectedItem],
    date_str: str,
    config: dict | None = None,
    timeout: int = 120,
) -> str:
    """Generate an AI-powered daily digest.

    Returns:
        The markdown digest text. Returns empty string on failure / no key.
    """
    if not items:
        return "今日无新内容。"

    cfg = resolve_ai_config(config)
    api_key = cfg["api_key"]
    if not api_key:
        print("  [AI Digest] Skipped: no API key (set AI_API_KEY / DEEPSEEK_API_KEY)")
        return ""

    print(f"  [AI Digest] Provider={cfg['provider']} Model={cfg['model']}")

    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(items, date_str)},
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    # DeepSeek V4 思考模式：仅在 provider 为 deepseek 且配置了 thinking 时附加
    # （官方格式：{"type": "enabled"}，对应原 deepseek-reasoner 的推理模式）
    if cfg.get("thinking") and cfg["provider"] == "deepseek":
        payload["thinking"] = {"type": cfg["thinking"]}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"{cfg['api_base'].rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        result = resp.json()
        content = result["choices"][0]["message"]["content"]
        print(f"  [AI Digest] Generated successfully ({len(content)} chars)")
        return content
    except Exception as e:
        print(f"  [AI Digest] Failed: {e}")
        return ""
