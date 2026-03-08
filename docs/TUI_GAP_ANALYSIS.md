# TUI Gap Analysis: RapidWebs Agent vs Industry Leaders

**Date:** March 8, 2026
**Analysis:** Comprehensive comparison with Qwen Code CLI and Gemini CLI
**Goal:** Identify missing features and propose innovative improvements
**Status:** ✅ **EXPAND/COLLAPSE IMPLEMENTED** (v2.3.1)

---

## Executive Summary

RapidWebs Agent has a **solid foundation** with approval modes, conversation management, and Rich-based UI components. Recent additions include collapsible tool output with keyboard shortcuts.

### Current State Assessment

| Category | Status | Notes |
|----------|--------|-------|
| **Core TUI Framework** | ✅ Good | Rich + prompt_toolkit working well |
| **Approval Workflow** | ✅ Excellent | 4 modes with keyboard shortcuts |
| **Conversation Management** | ✅ Good | Export, search, compress implemented |
| **TODO System** | ✅ **Implemented** | `TodoSkill`, `TodoListPanel`, `Ctrl+T` |
| **Collapsible Output** | ✅ **Implemented** | `e`/`c` keys, state tracking |
| **Visual Polish** | ⚠️ Basic | Missing incremental rendering, themes |
| **Interactive Elements** | ⚠️ Limited | No mouse support, limited shortcuts |
| **Real-time Feedback** | ⚠️ Basic | No streaming tokens, basic progress |
| **Session Management** | ⚠️ Basic | No auto-save, limited browser |
| **Accessibility** | ❌ Missing | No screen reader mode |

---

## 1. VISUAL/DISPLAY GAPS

### ❌ Missing Features

| Feature | Gemini CLI | Qwen Code | RapidWebs | Priority |
|---------|------------|-----------|-----------|----------|
| **Flicker-free rendering** | ✅ Alternate buffer | ✅ ink.js | ❌ Basic Rich | **HIGH** |
| **Incremental rendering** | ✅ Enabled by default | ⚠️ Chunked | ❌ Full buffer | **HIGH** |
| **Sticky headers/footers** | ✅ Locked input, anchored headers | ⚠️ Status bar | ❌ Scrolling | **MEDIUM** |
| **Dynamic window titles** | ✅ Status icons in title | ❌ | ❌ | LOW |
| **Auto-theme detection** | ✅ Light/dark background | ❌ | ❌ | MEDIUM |
| **Custom themes** | ✅ User-defined themes | ⚠️ Basic | ❌ None | MEDIUM |
| **Line numbers in code** | ✅ Configurable | ✅ Yes | ⚠️ Inconsistent | LOW |
| **Loading phrases** | ✅ Tips + witty phrases | ⚠️ Spinners | ⚠️ Basic spinners | LOW |

### 🔧 Proposed Solutions

#### 1.1 Incremental Rendering Engine (HIGH PRIORITY)

**Problem:** Current implementation renders full output at once, causing flicker on slow terminals.

**Solution:** Implement token-by-token streaming with buffered rendering.

```python
# New: agent/streaming_renderer.py
class StreamingRenderer:
    """Incremental token-by-token rendering with flicker reduction."""
    
    def __init__(self, console: Console, buffer_size: int = 5):
        self.console = console
        self.buffer_size = buffer_size  # Tokens to buffer before render
        self._buffer = []
        self._last_render_time = 0
        
    async def stream_response(self, token_generator: AsyncGenerator[str, None]):
        """Stream tokens with intelligent batching."""
        from rich.live import Live
        from rich.text import Text
        
        with Live("", console=self.console, refresh_per_second=30) as live:
            async for token in token_generator:
                self._buffer.append(token)
                
                # Render when buffer full or timeout
                if len(self._buffer) >= self.buffer_size:
                    live.update(Text("".join(self._buffer)))
                    self._buffer = []
                    
                await asyncio.sleep(0)  # Yield to event loop
            
            # Final render
            if self._buffer:
                live.update(Text("".join(self._buffer)))
```

**Benefits:**
- 60-80% reduction in visual flicker
- Smoother user experience on slow terminals
- Better perceived performance

**Implementation Effort:** Medium (2-3 days)

---

#### 1.2 Theme System (MEDIUM PRIORITY)

**Problem:** No theming support - users can't customize colors or match their terminal setup.

