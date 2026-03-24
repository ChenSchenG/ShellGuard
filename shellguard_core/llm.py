"""LLM API calls via stdlib urllib — OpenAI-compatible interface."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


def chat_completion(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    timeout: int = 30,
) -> str:
    """Send a chat completion request and return the assistant message content."""
    url = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps(
        {"model": model, "messages": messages, "temperature": 0.2}
    ).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except Exception as e:
        raise RuntimeError(str(e)) from e


def _parse_json_robust(text: str) -> Dict[str, Any]:
    """Parse JSON from LLM output, handling markdown code fences."""
    # Strip markdown fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
    # Try to find first {...} block
    match = re.search(r"\{[^{}]+\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}


RISK_PROMPT = """\
You are a shell command security analyst. Analyze the given shell command and return a JSON object.

Risk levels:
- LOW: read-only / listing operations (ls, cat, echo, pwd, git status, etc.)
- MED: file write / modify operations (cp, mv, mkdir, pip install, etc.)
- HIGH: privilege escalation / destructive operations (sudo, chmod 777, rm -rf, kill, etc.)
- CRIT: remote code execution / credential exposure (curl | bash, wget | sh, eval with remote input, exposed secrets, etc.)

Respond ONLY with a JSON object in this exact format (no markdown fences, no extra text):
{{"risk": "LOW|MED|HIGH|CRIT", "label": "brief Chinese description, max 20 chars"}}

Command to analyze: {cmd}
Working directory: {cwd}
Exit code: {exit_code}
"""


def analyze_command_risk(
    base_url: str,
    api_key: str,
    model: str,
    cmd: str,
    cwd: str = "",
    exit_code: int = 0,
) -> Dict[str, str]:
    """Analyze a shell command and return {"risk": ..., "label": ...}."""
    prompt = RISK_PROMPT.format(cmd=cmd, cwd=cwd, exit_code=exit_code)
    messages = [{"role": "user", "content": prompt}]
    try:
        response = chat_completion(base_url, api_key, model, messages)
        parsed = _parse_json_robust(response)
        risk = parsed.get("risk", "MED").upper()
        if risk not in ("LOW", "MED", "HIGH", "CRIT"):
            risk = "MED"
        label = str(parsed.get("label", ""))[:30]
        return {"risk": risk, "label": label}
    except Exception as e:
        return {"risk": "MED", "label": f"分析失败: {str(e)[:20]}"}


def answer_question(
    base_url: str,
    api_key: str,
    model: str,
    question: str,
    history_context: str,
) -> str:
    """Answer a user question with shell command history as context."""
    system_msg = (
        "You are ShellGuard, a terminal security assistant. "
        "The user has a history of shell commands with risk assessments. "
        "Answer questions about their command history in a helpful and concise way. "
        "Reply in the same language as the user's question."
    )
    user_msg = f"Command history:\n{history_context}\n\nQuestion: {question}"
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]
    try:
        return chat_completion(base_url, api_key, model, messages)
    except Exception as e:
        return f"[错误] {e}"
