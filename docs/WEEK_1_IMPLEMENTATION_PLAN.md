# Week 1 Implementation Plan

**Date:** March 8, 2026  
**Sprint:** Week 1 (Configuration Layers + Tool Registry)  
**Goal:** Close critical architecture gaps identified in Qwen Code comparison

---

## Overview

This plan addresses two critical gaps from the architecture analysis:

1. **Limited Configuration Layers** (3 → 6 layers)
2. **No Tool Registry** (manual registration → centralized registry with conflict resolution)

**Total Effort:** 7 days  
**Files to Create:** 3  
**Files to Modify:** 5  
**Tests to Add:** 2 test files

---

## Part 1: Configuration Layers (Days 1-3)

### Current State

```
Current Configuration Layers:
1. Environment variables
2. Config file (~/.config/rapidwebs-agent/config.yaml)
3. Default values
```

### Target State

```
Target Configuration Layers (Qwen Code style):
1. CLI arguments (highest priority) ← NEW
2. Environment variables
3. Project settings (.qwen/settings.json) ← NEW
4. User settings (~/.config/rapidwebs-agent/config.yaml)
5. System settings (/etc/rapidwebs-agent/config.yaml) ← NEW
6. Default values (lowest priority)
```

### Implementation Tasks

#### Task 1.1: Create Config Layer Loader
**File:** `agent/config_layers.py` (NEW - ~180 lines)  
**Owner:** Developer  
**Duration:** 1 day

**Requirements:**
- Implement `ConfigLayerLoader` class
- Support all 6 configuration layers
- Deep merge dictionaries (nested config support)
- Handle missing layers gracefully
- Log which layers were loaded

**Key Methods:**
```python
class ConfigLayerLoader:
    def load_all(self, cli_args: Optional[Dict] = None) -> Dict[str, Any]
    def _load_cli_args(self, cli_args: Dict) -> Dict
    def _load_env_vars(self) -> Dict
    def _load_project_config(self) -> Optional[Dict]
    def _load_user_config(self) -> Optional[Dict]
    def _load_system_config(self) -> Optional[Dict]
    def _get_defaults(self) -> Dict
    def _deep_merge(self, base: Dict, override: Dict) -> Dict
```

**Acceptance Criteria:**
- [ ] All 6 layers load correctly
- [ ] Higher priority layers override lower priority
- [ ] Deep merge works for nested dictionaries
- [ ] Missing layers don't cause errors
- [ ] Logging shows which layers were loaded

---

#### Task 1.2: Update Config Class
**File:** `agent/config.py` (MODIFY - ~25 lines)  
**Owner:** Developer  
**Duration:** 0.5 days

**Changes:**
```python
# BEFORE
class Config:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self._config = self._load_config()

# AFTER
class Config:
    def __init__(
        self,
        config_path: Optional[str] = None,
        cli_args: Optional[Dict] = None
    ):
        self.config_path = config_path
        self.cli_args = cli_args or {}
        
        loader = ConfigLayerLoader()
        self._config = loader.load_all(cli_args=self.cli_args)
```

**Acceptance Criteria:**
- [ ] Config class accepts `cli_args` parameter
- [ ] All existing tests pass
- [ ] Backward compatible (cli_args optional)

---

#### Task 1.3: Update CLI to Pass CLI Args
**File:** `rapidwebs_agent/cli.py` (MODIFY - ~15 lines)  
**Owner:** Developer  
**Duration:** 0.5 days

**Changes:**
```python
# In InteractiveCLI.initialize()
config_dict = {
    'model': args.model,
    'workspace': args.workspace,
    'no_cache': args.no_cache,
    'token_limit': args.token_limit,
}
agent = Agent(config_path=args.config, cli_args=config_dict)
```

**Acceptance Criteria:**
- [ ] CLI arguments override config file settings
- [ ] Manual testing confirms precedence works

---

#### Task 1.4: Write Tests
**File:** `tests/test_config_layers.py` (NEW - ~100 lines)  
**Owner:** Developer  
**Duration:** 1 day

