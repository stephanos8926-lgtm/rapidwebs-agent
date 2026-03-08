# RapidWebs Agent - Feature Roadmap 2026

**Version:** 1.1.0  
**Date:** March 7, 2026  
**Status:** Planning Complete  
**Last Revised:** March 7, 2026 - OAuth moved to Tier 2

---

## Executive Summary

After comprehensive analysis of the **Qwen Code CLI** repository (20.1k stars) and competitive agentic CLI tools, this document outlines a prioritized feature roadmap to bring RapidWebs Agent to parity with industry leaders while maintaining our competitive advantages.

### Key Findings

| Category | Qwen Code CLI | RapidWebs Agent | Verdict |
|----------|---------------|-----------------|---------|
| **Authentication** | OAuth + API Key | API Key only | 🟡 Tier 2 |
| **Model Providers** | 6+ providers | 2 providers | 🔴 Tier 1 |
| **IDE Integration** | VS Code, Zed, JetBrains | None | 🟡 Tier 2 |
| **Approval Modes** | YOLO only | 4 modes | ✅ Leading |
| **Token Efficiency** | Basic | 70-85% savings | ✅ Leading |
| **SubAgents** | Basic | 5 specialized | ✅ Leading |
| **Security** | API key management | Command whitelisting + SSRF | ✅ Leading |

---

## Competitive Advantages to Maintain

1. **4 Approval Modes** (plan/default/auto-edit/yolo) vs Qwen Code's single YOLO mode
2. **70-85% Token Savings** via advanced caching system
3. **5 Specialized SubAgents** (Code, Test, Docs, Research, Security)
4. **Command Whitelisting** for enhanced security
5. **Python Cross-Platform** (no Node.js 20+ requirement)
6. **SSRF Protection** for web scraping
7. **Token Budget Dashboard** with real-time tracking

---

## 📋 Prioritized Feature Roadmap

### **Tier 1: Essential / High Priority** 🔴

*Critical for competitiveness and user adoption - Can be implemented without OAuth*

---

#### **1.1 Multi-Provider Model Support**

**Priority:** ⭐⭐⭐⭐⭐ | **Effort:** 4-6 days | **Impact:** Major flexibility

**Why:** Qwen Code supports 6+ providers. We only support 2.

**Implementation Plan:**

```python
# Enhanced: agent/llm_models.py
SUPPORTED_PROVIDERS = {
    'openai': {
        'models': ['gpt-4o', 'gpt-4-turbo', 'o1-preview', 'o1-mini'],
        'base_url': 'https://api.openai.com/v1',
        'env_key': 'OPENAI_API_KEY',
        'cost_tier': '$$$$'
    },
    'anthropic': {
        'models': ['claude-sonnet-4-20250514', 'claude-opus-20240229'],
        'base_url': 'https://api.anthropic.com',
        'env_key': 'ANTHROPIC_API_KEY',
        'cost_tier': '$$$'
    },
    'google': {
        'models': ['gemini-2.5-pro', 'gemini-2.5-flash'],
        'base_url': 'https://generativelanguage.googleapis.com',
        'env_key': 'GOOGLE_API_KEY',
        'cost_tier': 'Free'
    },
    'qwen': {
        'models': ['qwen3-coder-plus', 'qwen3.5-plus', 'qwen3-coder-next'],
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'env_key': 'RW_QWEN_API_KEY',
        'cost_tier': 'Free'
    },
    'openrouter': {
        'models': ['multiple via single API (100+ models)'],
        'base_url': 'https://openrouter.ai/api/v1',
        'env_key': 'OPENROUTER_API_KEY',
        'cost_tier': '$$'
    },
    'vertex-ai': {
        'models': ['Google Cloud enterprise models'],
        'base_url': 'https://us-central1-aiplatform.googleapis.com',
        'env_key': 'GOOGLE_APPLICATION_CREDENTIALS',
        'cost_tier': '$$$'
    }
}
```

