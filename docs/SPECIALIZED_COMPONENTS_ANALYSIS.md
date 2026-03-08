# rw-agent Specialized Components Analysis

**Date:** March 7, 2026  
**Analysis Type:** Feature Implementation Audit  
**Status:** Complete  

---

## Executive Summary

This document analyzes rw-agent's implementation of three critical specialized components from the modern agentic CLI architecture pattern:

1. **Enhanced Code Parser** - Custom parser for model output, partial code block merging
2. **Model Context Protocol (MCP) Emulation** - Native implementation of standard protocol tools
3. **Session & Context Manager** - `/compress`, conversation persistence, repo mapping

### Overall Assessment

| Component | Implementation Status | Quality | Gap |
|-----------|---------------------|---------|-----|
| **Enhanced Code Parser** | ❌ Not Implemented | N/A | 🔴 Critical |
| **MCP Emulation** | ⚠️ Partial (SkillManager) | 🟢 Good | 🟡 Medium |
| **Session Manager** | ⚠️ Partial (save-only) | 🟡 Basic | 🔴 High |
| **Repo Mapping** | ⚠️ Partial (explore) | 🟡 Basic | 🟡 Medium |

---

## 1. Enhanced Code Parser

### Standard Implementation (Qwen Code CLI)

**Purpose:** Custom parser optimized for model's specific output format that:
- Correctly merges "lazy" or partial code blocks into existing files
- Preserves syntax without breaking
- Handles incremental edits safely

**Typical Implementation:**
```typescript
// packages/core/src/code-parser.ts (inferred)
class EnhancedCodeParser {
  /**
   * Parse LLM output for code blocks with intelligent merging
   */
  parseAndMerge(output: string, existingFile: string): string {
    // 1. Extract code blocks from LLM response
    const blocks = this.extractCodeBlocks(output);
    
    // 2. Parse existing file AST
    const ast = this.parseFile(existingFile);
    
    // 3. For each block, determine merge strategy:
    //    - Full file replacement (if marker present)
    //    - Function/class replacement (if signature matches)
    //    - Line-range replacement (if @@ markers present)
    //    - Append (if indicated)
    for (const block of blocks) {
      const strategy = this.determineMergeStrategy(block, ast);
      ast = this.applyMerge(ast, block, strategy);
    }
    
    // 4. Generate merged code with preserved formatting
    return this.generate(ast);
  }
  
  /**
   * Extract code blocks with context markers
   */
  extractCodeBlocks(output: string): CodeBlock[] {
    // Support multiple formats:
    // 1. Markdown: ```python ... ```
    // 2. SEARCH/REPLACE blocks
    // 3. @@ line-range markers
    // 4. Function/class signature markers
  }
  
  /**
   * Determine how to merge a code block
   */
  determineMergeStrategy(block: CodeBlock, ast: AST): MergeStrategy {
    // Check for explicit markers first
    if (block.hasMarker('FULL_FILE')) return 'REPLACE_ALL';
    if (block.hasMarker('@@ -start,+end @@')) return 'REPLACE_RANGE';
    
    // Check if block matches existing function/class
    const match = this.findMatchingSymbol(block.signature, ast);
    if (match) return 'REPLACE_SYMBOL';
    
    // Default to append or reject
    return block.isAppend ? 'APPEND' : 'REJECT';
  }
}
```

**Key Features:**
- AST-based parsing for accuracy
- Multiple merge strategies (full file, range, symbol, append)
- Context markers for explicit control
- Syntax validation before applying changes
- Rollback on parse errors

---

### rw-agent Implementation

**Status:** ❌ **NOT IMPLEMENTED**

**Current Approach:**
```python
# agent/skills_manager.py - FilesystemSkill._execute_write()
async def _execute_write(self, resolved_path: Path, content: Optional[str] = None) -> Dict[str, Any]:
    """Execute write operation with non-blocking I/O."""
    
    def write_file():
        # Read original content for diff
        original_content = ""
        if resolved_path.exists():
            with open(resolved_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        
        # Generate diff before writing
        diff_output = ""
        if original_content and original_content != content:
            import difflib
            diff = difflib.unified_diff(
                original_content.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f'a/{resolved_path.name}',
                tofile=f'b/{resolved_path.name}'
            )
            diff_output = ''.join(diff)
        
        # Write full content (REPLACE ALL)
        with open(resolved_path, 'w', encoding='utf-8') as f:
            f.write(content or '')
        
        return diff_output, original_content != content
```

