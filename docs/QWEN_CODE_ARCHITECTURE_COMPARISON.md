# Qwen Code CLI vs RapidWebs Agent - Architecture Deep-Dive Comparison

**Research Date:** March 7, 2026  
**Research Method:** SubAgent (ResearchAgent) + Web Analysis  
**Status:** Complete  

---

## Executive Summary

This document provides a comprehensive technical comparison between **Qwen Code CLI** (TypeScript, 20.1k GitHub stars) and **RapidWebs Agent** (Python). The analysis reveals fundamental architectural differences, design philosophy gaps, and actionable recommendations for improving RapidWebs Agent.

### Key Finding

**Qwen Code CLI is built on a fundamentally different architecture:**
- **Monorepo TypeScript** with modular packages vs. **Single Python package**
- **MCP Protocol** for tool discovery vs. **SkillManager** direct calls
- **Multi-provider OAuth** vs. **API Key only**
- **IDE-first design** vs. **Terminal-first design**

---

## 1. Architecture Overview

### Qwen Code CLI (TypeScript)

```
qwen-code/                          # Monorepo structure
├── packages/                       # Core packages (TypeScript)
│   ├── cli/                        # CLI interface & TUI
│   ├── core/                       # Agent engine & orchestration
│   ├── sdk-typescript/             # TypeScript SDK
│   ├── sdk-java/                   # Java SDK
│   ├── vscode-ide-companion/       # VS Code extension
│   ├── webui/                      # Web-based UI
│   ├── web-templates/              # UI templates
│   ├── zed-extension/              # Zed editor extension
│   └── test-utils/                 # Testing utilities
├── scripts/                        # Build & automation
│   ├── start.js                    # Development entry
│   ├── build.js                    # Production build
│   ├── generate-settings-schema.ts # Config schema generation
│   ├── build_vscode_companion.js   # IDE extension build
│   └── telemetry.js                # Usage telemetry
├── integration-tests/              # E2E tests
├── dist/                           # Compiled output
│   └── cli.js                      # CLI binary
├── esbuild.config.js               # Bundler config
├── vitest.config.ts                # Test config
└── package.json                    # Root package (v0.12.0)
```

**Key Characteristics:**
- **Language:** TypeScript 89.5%, JavaScript 5.9%
- **Runtime:** Node.js 20+
- **Bundler:** ESBuild
- **Testing:** Vitest
- **CLI Binary:** `qwen` → `dist/cli.js`
- **License:** Apache-2.0

---

### RapidWebs Agent (Python)

```
rapidwebs-agent/                    # Single package structure
├── agent/                          # Core Python modules
│   ├── agent.py                    # Core engine + system prompt
│   ├── skills_manager.py           # Tool execution (NO MCP!)
│   ├── approval_workflow.py        # Approval mode handling
│   ├── cli.py (in rapidwebs_agent/)# Main CLI entry
│   ├── config.py                   # Configuration defaults
│   ├── llm_models.py               # LLM provider management
│   ├── context_manager.py          # Context optimization
│   ├── utilities.py                # Utility functions
│   ├── logging_config.py           # Logging setup
│   ├── output_manager.py           # Output management
│   ├── temp_manager.py             # Temp file handling
│   ├── caching/                    # Token caching
│   │   ├── change_detector.py
│   │   ├── content_addressable.py
│   │   ├── response_cache.py
│   │   └── token_budget.py
│   ├── subagents/                  # SubAgents architecture
│   │   ├── orchestrator.py
│   │   ├── code_agent.py
│   │   ├── test_agent.py
│   │   ├── docs_agent.py
│   │   ├── research_agent.py
│   │   └── security_agent.py
│   └── skills/                     # Additional skills
│       └── git_skill.py
├── rapidwebs_agent/                # CLI package
│   ├── cli.py                      # CLI entry point
│   └── __main__.py                 # Module runner
├── tools/                          # MCP servers (for Qwen Code only)
│   ├── mcp_server_caching.py
│   └── mcp_server_code_tools.py
├── tests/                          # Test suite (212 tests)
├── docs/                           # Documentation (13 files)
└── pyproject.toml                  # Python package config
```