**Tasks:**
- [ ] Add OpenAI provider support
- [ ] Add Anthropic provider support
- [ ] Add OpenRouter support (access to 100+ models)
- [ ] Add Vertex AI support (for enterprise users)
- [ ] Update config schema to support multiple providers
- [ ] Add provider switching UI in interactive mode
- [ ] Update `/model` command to show all providers
- [ ] Add cost tracking per provider
- [ ] Implement provider fallback on rate limits

**Files to Modify:**
- `agent/llm_models.py`
- `agent/config.py`
- `agent/agent.py`
- `rapidwebs_agent/cli.py`

**Acceptance Criteria:**
- All 6 providers configurable
- Easy provider switching via `/model`
- Cost displayed per model
- Automatic fallback on rate limits

---

#### **1.2 Enhanced Conversation Management**

**Priority:** ⭐⭐⭐⭐⭐ | **Effort:** 3-4 days | **Impact:** Major UX improvement

**Why:** Qwen Code has `/compress`, persistent history, session stats. We have basic `/clear`.

**Implementation Plan:**

```python
# Enhanced: agent/agent.py (ConversationHistory class)
class ConversationHistory:
    """Persistent conversation management with advanced features."""
    
    - Auto-save conversations (~/.rapidwebs-agent/conversations/)
    - Conversation listing with metadata
    - Resume old conversations
    - Compress history using LLM summarization
    - Export as MD/JSON/PDF
    - Search conversation history
    - Session statistics
    - Conversation branching (fork conversations)
```

**New Commands:**
| Command | Description |
|---------|-------------|
| `/history` | List all saved conversations |
| `/resume <id>` | Resume a previous conversation |
| `/compress` | Compress history using LLM summarization |
| `/export [format]` | Export as markdown/json/pdf |
| `/search <query>` | Search conversation history |
| `/branch <message-id>` | Fork conversation at specific point |
| `/stats` | Show detailed session statistics |

**Tasks:**
- [ ] Implement conversation persistence (auto-save every 10 messages)
- [ ] Add `/history` command with conversation list UI
- [ ] Add `/resume <id>` command
- [ ] Implement `/compress` using LLM summarization
- [ ] Add `/export markdown|json|pdf` command
- [ ] Add `/search <query>` for full-text history search
- [ ] Show session stats automatically on exit
- [ ] Add conversation branching (fork conversations)
- [ ] Add conversation metadata (duration, turns, tokens, model used)

**Files to Modify:**
- `agent/agent.py` (ConversationHistory class)
- `rapidwebs_agent/cli.py`
- `agent/utilities.py` (add export formatters)

**Acceptance Criteria:**
- Conversations auto-saved
- Can list and resume old conversations
- Export works in all 3 formats
- Search returns relevant results
- Compression reduces token count by 50%+

---

#### **1.3 IDE Integration**

**Priority:** ⭐⭐⭐ | **Effort:** 10-15 days | **Impact:** Massive adoption

**Note:** Moved from Tier 1.4 - Big effort, defer until after core features

**Why:** Qwen Code integrates with VS Code, Zed, JetBrains. We have terminal-only.

**Implementation Plan:**

```
integrations/
├── vscode-extension/        # VS Code extension (TypeScript)
│   ├── src/
│   │   ├── extension.ts     # Main extension entry
│   │   ├── chat-view.ts     # Chat panel
│   │   └── code-actions.ts  # Right-click actions
│   ├── package.json
│   └── README.md
├── zed-extension/           # Zed extension (Rust/TypeScript)
└── jetbrains-plugin/        # IntelliJ/PyCharm plugin (Kotlin)
```

**VS Code Extension Features:**
- Inline chat (`Ctrl+Shift+P` → "Ask RapidWebs")
- Code actions (right-click → "Refactor with RapidWebs")
- Terminal integration
- File context awareness
- Diff viewer for suggested changes