**Solution:** Implement theme system with auto-detection and custom themes.

```python
# New: agent/themes.py
from dataclasses import dataclass
from typing import Dict

@dataclass
class Theme:
    """Terminal theme configuration."""
    name: str
    primary: str
    secondary: str
    success: str
    warning: str
    error: str
    info: str
    background: str  # "dark", "light", or "auto"
    
# Built-in themes
THEMES = {
    "default": Theme(
        name="Default",
        primary="cyan",
        secondary="blue",
        success="green",
        warning="yellow",
        error="red",
        info="white",
        background="auto"
    ),
    "github_dark": Theme(
        name="GitHub Dark",
        primary="#58a6ff",
        secondary="#79c0ff",
        success="#3fb950",
        warning="#d29922",
        error="#f85149",
        info="#c9d1d9",
        background="dark"
    ),
    "dracula": Theme(
        name="Dracula",
        primary="#8be9fd",
        secondary="#bd93f9",
        success="#50fa7b",
        warning="#f1fa8c",
        error="#ff5555",
        info="#f8f8f2",
        background="dark"
    ),
}

class ThemeManager:
    """Manage terminal themes with auto-detection."""
    
    def __init__(self):
        self.current_theme = THEMES["default"]
        self._auto_detect_background()
    
    def _auto_detect_background(self):
        """Detect terminal background color."""
        # Use ANSI escape codes to query background
        # Similar to Gemini CLI's implementation
        pass
    
    def apply(self, theme_name: str):
        """Apply a theme by name."""
        if theme_name in THEMES:
            self.current_theme = THEMES[theme_name]
            self._update_console_styles()
```

**Benefits:**
- Personalization for users
- Better accessibility (high contrast themes)
- Professional appearance

**Implementation Effort:** Medium (2-3 days)

---

#### 1.3 Sticky Input Prompt (MEDIUM PRIORITY)

**Problem:** Input prompt scrolls with content, losing context.

**Solution:** Implement fixed input area at bottom of screen using Rich Layout.

```python
# Enhancement to: agent/user_interface.py
from rich.layout import Layout

class FixedPromptUI:
    """Terminal UI with fixed input prompt at bottom."""
    
    def __init__(self, console: Console):
        self.console = console
        self.layout = Layout()
        self._setup_layout()
    
    def _setup_layout(self):
        """Create layout with fixed regions."""
        self.layout.split(
            Layout(name="header", size=3),      # Status bar
            Layout(name="main"),                 # Chat content
            Layout(name="input", size=5),       # Fixed input
        )
    
    def update_main(self, content: RenderableType):
        """Update main content area without affecting input."""
        self.layout["main"].update(content)
        self._refresh()
    
    def update_status(self, status: str):
        """Update status bar."""
        self.layout["header"].update(Panel(status, style="bold cyan"))
        self._refresh()
```

**Benefits:**
- Better context retention
- Professional appearance
- Matches industry standard (Gemini CLI)

**Implementation Effort:** Medium (3-4 days)

---

## 2. INTERACTIVE ELEMENTS GAPS

### ❌ Missing Features

| Feature | Gemini CLI | Qwen Code | RapidWebs | Priority |
|---------|------------|-----------|-----------|----------|
| **Mouse support** | ✅ Full (click, scroll) | ⚠️ Limited | ❌ None | **HIGH** |
| **Vim mode** | ✅ Full Vim keybindings | ❌ | ❌ | MEDIUM |
| **External editor** | ✅ Ctrl+X opens editor | ❌ | ❌ | MEDIUM |
| **Radio selection** | ✅ j/k navigation, 1-9 select | ❌ | ❌ | LOW |
| **Shell mode** | ✅ ! toggle interactive | ❌ | ❌ | LOW |
| **Advanced shortcuts** | ✅ 40+ shortcuts | ⚠️ ~15 | ⚠️ ~15 | MEDIUM |
| **Autocomplete** | ✅ Tab completion | ⚠️ Basic | ⚠️ Basic | LOW |
| **Multi-line paste** | ✅ Stable handling | ✅ Optimized | ⚠️ Basic | LOW |

### 🔧 Proposed Solutions

#### 2.1 Mouse Support (HIGH PRIORITY)

**Problem:** No mouse interaction - users can't click to scroll or select.

**Solution:** Enable mouse support in prompt_toolkit and Rich.