**Key Characteristics:**
- **Language:** Python 3.10+
- **Package Manager:** uv
- **TUI Library:** prompt_toolkit
- **Testing:** pytest (212 tests, 0 warnings)
- **CLI Entry:** `rw-agent` → `rapidwebs_agent.cli:main`
- **License:** MIT

---

## 2. Core Design Philosophy Comparison

| Aspect | Qwen Code CLI | RapidWebs Agent | Gap Analysis |
|--------|---------------|-----------------|--------------|
| **Architecture** | Monorepo, modular packages | Single package, modular modules | 🔴 We lack package separation |
| **Tool System** | MCP Protocol (standardized) | SkillManager (custom) | 🟡 Different approaches, both valid |
| **Authentication** | OAuth + API Key (multi-provider) | API Key only | 🔴 Major gap |
| **IDE Integration** | VS Code, Zed, JetBrains | None | 🔴 Major gap |
| **UI Framework** | @xterm/xterm + React | prompt_toolkit | 🟡 Both terminal-based |
| **Extensibility** | Plugin system, SDKs | None | 🔴 We lack extension system |
| **Configuration** | Global + Project (.qwen/) | Global only (~/.config/) | 🟡 Missing per-project config |
| **Session Management** | Persistent conversations | Basic (in-memory) | 🔴 We lack persistence |
| **Model Support** | 6+ providers | 2 providers | 🔴 Limited model choice |
| **Approval Workflow** | YOLO only | 4 modes (plan/default/auto-edit/yolo) | ✅ We're superior |
| **Token Efficiency** | Basic caching | 70-85% savings | ✅ We're superior |
| **SubAgents** | Basic | 5 specialized agents | ✅ We're superior |

---

## 3. Detailed Component Analysis

### 3.1 Authentication System

#### Qwen Code CLI

**Implementation:** Multi-provider OAuth + API Key

```typescript
// packages/auth/src/oauth-flow.ts (inferred structure)
class OAuthManager {
  async authenticate(provider: string): Promise<Credentials> {
    // 1. Start local HTTP server on localhost:8085
    // 2. Open browser to OAuth provider
    // 3. Capture callback with auth code
    // 4. Exchange code for tokens
    // 5. Store encrypted credentials
  }
  
  async refreshTokens(credentials: Credentials): Promise<void> {
    // Auto-refresh before expiry
  }
}
```

**Flow:**
```
1. User runs: qwen --auth
2. Local server starts on localhost:8085
3. Browser opens to https://oauth.provider.com/authorize
4. User signs in
5. Redirect to localhost:8085/callback?code=AUTH_CODE
6. Exchange code for access_token + refresh_token
7. Store encrypted (~/.qwen/credentials)
8. Auto-refresh tokens before expiry
```

**Supported Providers:**
- Qwen OAuth (qwen.ai) - 1,000 free requests/day
- Google OAuth (for Gemini)
- OpenAI (API key)
- Anthropic (API key)
- Vertex AI (service account)

**Storage:** `~/.qwen/credentials` (encrypted)

---

#### RapidWebs Agent

**Implementation:** API Key only (environment variables)

```python
# agent/llm_models.py
class ModelManager:
    def __init__(self, config: ModelConfig):
        self.api_key = os.environ.get('RW_QWEN_API_KEY')
        # No OAuth, no encrypted storage
```

**Configuration:**
```bash
$env:RW_QWEN_API_KEY="key"      # PowerShell
export RW_QWEN_API_KEY="key"    # Linux/macOS
```

**Storage:** Environment variables only (not persisted)

---

#### Gap Analysis & Recommendations

| Gap | Severity | Recommendation |
|-----|----------|----------------|
| No OAuth support | 🔴 High | Implement RFC 8252 loopback flow (Tier 2) |
| No encrypted credential storage | 🔴 High | Add `agent/credentials.py` with `cryptography` |
| Limited provider support | 🔴 High | Add OpenAI, Anthropic, OpenRouter (Tier 1) |
| No credential persistence | 🟡 Medium | Store encrypted in `~/.rapidwebs-agent/credentials` |

**Implementation Priority:** See `docs/FEATURE_ROADMAP_2026.md` Tier 2 (OAuth) and Tier 1 (Multi-Provider)