**Tasks:**
- [ ] Create VS Code extension scaffolding
- [ ] Implement chat panel with agent communication
- [ ] Add code actions (refactor, explain, document, test)
- [ ] Implement terminal integration
- [ ] Add file context passing to agent
- [ ] Create diff viewer for suggested changes
- [ ] Publish to VS Code Marketplace
- [ ] Create Zed extension (simpler, reuse logic)
- [ ] Create JetBrains plugin (larger effort)
- [ ] Add `--ide-mode` flag for IDE communication protocol

**Files to Create:**
- `integrations/vscode-extension/` (new directory)
- `agent/ide_bridge.py` (communication protocol)

**Acceptance Criteria:**
- Extension published to VS Code Marketplace
- Can chat with agent from VS Code
- Code actions work on selected code
- Terminal integration functional

---

#### **1.4 Model Switching UI**

**Priority:** ⭐⭐⭐⭐ | **Effort:** 2-3 days | **Impact:** Better UX

**Why:** Qwen Code has `/model` with interactive selection. We have basic support.

**Implementation:**

```
/model
┌─ Select Model ─────────────────────────────────┐
│ Provider    │ Model                  │ Cost    │
├─────────────┼────────────────────────┼─────────┤
│ ✓ Qwen      │ qwen3-coder-plus       │ Free    │
│   Qwen      │ qwen3.5-plus           │ Free    │
│   Google    │ gemini-2.5-pro         │ Free    │
│   OpenAI    │ gpt-4o                 │ $$$$    │
│   Anthropic │ claude-sonnet-4        │ $$      │
└─────────────────────────────────────────────────┘
Type model name or number to switch:
```

**Tasks:**
- [ ] Enhance `/model` command with interactive UI
- [ ] Show provider, model name, and cost tier
- [ ] Add model benchmarks (Terminal-Bench scores if available)
- [ ] Add `--model` flag for headless switching
- [ ] Remember last-used model per project
- [ ] Add model recommendations based on task type
- [ ] Show rate limit status per provider

**Files to Modify:**
- `rapidwebs_agent/cli.py`
- `agent/llm_models.py`

**Acceptance Criteria:**
- Interactive model selection UI
- Cost tier visible
- Model persists per project
- Rate limits displayed

---

### **Tier 2: Nice to Have / Medium Priority** 🟡

*Features that improve usability and competitiveness*

---

#### **2.1 OAuth Authentication (Browser-Based Sign-In)**

**Priority:** ⭐⭐⭐⭐ | **Effort:** 9-11 days | **Impact:** High user acquisition

**Why:** Qwen Code CLI and Gemini CLI both offer browser-based sign-in for easier authentication.

**Implementation Approach:**

This feature uses the **OAuth2 Loopback IP Flow (RFC 8252)** - a standard pattern for CLI applications:

```
1. User runs: rw-agent --auth google
2. Agent starts local HTTP server on localhost:8085
3. Agent opens browser to OAuth provider
4. User signs in via browser
5. OAuth provider redirects to localhost:8085/callback?code=AUTH_CODE
6. Agent captures AUTH_CODE from URL
7. Agent exchanges code for tokens (access_token + refresh_token)
8. Agent stores tokens encrypted (~/.rapidwebs-agent/credentials)
9. Agent auto-refreshes tokens before expiry
```

**Files to Create:**
- `agent/oauth/__init__.py`
- `agent/oauth/google_auth.py` (uses `google-auth-oauthlib`)
- `agent/oauth/qwen_auth.py` (uses `httpx` + `http.server`)
- `agent/oauth/encryption.py` (credential encryption)
- `tests/test_oauth.py`

**Dependencies to Add:**
```toml
[project]
dependencies = [
    "google-auth-oauthlib>=1.2.0",  # Google OAuth
    "cryptography>=42.0.0",          # Credential encryption
]
```

**Tasks:**
- [ ] **Phase 1: Google OAuth** (2-3 days)
  - [ ] Implement `GoogleAuthManager` class
  - [ ] Use `google-auth-oauthlib.flow.InstalledAppFlow`
  - [ ] Implement token refresh logic
  - [ ] Add encrypted credential storage