```python
# Enhancement to: rapidwebs_agent/cli.py
from prompt_toolkit.application import Application
from prompt_toolkit.mouse_events import MouseEventType

class MouseEnabledUI:
    """Add mouse support for scrolling and selection."""
    
    def __init__(self):
        self.mouse_enabled = True
        self._setup_mouse_bindings()
    
    def _setup_mouse_bindings(self):
        """Configure mouse event handlers."""
        @self.bindings.add('scroll_up')
        def _(event):
            self._scroll_history(-1)
        
        @self.bindings.add('scroll_down')
        def _(event):
            self._scroll_history(1)
        
        @self.bindings.add('click')
        def _(event):
            # Handle click on input prompt
            event.app.current_buffer.cursor_position = event.x
```

**Benefits:**
- Modern terminal experience
- Easier navigation for new users
- Matches GUI expectations

**Implementation Effort:** Medium (2-3 days)

---

#### 2.2 Vim Mode (MEDIUM PRIORITY)

**Problem:** No Vim keybindings - alienates Vim users.

**Solution:** Implement Vim mode for input navigation.

```python
# New: agent/vim_mode.py
class VimModeHandler:
    """Vim-style keybindings for input navigation."""
    
    MODES = {
        'normal': {
            'h': 'cursor_left',
            'l': 'cursor_right',
            'j': 'cursor_down',
            'k': 'cursor_up',
            'w': 'word_forward',
            'b': 'word_backward',
            '0': 'line_start',
            '$': 'line_end',
            'dd': 'delete_line',
            'yy': 'yank_line',
            'p': 'paste',
        },
        'insert': {
            # Standard input behavior
        }
    }
    
    def __init__(self):
        self.mode = 'insert'  # Start in insert mode
        self._setup_bindings()
    
    def _setup_bindings(self):
        """Configure Vim keybindings."""
        @self.bindings.add('escape')
        def _(event):
            """Enter normal mode."""
            self.mode = 'normal'
            self._update_status_bar()
        
        @self.bindings.add('i')
        def _(event):
            """Enter insert mode."""
            if self.mode == 'normal':
                self.mode = 'insert'
                self._update_status_bar()
```

**Benefits:**
- Attracts Vim power users
- Faster text navigation
- Industry standard feature

**Implementation Effort:** Medium (3-4 days)

---

#### 2.3 External Editor (MEDIUM PRIORITY)

**Problem:** Can't edit long prompts in external editor.

**Solution:** Add Ctrl+X to open system editor.

```python
# Enhancement to: rapidwebs_agent/cli.py
import subprocess
import tempfile

@bindings.add('c-x')
def open_external_editor(event):
    """Open current input in external editor."""
    current_text = event.app.current_buffer.text
    
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as f:
        f.write(current_text)
        temp_path = f.name
    
    # Open editor
    editor = os.environ.get('EDITOR', 'vim')
    subprocess.run([editor, temp_path])
    
    # Read back
    with open(temp_path, 'r') as f:
        new_text = f.read()
    
    event.app.current_buffer.text = new_text
    os.unlink(temp_path)
```

**Benefits:**
- Better for long prompts
- Users can use their preferred editor
- Matches Gemini CLI feature

**Implementation Effort:** Low (1 day)

---

## 3. CONVERSATION MANAGEMENT GAPS

### ❌ Missing Features

| Feature | Gemini CLI | Qwen Code | RapidWebs | Priority |
|---------|------------|-----------|-----------|----------|
| **Auto-save** | ✅ Every interaction | ⚠️ Manual | ⚠️ Manual | **HIGH** |
| **Session browser** | ✅ Interactive browser | ⚠️ Basic list | ⚠️ Basic list | **HIGH** |
| **Session search** | ✅ Filter by content | ❌ | ✅ Message search | MEDIUM |
| **Branching** | ❌ | ❌ | ❌ | MEDIUM |
| **Session delete** | ✅ Interactive delete | ❌ | ❌ | LOW |
| **Session config** | ✅ Retention settings | ❌ | ❌ | LOW |
| **Checkpointing** | ✅ Time-travel restore | ❌ | ❌ | MEDIUM |

### 🔧 Proposed Solutions

#### 3.1 Auto-Save System (HIGH PRIORITY)

**Problem:** Conversations only saved on exit - data loss on crash.

**Solution:** Implement background auto-save after each interaction.