**Test Cases:**
```python
def test_layer_precedence():
    """Higher priority layers override lower priority."""
    
def test_project_config_detection():
    """Detect .qwen/settings.json in current directory."""
    
def test_system_config_loading():
    """Load system config from /etc or ProgramData."""
    
def test_deep_merge_nested():
    """Deep merge works for nested dictionaries."""
    
def test_missing_layers_graceful():
    """Missing layers don't cause errors."""
    
def test_env_var_parsing():
    """Environment variables parsed correctly."""
```

**Acceptance Criteria:**
- [ ] All 6 test cases pass
- [ ] Test coverage > 80% for config_layers.py

---

### Configuration Layer File Locations

| Layer | Location | Format |
|-------|----------|--------|
| CLI args | Command line | Dict (runtime) |
| Env vars | Environment | `RW_*` prefix |
| Project | `.qwen/settings.json` (cwd) | JSON |
| User | `~/.config/rapidwebs-agent/config.yaml` | YAML |
| System | `/etc/rapidwebs-agent/config.yaml` (Linux) | YAML |
| | `C:\ProgramData\rapidwebs-agent\config.yaml` (Windows) | |
| Defaults | `agent/config.py` | Dict |

---

## Part 2: Tool Registry (Days 4-6)

### Current State

```python
# agent/skills_manager.py - Current implementation
class SkillManager:
    def __init__(self, config):
        self.skills = {}
        self._register_builtin_skills()
    
    def _register_builtin_skills(self):
        # Manual registration, no conflict handling
        self.skills['fs'] = FileSystemSkill(config)
        self.skills['terminal'] = TerminalSkill(config)
```

**Problems:**
- No conflict detection
- No server prefixing for MCP tools
- No status tracking
- No include/exclude filtering

### Target State

```python
# Centralized registry with:
# - Automatic conflict detection and resolution
# - Server prefixing for external tools
# - Status tracking (registered, connected, disconnected, error)
# - Include/exclude filtering for MCP servers
```

### Implementation Tasks

#### Task 2.1: Create Tool Registry
**File:** `agent/tool_registry.py` (NEW - ~220 lines)  
**Owner:** Developer  
**Duration:** 1.5 days

**Requirements:**
- Implement `ToolRegistry` class
- Implement `ToolInfo` dataclass
- Implement `ToolStatus` enum
- Automatic conflict resolution with prefixing
- Include/exclude filtering
- Status tracking

**Key Classes:**
```python
class ToolStatus(Enum):
    REGISTERED = "registered"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

@dataclass
class ToolInfo:
    name: str
    original_name: str
    server: Optional[str]
    status: ToolStatus
    schema: Dict
    risk_level: str
    enabled: bool

class ToolRegistry:
    def register(self, name, skill, server, schema, risk_level, include_tools, exclude_tools) -> str
    def get(self, name) -> Optional[Any]
    def get_tool_info(self, name) -> Optional[ToolInfo]
    def list_tools(self, server) -> List[ToolInfo]
    def update_status(self, name, status)
    def unregister(self, name) -> bool
    def _resolve_conflict(self, name, server) -> str
```

**Conflict Resolution Strategy:**
1. If no conflict → use original name
2. If conflict + has server → prefix with `server__name`
3. If conflict + no server → add numeric suffix `name__2`

**Acceptance Criteria:**
- [ ] Tools register successfully
- [ ] Conflicts resolved automatically
- [ ] Include/exclude filtering works
- [ ] Status tracking functional
- [ ] Logging shows registration details

---

#### Task 2.2: Integrate Registry with SkillManager
**File:** `agent/skills_manager.py` (MODIFY - ~40 lines)  
**Owner:** Developer  
**Duration:** 1 day

