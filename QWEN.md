# RapidWebs Agent - Qwen Code Guide (Compact)
**v1.1.0** | **Win32** | **Python 3.10+** | **uv**

## 🚀 Quick Start
```bash
.\.venv\Scripts\activate && python -m rapidwebs_agent
```

## 📁 Structure (Key Paths)
```
rapidwebs-agent/
├── .qwen/settings.json       # Qwen Code MCP config
├── agent/
│   ├── agent.py              # Core engine + system prompt
│   ├── skills_manager.py     # Tool execution (NO MCP!)
│   ├── approval_workflow.py  # Approval modes
│   ├── cli.py (in rapidwebs_agent/) # Main CLI entry
│   └── caching/              # Token caching
└── tests/                    # Test scripts
```

## ⚙️ Config Files
| File | Purpose |
|------|---------|
| `.qwen/settings.json` | Qwen Code CLI (MCP servers) |
| `~/.config/rapidwebs-agent/config.yaml` | Agent config |
| `agent/config.py` | Default settings |

## 🔌 MCP Servers (Qwen Code ONLY - NOT Python Agent!)
| Server | Status | Note |
|--------|--------|------|
| filesystem | ✅ | Qwen Code only |
| memory | ✅ | Qwen Code only |
| fetch | ✅ | Web content (rate limit safe) |
| brave-search | ✅ | Needs `BRAVE_API_KEY` |
| **Python Agent** | ❌ **NO MCP** | Uses `skills_manager.py` |

**CRITICAL:** Python agent uses `SkillManager`, NOT MCP!

## 🎯 Token Optimization
- **Budget:** 6000 tokens context max
- **Caching:** 70-85% savings via `agent/caching/`
- **File ignore:** `.qwenignore` excludes `.venv/`, `*.env`, `*.db` (40-60% savings)
- **Log location:** `%LOCALAPPDATA%\rapidwebs-agent\logs\`

## 🔐 Security
- **Blocked:** `rm -rf /`, `sudo`, `wget`, `curl`, `nc`
- **Excluded:** `*.env`, `*.key`, `*.pem`, `*.secret`, `.git/`
- **API keys:** Environment variables only

## ✅ Approval Modes (4 modes)
| Mode | Writes | Destructive | Use Case |
|------|--------|-------------|----------|
| `plan` | ❌ | ❌ | Safe exploration |
| `default` | ⚠️ | ⚠️ | Recommended |
| `auto-edit` | ✅ | ⚠️ | Daily dev |
| `yolo` | ✅ | ✅ | Rapid iteration |

**Commands:** `/mode [name]` or shortcuts: `Ctrl+P/D/A/Y`

## 🛠️ CLI Commands
| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/mode [name]` | Switch approval mode |
| `/stats` | Token usage |
| `/budget` | Budget status |
| `/clear` | Clear history |
| `/configure` | Config wizard |
| `subagents <cmd>` | SubAgents management |

**Shortcuts:** `Ctrl+P` (plan), `Ctrl+D` (default), `Ctrl+A` (auto-edit), `Ctrl+Y` (yolo), `Ctrl+L` (clear)

## 🧪 Testing
```bash
python tests/test_logging.py     # Verify logging
python tests/                    # Run all tests (pytest)
python -m rapidwebs_agent        # Manual test
```

## 🐛 Common Mistakes (READ BEFORE CODING!)
1. **MCP in Python?** ❌ NO! Python uses `SkillManager`, Qwen Code uses MCP
2. **Logging works?** ✅ Always run `python tests/test_logging.py` to verify
3. **CLI vs AgentUI?** CLI=`cli.py`, AgentUI=`user_interface.py` (separate!)
4. **Tests run?** ✅ Always run `python tests/` after changes
5. **System prompt updated?** ✅ Update `agent.py:_build_standard_context()`
6. **Imports checked?** ✅ Use `try/except` for optional imports
7. **Config defaults?** ✅ Update `config.py` AND `config.yaml`

## 📞 Quick Reference
| Question | Answer |
|----------|--------|
| Add command? | `cli.py:_handle_command()` |
| Add shortcut? | `cli.py:@bindings.add()` |
| Add approval mode? | `approval_workflow.py:ApprovalMode` |
| System prompt? | `agent.py:_build_standard_context()` |
| Test logging? | `python test_logging.py` |
| Log location? | `%LOCALAPPDATA%\rapidwebs-agent\logs\` |
| Python use MCP? | **NO!** Uses `skills_manager.py` |
| CLI or AgentUI? | CLI=`cli.py`, AgentUI=`user_interface.py` |

## 📝 Pre-Commit Checklist
- [ ] Run `python tests/` (all tests pass)
- [ ] All imports resolve (no circular deps)
- [ ] Log files created at expected location
- [ ] System prompt updated (if new features)
- [ ] Documentation updated (README.md, QWEN.md)
- [ ] Config defaults match code
- [ ] Manual test: `python -m rapidwebs_agent`

## 🔧 Environment Variables
```powershell
$env:RW_QWEN_API_KEY="key"      # Required
$env:BRAVE_API_KEY="key"         # Optional (brave-search)
$env:RW_DAILY_TOKEN_LIMIT="100000"  # Optional
```

## 📚 Extended Docs
- `CLI_ENHANCEMENTS.md` - Approval workflow & shortcuts
- `TUI_SUBAGENT_FIXES.md` - TUI fixes & logging
- `SYSTEM_PROMPT_UPDATES.md` - LLM prompt changes
- `docs/` - Detailed guides

---
**Memories:** Win32, Node v24.13.0, Auth: qwen-oauth, Model: coder-model, No sandbox

## Qwen Added Memories
- rapidwebs-agent: Python CLI agent framework for Win32, built on Qwen Code architecture
- rapidwebs-agent architecture: Python agent uses SkillManager, NOT MCP servers
- rapidwebs-agent architecture: Qwen Code CLI uses MCP servers (filesystem, memory, fetch, brave-search)
- rapidwebs-agent feature: Approval modes are plan, default, auto-edit, yolo
- rapidwebs-agent config: Token budget is 6000 context max, 70-85% savings via caching
- rapidwebs-agent config: Log location is %LOCALAPPDATA%\rapidwebs-agent\logs\
- rapidwebs-agent config: Config file is ~/.config/rapidwebs-agent/config.yaml
- rapidwebs-agent usage: Entry point is python -m rapidwebs_agent
- rapidwebs-agent tech: Python version 3.10+, uses uv for package management
- Context7 MCP configured with tools: resolve_library_id, query_docs. API key: ctx7sk-015f4b7e-4048-47dc-8d04-09ca6d77b45d. Provides automatic documentation injection to LLM context.