```python
# Enhancement to: agent/agent.py
import threading
import asyncio

class AutoSaveManager:
    """Background auto-save for conversation history."""
    
    def __init__(self, conversation: ConversationHistory, interval: int = 30):
        self.conversation = conversation
        self.interval = interval  # Seconds between saves
        self._running = False
        self._save_pending = False
        self._thread = None
    
    def start(self):
        """Start auto-save background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._auto_save_loop, daemon=True)
        self._thread.start()
    
    def mark_dirty(self):
        """Mark conversation as changed (needs save)."""
        self._save_pending = True
    
    def _auto_save_loop(self):
        """Background loop that saves when dirty."""
        while self._running:
            if self._save_pending:
                self.conversation.save()
                self._save_pending = False
            time.sleep(self.interval)
    
    def stop(self):
        """Stop auto-save and final save."""
        self._running = False
        if self._save_pending:
            self.conversation.save()
```

**Benefits:**
- No data loss on crash
- Transparent to users
- Industry standard (Gemini CLI)

**Implementation Effort:** Low (1-2 days)

---

#### 3.2 Interactive Session Browser (HIGH PRIORITY)

**Problem:** Session list is static text - no interactive selection.

**Solution:** Implement interactive browser with search and selection.

```python
# Enhancement to: rapidwebs_agent/cli.py
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import radiolist_dialog

async def browse_sessions_interactive(self):
    """Interactive session browser with search."""
    conversations = self.agent.conversation.list_conversations()
    
    if not conversations:
        console.print("[yellow]No saved conversations found.[/yellow]")
        return
    
    # Create searchable list
    async def search_filter(text: str):
        """Filter conversations by search text."""
        return [
            (conv['id'], HTML(f"<b>{conv['id']}</b> - {conv['date']} ({conv['message_count']} msgs)"))
            for conv in conversations
            if text.lower() in conv['id'].lower() or text.lower() in conv.get('first_message', '').lower()
        ]
    
    # Show interactive dialog
    from prompt_toolkit.shortcuts import search_input_toolbar
    
    selected = await radiolist_dialog(
        title='Session Browser',
        text='Select a conversation to resume (type to search):',
        values=[(conv['id'], f"{conv['id']} - {conv['date']}") for conv in conversations[-20:]]
    ).run_async()
    
    if selected:
        self.agent.conversation.load_conversation(selected)
        console.print(f"[green]✓ Resumed: {selected}[/green]")
```

**Benefits:**
- Much better UX than text list
- Search-as-you-type
- Visual feedback

**Implementation Effort:** Medium (2-3 days)

---

#### 3.3 Conversation Branching (MEDIUM PRIORITY)

**Problem:** Can't fork conversations to explore alternatives.

**Solution:** Implement branching at any message point.

```python
# Enhancement to: agent/agent.py
class BranchableConversation(ConversationHistory):
    """Conversation with branching support."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.branches: Dict[str, List[Dict]] = {}
        self.current_branch = "main"
    
    def create_branch(self, from_message: int, branch_name: str) -> str:
        """Create a new branch from a specific message."""
        branch_id = f"{branch_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.branches[branch_id] = self.history[:from_message].copy()
        return branch_id
    
    def switch_branch(self, branch_id: str) -> bool:
        """Switch to a different branch."""
        if branch_id in self.branches:
            self.current_branch = branch_id
            self.history = self.branches[branch_id]
            return True
        return False
    
    def list_branches(self) -> List[Dict]:
        """List all branches with metadata."""
        return [
            {
                'id': branch_id,
                'messages': len(messages),
                'created': self._extract_date_from_branch(branch_id)
            }
            for branch_id, messages in self.branches.items()
        ]
```

**Benefits:**
- Explore alternative solutions
- Non-destructive experimentation
- Unique differentiator

**Implementation Effort:** Medium (3-4 days)

---

## 4. TOOL INTEGRATION GAPS

### ❌ Missing Features

| Feature | Gemini CLI | Qwen Code | RapidWebs | Priority |
|---------|------------|-----------|-----------|----------|
| **Diff viewer** | ✅ VS Code integration | ✅ Terminal diff | ❌ None | **HIGH** |
| **Checkpointing** | ✅ Time-travel restore | ❌ | ❌ | MEDIUM |
| **Tool descriptions** | ✅ Ctrl+T toggle | ❌ | ❌ | LOW |
| **Progress tracking** | ✅ Spinners + phrases | ✅ MCP progress | ⚠️ Basic | MEDIUM |
| **Error verbosity** | ✅ Configurable | ❌ | ❌ | LOW |