**What rw-agent Does:**
- ✅ Full file replacement only
- ✅ Generates diff for display
- ✅ Non-blocking I/O (asyncio.to_thread)
- ✅ Error handling

**What rw-agent DOESN'T Do:**
- ❌ No partial code block parsing
- ❌ No AST-based merging
- ❌ No function/class-level replacement
- ❌ No line-range replacement
- ❌ No syntax validation before write
- ❌ No rollback on errors
- ❌ No context marker support

**How SubAgents Write Code:**
```python
# agent/subagents/code_agent.py
async def _write_file(self, path: str, content: str):
    """Write file content."""
    # Direct full-file write via SkillManager
    result = await self.skill_manager.execute(
        'fs',
        operation='write',
        path=path,
        content=content
    )
    return result
```

**Risk Assessment:**

| Risk | Severity | Current Mitigation |
|------|----------|-------------------|
| Syntax errors from partial writes | 🔴 High | LLM instructed to write full files |
| Broken imports from incomplete edits | 🟡 Medium | Code review before commit |
| Lost code from failed merges | 🟡 Medium | Full file replacement (safer) |
| No validation before write | 🔴 High | None |

---

### Gap Analysis & Recommendations

| Feature | Standard | rw-agent | Priority |
|---------|----------|----------|----------|
| AST-based parsing | ✅ Yes | ❌ No | 🔴 High |
| Partial block merging | ✅ Yes | ❌ No | 🔴 High |
| Function-level replacement | ✅ Yes | ❌ No | 🟡 Medium |
| Line-range replacement | ✅ Yes | ❌ No | 🟡 Medium |
| Syntax validation | ✅ Yes | ❌ No | 🔴 High |
| Rollback on error | ✅ Yes | ❌ No | 🟡 Medium |
| Context markers | ✅ Yes | ❌ No | 🟢 Low |

**Recommendation:** Implement basic code parser with:
1. **Syntax validation** before write (use `ast.parse()` for Python)
2. **Function/class-level replacement** using existing `ASTSemanticChunker`
3. **Rollback mechanism** on parse errors

**Implementation Plan:**

```python
# New: agent/code_parser.py
class EnhancedCodeParser:
    """Parse and merge LLM code output safely."""
    
    def validate_syntax(self, content: str, language: str = 'python') -> Tuple[bool, str]:
        """Validate code syntax before applying."""
        if language == 'python':
            try:
                ast.parse(content)
                return True, ""
            except SyntaxError as e:
                return False, f"Syntax error at line {e.lineno}: {e.msg}"
        # Add other languages as needed
        return True, ""
    
    def extract_code_blocks(self, output: str) -> List[CodeBlock]:
        """Extract code blocks from LLM output."""
        blocks = []
        # Extract ```language ... ``` blocks
        # Extract SEARCH/REPLACE blocks
        # Extract @@ range markers
        return blocks
    
    def merge_code(self, existing: str, new_block: CodeBlock, 
                   language: str = 'python') -> Tuple[str, bool]:
        """
        Merge new code block into existing file.
        
        Returns:
            (merged_content, success)
        """
        # 1. Validate syntax
        valid, error = self.validate_syntax(new_block.content, language)
        if not valid:
            return existing, False
        
        # 2. Determine merge strategy
        strategy = self._determine_strategy(new_block, existing)
        
        # 3. Apply merge
        try:
            if strategy == 'REPLACE_ALL':
                return new_block.content, True
            elif strategy == 'REPLACE_FUNCTION':
                return self._replace_function(existing, new_block), True
            # ... other strategies
        except Exception as e:
            return existing, False
        
        return existing, False
```

**Files to Create:**
- `agent/code_parser.py` - Enhanced code parser
- `tests/test_code_parser.py` - Parser tests

**Files to Modify:**
- `agent/skills_manager.py` - Use parser in `_execute_write()`
- `agent/subagents/code_agent.py` - Use parser for refactoring

**Effort:** 3-5 days

---

## 2. Model Context Protocol (MCP) Emulation

### Standard Implementation (Qwen Code CLI)

**Purpose:** Native implementation of MCP standard for tool interoperability.

