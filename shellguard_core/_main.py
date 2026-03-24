#!/usr/bin/env python3
"""ShellGuard CLI entry point — called by the 'shellguard' shell wrapper."""
from __future__ import annotations

import sys
import os

# Allow running from ~/.shellguard/lib (installed) or from repo root
_HERE = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))  # shellguard_core/../
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Also accept repo-root invocation (python shellguard_core/_main.py from shellguard/)
_REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
_REPO2 = os.path.join(_REPO, "..")
for _p in (_REPO, os.path.normpath(_REPO2)):
    if os.path.isdir(os.path.join(_p, "shellguard_core")) and _p not in sys.path:
        sys.path.insert(0, _p)


def main() -> None:
    from shellguard_core.config import load_config
    from shellguard_core.history import load_cache, save_cache, SHELLGUARD_DIR

    args = sys.argv[1:]

    # --- shellguard clear ---
    if args and args[0] == "clear":
        cache_path = SHELLGUARD_DIR / "cache.json"
        if cache_path.exists():
            cache_path.unlink()
            print("Cache cleared.")
        else:
            print("No cache to clear.")
        return

    # --- shellguard analyze ---
    if args and args[0] == "analyze":
        from shellguard_core.history import read_history_merged
        from shellguard_core.analyzer import ensure_risk_labels

        cfg = load_config()
        if not cfg.api_key:
            print("Error: No API key configured. Run: bash install.sh", file=sys.stderr)
            sys.exit(1)

        records = read_history_merged(cfg.max_history_display)
        if not records:
            print("No command history found.")
            return

        # Force re-analysis by clearing risk fields and cache
        for rec in records:
            rec.pop("risk", None)
            rec.pop("risk_label", None)
        save_cache({})

        def progress(current: int, total: int, cmd: str) -> None:
            truncated = cmd[:50] + "…" if len(cmd) > 50 else cmd
            print(f"[{current}/{total}] {truncated}", flush=True)

        ensure_risk_labels(records, cfg, on_progress=progress)
        print(f"\nAnalysis complete. {len(records)} commands processed.")
        return

    # --- shellguard ask "question" ---
    if args and args[0] == "ask":
        question = " ".join(args[1:]).strip()
        if not question:
            print('Usage: shellguard ask "your question"', file=sys.stderr)
            sys.exit(1)
        try:
            from shellguard_core.tui import run_ask
        except ImportError as e:
            print(f"Error: Missing dependency — {e}", file=sys.stderr)
            sys.exit(1)
        cfg = load_config()
        run_ask(cfg, question)
        return

    # --- shellguard (default: TUI) ---
    try:
        from shellguard_core.tui import run_tui
    except ImportError as e:
        print(f"Error: Missing dependency — {e}", file=sys.stderr)
        print("Try: bash install.sh  to reinstall dependencies.", file=sys.stderr)
        sys.exit(1)

    cfg = load_config()
    run_tui(cfg)


if __name__ == "__main__":
    main()
