# RapidWebs Agent - QWEN GUIDE v1.2
**Win32** | **Python 3.10+** | **uv**

---

## 🚀 Quick Start
```bash
.\.venv\Scripts\activate && python -m rapidwebs_agent
```

## 📁 Structure
```
rapidwebs-agent/
├── .qwen/settings.json    # MCP config
├── agent/
│   ├── agent.py           # Core + system prompt
│   ├── skills_manager.py  # Tools (NO MCP!)
│   ├── user_interface.py  # TUI
│   └── ui_components.py   # TUI components
└── rapidwebs_agent/cli.py # Entry
```

## 🔌 MCP Servers (Qwen Code ONLY!)
| Server | Tools | Note |
|--------|-------|------|
| filesystem | read/write/edit_file, list_directory | Qwen Code only |
| **memory** | `create_entities`, `create_relations`, `read_graph`, `search_nodes`, `open_nodes` | **PLURAL!** |
| caching | check_cache, cache_response | 70-85% savings |
| code-tools | lint/format/fix_file | Tier 1 |
| context7 | resolve_library_id, query_docs | Docs |
| **Python Agent** | ❌ NO MCP | Uses `skills_manager` |

⚠️ **CRITICAL:** Python agent uses `SkillManager`, NOT MCP!
⚠️ **Memory MCP:** `create_entities` NOT `create_entity`!

## 🎯 Token Optimization
- **Budget:** 6000 context max
- **Caching:** 70-85% savings
- **Ignore:** `.venv/`, `*.env`, `*.db` (40-60% savings)
- **Logs:** `%LOCALAPPDATA%\rapidwebs-agent\logs\`

## 🔐 Security
- **Blocked:** `rm -rf /`, `sudo`, `wget`, `curl`
- **Excluded:** `*.env`, `*.key`, `*.pem`, `.git/`
- **API keys:** Env vars only

## ✅ Approval Modes
| Mode | Writes | Destructive | Shortcut |
|------|--------|-------------|----------|
| `plan` | ❌ | ❌ | Ctrl+P |
| `default` | ⚠️ | ⚠️ | Ctrl+D |
| `auto-edit` | ✅ | ⚠️ | Ctrl+A |
| `yolo` | ✅ | ✅ | Ctrl+Y |

Commands: `/mode [name]`

## 🛠️ CLI Commands
`/help`, `/mode`, `/stats`, `/budget`, `/clear`, `/configure`, `/todos`, `subagents`

Shortcuts: Ctrl+P/D/A/Y (modes), Ctrl+L (clear)

## 🧪 Testing
```bash
python tests/           # All tests
python -m rapidwebs_agent  # Manual
```

## 🎨 TUI Features
**Components:** `display_tool_call_card()`, `display_diff()`, `display_code_block()`, `display_collapsible_output()`, `display_todos()`

**Commands:** `/todos` or `/tasks`

**Syntax:** Auto-detects `.py`, `.js`, `.ts`, `.html`, `.css`, `.json`, `.yaml`, `.md`, `.sh`, `.go`, `.rs`, `.java`, `.c`, `.cpp`, `.rb`, `.php`, `.sql`, `.xml`

## 🐛 Common Mistakes
1. **MCP in Python?** ❌ NO! Uses `SkillManager`
2. **Memory MCP names?** ❌ PLURAL: `create_entities`
3. **Logging?** ✅ `python tests/test_logging.py`
4. **CLI vs AgentUI?** Separate: `cli.py` vs `user_interface.py`
5. **Tests?** ✅ `python tests/` after changes
6. **TUI components?** ✅ Import + call `render()`
7. **Duration tracking?** ✅ 3-level chain

## 📞 Quick Reference
| Question | Answer |
|----------|--------|
| Add command? | `cli.py:_handle_command()` |
| Add shortcut? | `cli.py:@bindings.add()` |
| System prompt? | `agent.py:_build_standard_context()` |
| Memory MCP tools? | `create_entities`, `create_relations` (PLURAL!) |
| TUI not showing? | Imports + `render()` + `TUI_COMPONENTS_AVAILABLE` |
| Tool duration? | 3-level: skills_manager → agent → display |

## 📝 Pre-Commit Checklist
- [ ] `python tests/` passes
- [ ] Imports resolve
- [ ] Logs at expected location
- [ ] TUI: imports + `render()` verified
- [ ] Memory MCP: PLURAL names
- [ ] Duration: 3-level chain

## 🔧 Env Vars
```powershell
$env:RW_QWEN_API_KEY="key"      # Required
$env:BRAVE_API_KEY="key"         # Optional
```

## 🔧 MCP Troubleshooting
**Memory MCP not working?**
1. PLURAL names?
2. Server starts: `npx -y @modelcontextprotocol/server-memory`
3. `.qwen/memory/` exists?
4. Restart Qwen Code CLI

**TUI not showing?**
1. Imports + `render()`?
2. `TUI_COMPONENTS_AVAILABLE`?

**Duration not displaying?**
1. `skills_manager.py`: `start_time` → `result['duration_ms']`
2. `agent.py`: Pass to `display_skill_result()`
3. `user_interface.py`: `"✓ tool_name (145ms)"`

---

**v1.2** | **2026-03-08** | **Compressed: -25% tokens, 0%% functionality loss**

## Qwen Added Memories
- rapidwebs-agent: Python CLI for Win32, Qwen Code architecture
- Architecture: Python uses `SkillManager`, NOT MCP; Qwen Code uses MCP
- Approval modes: plan, default, auto-edit, yolo
- Config: 6000 token budget, 70-85% caching savings
- Logs: `%LOCALAPPDATA%\rapidwebs-agent\logs\`
- Entry: `python -m rapidwebs_agent`
- Tech: Python 3.10+, uv
- Context7: `resolve_library_id`, `query_docs` (no API key in docs!)
- TUI: Import + `render()`, fallbacks, Rich box styles (ROUNDED, SIMPLE)
- Duration: 3-level chain (skills_manager → agent → display)
- Syntax: `.py=python`, `.js=javascript`, `.ts=typescript`, etc.
- Output Manager: Check `routing_decision`/`original_size` keys
- Memory MCP: PLURAL tool names (`create_entities` NOT `create_entity`)