**Changes:**
```python
# BEFORE
class SkillManager:
    def __init__(self, config):
        self.skills = {}
        self._register_builtin_skills()

# AFTER
class SkillManager:
    def __init__(self, config):
        self.config = config
        self.registry = ToolRegistry()
        self._register_builtin_skills()
    
    def _register_builtin_skills(self):
        self.registry.register(
            name='fs',
            skill=FileSystemSkill(self.config),
            schema=FS_SKILL_SCHEMA,
            risk_level='read'
        )
        # ... register other skills
    
    async def execute(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        skill = self.registry.get(tool_name)
        if not skill:
            return {'success': False, 'error': f'Unknown tool: {tool_name}'}
        
        tool_info = self.registry.get_tool_info(tool_name)
        if tool_info and not tool_info.enabled:
            return {'success': False, 'error': f'Tool {tool_name} is disabled'}
        
        try:
            result = await skill.execute(**kwargs)
            return result
        except Exception as e:
            self.registry.update_status(tool_name, ToolStatus.ERROR)
            return {'success': False, 'error': str(e)}
```

**Acceptance Criteria:**
- [ ] All built-in skills register via registry
- [ ] Tool execution works through registry
- [ ] Error handling updates status
- [ ] Existing tests pass

---

#### Task 2.3: Create MCP Client Stub
**File:** `agent/mcp_client.py` (NEW - ~60 lines)  
**Owner:** Developer  
**Duration:** 0.5 days

**Requirements:**
- Create foundation for Week 2 MCP implementation
- Stub methods for future server discovery
- Integrate with tool registry

**Key Methods:**
```python
class MCPClient:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.servers: Dict[str, Dict] = {}
    
    async def discover_server(self, server_name: str, config: Dict) -> List[str]:
        """Discover tools from an MCP server (stub for Week 2)."""
        logger.info(f"MCP server {server_name} discovery (stub)")
        return []
    
    async def connect_server(self, server_name: str) -> bool:
        """Connect to an MCP server (stub for Week 2)."""
        return False
    
    async def disconnect_server(self, server_name: str) -> bool:
        """Disconnect from an MCP server (stub for Week 2)."""
        return False
```

**Acceptance Criteria:**
- [ ] MCP client stub compiles
- [ ] Integrates with tool registry
- [ ] Clear TODO comments for Week 2 work
- [ ] Documentation explains future implementation

---

#### Task 2.4: Update Agent to Expose Registry
**File:** `agent/agent.py` (MODIFY - ~5 lines)  
**Owner:** Developer  
**Duration:** 0.25 days

**Changes:**
```python
class Agent:
    def __init__(self, config_path: Optional[str] = None, cli_args: Optional[Dict] = None):
        # ... existing init ...
        
        self.skill_manager = SkillManager(self.config)
        
        # Expose registry for MCP client and external access
        self.tool_registry = self.skill_manager.registry
```

**Acceptance Criteria:**
- [ ] Registry accessible via `agent.tool_registry`
- [ ] No breaking changes to existing API

---

#### Task 2.5: Write Tests
**File:** `tests/test_tool_registry.py` (NEW - ~120 lines)  
**Owner:** Developer  
**Duration:** 0.75 days

**Test Cases:**
```python
def test_register_builtin_tool():
    """Built-in tools register successfully."""
    
def test_conflict_resolution_with_server():
    """Server tools get prefixed on conflict."""
    
def test_conflict_resolution_without_server():
    """Non-server tools get numeric suffix on conflict."""
    
def test_exclude_tools():
    """Excluded tools are not registered."""
    
def test_include_tools():
    """Only included tools are registered."""
    
def test_status_tracking():
    """Tool status updates correctly."""
    
def test_list_tools_filter():
    """List tools filtered by server."""
    
def test_unregister_tool():
    """Tools can be unregistered."""
```

**Acceptance Criteria:**
- [ ] All 8 test cases pass
- [ ] Test coverage > 80% for tool_registry.py

---

## Part 3: Testing & Documentation (Day 7)

### Task 3.1: Integration Testing
**Duration:** 0.5 days

**Test Scenarios:**
1. Config layers load in correct order
2. CLI args override all other layers
3. Project config auto-detected
4. Tool registry handles conflicts
5. All existing tests still pass

