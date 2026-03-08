# TODO System & Tool Output Analysis

**Date:** March 8, 2026  
**Analysis:** Comparison with Gemini CLI and Qwen Code CLI  
**Status:** Current implementation assessment + recommendations

---

## Executive Summary

RapidWebs Agent has **partial implementation** of tool output management but **lacks a dedicated TODO system**. Our `OutputManager` provides good truncation, but we need:

1. **TODO/Task Tracking System** - ❌ Missing
2. **Collapsible Tool Output** - ⚠️ Partial (has truncation, no collapse)
3. **File-based Output Storage** - ✅ Implemented
4. **Interactive TODO UI** - ❌ Missing

---

## 1. TODO/TASK TRACKING COMPARISON

### Current State: ❌ NOT IMPLEMENTED

| Feature | Gemini CLI | Qwen Code CLI | RapidWebs Agent |
|---------|------------|---------------|-----------------|
| **TODO Tool** | ✅ `write_todos` | ✅ `todo_write` | ❌ None |
| **User Commands** | ✅ Direct commands | ❌ Automatic only | ❌ None |
| **Toggle Shortcut** | ✅ `Ctrl+T` | ✅ `Ctrl+T` | ❌ None |
| **Visual Display** | ✅ Above input | ✅ Real-time | ❌ None |
| **Persistence** | ✅ Session files | ✅ `~/.qwen/todos/` | ❌ None |
| **Task Status** | ✅ 4 states | ✅ 3 states | ❌ N/A |

### What We Have

- SubAgents have internal task tracking (`SubAgentTask`, `SubAgentOrchestrator`)
- No user-facing TODO system
- No visual task list display
- No task persistence

---

## 2. TOOL OUTPUT MANAGEMENT COMPARISON

### Current State: ⚠️ PARTIALLY IMPLEMENTED

| Feature | Gemini CLI | Qwen Code CLI | RapidWebs Agent |
|---------|------------|---------------|-----------------|
| **Truncation Threshold** | 40,000 chars | 25,000 chars | ✅ 10,000 bytes |
| **Line Limit** | Configurable | 1,000 lines | ✅ 20-50 lines |
| **File Storage** | ⚠️ Session temp | ⚠️ Session temp | ✅ `temp_manager.py` |
| **Collapsible Output** | ✅ `Ctrl+O` | ✅ HTML modals | ❌ None |
| **Output Masking** | ✅ 50K token protection | ❌ None | ❌ None |
| **Summarization** | ✅ LLM-based | ✅ LLM-based | ✅ `OutputManager` |
| **Pagination** | ✅ `offset/limit` | ✅ `offset/limit` | ✅ `read_file` |

### What We Have (Good!)

**`agent/output_manager.py`** - Well implemented:
```python
class OutputManager:
    - inline_max_bytes: 10000  # Configurable
    - max_inline_lines: 20-50  # Configurable
    - summary_max_bytes: 1000  # For summarization
    - Three routing strategies:
      1. _route_inline() - Small outputs
      2. _route_summarized() - Medium outputs
      3. _route_file_only() - Large outputs
```

**`agent/temp_manager.py`** - File storage:
```python
class TempManager:
    - Creates temp files for large outputs
    - Session-based organization
    - Automatic cleanup
    - Search capability (grep)
```

**`agent/skills_manager.py`** - Read truncation:
```python
async def _execute_read(self, path, max_lines=None):
    - Supports max_lines parameter
    - Returns truncated flag
    - Shows lines_read count
```

### What We're Missing

1. **Collapsible Output Cards** - Can't expand/collapse after display
2. **Output Masking** - Old outputs not automatically hidden
3. **Interactive Viewer** - No click/key to expand full content
4. **TODO Integration** - No task tracking for tool calls

---

## 3. RECOMMENDED IMPLEMENTATIONS

### Priority 1: TODO System (HIGH IMPACT)

**Implementation Plan:**

#### A. Create TODO Tool (`agent/skills/todo_skill.py`)

