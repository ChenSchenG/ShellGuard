#!/usr/bin/env bash
# ShellGuard — One-click installer and configuration guide
# Usage: bash install.sh

set -e

SHELLGUARD_DIR="$HOME/.shellguard"
LIB_DIR="$SHELLGUARD_DIR/lib"
BIN_DIR="$HOME/.local/bin"
HOOK_MARKER="# >>> shellguard hook >>>"
HOOK_END_MARKER="# <<< shellguard hook <<<"

# Color helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${CYAN}[ShellGuard]${RESET} $*"; }
success() { echo -e "${GREEN}[ShellGuard]${RESET} $*"; }
warn()    { echo -e "${YELLOW}[ShellGuard]${RESET} $*"; }
error()   { echo -e "${RED}[ShellGuard]${RESET} $*" >&2; }

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║         ShellGuard  Installer            ║${RESET}"
echo -e "${BOLD}${CYAN}║  Lightweight Terminal Security Monitor   ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════╝${RESET}"
echo ""

# ── Step 1: Check Python 3.8+ ──────────────────────────────────────────────
info "Checking Python version..."
PYTHON=""
for py in python3 python; do
    if command -v "$py" &>/dev/null; then
        ver=$("$py" -c "import sys; print(sys.version_info >= (3,8))" 2>/dev/null)
        if [ "$ver" = "True" ]; then
            PYTHON="$py"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    error "Python 3.8+ is required but not found."
    error "Please install Python 3.8+ and re-run this script."
    exit 1
fi
success "Found Python: $($PYTHON --version)"

# ── Step 2: Install rich ────────────────────────────────────────────────────
VENV_DIR="$SHELLGUARD_DIR/venv"
VENV_PYTHON=""

info "Checking for 'rich' library..."

# Helper: try to install rich using the best available method
install_rich() {
    # Strategy 1: use existing venv if already created
    if [ -f "$VENV_DIR/bin/python" ]; then
        VENV_PYTHON="$VENV_DIR/bin/python"
        if "$VENV_PYTHON" -c "import rich" &>/dev/null; then
            return 0
        fi
        "$VENV_PYTHON" -m pip install rich --quiet && return 0
    fi

    # Strategy 2: try pip install --user (works on most systems)
    if "$PYTHON" -m pip install rich --user --quiet 2>/dev/null; then
        return 0
    fi

    # Strategy 3: create a dedicated venv under ~/.shellguard/venv
    info "Creating isolated virtual environment at $VENV_DIR ..."
    "$PYTHON" -m venv "$VENV_DIR" && \
        "$VENV_DIR/bin/pip" install rich --quiet && \
        VENV_PYTHON="$VENV_DIR/bin/python" && \
        return 0

    # Strategy 4: last resort — break-system-packages (user must confirm)
    warn "Could not install 'rich' automatically."
    warn "Options:"
    warn "  a) brew install python-rich  (recommended on macOS)"
    warn "  b) pip install rich --break-system-packages"
    warn "  c) pipx install rich"
    read -rp "Try '--break-system-packages' now? [y/N]: " _confirm
    if [[ "$_confirm" =~ ^[Yy]$ ]]; then
        "$PYTHON" -m pip install rich --break-system-packages --quiet && return 0
    fi
    return 1
}

if "$PYTHON" -c "import rich" &>/dev/null; then
    success "'rich' already installed (system)."
elif [ -f "$VENV_DIR/bin/python" ] && "$VENV_DIR/bin/python" -c "import rich" &>/dev/null; then
    VENV_PYTHON="$VENV_DIR/bin/python"
    success "'rich' already installed (venv)."
else
    if ! install_rich; then
        error "Failed to install 'rich'. Please install it manually and re-run."
        exit 1
    fi
    success "'rich' installed."
fi

# If using venv python, point PYTHON to it for subsequent imports
if [ -n "$VENV_PYTHON" ]; then
    PYTHON="$VENV_PYTHON"
    info "Using venv Python: $VENV_PYTHON"