**Acceptance Criteria:**
- [ ] Run full test suite - all tests pass
- [ ] Manual testing confirms features work

---

### Task 3.2: Documentation Updates
**Duration:** 0.5 days

**Files to Update:**
- `README.md` - Add configuration layer documentation
- `docs/CONFIGURATION.md` (NEW) - Detailed config guide
- `docs/TOOL_REGISTRY.md` (NEW) - Registry usage guide

**Acceptance Criteria:**
- [ ] Configuration layers documented
- [ ] Tool registry usage documented
- [ ] Examples provided for both features

---

## File Summary

### Files to Create (3)
| File | Lines | Purpose |
|------|-------|---------|
| `agent/config_layers.py` | ~180 | Configuration layer loader |
| `agent/tool_registry.py` | ~220 | Centralized tool registry |
| `agent/mcp_client.py` | ~60 | MCP client stub for Week 2 |

### Files to Modify (5)
| File | Lines Changed | Purpose |
|------|---------------|---------|
| `agent/config.py` | ~25 | Integrate layer loader |
| `agent/skills_manager.py` | ~40 | Use registry instead of dict |
| `agent/agent.py` | ~5 | Expose registry |
| `rapidwebs_agent/cli.py` | ~15 | Pass CLI args to Config |
| `README.md` | ~30 | Document new features |

### Tests to Create (2)
| File | Lines | Test Cases |
|------|-------|------------|
| `tests/test_config_layers.py` | ~100 | 6 test cases |
| `tests/test_tool_registry.py` | ~120 | 8 test cases |

---

## Schedule

| Day | Tasks | Deliverables |
|-----|-------|--------------|
| **Day 1** | Task 1.1: Config layer loader | `config_layers.py` |
| **Day 2** | Task 1.2-1.3: Integrate config | Config working end-to-end |
| **Day 3** | Task 1.4: Config tests | All config tests pass |
| **Day 4** | Task 2.1: Tool registry | `tool_registry.py` |
| **Day 5** | Task 2.2-2.4: Integrate registry | Registry working end-to-end |
| **Day 6** | Task 2.5: Registry tests + MCP stub | All registry tests pass |
| **Day 7** | Task 3.1-3.2: Testing + docs | Full test suite passes |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing config | Low | High | Backward compatible - existing config becomes "user" layer |
| Tool name conflicts | Medium | Medium | Automatic prefixing, no manual changes needed |
| Performance (6 layers) | Low | Low | Cache merged config, reload only on change |
| MCP stub confusion | Medium | Low | Clear TODO comments, documentation |
| Test coverage gaps | Medium | Medium | Require >80% coverage for new files |

---

## Success Criteria

### Configuration Layers
- [ ] 6 layers load in correct precedence order
- [ ] Project config auto-detected from `.qwen/settings.json`
- [ ] CLI args override all other layers
- [ ] Backward compatible with existing configs
- [ ] All tests pass (>80% coverage)

### Tool Registry
- [ ] Built-in skills registered via registry
- [ ] Conflict resolution works (prefixing)
- [ ] Include/exclude filtering works
- [ ] Status tracking functional
- [ ] MCP stub ready for Week 2 extension
- [ ] All tests pass (>80% coverage)

### Overall
- [ ] Full test suite passes
- [ ] No breaking changes to existing API
- [ ] Documentation complete
- [ ] Code reviewed and approved

---

## Next Steps (Week 2 Preview)

After Week 1 completion, Week 2 will implement:

1. **OAuth 2.0 Client** (1-2 weeks)
   - OAuth flow for remote MCP servers
   - Token storage with refresh
   - Local callback server

2. **MCP Client Full Implementation** (2-3 weeks)
   - MCP protocol implementation
   - Transport layers (Stdio, SSE, HTTP)
   - Tool discovery and execution

---

**Approval Required:**  
This plan requires approval before implementation begins. Once approved, development can start on Day 1 tasks.