**MCP Tools:**
| Tool | Purpose | Implementation |
|------|---------|----------------|
| `filesystem` | File operations | MCP server (`@modelcontextprotocol/server-filesystem`) |
| `memory` | Persistent context | MCP server (`@modelcontextprotocol/server-memory`) |
| `fetch` | Web content | MCP server (`@modelcontextprotocol/server-fetch`) |
| `brave-search` | Web search | MCP server (`@modelcontextprotocol/server-brave-search`) |
| `sequential-thinking` | Complex reasoning | MCP server |

**Architecture:**
```
┌─────────────────┐         ┌──────────────────┐
│  Qwen Code CLI  │◄────MCP─►│  MCP Servers     │
│  (TypeScript)   │  JSON   │  (filesystem,    │
│                 │  RPC    │   memory, etc.)  │
└─────────────────┘         └──────────────────┘
```

**Benefits:**
- Standardized protocol
- Hot-reloadable servers
- Language-agnostic
- Tool discovery automatic

---

### rw-agent Implementation

**Status:** ⚠️ **PARTIAL (SkillManager instead of MCP)**

**Architecture:**
```
┌─────────────────┐         ┌──────────────────┐
│  Python Agent   │◄───────►│  SkillManager    │
│  (cli.py)       │  Direct │  (NO MCP!)       │
└─────────────────┘         └──────────────────┘
```

**Implementation:**
```python
# agent/skills_manager.py
class SkillManager:
    """Execute tools via direct function calls (NOT MCP)."""
    
    def __init__(self, config: Config):
        self.skills = {}
        self._register_builtin_skills()
    
    def _register_builtin_skills(self):
        """Register all built-in skills."""
        self.skills['terminal'] = TerminalExecutorSkill(self.config)
        self.skills['fs'] = FilesystemSkill(self.config)
        self.skills['web'] = WebScraperSkill(self.config)
        self.skills['search'] = SearchSkill(self.config)
        self.skills['code_tools'] = CodeToolsSkill(self.config)
        self.skills['subagents'] = SubAgentsSkill(self.config)
        if GIT_SKILL_AVAILABLE:
            self.skills['git'] = GitSkill(self.config)
    
    async def execute(self, skill_name: str, **kwargs) -> Dict[str, Any]:
        """Execute skill with given parameters."""
        if skill_name not in self.skills:
            raise ValueError(f"Unknown skill: {skill_name}")
        
        skill = self.skills[skill_name]
        return await skill.execute(**kwargs)
```

**Available Skills (MCP-equivalent):**

| Skill | MCP Equivalent | Status | Quality |
|-------|---------------|--------|---------|
| `fs` | `filesystem` | ✅ Complete | 🟢 Excellent |
| `terminal` | (none directly) | ✅ Complete | 🟢 Excellent |
| `web` | `fetch` | ✅ Complete | 🟢 Excellent |
| `search` | (custom) | ✅ Complete | 🟢 Excellent |
| `code_tools` | (custom) | ✅ Complete | 🟢 Excellent |
| `subagents` | (custom) | ✅ Complete | 🟢 Excellent |
| `git` | (custom) | ✅ Complete | 🟢 Excellent |
| `memory` | `memory` | ❌ Missing | 🔴 Gap |

**Skill Quality Assessment:**

#### **FilesystemSkill** ✅ Excellent
```python
class FilesystemSkill(SkillBase):
    """Filesystem operations with timeout protection."""
    
    # Operations: read, list, explore, write, delete
    
    # Features:
    - Path validation (sanitize_path, is_safe_path)
    - Timeout protection (asyncio.wait_for)
    - Non-blocking I/O (asyncio.to_thread)
    - Diff generation for writes
    - Depth-limited explore (max 2 levels)
```

**Quality:** Better than MCP filesystem (has timeout, diff generation)

#### **WebScraperSkill** ✅ Excellent
```python
class WebScraperSkill(SkillBase):
    """Web scraping with SSRF protection."""
    
    # Features:
    - SSRF protection (blocks localhost, private IPs)
    - DNS rebinding protection
    - BeautifulSoup parsing
    - Text extraction
    - Timeout protection
```

**Quality:** Better than MCP fetch (has SSRF protection)

#### **SearchSkill** ✅ Excellent
```python
class SearchSkill(SkillBase):
    """Codebase search (grep, file search)."""
    
    # Operations: grep, find_files
    
    # Features:
    - Regex pattern matching
    - File pattern filtering
    - Timeout protection (30s)
    - Max results limiting (100)
    - Hidden directory exclusion
```