- [ ] **Phase 2: Qwen OAuth** (3-4 days)
  - [ ] Implement `QwenAuthManager` class
  - [ ] Create local callback server (`http.server`)
  - [ ] Implement token exchange with Alibaba Cloud
  - [ ] Add auto-refresh mechanism
- [ ] **Phase 3: CLI Integration** (1 day)
  - [ ] Add `--auth` command
  - [ ] Add `--auth-revoke` command
  - [ ] Add credential status display
- [ ] **Phase 4: Encryption** (1 day)
  - [ ] Implement credential encryption (using `cryptography`)
  - [ ] Key derived from machine ID
- [ ] **Phase 5: Testing** (2 days)
  - [ ] Test OAuth flows end-to-end
  - [ ] Test token refresh
  - [ ] Test credential encryption/decryption

**Acceptance Criteria:**
- User can authenticate via browser flow for both Google and Qwen
- Tokens refresh automatically before expiry
- Credentials encrypted on disk
- Works in both interactive and headless modes
- `--auth revoke` deletes credentials

**Technical Notes:**
- Google OAuth: Use official `google-auth-oauthlib` library (handles everything)
- Qwen OAuth: Implement RFC 8252 loopback flow manually with `http.server`
- Client secrets will be bundled with package (standard for CLI apps)
- Scopes minimized to only what's necessary

---

#### **2.2 Plugin/Extension System**

**Priority:** ⭐⭐⭐⭐ | **Effort:** 5-7 days | **Impact:** Extensibility

**Implementation:**

```python
# New: agent/plugins/
class PluginManager:
    """Load and manage community plugins."""
    
    - Load plugins from ~/.rapidwebs-agent/plugins/
    - Plugin lifecycle (init, execute, shutdown)
    - Hook system (pre-tool, post-tool, pre-response)
    - Plugin marketplace (future)
```

**Example Plugins:**
- Docker integration plugin
- Database connector plugin (PostgreSQL, MySQL, SQLite)
- Cloud deployment plugin (AWS/GCP/Azure)
- Jupyter notebook plugin
- GraphQL API plugin

**Tasks:**
- [ ] Create plugin architecture
- [ ] Define plugin API (Python interface)
- [ ] Add plugin discovery (`plugins/` directory)
- [ ] Implement plugin lifecycle management
- [ ] Create hook system for tool interception
- [ ] Create 2-3 example plugins
- [ ] Add `/plugins` command for management
- [ ] Document plugin development

**Files to Create:**
- `agent/plugins/__init__.py`
- `agent/plugins/manager.py`
- `agent/plugins/base.py`
- `plugins/example_docker_plugin.py`

**Acceptance Criteria:**
- Plugins load automatically
- Plugin API documented
- 3 example plugins working
- `/plugins list|enable|disable` commands work

---

#### **2.2 API Key Management UI**

**Priority:** ⭐⭐⭐ | **Effort:** 1-2 days | **Impact:** Better UX

**Why:** Users hate editing config files to add API keys.

**Implementation:**
```python
# New: agent/api_key_manager.py
class APIKeyManager:
    """Secure API key storage and management."""
    
    - Encrypted key storage (using `cryptography` library)
    - Multi-key support (different keys per provider)
    - Key rotation support
    - `/keys` command to manage keys
    - Import/export keys securely
```

**Tasks:**
- [ ] Add encrypted key storage (`~/.rapidwebs-agent/keys.enc`)
- [ ] Add `/keys add <provider>` interactive command
- [ ] Add `/keys list` (shows masked keys)
- [ ] Add `/keys remove <provider>`
- [ ] Add `/keys rotate <provider>`
- [ ] Support environment variable fallback

**Acceptance Criteria:**
- Keys stored encrypted (not plaintext in config)
- Interactive key entry via CLI
- Environment variables still work as fallback

---

#### **2.3 Desktop GUI Application**

**Priority:** ⭐⭐⭐ | **Effort:** 10-15 days | **Impact:** Broader audience

**Implementation:**