### 🔧 Proposed Solutions

#### 4.1 Side-by-Side Diff Viewer (HIGH PRIORITY)

**Problem:** No visual diff display for file changes.

**Solution:** Implement Rich-based diff viewer with color coding.

```python
# New: agent/ui_components.py - Add DiffViewer class
from rich.console import Group
from rich.panel import Panel
from difflib import unified_diff

class DiffViewer:
    """Side-by-side diff display for file changes."""
    
    def __init__(self, old_content: str, new_content: str, filename: str = ""):
        self.old_content = old_content
        self.new_content = new_content
        self.filename = filename
    
    def render(self, console: Console) -> None:
        """Render diff with syntax highlighting."""
        from rich.syntax import Syntax
        
        # Generate unified diff
        diff_lines = list(unified_diff(
            self.old_content.splitlines(keepends=True),
            self.new_content.splitlines(keepends=True),
            fromfile=f"a/{self.filename}",
            tofile=f"b/{self.filename}"
        ))
        
        # Color-code diff lines
        diff_text = []
        for line in diff_lines:
            if line.startswith('+') and not line.startswith('+++'):
                diff_text.append(f"[green]{line}[/green]")
            elif line.startswith('-') and not line.startswith('---'):
                diff_text.append(f"[red]{line}[/red]")
            elif line.startswith('@'):
                diff_text.append(f"[cyan]{line}[/cyan]")
            else:
                diff_text.append(f"[dim]{line}[/dim]")
        
        diff_display = "\n".join(diff_text)
        
        console.print(Panel(
            diff_display,
            title=f"📝 Changes to {self.filename}",
            border_style="blue"
        ))
    
    def render_side_by_side(self, console: Console) -> None:
        """Render side-by-side comparison (for small files)."""
        from rich.table import Table
        
        table = Table(show_header=True, show_lines=True)
        table.add_column("Before", style="red", width=60)
        table.add_column("After", style="green", width=60)
        
        # Implementation for side-by-side view
        # ...
        
        console.print(table)
```

**Benefits:**
- Clear visualization of changes
- Better approval decisions
- Industry standard feature

**Implementation Effort:** Medium (2-3 days)

---

#### 4.2 Enhanced Progress Tracking (MEDIUM PRIORITY)

**Problem:** Basic spinner doesn't show detailed progress.

**Solution:** Implement MCP-style progress with percentages and ETA.

```python
# Enhancement to: agent/user_interface.py
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, 
    BarColumn, TaskProgressColumn, TimeRemainingColumn
)

class ProgressTracker:
    """Enhanced progress tracking for long operations."""
    
    def __init__(self, console: Console):
        self.console = console
        self._progress = None
        self._task = None
    
    def start(self, description: str, total: int = 100):
        """Start progress tracking."""
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console
        )
        self._progress.start()
        self._task = self._progress.add_task(description, total=total)
    
    def update(self, completed: int, description: str = None):
        """Update progress."""
        if self._progress and self._task:
            self._progress.update(self._task, completed=completed)
            if description:
                self._progress.update(self._task, description=description)
    
    def stop(self):
        """Stop progress tracking."""
        if self._progress:
            self._progress.stop()
            self._progress = None
```

**Benefits:**
- Better user feedback
- Perceived performance improvement
- Matches Qwen Code MCP progress

**Implementation Effort:** Low (1-2 days)

---

## 5. PERFORMANCE OPTIMIZATION GAPS

### ❌ Missing Features

| Feature | Gemini CLI | Qwen Code | RapidWebs | Priority |
|---------|------------|-----------|-----------|----------|
| **Token streaming** | ✅ Real-time | ⚠️ Chunked | ❌ Full response | **HIGH** |
| **Lazy loading** | ⚠️ Not documented | ⚠️ Not documented | ❌ None | MEDIUM |
| **Cache indicators** | ⚠️ Stats only | ✅ Cached tokens | ⚠️ Stats only | LOW |
| **Resize handling** | ✅ No glitches | ⚠️ Basic | ⚠️ Basic | LOW |

### 🔧 Proposed Solutions