**Quality:** Equivalent to custom MCP server

#### **CodeToolsSkill** ✅ Excellent
```python
class CodeToolsSkill(SkillBase):
    """Code linting and formatting."""
    
    # Operations: lint, format, fix, install
    
    # Features:
    - Multi-language (Python, JS/TS, Go, Rust, SQL, Shell)
    - Auto-detect language
    - Tool availability checking
    - Auto-install Tier 1 tools
    - Temp file handling
```

**Quality:** Better than standard (auto-install, multi-language)

#### **SubAgentsSkill** ✅ Unique
```python
class SubAgentsSkill(SkillBase):
    """Parallel task delegation to specialized agents."""
    
    # Types: code, test, docs, research, security
    
    # Features:
    - Parallel execution (up to 3 concurrent)
    - Result aggregation
    - Conflict detection
    - Token budget enforcement
```

**Quality:** Unique to rw-agent (not in MCP)

---

### Gap Analysis & Recommendations

| Feature | MCP Standard | rw-agent SkillManager | Verdict |
|---------|-------------|----------------------|---------|
| **Protocol** | JSON-RPC over stdio | Direct function calls | 🟡 Different but valid |
| **Tool Discovery** | Automatic (query server) | Manual registration | 🟡 Manual is fine for built-ins |
| **Hot Reload** | ✅ Yes | ❌ No | 🟡 Optional |
| **Language Agnostic** | ✅ Yes | ❌ Python only | ✅ Python-only is fine |
| **External Servers** | ✅ Yes | ❌ No | 🟡 Could add plugin support |
| **Performance** | ⚠️ Subprocess overhead | ✅ Direct calls (faster) | ✅ Better |
| **Security** | Sandboxed processes | Command whitelist | ✅ Both secure |
| **Tool Count** | 4-5 standard | 7 skills | ✅ More tools |

**Recommendation:** **Keep SkillManager architecture** - it's faster and simpler for our use case. However, consider:

1. **Add `memory` skill** - Persistent context storage (like MCP memory server)
2. **Add plugin system** - Allow external tool registration (Tier 2 feature)
3. **Optional MCP client** - For compatibility with external MCP servers (future)

**Implementation Plan:**

```python
# New: agent/skills/memory_skill.py
class MemorySkill(SkillBase):
    """Persistent memory and context storage."""
    
    def __init__(self, config: Any):
        super().__init__(config, 'memory')
        self.storage_path = Path.home() / '.rapidwebs-agent' / 'memory.db'
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database."""
        # Create entities and relations tables
        pass
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute memory operation."""
        if action == 'create_entity':
            return self._create_entity(kwargs)
        elif action == 'create_relation':
            return self._create_relation(kwargs)
        elif action == 'search':
            return self._search(kwargs)
        # ... other operations
```

**Files to Create:**
- `agent/skills/memory_skill.py` - Memory skill implementation

**Files to Modify:**
- `agent/skills_manager.py` - Register memory skill

**Effort:** 2-3 days

---

## 3. Session & Context Manager

### Standard Implementation (Qwen Code CLI)

**Features:**
- `/compress` - Summarize long conversations into dense briefing
- `/history` - List all saved conversations
- `/resume <id>` - Resume old conversation
- `/export [format]` - Export as MD/JSON/PDF
- `/search <query>` - Search conversation history
- Repo mapping - Auto-generate project skeleton

**Implementation:**
```typescript
// packages/core/src/conversation-manager.ts (inferred)
class ConversationManager {
  async compressConversation(sessionId: string): Promise<void> {
    // 1. Load full conversation
    const messages = await this.loadConversation(sessionId);
    
    // 2. Use LLM to summarize
    const summary = await this.llm.generate(`
      Summarize this conversation into a dense technical briefing.
      Preserve:
      - Key decisions made
      - Code snippets and file paths
      - Action items and TODOs
      - Problem context and solution approach
      
      Conversation:
      ${messages.map(m => `${m.role}: ${m.content}`).join('\n')}
    `);
    
    // 3. Replace detailed messages with summary
    await this.saveConversation(sessionId, [{
      role: 'system',
      content: `Previous conversation summary:\n${summary}`
    }]);
  }
  
  async listConversations(): Promise<ConversationSummary[]> {
    // Query all saved conversations
    // Return metadata (date, model, token count, first message)
  }
  
  async resumeConversation(sessionId: string): Promise<Message[]> {
    // Load conversation from storage
    // Restore context window
  }
}
```