```
gui/
├── main.py              # Tauri or Electron app entry
├── src/                 # React frontend
│   ├── components/
│   ├── views/
│   └── App.tsx
└── bridge/              # Python backend bridge
    └── server.py        # WebSocket/HTTP bridge
```

**Features:**
- Chat interface (mirrors terminal UI)
- File tree viewer
- Settings panel
- Conversation sidebar
- Token usage dashboard
- Model selection dropdown

**Tasks:**
- [ ] Choose framework (Tauri recommended for size)
- [ ] Create chat interface
- [ ] Add file tree viewer
- [ ] Add settings panel
- [ ] Add conversation sidebar
- [ ] Package as native app (Windows/macOS/Linux)
- [ ] Add auto-update mechanism

**Acceptance Criteria:**
- Native app for all 3 platforms
- Feature parity with terminal
- Auto-updates working

---

#### **2.4 Thinking Mode Support**

**Priority:** ⭐⭐⭐ | **Effort:** 1-2 days | **Impact:** Better reasoning

**Implementation:**

```python
# Enhanced: agent/llm_models.py
class ModelManager:
    def set_thinking_mode(self, enabled: bool, effort: str = 'medium'):
        """
        Enable thinking/reasoning mode for supported models.
        
        - Qwen3.5-Plus: enable_thinking parameter
        - O1 models: reasoning effort (low/medium/high)
        - Claude: extended thinking toggle
        """
```

**Tasks:**
- [ ] Add thinking mode toggle (`/thinking on|off`)
- [ ] Support Qwen3.5-Plus thinking parameter
- [ ] Support O1 reasoning effort levels
- [ ] Support Claude extended thinking
- [ ] Show thinking indicators in UI
- [ ] Add thinking token tracking (separate from response tokens)

**Acceptance Criteria:**
- `/thinking on` enables for supported models
- Thinking tokens tracked separately
- UI shows when thinking mode is active

---

#### **2.5 Voice Input/Output**

**Priority:** ⭐⭐⭐ | **Effort:** 5-7 days | **Impact:** Accessibility

**Implementation:**

```python
# New: agent/voice_manager.py
class VoiceManager:
    """Speech-to-text and text-to-speech for voice interaction."""
    
    - Speech-to-text (Whisper.cpp or Vosk - offline)
    - Text-to-speech (Piper or Coqui TTS - offline)
    - Voice commands ("Hey RapidWebs...")
```

**Tasks:**
- [ ] Integrate Whisper.cpp for STT (offline, privacy-focused)
- [ ] Integrate Piper TTS for output (offline)
- [ ] Add `/voice` command to toggle voice mode
- [ ] Add wake word detection (optional, "Hey RapidWebs")
- [ ] Support voice commands ("create file", "run tests")
- [ ] Add voice settings (speed, pitch, language)

**Acceptance Criteria:**
- Voice input works offline
- Voice output works offline
- Basic voice commands recognized

---

#### **2.6 Per-Project Configuration**

**Priority:** ⭐⭐⭐ | **Effort:** 1 day | **Impact:** Better workflow

**Why:** Qwen Code has `.qwen/settings.json` per project.

**Implementation:**

```python
# Enhanced: agent/config.py
class Config:
    """Configuration with project-level overrides."""
    
    Config Priority (lowest to highest):
    1. ~/.config/rapidwebs-agent/config.yaml (global)
    2. .rapidwebs-config.yaml (project root)
    3. .env (project-specific env vars)
    4. CLI arguments (highest priority)
```

**Project Config Example:**
```yaml
# .rapidwebs-config.yaml
model:
  provider: openai
  name: gpt-4o

approval:
  default_mode: auto-edit

skills:
  filesystem:
    allowed_directories: ['./src', './tests']
```

**Tasks:**
- [ ] Add project config file loading
- [ ] Implement config priority system
- [ ] Add `.rapidwebs-config.yaml` schema
- [ ] Support `.env` file loading
- [ ] Add `/config show` to display effective config

**Acceptance Criteria:**
- Project config overrides global
- `.env` files loaded automatically
- Config priority documented

---

### **Tier 3: Extras / Low Priority** 🟢