fi

# ── Step 3: Interactive configuration ──────────────────────────────────────
echo ""
echo -e "${BOLD}Configuration Setup${RESET}"
echo "Press Enter to accept defaults (shown in brackets)."
echo ""

# Check for existing config
existing_base_url=""
existing_api_key=""
existing_model=""
existing_max_history=""
if [ -f "$SHELLGUARD_DIR/config.json" ] && command -v "$PYTHON" &>/dev/null; then
    existing_base_url=$("$PYTHON" -c "import json; d=json.load(open('$SHELLGUARD_DIR/config.json')); print(d.get('base_url',''))" 2>/dev/null || echo "")
    existing_api_key=$("$PYTHON" -c "import json; d=json.load(open('$SHELLGUARD_DIR/config.json')); print(d.get('api_key',''))" 2>/dev/null || echo "")
    existing_model=$("$PYTHON" -c "import json; d=json.load(open('$SHELLGUARD_DIR/config.json')); print(d.get('model',''))" 2>/dev/null || echo "")
    existing_max_history=$("$PYTHON" -c "import json; d=json.load(open('$SHELLGUARD_DIR/config.json')); print(d.get('max_history_display',''))" 2>/dev/null || echo "")
fi

DEFAULT_BASE_URL="${existing_base_url:-https://api.openai.com/v1}"
DEFAULT_API_KEY="${existing_api_key:-}"
DEFAULT_MODEL="${existing_model:-gpt-4o-mini}"
DEFAULT_MAX_HISTORY="${existing_max_history:-50}"

read -rp "API Base URL [$DEFAULT_BASE_URL]: " INPUT_BASE_URL
BASE_URL="${INPUT_BASE_URL:-$DEFAULT_BASE_URL}"

read -rp "API Key [${DEFAULT_API_KEY:+****}]: " INPUT_API_KEY
API_KEY="${INPUT_API_KEY:-$DEFAULT_API_KEY}"

read -rp "Model [$DEFAULT_MODEL]: " INPUT_MODEL
MODEL="${INPUT_MODEL:-$DEFAULT_MODEL}"

read -rp "Max history to display [$DEFAULT_MAX_HISTORY]: " INPUT_MAX_HISTORY
MAX_HISTORY="${INPUT_MAX_HISTORY:-$DEFAULT_MAX_HISTORY}"

# ── Step 4: Write config ────────────────────────────────────────────────────
mkdir -p "$SHELLGUARD_DIR"
"$PYTHON" -c "
import json
config = {
    'base_url': '$BASE_URL',
    'api_key': '$API_KEY',
    'model': '$MODEL',
    'max_history_display': int('$MAX_HISTORY'),
    'risk_cache_ttl_seconds': 3600,
    'auto_analyze': False,
}
with open('$SHELLGUARD_DIR/config.json', 'w') as f:
    json.dump(config, f, indent=2)
"
success "Config written to $SHELLGUARD_DIR/config.json"

# ── Step 5: Copy files ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$BIN_DIR"
mkdir -p "$LIB_DIR"

# Copy CLI scripts
cp "$SCRIPT_DIR/shellguard" "$BIN_DIR/shellguard"
cp "$SCRIPT_DIR/shellguard-log" "$BIN_DIR/shellguard-log"
chmod +x "$BIN_DIR/shellguard" "$BIN_DIR/shellguard-log"

# Copy library
cp -r "$SCRIPT_DIR/shellguard_core" "$LIB_DIR/"

success "Files installed to $BIN_DIR/"
success "Library installed to $LIB_DIR/"

# Ensure ~/.local/bin is in PATH message
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    warn "$BIN_DIR is not in your PATH."
    warn "Add this to your shell config: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# ── Step 6: Inject shell hooks (idempotent) ─────────────────────────────────