**Repo Mapping:**
```typescript
// packages/core/src/repo-mapper.ts (inferred)
class RepoMapper {
  async generateSkeleton(root: string): Promise<ProjectSkeleton> {
    // 1. Scan directory structure (depth-limited)
    // 2. Identify key files (README, package.json, etc.)
    // 3. Detect project type (Python, Node, Go, etc.)
    // 4. Generate skeleton with:
    //    - Directory tree
    //    - Key file descriptions
    //    - Dependency graph
    return skeleton;
  }
}
```

---

### rw-agent Implementation

**Status:** ⚠️ **PARTIAL (save-only, no compress/resume/search)**

#### **ConversationHistory Class**

**File:** `agent/agent.py` (lines 56-115)

```python
class ConversationHistory:
    """Persistent conversation history management."""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or self._default_storage_path()
        self.history: List[Dict[str, str]] = []
        self._load()  # Currently empty!
    
    def _default_storage_path(self) -> str:
        storage_dir = Path.home() / '.local' / 'share' / 'rapidwebs-agent' / 'conversations'
        storage_dir.mkdir(parents=True, exist_ok=True)
        return str(storage_dir / f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    def _load(self):
        """Load existing conversations."""
        pass  # ❌ Start fresh for now - NOT IMPLEMENTED!
    
    def save(self):
        """Save conversation history to disk."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception:
            pass  # ❌ Silently fail - NOT IDEAL!
    
    def add(self, role: str, content: str, **kwargs):
        """Add message to history."""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        self.history.append(message)
        
        # Auto-save every 10 messages
        if len(self.history) % 10 == 0:
            self.save()
    
    def get_recent(self, n: int = 5) -> List[Dict[str, str]]:
        """Get n most recent messages."""
        return self.history[-n:]
    
    def clear(self):
        """Clear conversation history."""
        self.history.clear()
    
    def export(self, format: str = 'markdown') -> str:
        """Export conversation in specified format."""
        if format == 'markdown':
            lines = ["# Conversation Log\n"]
            for msg in self.history:
                role = "User" if msg['role'] == 'user' else "Agent"
                lines.append(f"## {role}\n\n{msg['content']}\n")
            return '\n'.join(lines)
        elif format == 'json':
            return json.dumps(self.history, indent=2)
        return str(self.history)
```

**What Works:**
- ✅ Auto-save every 10 messages
- ✅ Export to markdown/JSON
- ✅ Storage path management

**What DOESN'T Work:**
- ❌ `_load()` is empty - doesn't load old conversations
- ❌ No conversation listing (`/history`)
- ❌ No resume functionality (`/resume <id>`)
- ❌ No compression (`/compress`)
- ❌ No search (`/search <query>`)
- ❌ Silent failures on save errors

---

#### **CLI Commands**

**File:** `rapidwebs_agent/cli.py` (lines 623-770)

**Available Commands:**
| Command | Status | Implementation |
|---------|--------|----------------|
| `/clear` | ✅ Working | Clears in-memory history |
| `/stats` | ✅ Working | Shows token usage |
| `/export` | ❌ Missing | Not implemented |
| `/history` | ❌ Missing | Not implemented |
| `/resume` | ❌ Missing | Not implemented |
| `/compress` | ❌ Missing | Not implemented |
| `/search` | ❌ Missing | Not implemented |

**Current Implementation:**
```python
elif cmd == '/clear':
    if self.agent:
        self.agent.conversation.clear()
        console.print("[green]Conversation cleared.[/green]")
```

**Missing Commands:**
```python
# NOT IMPLEMENTED:
elif cmd == '/history':
    # List all saved conversations
    pass

elif cmd == '/resume':
    # Resume conversation by ID
    pass

elif cmd == '/compress':
    # Summarize conversation using LLM
    pass

elif cmd == '/search':
    # Search conversation history
    pass

elif cmd == '/export':
    # Export conversation to file
    pass
```

---

#### **Repo Mapping / Project Skeleton**

**Status:** ⚠️ **PARTIAL (directory explore only)**

