"""JSONL history read/write with append-only patch merging."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

SHELLGUARD_DIR = Path.home() / ".shellguard"
HISTORY_PATH = SHELLGUARD_DIR / "history.jsonl"
CACHE_PATH = SHELLGUARD_DIR / "cache.json"


def _ensure_dir() -> None:
    SHELLGUARD_DIR.mkdir(parents=True, exist_ok=True)


def read_history_merged(limit: int = 50) -> List[Dict[str, Any]]:
    """Read history.jsonl, apply patch records, sort by ts, return last `limit` records."""
    _ensure_dir()
    if not HISTORY_PATH.exists():
        return []

    raw_records: List[Dict[str, Any]] = []
    patches: Dict[str, Dict[str, Any]] = {}  # ts -> patch data

    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("_type") == "patch":
                ts = obj.get("ts")
                if ts:
                    # Merge patch data (later patches overwrite earlier)
                    if ts not in patches:
                        patches[ts] = {}
                    patches[ts].update({k: v for k, v in obj.items() if k not in ("_type", "ts")})
            else:
                raw_records.append(obj)

    # Deduplicate by ts (keep last occurrence)
    seen: Dict[str, Dict[str, Any]] = {}
    for rec in raw_records:
        ts = rec.get("ts", "")
        seen[ts] = rec

    # Apply patches
    for ts, patch in patches.items():
        if ts in seen:
            seen[ts].update(patch)

    # Sort by ts descending, return last `limit`
    sorted_records = sorted(seen.values(), key=lambda r: r.get("ts", ""))
    return sorted_records[-limit:]


def update_risk_in_history(ts: str, risk: str, label: str) -> None:
    """Append a patch record to history.jsonl to update risk info without rewriting."""
    _ensure_dir()
    patch = {"_type": "patch", "ts": ts, "risk": risk, "risk_label": label}
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(patch, ensure_ascii=False) + "\n")


def load_cache() -> Dict[str, Any]:
    """Load LLM analysis cache from ~/.shellguard/cache.json."""
    _ensure_dir()
    if not CACHE_PATH.exists():
        return {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache: Dict[str, Any]) -> None:
    """Save LLM analysis cache to ~/.shellguard/cache.json."""
    _ensure_dir()
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