#### 5.1 True Token Streaming (HIGH PRIORITY)

**Problem:** Current implementation waits for full response before display.

**Solution:** Implement true token-by-token streaming from LLM.

```python
# Enhancement to: agent/llm_models.py
async def generate_stream(self, prompt: str, system_prompt: str = None) -> AsyncGenerator[str, None]:
    """Stream tokens from LLM in real-time."""
    # Check cache first
    cache_key = self._make_cache_key(prompt, system_prompt)
    cached = self.cache.get(cache_key)
    if cached:
        yield cached
        return
    
    # Stream from API
    full_response = []
    async for token in self._stream_from_api(prompt, system_prompt):
        full_response.append(token)
        yield token  # Yield immediately to UI
    
    # Cache full response
    self.cache.set(cache_key, "".join(full_response))

async def _stream_from_api(self, prompt: str, system_prompt: str) -> AsyncGenerator[str, None]:
    """Stream tokens from API endpoint."""
    # Implementation depends on LLM provider
    # Qwen Coder API supports streaming
    async with await self._get_client() as client:
        async with client.stream(
            "POST",
            self.config.api_endpoint,
            json={
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                "stream": True
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    yield data.get("content", "")
```

**Benefits:**
- Much better perceived performance
- Users can start reading immediately
- Industry standard (Gemini CLI, Qwen Code)

**Implementation Effort:** Medium (3-4 days)

---

## 6. UNIQUE INNOVATIONS WE CAN ADD

### 💡 Proposed Differentiators

These features don't exist in Gemini CLI or Qwen Code - they could make RapidWebs Agent stand out:

#### 6.1 AI-Powered Command Suggestions

**Idea:** Analyze conversation context and suggest relevant commands.

```python
class CommandSuggester:
    """AI-powered command suggestions based on context."""
    
    def suggest(self, conversation_history: List[Dict]) -> List[str]:
        """Suggest commands based on conversation state."""
        # Analyze last user message
        last_message = conversation_history[-1]['content']
        
        suggestions = []
        
        if "error" in last_message.lower():
            suggestions.append("/search error")
            suggestions.append("/memory create note debugging_session")
        
        if len(conversation_history) > 20:
            suggestions.append("/compress")
        
        if "project" in last_message.lower():
            suggestions.append("/project detect")
            suggestions.append("/project skeleton")
        
        return suggestions
```

**Display:** Show suggestions as subtle hint below input prompt.

---

#### 6.2 Session Analytics Dashboard

**Idea:** Real-time dashboard showing usage patterns and insights.

```python
class SessionAnalytics:
    """Real-time session analytics and insights."""
    
    def generate_dashboard(self) -> str:
        """Generate analytics dashboard."""
        return f"""
╔═══════════════════════════════════════════════════════╗
║  📊 Session Analytics Dashboard                       ║
╠═══════════════════════════════════════════════════════╣
║  Messages: 47 | Tokens: 12,453 | Cost: $0.023        ║
║                                                       ║
║  Most Used Tools:                                     ║
║    • read_file (23x)  • write_file (12x)             ║
║    • run_command (8x)  • search (4x)                 ║
║                                                       ║
║  Productivity Insights:                               ║
║    ✓ You're 23% faster than last session             ║
║    ⚠ Consider /compress to save tokens               ║
║    💡 Try /mode yolo for faster iteration            ║
╚═══════════════════════════════════════════════════════╝
"""
```

**Display:** Available via `/dashboard` command or auto-show after long sessions.

---

#### 6.3 Smart Context Preloading

**Idea:** Automatically load relevant files based on conversation.

```python
class SmartContextLoader:
    """Automatically preload relevant files based on context."""
    
    def preload(self, user_message: str, workspace: Path) -> List[Path]:
        """Preload files likely relevant to the task."""
        relevant_files = []
        
        # Detect file references
        file_pattern = r'[\w./-]+\.(py|js|ts|md|json|yaml|yml)'
        for match in re.finditer(file_pattern, user_message):
            file_path = workspace / match.group()
            if file_path.exists():
                relevant_files.append(file_path)
        
        # Detect project patterns
        if "test" in user_message.lower():
            relevant_files.extend(workspace.glob("**/test_*.py"))
        
        if "api" in user_message.lower():
            relevant_files.extend(workspace.glob("**/api/**/*.py"))
        
        return relevant_files[:10]  # Limit to 10 files
```