*Nice-to-have features for differentiation*

---

#### **3.1 Conversation Search & Branching**

**Priority:** ⭐⭐⭐ | **Effort:** 2-3 days

**Implementation:**
```python
# Enhanced: agent/agent.py
class ConversationHistory:
    def search(self, query: str) -> List[Message]:
        """Full-text search across all conversations."""
    
    def branch(self, message_id: str) -> 'ConversationHistory':
        """Create fork at specific message."""
```

**Tasks:**
- [ ] Implement full-text search (SQLite FTS5 or Whoosh)
- [ ] Add search UI with highlighting
- [ ] Implement conversation branching
- [ ] Add branch visualization

---

#### **3.2 PDF/HTML Conversation Export**

**Priority:** ⭐⭐ | **Effort:** 1-2 days

**Implementation:**
```python
# Enhanced: agent/agent.py
def export(self, format: str) -> str:
    if format == 'pdf':
        # Use reportlab or weasyprint
    elif format == 'html':
        # Generate styled HTML with syntax highlighting
```

**Tasks:**
- [ ] Add PDF export with syntax highlighting
- [ ] Add HTML export with CSS styling
- [ ] Include metadata (date, model, tokens)

---

#### **3.3 Improved Test Coverage (80% target)**

**Priority:** ⭐⭐⭐ | **Effort:** 5-7 days

**Current:** ~65% (estimated)  
**Target:** 80%

**Tasks:**
- [ ] Add tests for oauth_manager
- [ ] Add tests for conversation management
- [ ] Add integration tests for IDE bridge
- [ ] Add performance tests for caching
- [ ] Generate coverage report

---

#### **3.4 Docker Integration**

**Priority:** ⭐⭐ | **Effort:** 3-4 days

**Implementation:**
```python
# New skill: agent/skills/docker_skill.py
class DockerSkill:
    """Docker container operations."""
    
    - Run commands in containers
    - Build images from Dockerfile
    - Manage container lifecycle
    - Docker Compose support
```

---

#### **3.5 Database Plugin**

**Priority:** ⭐⭐ | **Effort:** 4-5 days

**Implementation:**
```python
# Plugin: plugins/database_plugin.py
class DatabasePlugin:
    """Database connectivity and operations."""
    
    - Connect to PostgreSQL, MySQL, SQLite
    - Run queries via agent
    - Schema exploration
    - Data export/import
```

---

#### **3.6 Cloud Deployment Helpers**

**Priority:** ⭐⭐ | **Effort:** 5-7 days

**Implementation:**
```python
# New skill: agent/skills/cloud_skill.py
class CloudSkill:
    """Cloud deployment operations."""
    
    - AWS: Deploy to Lambda, ECS, S3
    - GCP: Deploy to Cloud Run, GKE
    - Azure: Deploy to Functions, AKS
    - Vercel/Netlify: One-click deploys
```

---

#### **3.7 Analytics Dashboard**

**Priority:** ⭐ | **Effort:** 2-3 days

**Implementation:**
```python
# New: agent/analytics.py
class AnalyticsManager:
    """Usage analytics and reporting."""
    
    - Token usage over time
    - Most-used tools/skills
    - Success/failure rates
    - Cost tracking (by provider)
    - Export to CSV/JSON
```

---

#### **3.8 Real-time Collaboration**

**Priority:** ⭐⭐ | **Effort:** 7-10 days

**Implementation:**
```python
# New: agent/collaboration.py
class CollaborationManager:
    """Multi-user session management."""
    
    - WebSocket server for shared sessions
    - User presence indicators
    - Chat alongside agent
    - Shared conversation state
```

---

## 📅 Implementation Timeline

### **Phase 1: Core Features (Weeks 1-2)**

| Week | Features | Deliverables |
|------|----------|--------------|
| 1 | Multi-Provider Support | 6 providers configurable |
| 2 | Conversation Management | All new `/history`, `/resume`, `/export` commands |

**Milestone:** v2.4.0 release

---

