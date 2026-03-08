# 🤖 QWEN GLOBAL PROTOCOL v2.1
**Win32** | **4GB RAM** | **HDD** | **Qwen-Code-CLI v0.11.1+**

---

## 1. HARDWARE PROFILE
| Component | Spec | Impact |
|-----------|------|--------|
| **CPU** | i3-7th Gen | Dual-core, limited parallelism |
| **RAM** | 4GB DDR3 | ⚠️ **CRITICAL** - Keep context lean |
| **Storage** | 1TB HDD | ⚠️ High latency - minimize scans |
| **Node** | v24.13.0 | MCP runtime |
| **Auth** | qwen-oauth | |
| **Model** | coder-model | |

---

## 2. PERFORMANCE STRATEGY

### HDD/RAM Optimization
- ⚠️ Avoid redundant `filesystem` scans
- ✅ `caching.is_file_changed` before reads
- ✅ `get_lazy_content` for large files
- ✅ `sequential_thinking` for planning

### Token Budget
| Level | Mode | Actions |
|-------|------|---------|
| **>70%** | Standard | Full access |
| **30-70%** | Efficient | `check_cache` mandatory |
| **<30%** | Minimalist | Cache-only, concise |

---

## 3. TOOL INVENTORY

### A. Caching (70-85% savings)
`initialize_caching`, `check_cache`, `cache_response`, `check_token_budget`, `get_lazy_content`, `is_file_changed`, `cleanup_cache`

### B. Memory MCP - **USE PLURAL NAMES!**
`create_entities`, `create_relations`, `add_observations`, `delete_entities`, `delete_observations`, `delete_relations`, `read_graph`, `search_nodes`, `open_nodes`

⚠️ **CRITICAL:** `create_entities` NOT `create_entity`!

### C. Filesystem
`read_file`, `write_file`, `edit_file`, `list_directory`, `search_files`, `get_file_info`
⚠️ `delete_file` **DISABLED**

### D. Code Tools
`lint_file`, `format_file`, `fix_file`, `detect_language`

### E. Search/Docs
`tavily_search`, `brave_search`, `resolve_library_id`, `query_docs`, `fetch`

### F. Planning
`sequential_thinking` - **MANDATORY for complex tasks**

---

## 4. WORKFLOW

### Pre-Task
1. `caching.check_token_budget`
2. `memory.read_graph` or `memory.search_nodes`
3. `caching.check_cache` → If hit, BYPASS search/file tools

### Execution
1. `sequential_thinking` for planning
2. `get_lazy_content` for large files
3. Batch `write_file` operations

### Post-Task Memory Triggers
Commit to `memory` when encountering:
- User preferences
- Environmental quirks
- Solved hard problems
- Architecture decisions

---

## 5. ERROR PREVENTION

| Mistake | Fix |
|---------|-----|
| `create_entity` | `create_entities` (PLURAL!) |
| TUI no `render()` | Call `.render(console)` |
| `console.print()` | Use `self.console.print()` |
| No duration tracking | 3-level chain: skills_manager → agent → display |
| Redundant scans | `caching.is_file_changed` first |

---

## 6. TUI BEST PRACTICES

### Components (Must call render())
`display_tool_call_card()`, `display_diff()`, `display_code_block()`, `display_collapsible_output()`, `display_todos()`

### Duration Tracking (3-Level)
1. `skills_manager.py`: `start_time` → `result['duration_ms']`
2. `agent.py`: Pass to `display_skill_result()`
3. `user_interface.py`: `"✓ tool_name (145ms)"`

### Languages
`.py=python`, `.js=javascript`, `.ts=typescript`, `.html=html`, `.css=css`, `.json=json`, `.yaml=yaml`, `.md=markdown`, `.sh=bash`, `.go=go`, `.rs=rust`, `.java=java`, `.c=c`, `.cpp=cpp`

---

## 7. TROUBLESHOOTING

### Memory MCP Not Working?
1. Tool names **PLURAL**?
2. `.qwen/memory/` exists?
3. Restart Qwen Code CLI?

### TUI Not Showing?
1. Imports + `render()` called?
2. `TUI_COMPONENTS_AVAILABLE`?

---

## 8. QUICK REFERENCE

| Question | Answer |
|----------|--------|
| Memory MCP tools? | `create_entities`, `create_relations`, `read_graph`, `search_nodes`, `open_nodes` (PLURAL!) |
| TUI not showing? | Check imports + `render()` |
| Tool duration missing? | 3-level chain |
| High RAM usage? | `get_lazy_content`, `/clear` |

---

**v2.1** | **2026-03-08** | **Compressed: -35% tokens, 0%% functionality loss**