inject_bash_hook() {
    local RC="$1"
    if [ ! -f "$RC" ]; then
        touch "$RC"
    fi
    if grep -qF "$HOOK_MARKER" "$RC" 2>/dev/null; then
        warn "Bash hook already present in $RC (skipping)"
        return
    fi
    cat >> "$RC" << 'BASH_HOOK'

# >>> shellguard hook >>>
# ShellGuard — terminal security monitor hook
_shellguard_prev_cmd=""
_shellguard_preexec() {
    _shellguard_prev_cmd="$BASH_COMMAND"
}
_shellguard_precmd() {
    local _exit=$?
    local _cmd="$_shellguard_prev_cmd"
    local _cwd="$PWD"
    if [ -n "$_cmd" ] && [ "$_cmd" != "$PROMPT_COMMAND" ]; then
        "$HOME/.local/bin/shellguard-log" --cmd "$_cmd" --cwd "$_cwd" --exit "$_exit" &>/dev/null &
    fi
    _shellguard_prev_cmd=""
}
trap '_shellguard_preexec' DEBUG
if [[ "$PROMPT_COMMAND" != *"_shellguard_precmd"* ]]; then
    PROMPT_COMMAND="_shellguard_precmd${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
fi
# <<< shellguard hook <<<
BASH_HOOK
    success "Bash hook injected into $RC"
}

inject_zsh_hook() {
    local RC="$1"
    if [ ! -f "$RC" ]; then
        touch "$RC"
    fi
    if grep -qF "$HOOK_MARKER" "$RC" 2>/dev/null; then
        warn "Zsh hook already present in $RC (skipping)"
        return
    fi
    cat >> "$RC" << 'ZSH_HOOK'

# >>> shellguard hook >>>
# ShellGuard — terminal security monitor hook
_shellguard_cmd=""
_shellguard_preexec() {
    _shellguard_cmd="$1"
}
_shellguard_precmd() {
    local _exit=$?
    if [ -n "$_shellguard_cmd" ]; then
        "$HOME/.local/bin/shellguard-log" --cmd "$_shellguard_cmd" --cwd "$PWD" --exit "$_exit" &>/dev/null &
        _shellguard_cmd=""
    fi
}
autoload -Uz add-zsh-hook 2>/dev/null || true
add-zsh-hook preexec _shellguard_preexec 2>/dev/null || preexec_functions+=(_shellguard_preexec)
add-zsh-hook precmd _shellguard_precmd 2>/dev/null || precmd_functions+=(_shellguard_precmd)
# <<< shellguard hook <<<
ZSH_HOOK
    success "Zsh hook injected into $RC"
}

# Detect which shell configs to update
INJECTED=0
if [ -f "$HOME/.bashrc" ] || [ "$SHELL" = "/bin/bash" ] || [ "$SHELL" = "/usr/bin/bash" ]; then
    inject_bash_hook "$HOME/.bashrc"
    INJECTED=1
fi
if [ -f "$HOME/.zshrc" ] || [ "$SHELL" = "/bin/zsh" ] || [ "$SHELL" = "/usr/bin/zsh" ]; then
    inject_zsh_hook "$HOME/.zshrc"
    INJECTED=1
fi
if [ "$INJECTED" -eq 0 ]; then
    warn "Could not detect shell type. Manually add hooks to your shell config."
    warn "Bash: Add the contents of install.sh's BASH_HOOK section to ~/.bashrc"
    warn "Zsh:  Add the contents of install.sh's ZSH_HOOK section to ~/.zshrc"
fi

# ── Step 7: Final instructions ──────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}✔ ShellGuard installed successfully!${RESET}"
echo ""
echo "Next steps:"
echo "  1. Reload your shell:  source ~/.bashrc  (or ~/.zshrc)"
echo "  2. Run a few commands, then launch the TUI:"
echo "     shellguard"
echo ""
echo "Commands:"
echo "  shellguard           — Open TUI (command history + risk analysis)"
echo "  shellguard analyze   — Batch analyze all untagged commands"
echo "  shellguard ask \"...\" — One-shot question about your history"
echo "  shellguard clear     — Clear LLM analysis cache"
echo ""
