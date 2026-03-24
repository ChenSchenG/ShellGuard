"""Configuration loading and saving for ShellGuard."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

SHELLGUARD_DIR = Path.home() / ".shellguard"
CONFIG_PATH = SHELLGUARD_DIR / "config.json"


@dataclass
class Config:
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    max_history_display: int = 50
    risk_cache_ttl_seconds: int = 3600
    auto_analyze: bool = False


def load_config() -> Config:
    """Load config from ~/.shellguard/config.json, returning defaults if missing."""
    if not CONFIG_PATH.exists():
        return Config()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Only set known fields to avoid errors on unknown keys
        known = {k: v for k, v in data.items() if k in Config.__dataclass_fields__}
        return Config(**known)
    except Exception:
        return Config()


def save_config(cfg: Config) -> None:
    """Save config to ~/.shellguard/config.json."""
    SHELLGUARD_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, indent=2, ensure_ascii=False)