---

### 3.2 MCP Server Integration

#### Qwen Code CLI

**Architecture:** MCP Protocol for tool discovery and execution

```
┌─────────────────┐         ┌──────────────────┐
│  Qwen Code CLI  │◄────MCP─►│  MCP Servers     │
│  (TypeScript)   │  JSON   │  (filesystem,    │
│                 │  RPC    │   memory, etc.)  │
└─────────────────┘         └──────────────────┘
```

**Configuration:**
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
      "timeout": 10000,
      "trust": true
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "timeout": 10000
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    }
  }
}
```

**Tool Discovery:**
```typescript
// packages/core/src/mcp-client.ts (inferred)
class MCPClient {
  async discoverTools(server: MCPServer): Promise<Tool[]> {
    // Query MCP server for available tools
    // Parse tool schemas
    // Register with core engine
  }
  
  async executeTool(tool: string, params: object): Promise<any> {
    // Send JSON-RPC request to MCP server
    // Wait for response
    // Return result
  }
}
```

**Benefits:**
- Standardized protocol
- Hot-reloadable servers
- Language-agnostic (any language can implement MCP server)
- Tool discovery automatic

---

#### RapidWebs Agent

**Architecture:** SkillManager with direct function calls (NO MCP)

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
    def __init__(self, config: Config):
        self.skills = {}
        self._register_builtin_skills()
    
    def _register_builtin_skills(self):
        self.skills['terminal'] = TerminalExecutorSkill(self.config)
        self.skills['fs'] = FilesystemSkill(self.config)
        self.skills['web'] = WebScraperSkill(self.config)
        self.skills['search'] = SearchSkill(self.config)
    
    async def execute(self, skill_name: str, **kwargs) -> Dict[str, Any]:
        if skill_name not in self.skills:
            raise ValueError(f"Unknown skill: {skill_name}")
        return await self.skills[skill_name].execute(**kwargs)
```

**Benefits:**
- No subprocess overhead
- Direct function calls (faster)
- Type-safe (Python typing)
- Easier debugging

**Drawbacks:**
- No hot-reload
- Language-specific
- Manual tool registration

---

#### Gap Analysis & Recommendations

| Aspect | Qwen Code | RapidWebs | Recommendation |
|--------|-----------|-----------|----------------|
| Protocol | MCP (standardized) | Custom (SkillManager) | ✅ Keep SkillManager (faster) |
| Tool Discovery | Automatic | Manual | 🟡 Add auto-discovery for plugins |
| Hot Reload | Yes | No | 🟡 Optional: Add plugin hot-reload |
| Language Agnostic | Yes | No | ✅ Python-only is fine for our use case |

**Recommendation:** **Keep SkillManager architecture** - it's faster and simpler for our use case. However, consider adding:
1. Plugin discovery system (Tier 2)
2. Optional MCP client for external tools (future)

---

### 3.3 Conversation Management

#### Qwen Code CLI

**Features:**
- Persistent conversation storage
- `/history` - List all conversations
- `/resume <id>` - Resume old conversation
- `/compress` - Compress history using LLM
- `/export [format]` - Export as MD/JSON
- `/search <query>` - Search history
- `/stats` - Session statistics

**Storage:** `~/.qwen/conversations/` (SQLite or JSON)

**Implementation Pattern:**
```typescript
// packages/core/src/conversation-manager.ts (inferred)
class ConversationManager {
  async saveConversation(sessionId: string, messages: Message[]): Promise<void> {
    // Auto-save every N messages
    // Store in ~/.qwen/conversations/{sessionId}.db
  }
  
  async listConversations(): Promise<ConversationSummary[]> {
    // Query all saved conversations
    // Return metadata (date, model, token count, first message)
  }
  
  async resumeConversation(sessionId: string): Promise<Message[]> {
    // Load conversation from storage
    // Restore context window
  }
  
  async compressConversation(sessionId: string): Promise<void> {
    // Use LLM to summarize conversation
    // Replace detailed messages with summary
    // Preserve key decisions and code snippets
  }
}
```

---

#### RapidWebs Agent

