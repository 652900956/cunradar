"""Configuration loader for CunRadar.

Loads config.yaml, resolves ${ENV_VAR} references,
and provides typed access to all settings.
"""

import os
import re
from pathlib import Path

import yaml

_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def _resolve_env(value: str) -> str:
    """Replace ${VAR} references with environment variable values."""
    def _replace(m: re.Match) -> str:
        var_name = m.group(1)
        val = os.environ.get(var_name)
        if val is None:
            print(f"  [Config] Warning: environment variable '{var_name}' is not set. Leaving empty.")
            return ""
        return val
    return _ENV_VAR_PATTERN.sub(_replace, value)


def _resolve_dict(d: dict) -> dict:
    """Recursively resolve environment variables in a dict."""
    for k, v in d.items():
        if isinstance(v, str):
            d[k] = _resolve_env(v)
        elif isinstance(v, dict):
            d[k] = _resolve_dict(v)
        elif isinstance(v, list):
            d[k] = [_resolve_env(item) if isinstance(item, str) else item for item in v]
    return d


def _load_dotenv(root: Path) -> None:
    """Load .env file from project root into environment variables.

    Simple key=value parser; does not support export, quoting, or
    multiline values.
    """
    dotenv_path = root / ".env"
    if not dotenv_path.exists():
        return
    with open(dotenv_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            # Only set if not already present
            if key and key not in os.environ:
                os.environ[key] = val


def load_config(path: str | None = None) -> dict:
    """Load and resolve the configuration file.

    Args:
        path: Path to config.yaml. Defaults to ``config/config.yaml``
              relative to the project root.

    Returns:
        A flat dictionary with all env vars resolved.
    """
    if path is None:
        # Walk up to find project root (where pyproject.toml lives)
        root = Path(__file__).resolve().parent.parent
        path = str(root / "config" / "config.yaml")

    # Auto-load .env from project root
    _load_dotenv(Path(path).resolve().parent.parent)

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return _resolve_dict(raw)