**Benefit:** Reduces manual file references, feels "smarter" than competitors.

---

#### 6.4 Voice Input Support (Experimental)

**Idea:** Voice-to-text input for hands-free operation.

```python
class VoiceInputHandler:
    """Voice input support using speech recognition."""
    
    def __init__(self):
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.available = True
        except ImportError:
            self.available = False
    
    def listen(self) -> Optional[str]:
        """Listen for voice input."""
        if not self.available:
            return None
        
        with sr.Microphone() as source:
            audio = self.recognizer.listen(source)
            
        try:
            return self.recognizer.recognize_google(audio)
        except:
            return None
```

**Activation:** `/voice` command or Ctrl+Shift+V shortcut.

---

## 7. IMPLEMENTATION ROADMAP

### Phase 1: Critical Foundations (Week 1-2)

| Feature | Effort | Impact | Priority |
|---------|--------|--------|----------|
| **Incremental rendering** | 2-3 days | High | P0 |
| **Token streaming** | 3-4 days | High | P0 |
| **Auto-save system** | 1-2 days | High | P0 |
| **Diff viewer** | 2-3 days | High | P0 |

**Total:** 8-12 days

---

### Phase 2: Interactive Enhancements (Week 3-4)

| Feature | Effort | Impact | Priority |
|---------|--------|--------|----------|
| **Mouse support** | 2-3 days | Medium | P1 |
| **External editor** | 1 day | Medium | P1 |
| **Session browser** | 2-3 days | High | P1 |
| **Theme system** | 2-3 days | Medium | P1 |

**Total:** 7-10 days

---

### Phase 3: Advanced Features (Week 5-6)

| Feature | Effort | Impact | Priority |
|---------|--------|--------|----------|
| **Vim mode** | 3-4 days | Medium | P2 |
| **Conversation branching** | 3-4 days | Medium | P2 |
| **Progress tracking** | 1-2 days | Medium | P2 |
| **Sticky headers/footers** | 3-4 days | Medium | P2 |

**Total:** 10-14 days

---

### Phase 4: Innovation & Differentiation (Week 7-8)

| Feature | Effort | Impact | Priority |
|---------|--------|--------|----------|
| **Command suggestions** | 2-3 days | High | P3 |
| **Analytics dashboard** | 2-3 days | Medium | P3 |
| **Smart context preload** | 2-3 days | High | P3 |
| **Voice input** | 3-4 days | Low | P4 |

**Total:** 9-13 days

---

## 8. SUMMARY: TOP 10 RECOMMENDATIONS

| Rank | Feature | Effort | Impact | Why |
|------|---------|--------|--------|-----|
| 1 | **Token streaming** | Medium | High | Industry standard, huge UX improvement |
| 2 | **Incremental rendering** | Medium | High | Eliminates flicker, professional feel |
| 3 | **Auto-save** | Low | High | Prevents data loss, expected feature |
| 4 | **Diff viewer** | Medium | High | Essential for code review workflow |
| 5 | **Session browser** | Medium | High | Much better than text list |
| 6 | **Mouse support** | Medium | Medium | Modern terminal expectation |
| 7 | **Theme system** | Medium | Medium | Personalization, accessibility |
| 8 | **Command suggestions** | Medium | High | Unique differentiator |
| 9 | **Conversation branching** | Medium | Medium | Unique differentiator |
| 10 | **External editor** | Low | Medium | Power user feature |

---

## 9. CONCLUSION

RapidWebs Agent has a **solid foundation** but needs significant TUI improvements to compete with Gemini CLI and Qwen Code CLI. The **critical gaps** are:

1. **No streaming** - Users wait for full response
2. **No auto-save** - Risk of data loss
3. **Basic visual polish** - Flicker, no themes
4. **Limited interactivity** - No mouse, few shortcuts

By implementing the **Phase 1 features** (streaming, incremental rendering, auto-save, diff viewer), we can achieve **80% parity** with industry leaders in **2 weeks**.

The **innovation features** (command suggestions, analytics, smart context) can make us **better than competitors** in specific areas, giving users reasons to choose RapidWebs Agent over established alternatives.

---

**Next Steps:**
1. Review and prioritize features with team
2. Start Phase 1 implementation
3. Gather user feedback after each phase
4. Iterate based on usage patterns
