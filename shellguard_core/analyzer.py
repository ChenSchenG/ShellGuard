"""Cache-aware risk labeling for shell commands."""
from __future__ import annotations

import hashlib
import time
from typing import Any, Callable, Dict, List, Optional

from .config import Config
from .history import load_cache, save_cache, update_risk_in_history
from .llm import analyze_command_risk


def _cmd_hash(cmd: str) -> str:
    """Return first 16 hex chars of sha256(cmd) as cache key."""
    return hashlib.sha256(cmd.encode("utf-8")).hexdigest()[:16]


def ensure_risk_labels(
    records: List[Dict[str, Any]],
    cfg: Config,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> List[Dict[str, Any]]:
    """
    For each record without a risk label (or with expired cache), call LLM to analyze.
    Updates records in-place and persists patches to history.jsonl + cache.json.

    on_progress(current, total, cmd) is called before each LLM call.
    """
    cache = load_cache()
    now = time.time()
    ttl = cfg.risk_cache_ttl_seconds

    # Identify which records need analysis
    to_analyze = []
    for rec in records:
        if rec.get("risk"):
            continue  # already labeled
        key = _cmd_hash(rec.get("cmd", ""))
        entry = cache.get(key)
        if entry and (now - entry.get("ts", 0)) < ttl:
            # Cache hit — apply cached value
            rec["risk"] = entry["risk"]
            rec["risk_label"] = entry["label"]
        else:
            to_analyze.append(rec)

    total = len(to_analyze)
    cache_dirty = False

    for i, rec in enumerate(to_analyze):
        cmd = rec.get("cmd", "")
        cwd = rec.get("cwd", "")
        exit_code = rec.get("exit_code", 0)
        ts = rec.get("ts", "")

        if on_progress:
            on_progress(i + 1, total, cmd)

        result = analyze_command_risk(cfg.base_url, cfg.api_key, cfg.model, cmd, cwd, exit_code)
        risk = result["risk"]
        label = result["label"]

        # Update record in memory
        rec["risk"] = risk
        rec["risk_label"] = label

        # Persist patch to history
        if ts:
            update_risk_in_history(ts, risk, label)

        # Update cache
        key = _cmd_hash(cmd)
        cache[key] = {"risk": risk, "label": label, "ts": now}
        cache_dirty = True

    if cache_dirty:
        save_cache(cache)

    return records