### **Phase 2: UX Improvements (Weeks 3-5)**

| Week | Features | Deliverables |
|------|----------|--------------|
| 3 | Model Switching UI | Interactive `/model` command |
| 4 | API Key Management | `/keys` commands, encrypted storage |
| 5 | Per-Project Config | `.rapidwebs-config.yaml` support |

**Milestone:** v2.5.0 release

---

### **Phase 3: Advanced Features (Weeks 6-10)**

| Week | Features | Deliverables |
|------|----------|--------------|
| 6-7 | OAuth Authentication | Browser sign-in for Google + Qwen |
| 8-9 | IDE Integration (VS Code) | Published VS Code extension |
| 10 | Plugin System | Plugin API + 3 example plugins |

**Milestone:** v2.6.0 release

---

### **Phase 4: Enhancement (Weeks 11+)**

| Feature | Priority | Notes |
|---------|----------|-------|
| Desktop GUI | Medium | Native app |
| Thinking Mode | Low | For reasoning models |
| Voice I/O | Low | Accessibility feature |
| Conversation Search | Medium | Full-text search |
| PDF Export | Low | Nice-to-have |
| Test Coverage | Medium | Target 80% |

---

## 📊 Success Metrics

| Metric | Current | 3 Month Target | 6 Month Target |
|--------|---------|----------------|----------------|
| **Model Providers** | 2 | 6+ | 10+ |
| **Authentication Methods** | 1 (API Key) | 2 (API Key + Encrypted) | 3 (API Key + Encrypted + OAuth) |
| **IDE Integrations** | 0 | 1 (VS Code) | 3 (VS Code, Zed, JetBrains) |
| **Conversation Features** | 2 | 8 | 12 |
| **Plugins Available** | 0 | 5 | 20+ |
| **GitHub Stars** | N/A | 1,000+ | 5,000+ |
| **Daily Active Users** | N/A | 100+ | 1,000+ |
| **Test Coverage** | ~65% | 75% | 80%+ |

---

## 🔧 Technical Debt to Address

1. **Remove remaining shim imports** - Complete migration to new module names ✅ Done v2.3.0
2. **Consolidate documentation** - Reduce from 24 to 13 files ✅ Done v2.3.0
3. **Fix pytest warnings** - 26 warnings → 0 ✅ Done v2.3.0
4. **Add type hints** - Comprehensive typing across codebase
5. **Improve error messages** - More actionable error messages
6. **Add performance profiling** - Identify bottlenecks

---

## 📚 Related Documentation

- [`CHANGELOG.md`](../CHANGELOG.md) - Version history
- [`README.md`](../README.md) - Quick start guide
- [`QWEN.md`](../QWEN.md) - Integration guide
- [`docs/SUBAGENTS_ARCHITECTURE.md`](./SUBAGENTS_ARCHITECTURE.md) - SubAgents design
- [`docs/MCP_SERVERS_GUIDE.md`](./MCP_SERVERS_GUIDE.md) - MCP server setup

---

## 🎯 Recommendations Summary

### **Immediate Actions (This Week):**
1. ⭐ **Multi-Provider Support** - Add OpenAI, Anthropic, OpenRouter
2. ⭐ **Conversation Management** - Implement persistence and export
3. ⭐ **Model Switching UI** - Quick win, high visibility

### **Next Month:**
4. ⭐ **API Key Management** - Encrypted storage, `/keys` commands
5. ⭐ **Per-Project Config** - `.rapidwebs-config.yaml` support
6. ⭐ **Start OAuth (Phase 1)** - Google OAuth first (easier)

### **Maintain Competitive Advantages:**
- ✅ **4 approval modes** (Qwen Code only has YOLO)
- ✅ **70-85% token savings** (superior caching)
- ✅ **5 SubAgents** (more specialized than Qwen Code)
- ✅ **Command whitelisting** (better security)
- ✅ **Python cross-platform** (no Node.js 20+ requirement)

---

**Last Updated:** March 7, 2026  
**Version:** 2.3.0  
**Next Review:** April 7, 2026