**Current Implementation:**
```python
# agent/skills_manager.py - FilesystemSkill._execute_explore()
async def _execute_explore(self, resolved_path: Path) -> Dict[str, Any]:
    """Execute explore operation with depth limiting."""
    if not resolved_path.is_dir():
        return {'success': False, 'error': 'Path is not a directory'}
    
    max_depth = 2
    result = {'success': True, 'operation': 'explore', 'path': str(resolved_path), 'structure': []}
    
    def scan_dir(dir_path: Path, depth: int = 0):
        if depth > max_depth:
            return
        for item in sorted(dir_path.iterdir(), key=lambda x: x.name.lower()):
            if item.name.startswith('.'):
                continue
            if item.is_file():
                result['structure'].append({
                    'path': str(item),
                    'type': 'file',
                    'size': item.stat().st_size,
                    'extension': item.suffix
                })
            elif item.is_dir():
                result['structure'].append({
                    'path': str(item),
                    'type': 'directory'
                })
                scan_dir(item, depth + 1)
    
    scan_dir(resolved_path)
    result['file_count'] = len([x for x in result['structure'] if x['type'] == 'file'])
    result['dir_count'] = len([x for x in result['structure'] if x['type'] == 'directory'])
    return result
```

**What Works:**
- ✅ Directory tree scanning (depth 2)
- ✅ File counting
- ✅ Hidden file exclusion
- ✅ Sorted output

**What's Missing:**
- ❌ No project type detection (Python, Node, Go, etc.)
- ❌ No key file identification (README, package.json, etc.)
- ❌ No dependency graph
- ❌ No intelligent summarization
- ❌ No "skeleton" view (just raw file list)

**Related Feature: `suggest_related_files()`** ✅ Good

```python
# agent/context_manager.py
def suggest_related_files(current_file: Path, workspace: Optional[Path] = None,
                          max_suggestions: int = 5) -> List[Path]:
    """Suggest files related to current file."""
    
    # 1. Test files (highest priority)
    test_patterns = [
        parent / f"test_{stem}{suffix}",
        workspace / "tests" / f"test_{stem}{suffix}",
    ]
    
    # 2. Same directory siblings
    # 3. Files with same name in different directories
    
    return suggestions[:max_suggestions]
```

**Quality:** Good heuristic-based suggestions

---

### Gap Analysis & Recommendations

| Feature | Standard | rw-agent | Priority |
|---------|----------|----------|----------|
| **Conversation Persistence** | ✅ Full CRUD | ⚠️ Save-only | 🔴 High |
| **Conversation Listing** | ✅ `/history` | ❌ Missing | 🔴 High |
| **Resume Conversations** | ✅ `/resume` | ❌ Missing | 🔴 High |
| **Compression** | ✅ `/compress` | ❌ Missing | 🟡 Medium |
| **Search** | ✅ `/search` | ❌ Missing | 🟡 Medium |
| **Export** | ✅ MD/JSON/PDF | ⚠️ MD/JSON only | 🟢 Low |
| **Repo Mapping** | ✅ Intelligent | ⚠️ Basic explore | 🟡 Medium |
| **Project Type Detection** | ✅ Yes | ❌ No | 🟡 Medium |

**Recommendation:** Implement conversation management features (Tier 1.2 in roadmap)

**Implementation Plan:**