```python
class TodoSkill(SkillBase):
    """TODO/task management skill.
    
    Operations:
    - create: Add new task
    - update: Change task status
    - list: Show all tasks
    - clear: Remove completed tasks
    - export: Save to file
    """
    
    def __init__(self, config, session_id: str):
        super().__init__(config, 'todo')
        self.session_id = session_id
        self.todos: List[TodoItem] = []
        self.storage_path = Path.home() / '.local' / 'share' / 'rapidwebs-agent' / 'todos' / f'{session_id}.json'
        self._load()
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        actions = {
            'create': self._create,
            'update': self._update,
            'list': self._list,
            'clear': self._clear,
            'export': self._export
        }
        return await actions[action](**kwargs)
```

#### B. Add Keyboard Shortcut (`Ctrl+T`)

```python
# In rapidwebs_agent/cli.py
@bindings.add('c-t')
def toggle_todo_list(event):
    """Toggle TODO list visibility."""
    if self._todo_visible:
        self._hide_todo_list()
    else:
        self._show_todo_list()
```

#### C. Visual Display Component (`agent/ui_components.py`)

```python
class TodoListPanel:
    """TODO list display with status indicators.
    
    Visual format:
    ╭─────────────────────────────────╮
    │ 📋 Tasks (3 active)             │
    ├─────────────────────────────────┤
    │ ✓ Task 1 completed              │
    │ ⏳ Task 2 in progress            │
    │ ⏸ Task 3 pending                │
    ╰─────────────────────────────────╯
    """
```

#### D. Integration with Agent

```python
# In agent/agent.py
class Agent:
    def __init__(self):
        self.todo_skill = TodoSkill(config, session_id=self._session_id)
        
    async def _parse_and_execute_tool(self, response):
        # Auto-create TODOs for complex tasks
        if self._detect_complex_task(response):
            await self._auto_generate_todos(response)
```

---

### Priority 2: Collapsible Tool Output (MEDIUM IMPACT)

**Implementation Plan:**

#### A. Enhance ToolCallCard with Collapse

```python
# In agent/ui_components.py
class ToolCallCard:
    def __init__(self, ..., collapsible: bool = True, collapsed: bool = False):
        self.collapsible = collapsible
        self.collapsed = collapsed
        self.output_preview_lines = 5  # Show first 5 lines when collapsed
    
    def render(self, console, full_output: str = None):
        if self.collapsed and full_output:
            # Show preview
            preview = '\n'.join(full_output.split('\n')[:self.output_preview_lines])
            console.print(f"[dim]{preview}...[/dim]")
            console.print("[dim]Press 'e' to expand[/dim]")
        else:
            # Show full output
            console.print(full_output)
```

#### B. Add Expand/Collapse Key Binding

```python
# In rapidwebs_agent/cli.py
@bindings.add('e')
def expand_output(event):
    """Expand collapsed tool output."""
    self._expand_last_output()

@bindings.add('c')
def collapse_output(event):
    """Collapse expanded tool output."""
    self._collapse_last_output()
```

#### C. Output Masking (Token Savings)

```python
# In agent/output_manager.py
class OutputManager:
    def __init__(self, ..., mask_old_outputs: bool = True):
        self.mask_old_outputs = mask_old_outputs
        self.output_history: List[OutputResult] = []
        self.mask_threshold = 50000  # tokens
    
    def _mask_old_outputs(self):
        """Mask outputs older than threshold."""
        total_tokens = sum(o.estimated_tokens for o in self.output_history[-5:])
        for old_output in self.output_history[:-5]:
            if total_tokens > self.mask_threshold:
                old_output.masked = True
```

---

### Priority 3: Interactive Output Viewer (LOW IMPACT)

**Implementation Plan:**

#### A. Modal Viewer Component

```python
# In agent/ui_components.py
class OutputModal:
    """Full-screen output viewer with scrolling.
    
    Features:
    - Full content display
    - Search within output
    - Copy to clipboard
    - Save to file
    """
    
    def __init__(self, content: str, title: str = "Output"):
        self.content = content
        self.title = title
        self.search_query = ""
    
    async def show(self, console: Console):
        """Show modal with interactive controls."""
        # Use Rich Live for interactive display
        with Live(self._render(), console=console, refresh_per_second=10) as live:
            # Handle keyboard input
            while True:
                key = await self._get_key()
                if key == 'q':
                    break
                elif key == '/':
                    self.search_query = await self._prompt_search()
                live.update(self._render())
```

---

## 4. CONFIGURATION OPTIONS

Add to `~/.config/rapidwebs-agent/config.yaml`:

```yaml
# TODO System
todo:
  enabled: true
  auto_create: true  # Auto-create TODOs for complex tasks
  storage_path: ~/.local/share/rapidwebs-agent/todos
  show_on_startup: false
  default_status: pending

# Tool Output Management
output_management:
  inline_max_bytes: 10000
  max_inline_lines: 20
  summary_max_bytes: 1000
  collapsible: true
  mask_old_outputs: true
  mask_threshold_tokens: 50000
  file_storage_enabled: true
  file_storage_path: ~/.local/share/rapidwebs-agent/output
  auto_cleanup_hours: 24

# Visual Display
ui:
  show_todo_panel: true
  todo_panel_position: top  # top, bottom, right
  collapse_tool_output: true
  default_collapsed_lines: 5
  enable_output_modal: true
```

---

## 5. KEYBOARD SHORTCUTS

| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl+T` | Toggle TODO list | Always |
| `Ctrl+Shift+T` | Create new TODO | Always |
| `e` | Expand output | When output collapsed |
| `c` | Collapse output | When output expanded |
| `m` | Open output modal | When output selected |
| `/` | Search in output | In modal view |
| `s` | Save output to file | In modal view |

---

## 6. IMPLEMENTATION TIMELINE

### Week 1: TODO System
- Day 1-2: Create `TodoSkill` class
- Day 3: Add `TodoListPanel` UI component
- Day 4: Integrate with Agent and CLI
- Day 5: Add keyboard shortcuts and testing

### Week 2: Collapsible Output
- Day 1-2: Enhance `ToolCallCard` with collapse
- Day 3: Add output masking to `OutputManager`
- Day 4: Add expand/collapse key bindings
- Day 5: Testing and documentation

### Week 3: Interactive Viewer
- Day 1-3: Create `OutputModal` component
- Day 4: Add search and save features
- Day 5: Integration and testing

---

## 7. UNIQUE INNOVATIONS WE CAN ADD

### A. Auto-Generated TODOs from Tool Calls

When LLM makes multiple tool calls, automatically create TODOs:

```python
async def _parse_and_execute_tool(self, response):
    tool_calls = self._extract_tool_calls(response)
    
    if len(tool_calls) >= 3:
        # Auto-generate TODO list
        await self.todo_skill.execute('create', tasks=[
            {'description': f'Execute {tc["tool"]}', 'status': 'pending'}
            for tc in tool_calls
        ])
```

### B. TODO-Based Progress Tracking

Show progress bar for TODO completion:

```
╭─────────────────────────────────╮
│ 📋 Tasks: 5/8 completed (62%)   │
│ ████████░░░░░░░░░░░░░           │
╰─────────────────────────────────╯
```

### C. Smart TODO Suggestions

Analyze conversation and suggest TODOs:

```python
def suggest_todos(conversation: str) -> List[str]:
    suggestions = []
    
    if "refactor" in conversation.lower():
        suggestions.append("Identify code smells")
        suggestions.append("Create refactoring plan")
        suggestions.append("Implement changes")
        suggestions.append("Run tests")
    
    return suggestions
```

### D. TODO Persistence Across Sessions

Save TODOs and offer to resume:

```
Welcome back! You have 3 pending tasks from last session:
  ⏸ Update database schema
  ⏸ Write migration tests
  ⏸ Update API documentation

Resume these tasks? (Y/n)
```

---

## 8. SUMMARY

### What We're Doing Well ✅

1. **OutputManager** - Excellent truncation and routing
2. **TempManager** - Good file-based storage
3. **Read truncation** - max_lines parameter works well
4. **Configurable thresholds** - All settings in config

### Critical Gaps ❌

1. **No TODO system** - Major missing feature
2. **No collapsible output** - Consumes too much space
3. **No output masking** - Wastes tokens on old outputs
4. **No interactive viewer** - Can't inspect full output easily

### Recommended Priority

1. **TODO System** (Week 1) - High impact, differentiates from basic agents
2. **Collapsible Output** (Week 2) - Medium impact, saves TUI space
3. **Interactive Viewer** (Week 3) - Nice-to-have, power user feature

---

**Next Steps:**
1. Implement `TodoSkill` class
2. Add `TodoListPanel` UI component
3. Integrate with Agent and CLI
4. Add keyboard shortcuts
5. Test and document
