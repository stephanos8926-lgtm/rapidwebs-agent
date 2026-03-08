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
| Server | Status | Tools | Note |
|--------|--------|-------|------|
| filesystem | ✅ | read_file, write_file, edit_file, list_directory, etc. | Qwen Code only |
| **memory** | ✅ | `create_entities`, `create_relations`, `add_observations`, `read_graph`, `search_nodes`, `open_nodes` | Qwen Code only - **use plural names!** |
| fetch | ✅ | fetch | Web content (rate limit safe) |
| brave-search | ✅ | brave_search | Needs `BRAVE_API_KEY` |
| caching | ✅ | check_cache, cache_response, etc. | Token caching (70-85% savings) |
| code-tools | ✅ | lint_file, format_file, fix_file | Tier 1 code tools |
| sequential-thinking | ✅ | sequential_thinking | Complex task planning |
| context7 | ✅ | resolve_library_id, query_docs | Library documentation |
| **Python Agent** | ❌ **NO MCP** | Uses `skills_manager.py` |

**CRITICAL:** Python agent uses `SkillManager`, NOT MCP!

**Memory MCP Tool Names (IMPORTANT):**
- ✅ Correct: `create_entities`, `create_relations`, `add_observations`, `read_graph`, `search_nodes`, `open_nodes`
- ❌ Wrong: `create_entity`, `create_relation`, `search_relations` (singular forms don't exist!)

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

## 🎨 TUI Features (NEW!)
**Display Components:**
- `display_tool_call_card()` - Tool execution with status, timing, params
- `display_diff()` - Side-by-side code comparison with syntax highlighting
- `display_code_block()` - Syntax-highlighted code (20+ languages)
- `display_collapsible_output()` - Large outputs in collapsible panels
- `display_todos()` - TODO list with status indicators
- `_detect_language()` - Auto-detect language from file extension

**Commands:**
- `/todos` or `/tasks` - View current TODO list

**Syntax Highlighting:** Auto-detects from `.py`, `.js`, `.ts`, `.html`, `.css`, `.json`, `.yaml`, `.md`, `.sh`, `.go`, `.rs`, `.java`, `.c`, `.cpp`, `.rb`, `.php`, `.sql`, `.xml`, etc.

## 🐛 Common Mistakes (READ BEFORE CODING!)
1. **MCP in Python?** ❌ NO! Python uses `SkillManager`, Qwen Code uses MCP
2. **Memory MCP tool names?** ❌ Use PLURAL: `create_entities` NOT `create_entity`
3. **Logging works?** ✅ Always run `python tests/test_logging.py` to verify
4. **CLI vs AgentUI?** CLI=`cli.py`, AgentUI=`user_interface.py` (separate!)
5. **Tests run?** ✅ Always run `python tests/` after changes
6. **System prompt updated?** ✅ Update `agent.py:_build_standard_context()`
7. **Imports checked?** ✅ Use `try/except` for optional imports
8. **Config defaults?** ✅ Update `config.py` AND `config.yaml`
9. **TUI components imported?** ✅ Must import AND call `render()` methods
10. **Duration tracking?** ✅ Must capture at 3 levels: skills_manager → agent → display

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
| Memory MCP tools? | `create_entities`, `create_relations`, `read_graph`, `search_nodes`, `open_nodes` (PLURAL!) |
| TUI not showing? | Check imports, call `render()`, verify `TUI_COMPONENTS_AVAILABLE` |
| Add syntax highlight? | Use `_detect_language(file_path)` then `Syntax(code, language)` |
| Tool duration missing? | Check 3-level chain: skills_manager → agent → display_skill_result() |

## 📝 Pre-Commit Checklist
- [ ] Run `python tests/` (all tests pass)
- [ ] All imports resolve (no circular deps)
- [ ] Log files created at expected location
- [ ] System prompt updated (if new features)
- [ ] Documentation updated (README.md, QWEN.md)
- [ ] Config defaults match code
- [ ] Manual test: `python -m rapidwebs_agent`
- [ ] TUI components: imports + render() calls verified
- [ ] Memory MCP: tool names are PLURAL (entities, relations)
- [ ] Duration tracking: 3-level chain intact

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
- `QWEN.COMPACT.md` - Compact reference (this file)

## 🔧 MCP Troubleshooting
**Memory MCP not working?**
1. Check tool names are PLURAL: `create_entities` NOT `create_entity`
2. Verify server starts: `npx -y @modelcontextprotocol/server-memory`
3. Check `.qwen/memory/` directory exists
4. Restart Qwen Code CLI after config changes

**TUI components not showing?**
1. Verify imports in `user_interface.py`
2. Check `TUI_COMPONENTS_AVAILABLE` flag
3. Ensure `render()` methods are called
4. Add fallback for when components unavailable

**Tool duration not displaying?**
1. `skills_manager.py`: Capture `start_time`, add `result['duration_ms']`
2. `agent.py`: Pass `duration_ms` to `display_skill_result()`
3. `user_interface.py`: Display in header like `"✓ tool_name (145ms)"`

---

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
- Context7 MCP configured with tools: resolve_library_id, query_docs. Provides automatic documentation injection to LLM context.
- TUI Integration Critical Requirements: (1) Components must be imported AND actively used - having ui_components.py isn't enough, (2) All display methods need fallbacks when TUI_COMPONENTS_AVAILABLE is False, (3) Import Rich box styles (ROUNDED, SIMPLE) explicitly for Panel styling, (4) Remove unused imports (like rich.text.Text) to pass linting
- Tool Execution Duration Tracking: Duration must be captured at THREE levels - (1) skills_manager.py: capture start_time before skill.execute(), add result['duration_ms'] after completion, (2) agent.py: pass duration_ms in result to display_skill_result(), (3) user_interface.py: display duration in header like "✓ tool_name (145ms)". Without this chain, timing info is lost
- TUI Display Methods Required for Complete Integration: (1) display_tool_call_card() - shows tool execution status with ToolCallCard, (2) display_diff() - shows code changes with DiffViewer, (3) display_code_block() - syntax-highlighted code with line numbers, (4) display_collapsible_output() - large outputs in CollapsiblePanel, (5) display_todos() - TODO list with TodoListPanel, (6) _detect_language() - auto-detect language from file extension for syntax highlighting
- Syntax Highlighting Language Map: Must support .py=python, .js=javascript, .ts/.tsx=typescript, .html=html, .css/.scss=css, .json=json, .yaml/.yml=yaml, .md=markdown, .sh/.bash/.zsh=bash, .go=go, .rs=rust, .java=java, .c/.h=c, .cpp/.hpp=cpp, .rb=ruby, .php=php, .sql=sql, .xml=xml, .toml=toml, .ini=ini, .env=dotenv. Use Path(file_path).suffix.lower() for detection
- Output Manager Integration Pattern: Check result for 'routing_decision' or 'original_size' keys to detect output_manager format. If present, use create_tool_result_display(). If not, fall back to _display_skill_result_traditional(). The skills_manager must merge output_manager results: result['output_manager'] = output_result.to_dict(), result['display_text'], result['routing_decision'], result['summary'], result['file_path']
- Common TUI Integration Mistakes to Avoid: (1) Don't just import components - must call their render() methods, (2) Don't use console.print() directly in display methods - use self.console.print(), (3) Don't forget to pass tool_name and duration_ms to display_skill_result(), (4) Don't hardcode Rich box styles - import ROUNDED, SIMPLE from rich.box, (5) Don't leave unused variables (linting fails), (6) Don't duplicate class definitions (InteractiveAgentUI was defined twice), (7) Always provide fallback when TUI components unavailable
- RapidWebs Agent TUI Commands: /todos or /tasks - displays TODO list panel with status indicators (✓ completed, ⏳ in_progress, ⏸ pending). Auto-created TODOs appear after complex multi-step operations (3+ different tool calls in sequence). TODO skill must be initialized with session_id for persistence
- Memory MCP Server Tool Names: The @modelcontextprotocol/server-memory exposes these exact tool names: create_entities, create_relations, add_observations, delete_entities, delete_observations, delete_relations, read_graph, search_nodes, open_nodes. NOT: create_entity, create_relation, search_relations (singular forms are wrong). Settings.json must use exact plural forms