```python
# Enhanced: agent/agent.py - ConversationHistory
class ConversationHistory:
    def _load(self):
        """Load existing conversations."""
        # Find all conversation files
        storage_dir = Path(self.storage_path).parent
        conversations = []
        for conv_file in storage_dir.glob('conversation_*.json'):
            try:
                with open(conv_file, 'r') as f:
                    data = json.load(f)
                    conversations.append({
                        'id': conv_file.stem,
                        'path': str(conv_file),
                        'date': self._extract_date(conv_file.name),
                        'message_count': len(data),
                        'first_message': data[0]['content'][:100] if data else ''
                    })
            except Exception:
                continue
        
        # Store for /history command
        self._available_conversations = conversations
    
    def list_conversations(self) -> List[Dict]:
        """List all saved conversations."""
        return self._available_conversations
    
    def resume(self, conversation_id: str) -> bool:
        """Resume a specific conversation."""
        for conv in self._available_conversations:
            if conv['id'] == conversation_id:
                try:
                    with open(conv['path'], 'r') as f:
                        self.history = json.load(f)
                    return True
                except Exception:
                    return False
        return False
    
    async def compress(self, llm_callback) -> str:
        """Compress conversation using LLM summarization."""
        if len(self.history) < 5:
            return "Conversation too short to compress"
        
        # Format conversation for LLM
        conversation_text = '\n'.join([
            f"{msg['role']}: {msg['content']}" for msg in self.history[-20:]
        ])
        
        # Request summary
        summary_prompt = f"""
        Summarize this conversation into a dense technical briefing.
        Preserve:
        - Key decisions made
        - Code snippets and file paths
        - Action items and TODOs
        - Problem context and solution approach
        
        Conversation:
        {conversation_text}
        """
        
        summary, _ = await llm_callback(summary_prompt)
        
        # Replace with summary
        self.history = [{
            'role': 'system',
            'content': f"Previous conversation summary:\n{summary}",
            'timestamp': datetime.now().isoformat()
        }]
        
        return summary
    
    def search(self, query: str) -> List[Dict]:
        """Search conversation history."""
        results = []
        for i, msg in enumerate(self.history):
            if query.lower() in msg['content'].lower():
                results.append({
                    'index': i,
                    'role': msg['role'],
                    'content': msg['content'][:200],
                    'timestamp': msg['timestamp']
                })
        return results
```

**CLI Commands to Add:**
```python
# rapidwebs_agent/cli.py
elif cmd == '/history':
    conversations = self.agent.conversation.list_conversations()
    # Display list with selection
    
elif cmd == '/resume':
    if len(parts) < 2:
        console.print("Usage: /resume <conversation_id>")
    else:
        success = self.agent.conversation.resume(parts[1])
        # Show result
    
elif cmd == '/compress':
    summary = await self.agent.conversation.compress(self.agent.model_manager.generate)
    console.print(f"Summary:\n{summary}")
    
elif cmd == '/search':
    if len(parts) < 2:
        console.print("Usage: /search <query>")
    else:
        results = self.agent.conversation.search(parts[1])
        # Display results
    
elif cmd == '/export':
    format = parts[1] if len(parts) > 1 else 'markdown'
    content = self.agent.conversation.export(format)
    # Save to file
```

**Files to Modify:**
- `agent/agent.py` - Enhance `ConversationHistory` class
- `rapidwebs_agent/cli.py` - Add `/history`, `/resume`, `/compress`, `/search`, `/export` commands

**Effort:** 3-4 days (Tier 1.2 in roadmap)

---

## 4. Summary & Priority Matrix

### Implementation Status

| Component | Status | Quality | Priority |
|-----------|--------|---------|----------|
| **Enhanced Code Parser** | ❌ Not Implemented | N/A | 🔴 High |
| **MCP Emulation** | ⚠️ Partial (SkillManager) | 🟢 Excellent | 🟡 Medium |
| **Session Manager** | ⚠️ Partial (save-only) | 🟡 Basic | 🔴 High |
| **Repo Mapping** | ⚠️ Partial (explore) | 🟡 Basic | 🟡 Medium |

### Priority Actions

**Immediate (This Week):**
1. ⭐ **Add syntax validation** to file writes (prevent broken code)
2. ⭐ **Implement `_load()`** for conversation persistence
3. ⭐ **Add `/history` and `/resume` commands**

**Next Month:**
4. ⭐ **Implement `/compress`** using LLM summarization
5. ⭐ **Add conversation search** (`/search` command)
6. ⭐ **Enhance repo mapping** with project type detection

**Next Quarter:**
7. 🟡 **Implement function-level code merging**
8. 🟡 **Add memory skill** (MCP-equivalent)
9. 🟡 **Add plugin system** for external tools

---

## 5. Files to Create/Modify

### New Files
```
agent/code_parser.py              # Enhanced code parser
tests/test_code_parser.py         # Parser tests
agent/skills/memory_skill.py      # Memory skill (MCP-equivalent)
```

### Modified Files
```
agent/agent.py                    # Enhance ConversationHistory
agent/skills_manager.py           # Use code parser, add memory skill
rapidwebs_agent/cli.py            # Add /history, /resume, /compress, /search
agent/subagents/code_agent.py     # Use code parser for refactoring
```

---

**Analysis Completed:** March 7, 2026  
**Next Review:** After implementing Tier 1 features
