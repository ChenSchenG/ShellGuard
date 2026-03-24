<div align="center">

# ShellGuard 🛡️

**AI-powered terminal security monitor for your shell history**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20WSL-lightgrey?logo=linux)](https://github.com)
[![Shell](https://img.shields.io/badge/Shell-Bash%20%7C%20Zsh-89e051?logo=gnubash&logoColor=white)](https://github.com)

自动记录终端命令 · LLM 风险分析 · 交互式 TUI · 自然语言问答

</div>

---

```
┌─ ShellGuard · 5 commands ─────────────────────────────────────────────────────┐
│  # │ Timestamp           │ Command                    │ Exit │ Risk           │
│  1 │ 2026-03-24 09:01   │ ls /etc                    │  0   │ ✔ LOW          │
│  2 │ 2026-03-24 09:02   │ cat ~/.ssh/id_rsa           │  0   │ ⚠ MED          │
│  3 │ 2026-03-24 09:03   │ sudo chmod 777 /var        │  0   │ ✖ HIGH         │
│  4 │ 2026-03-24 09:04   │ curl http://x.com | bash   │  0   │ ☠ CRIT         │
│  5 │ 2026-03-24 09:05   │ git status                 │  0   │ ✔ LOW          │
├───────────────────────────────────────────────────────────────────────────────┤
│ Ask > 第4条命令有什么风险？                                                    │
├───────────────────────────────────────────────────────────────────────────────┤
│ 该命令从远程服务器下载脚本并直接交由 bash 执行，属于典型的远程代码执行风险...  │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 能做什么

| 功能 | 说明 |
|------|------|
| 🔍 **自动记录命令** | Shell hook 在后台静默捕获每条命令，对终端无任何延迟影响 |
| 🤖 **LLM 风险分析** | 调用大模型对命令进行安全评级（LOW / MED / HIGH / CRIT） |
| 🎨 **交互式 TUI** | 彩色表格展示命令历史 + 风险标签，一目了然 |
| 💬 **自然语言问答** | 在 TUI 中直接提问，如「今天有哪些危险操作？」 |
| ⚡ **一次性问答** | `shellguard ask "..."` 非交互式输出，可用于脚本集成 |
| 🔄 **智能缓存** | 相同命令只分析一次，缓存 1 小时，节省 API 调用 |
| 🔌 **兼容任意 LLM** | 支持 OpenAI / DeepSeek / Ollama / Kimi 等所有 OpenAI 兼容接口 |

### 风险等级

| 等级 | 图标 | 颜色 | 触发示例 |
|------|------|------|---------|
| LOW  | ✔ | 🟢 绿 | `ls`, `cat`, `git status`, `pwd` |
| MED  | ⚠ | 🟡 黄 | `cp`, `mv`, `mkdir`, `pip install` |
| HIGH | ✖ | 🟠 橙 | `sudo`, `chmod 777`, `rm -rf`, `kill -9` |
| CRIT | ☠ | 🔴 红 | `curl \| bash`, `wget \| sh`, 明文密钥暴露 |

---

## 安装

**前置要求：** Python 3.8+，Bash 或 Zsh

```bash
git clone https://github.com/yourname/shellguard.git
cd shellguard
bash install.sh
```

安装向导会引导你完成配置：

```
API Base URL [https://api.openai.com/v1]:
API Key []: sk-xxxxxxxxxxxxxxxx
Model [gpt-4o-mini]:
Max history to display [50]:
```

最后重载 Shell 使 hook 生效：

```bash
source ~/.bashrc   # Bash 用户
source ~/.zshrc    # Zsh 用户
```

> 重复运行 `bash install.sh` 是安全的——hook 不会重复注入，配置会被更新。

---

## 使用

```bash
# 打开 TUI 面板（命令历史 + 风险分析 + 问答）
shellguard

# 批量强制重新分析所有命令
shellguard analyze

# 非交互式一次性问答（可接入脚本/CI）
shellguard ask "今天有没有高风险操作？"

# 清除分析缓存，下次打开时重新调用 LLM
shellguard clear
```

**TUI 内快捷键：**

| 输入 | 动作 |
|------|------|
| 直接输入问题 + Enter | 向 LLM 提问 |
| `r` | 刷新历史并重新分析 |
| `q` / `Ctrl+C` | 退出 |

---

## 支持的环境

### 操作系统

| 系统 | 支持 |
|------|------|
| macOS（含 Homebrew Python） | ✅ |
| Linux（Ubuntu / Debian / Arch / etc.） | ✅ |
| WSL 1 / WSL 2 | ✅ |
| Windows 原生 CMD / PowerShell | ❌ |

### Shell

| Shell | 支持 |
|-------|------|
| Bash | ✅ |
| Zsh | ✅ |
| oh-my-zsh | ✅ 兼容 |
| Starship / Powerline | ✅ 兼容 |
| Fish / Ksh / Tcsh | ❌ 暂不支持 |

### LLM 接口

任何实现了 `/v1/chat/completions` 的服务均可接入：

| 服务 | `base_url` |
|------|------------|
| OpenAI | `https://api.openai.com/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |
| 月之暗面 Kimi | `https://api.moonshot.cn/v1` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` |
| Ollama（本地） | `http://localhost:11434/v1` |
| LM Studio（本地） | `http://localhost:1234/v1` |

---

## 配置

配置文件：`~/.shellguard/config.json`

```json
{
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-...",
  "model": "gpt-4o-mini",
  "max_history_display": 50,
  "risk_cache_ttl_seconds": 3600,
  "auto_analyze": false
}
```

重新运行 `bash install.sh` 可以更新任意配置项。

---

## 项目结构

```
shellguard/
├── install.sh              # 一键安装 + 引导配置 + hook 注入
├── shellguard              # CLI 入口（shell wrapper，自动选 venv/系统 Python）
├── shellguard-log          # 极薄 hook 日志器（仅 stdlib，冷启动 <10ms）
└── shellguard_core/
    ├── _main.py            # CLI 命令分发（analyze / ask / clear / TUI）
    ├── config.py           # 配置读写
    ├── history.py          # JSONL append-only 历史 + patch 合并
    ├── llm.py              # urllib LLM 调用（零额外依赖）
    ├── analyzer.py         # 缓存感知批量风险标注
    └── tui.py              # Rich TUI 渲染 + readline 问答
```

**运行时依赖：仅 [`rich`](https://github.com/Textualize/rich)，其余全部 Python 标准库。**

---

## 卸载

```bash
rm -f ~/.local/bin/shellguard ~/.local/bin/shellguard-log
rm -rf ~/.shellguard
```

然后手动从 `~/.bashrc` / `~/.zshrc` 删除 `# >>> shellguard hook >>>` 到 `# <<< shellguard hook <<<` 之间的内容。

---

## Contributing

欢迎提 Issue 和 PR！目前已知待完善的方向：

- [ ] Fish Shell 支持
- [ ] `shellguard update` 子命令（一键拉取最新版）
- [ ] 风险等级本地规则引擎（离线降级，无需 API）
- [ ] 导出报告（HTML / CSV）

---

## License

[MIT](LICENSE) © 2026