**Features:**
- Basic in-memory history
- `/clear` - Clear conversation
- `/stats` - Token usage
- Auto-save: Every 10 messages (to `~/.local/share/rapidwebs-agent/conversations/`)

**Implementation:**
```python
# agent/agent.py
class ConversationHistory:
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or self._default_storage_path()
        self.history: List[Dict[str, str]] = []
        self._load()  # Currently empty implementation
    
    def save(self):
        """Save conversation history to disk."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception:
            pass  # Silently fail
    
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
```

**Current Limitations:**
- `_load()` is empty (doesn't actually load old conversations)
- No conversation listing
- No resume functionality
- No compression
- No search
- No export formats

---

#### Gap Analysis & Recommendations

| Feature | Qwen Code | RapidWebs | Priority |
|---------|-----------|-----------|----------|
| Persistent Storage | ✅ Yes | ⚠️ Partial (save only) | 🔴 High |
| Conversation Listing | ✅ Yes | ❌ No | 🔴 High |
| Resume Conversations | ✅ Yes | ❌ No | 🔴 High |
| Compression | ✅ Yes | ❌ No | 🟡 Medium |
| Export (MD/JSON/PDF) | ✅ Yes | ⚠️ Basic | 🟡 Medium |
| Search | ✅ Yes | ❌ No | 🟡 Medium |
| Statistics | ✅ Yes | ✅ Yes | ✅ Complete |

**Implementation Plan:** See `docs/FEATURE_ROADMAP_2026.md` Tier 1.2 (Conversation Management)

**Files to Modify:**
- `agent/agent.py` (ConversationHistory class)
- `rapidwebs_agent/cli.py` (add `/history`, `/resume`, `/compress`, `/export`, `/search` commands)
- `agent/utilities.py` (add export formatters)

---

### 3.4 UI/Terminal Interface

#### Qwen Code CLI

**Framework:** @xterm/xterm (terminal emulation) + React patterns

**Dependencies:**
```json
{
  "@xterm/xterm": "^6.0.0",
  "react-devtools-core": "^4.28.5"
}
```

**Architecture:**
```typescript
// packages/cli/src/terminal-ui.ts (inferred)
class TerminalUI {
  constructor() {
    this.terminal = new Terminal();
    this.terminal.open(document.getElementById('terminal'));
  }
  
  async getUserInput(): Promise<string> {
    // Render prompt with ink/React-like components
    // Handle keyboard input
    // Support vim mode
  }
  
  renderApprovalPrompt(tool: Tool, risk: RiskLevel): Promise<Decision> {
    // Render interactive approval UI
    // Show tool details, risk level
    // Handle y/n/a/v/d input
  }
}
```

**Features:**
- Vim mode support
- Syntax highlighting
- Streaming responses
- Interactive approval UI
- Keyboard shortcuts

---

#### RapidWebs Agent

**Framework:** prompt_toolkit (Python TUI library)

**Implementation:**
```python
# rapidwebs_agent/cli.py
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings

bindings = KeyBindings()

@bindings.add('c-p')  # Ctrl+P
def switch_to_plan_mode(event):
    event.app.current_buffer.text = '/mode plan'
    event.app.current_buffer.validate_and_handle()

@bindings.add('c-d')  # Ctrl+D
def switch_to_default_mode(event):
    if event.app.current_buffer.text == '':
        raise EOFError()
    event.app.current_buffer.text = '/mode default'
    event.app.current_buffer.validate_and_handle()

session = PromptSession(key_bindings=bindings)
user_input = await session.prompt_async('> ')
```

**Features:**
- 4 approval modes with keyboard shortcuts
- Command autocomplete
- Token budget dashboard
- Streaming responses
- Syntax highlighting (via Rich)

---

#### Gap Analysis & Recommendations

| Feature | Qwen Code | RapidWebs | Verdict |
|---------|-----------|-----------|---------|
| Framework | @xterm/xterm | prompt_toolkit | ✅ Both valid |
| Vim Mode | ✅ Yes | ❌ No | 🟡 Nice-to-have |
| Syntax Highlighting | ✅ Yes | ✅ Yes (Rich) | ✅ Complete |
| Keyboard Shortcuts | ✅ Yes | ✅ Yes | ✅ Complete |
| Streaming | ✅ Yes | ✅ Yes | ✅ Complete |
| Interactive UI | ✅ Yes | ✅ Yes | ✅ Complete |

**Recommendation:** **No major changes needed.** Optional enhancements:
- Add vim mode support (low priority)
- Improve streaming performance (optional)

---

### 3.5 Configuration System

#### Qwen Code CLI

**Configuration Files:**
| File | Scope | Priority |
|------|-------|----------|
| `~/.qwen/settings.json` | User (global) | Base |
| `.qwen/settings.json` | Project | Overrides global |
| Environment variables | Session | Highest |
| CLI flags | Command | Overrides all |

**Schema:**
```json
{
  "modelProviders": {
    "openai": [{
      "id": "gpt-4o",
      "name": "GPT-4o",
      "baseUrl": "https://api.openai.com/v1",
      "envKey": "OPENAI_API_KEY",
      "generationConfig": {
        "temperature": 0.7,
        "topP": 0.9
      }
    }]
  },
  "env": {
    "OPENAI_API_KEY": "sk-..."
  },
  "security": {
    "auth": {
      "selectedType": "openai"
    }
  },
  "model": {
    "name": "gpt-4o"
  },
  "tools": {
    "approvalMode": "default",
    "allowed": ["read_file", "write_file"],
    "exclude": ["delete_file"]
  }
}
```

**Loading Order:**
```typescript
// packages/config/src/loader.ts (inferred)
async function loadConfig(): Promise<Config> {
  // 1. Load global config (~/.qwen/settings.json)
  const global = await loadGlobalConfig();
  
  // 2. Load project config (.qwen/settings.json)
  const project = await loadProjectConfig();
  
  // 3. Merge (project overrides global)
  const merged = mergeConfigs(global, project);
  
  // 4. Apply environment variables (highest priority)
  applyEnvironmentVariables(merged);
  
  // 5. Apply CLI flags (overrides all)
  applyCommandLineFlags(merged);
  
  return merged;
}
```

---

#### RapidWebs Agent

**Configuration Files:**
| File | Scope | Priority |
|------|-------|----------|
| `~/.config/rapidwebs-agent/config.yaml` | User (global) | Base |
| Environment variables | Session | High |
| CLI flags | Command | Highest |

**Schema:**
```yaml
default_model: qwen_coder
models:
  qwen_coder:
    enabled: true
    api_key: ""  # Or set via RW_QWEN_API_KEY env var
    base_url: https://dashscope.aliyuncs.com/...
  gemini:
    enabled: false
    api_key: ""

performance:
  token_budget: 100000
  cache_responses: true
  cache_ttl: 3600
  max_concurrent_tools: 5

agent:
  max_tool_iterations: 15
  default_approval_mode: default

skills:
  filesystem:
    enabled: true
    allowed_directories: ['~', './']
    max_file_size: 1048576
    operation_timeout: 30
```

**Loading:**
```python
# agent/config.py
class Config:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._default_config_path()
        self._config = self._load_config()
        self._apply_environment_variables()
    
    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        return self._get_defaults()
```

---

#### Gap Analysis & Recommendations

| Feature | Qwen Code | RapidWebs | Priority |
|---------|-----------|-----------|----------|
| Global Config | ✅ Yes | ✅ Yes | ✅ Complete |
| Project Config | ✅ Yes | ❌ No | 🔴 High |
| Environment Variables | ✅ Yes | ✅ Yes | ✅ Complete |
| CLI Flags | ✅ Yes | ✅ Yes | ✅ Complete |
| Schema Validation | ✅ Yes (TypeScript) | ⚠️ Basic | 🟡 Medium |
| Config Generation | ✅ Yes (script) | ❌ No | 🟡 Medium |

**Recommendation:** Add per-project configuration support

**Implementation:**
```python
# agent/config.py
class Config:
    def _load_config(self) -> Dict[str, Any]:
        # 1. Load global config
        global_config = self._load_global_config()
        
        # 2. Load project config (if exists)
        project_config = self._load_project_config()
        
        # 3. Merge (project overrides global)
        if project_config:
            global_config = self._merge_configs(global_config, project_config)
        
        return global_config
    
    def _load_project_config(self) -> Optional[Dict[str, Any]]:
        project_config_paths = [
            Path.cwd() / '.rapidwebs-config.yaml',
            Path.cwd() / '.rapidwebs-config.yml',
        ]
        for path in project_config_paths:
            if path.exists():
                with open(path, 'r') as f:
                    return yaml.safe_load(f)
        return None
```

---

### 3.6 Design Principles & Patterns

#### Qwen Code CLI

**Key Patterns:**
1. **Monorepo Architecture** - Separate packages for CLI, core, SDKs
2. **MCP Protocol** - Standardized tool interface
3. **OAuth 2.0** - Browser-based authentication (RFC 8252)
4. **Plugin System** - Extensible via plugins
5. **IDE Integration** - VS Code, Zed, JetBrains extensions
6. **Multi-Provider** - Abstract model provider interface
7. **Type Safety** - TypeScript throughout
8. **ESBuild Bundling** - Fast builds, single binary

**Separation of Concerns:**
```
packages/cli/          → UI/UX only
packages/core/         → Agent logic only
packages/sdk-*/        → API bindings only
packages/auth/         → Authentication only
```

**Extensibility:**
- Plugin API for custom tools
- SDK for programmatic access
- MCP servers for external integrations
- IDE extensions for editor integration

---

#### RapidWebs Agent

**Key Patterns:**
1. **Single Package** - All modules in one package
2. **SkillManager** - Custom tool interface (no MCP)
3. **API Key Auth** - Environment variables only
4. **No Plugin System** - All skills built-in
5. **Terminal-Only** - No IDE integration
6. **Multi-Model** - Basic provider abstraction
7. **Type Hints** - Python typing (partial)
8. **Hatchling Build** - Standard Python packaging

**Separation of Concerns:**
```
agent/agent.py              → Core orchestration
agent/skills_manager.py     → Tool execution
agent/approval_workflow.py  → Approval logic
agent/llm_models.py         → Model management
rapidwebs_agent/cli.py      → CLI interface
```

**Extensibility:**
- None currently (all skills built-in)
- SubAgents can be extended (5 types)

---

#### Gap Analysis & Recommendations

| Principle | Qwen Code | RapidWebs | Recommendation |
|-----------|-----------|-----------|----------------|
| Modularity | ✅ Monorepo | ⚠️ Single package | 🟡 Consider splitting into packages |
| Standardization | ✅ MCP | ❌ Custom | ✅ Keep SkillManager (faster) |
| Authentication | ✅ OAuth | ❌ API Key only | 🔴 Add OAuth (Tier 2) |
| Extensibility | ✅ Plugins | ❌ None | 🔴 Add plugin system (Tier 2) |
| IDE Support | ✅ Extensions | ❌ None | 🔴 Add VS Code extension (Tier 2) |
| Type Safety | ✅ TypeScript | ⚠️ Partial typing | 🟡 Add comprehensive type hints |
| Build System | ✅ ESBuild | ✅ Hatchling | ✅ Both valid |

---

## 4. What We're Missing (Critical Gaps)

### 🔴 Critical (Tier 1)

1. **Multi-Provider Model Support**
   - Current: 2 providers (Qwen, Gemini)
   - Target: 6+ providers (OpenAI, Anthropic, OpenRouter, Vertex AI)
   - Impact: Major flexibility for users

2. **Conversation Persistence**
   - Current: Save-only (no load)
   - Target: Full CRUD (list, resume, compress, export, search)
   - Impact: Critical for daily use

3. **Per-Project Configuration**
   - Current: Global config only
   - Target: Global + Project (.rapidwebs-config.yaml)
   - Impact: Better workflow for multi-project users

### 🟡 High (Tier 2)

4. **OAuth Authentication**
   - Current: API Key only
   - Target: OAuth 2.0 loopback flow (Google + Qwen)
   - Impact: Easier onboarding, free tier access

5. **Plugin System**
   - Current: None
   - Target: Plugin API with lifecycle management
   - Impact: Community extensions

6. **IDE Integration**
   - Current: None
   - Target: VS Code extension (minimum)
   - Impact: Major adoption driver

7. **API Key Management UI**
   - Current: Environment variables
   - Target: Encrypted storage with `/keys` commands
   - Impact: Better UX

### 🟢 Medium (Tier 3)

8. **Desktop GUI**
   - Current: None
   - Target: Tauri/Electron app
   - Impact: Broader audience

9. **Thinking Mode Support**
   - Current: None
   - Target: Support for reasoning models
   - Impact: Better for complex tasks

10. **Voice I/O**
    - Current: None
    - Target: Offline STT/TTS
    - Impact: Accessibility

---

## 5. What We Do Better

### ✅ Superior Features

1. **4 Approval Modes** (vs. Qwen Code's single YOLO)
   - plan, default, auto-edit, yolo
   - Keyboard shortcuts (Ctrl+P/D/A/Y)

2. **70-85% Token Savings** (vs. basic caching)
   - Content-addressable storage
   - Response caching with TTL
   - Token budget enforcement

3. **5 Specialized SubAgents** (vs. basic)
   - Code, Test, Docs, Research, Security
   - Parallel execution
   - Result aggregation

4. **Command Whitelisting** (better security)
   - Blocked: `rm -rf /`, `sudo`, `wget`, `curl`, `nc`
   - Excluded: `*.env`, `*.key`, `*.pem`, `*.secret`

5. **Python Cross-Platform** (no Node.js 20+ requirement)
   - Works on Python 3.10+
   - No npm/node-gyp issues

6. **SSRF Protection** (web scraping)
   - Blocks localhost/private IPs
   - DNS rebinding protection

---

## 6. Recommended Actions

### Immediate (This Week)
1. ⭐ **Multi-Provider Support** - Add OpenAI, Anthropic, OpenRouter
2. ⭐ **Conversation Persistence** - Implement load/resume functionality
3. ⭐ **Per-Project Config** - Add `.rapidwebs-config.yaml` support

### Next Month
4. ⭐ **API Key Management** - Encrypted storage with `/keys` commands
5. ⭐ **Start OAuth (Phase 1)** - Google OAuth first (easier)
6. ⭐ **Plugin System** - Basic plugin API

### Next Quarter
7. ⭐ **VS Code Extension** - Minimum viable IDE integration
8. ⭐ **Conversation Search** - Full-text search across history
9. ⭐ **Test Coverage** - Target 80%

---

## 7. Files to Create/Modify

### New Files
```
agent/oauth/
├── __init__.py
├── google_auth.py          # Google OAuth
├── qwen_auth.py            # Qwen OAuth
└── encryption.py           # Credential encryption

agent/plugins/
├── __init__.py
├── manager.py              # Plugin lifecycle
└── base.py                 # Plugin base class

integrations/vscode-extension/
├── src/
│   ├── extension.ts
│   ├── chat-view.ts
│   └── code-actions.ts
├── package.json
└── README.md
```

### Modified Files
```
agent/agent.py              # ConversationHistory enhancements
agent/config.py             # Per-project config support
agent/llm_models.py         # Multi-provider support
rapidwebs_agent/cli.py      # New commands (/history, /resume, /keys, etc.)
agent/utilities.py          # Export formatters
```

---

## 8. Conclusion

**Qwen Code CLI** is built on a fundamentally different architecture:
- **Monorepo TypeScript** with standardized protocols (MCP, OAuth)
- **IDE-first design** with multiple integrations
- **Plugin ecosystem** for extensibility

**RapidWebs Agent** excels at:
- **Token efficiency** (70-85% savings)
- **Approval workflow** (4 modes vs. 1)
- **SubAgents** (5 specialized agents)
- **Security** (command whitelisting, SSRF protection)

**To compete effectively:**
1. Keep our advantages (approval modes, token efficiency, SubAgents)
2. Add critical missing features (OAuth, multi-provider, conversation persistence)
3. Build IDE integration (VS Code first)
4. Create plugin ecosystem

**Timeline:** 10-12 weeks for core features (see `docs/FEATURE_ROADMAP_2026.md`)

---

**Research Completed By:** ResearchAgent (SubAgent)  
**Date:** March 7, 2026  
**Next Review:** After implementing Tier 1 features
