# Qwen Code - SubAgents Architecture & Implementation Plan

**Version:** 1.0.0  
**Last Updated:** March 4, 2026  
**Status:** Implementation Planning

---

## 📋 Overview

SubAgents enable **delegated task execution** to specialized agents with isolated contexts. The main agent orchestrates tasks while subagents handle specific domains in parallel or sequentially.

---

## 🏗️ Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                         Main Agent                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Orchestrator                                           │    │
│  │  - Task decomposition                                   │    │
│  │  - Subagent assignment                                  │    │
│  │  - Result aggregation                                   │    │
│  │  - Conflict resolution                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │   Code Agent    │ │   Test Agent    │ │   Docs Agent    │
    │  ┌───────────┐  │ │  ┌───────────┐  │ │  ┌───────────┐  │
    │  │ - Refactor│  │ │  │ - Write   │  │ │  │ - Generate│  │
    │  │ - Debug   │  │ │  │ - Run     │  │ │  │ - Explain │  │
    │  │ - Review  │  │ │  │ - Fix     │  │ │  │ - Summarize│ │
    │  └───────────┘  │ │  └───────────┘  │ │  └───────────┘  │
    │  Isolated Context│ │ Isolated Context│ │ Isolated Context│
    └─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Key Characteristics

| Feature | Description |
|---------|-------------|
| **Isolated Context** | Each subagent has its own context window |
| **Parallel Execution** | Up to 3 subagents can run concurrently |
| **Result Merging** | Outputs merged back to main agent context |
| **Sequential Thinking** | Complex tasks decomposed into steps |
| **Task Delegation** | Main agent assigns based on capability |

---

## 🎯 SubAgent Types

### 1. Code Agent

**Purpose:** Code manipulation, refactoring, debugging

| Capability | Tools Used | Token Budget |
|------------|------------|--------------|
| Refactoring | `read_file`, `edit_file`, LSP | 5,000-15,000 |
| Debugging | `read_file`, `run_shell_command`, diagnostics | 3,000-10,000 |
| Code Review | `read_multiple_files`, LSP | 2,000-8,000 |
| Implementation | `write_file`, `edit_file`, `run_shell_command` | 5,000-20,000 |

**Configuration:**
```json
{
  "subagents": {
    "code": {
      "enabled": true,
      "maxTokenBudget": 20000,
      "allowedTools": ["read_file", "edit_file", "write_file", "run_shell_command"],
      "lspIntegration": true,
      "parallelLimit": 2
    }
  }
}
```

---

### 2. Test Agent

**Purpose:** Test generation, execution, and fixing

| Capability | Tools Used | Token Budget |
|------------|------------|--------------|
| Test Writing | `read_file`, `write_file`, `list_directory` | 3,000-10,000 |
| Test Running | `run_shell_command`, output parsing | 2,000-5,000 |
| Test Fixing | `read_file`, `edit_file`, diagnostics | 3,000-8,000 |
| Coverage Analysis | `run_shell_command`, report parsing | 2,000-5,000 |

**Configuration:**
```json
{
  "subagents": {
    "test": {
      "enabled": true,
      "maxTokenBudget": 10000,
      "allowedTools": ["read_file", "write_file", "run_shell_command"],
      "testFrameworks": ["pytest", "unittest", "jest"],
      "autoRun": true
    }
  }
}
```

---

### 3. Docs Agent

**Purpose:** Documentation generation and explanation

| Capability | Tools Used | Token Budget |
|------------|------------|--------------|
| Doc Generation | `read_file`, `write_file`, Context7 | 2,000-8,000 |
| Code Explanation | `read_file`, LSP symbols | 1,000-5,000 |
| API Summarization | `read_multiple_files`, summarization | 3,000-10,000 |
| Changelog | `read_file` (git history), `write_file` | 2,000-6,000 |

**Configuration:**
```json
{
  "subagents": {
    "docs": {
      "enabled": true,
      "maxTokenBudget": 10000,
      "allowedTools": ["read_file", "write_file", "query-docs"],
      "outputFormats": ["markdown", "rst", "docstring"],
      "context7Enabled": true
    }
  }
}
```

---

### 4. Research Agent

**Purpose:** Web search, documentation lookup, information gathering

| Capability | Tools Used | Token Budget |
|------------|------------|--------------|
| Web Search | `brave_web_search`, `fetch` | 1,000-3,000 |
| Documentation | `query-docs`, `read_file` | 2,000-8,000 |
| Code Search | `search_files`, `read_file` | 1,000-5,000 |
| Information Synthesis | `sequential_thinking`, summarization | 3,000-10,000 |

**Configuration:**
```json
{
  "subagents": {
    "research": {
      "enabled": true,
      "maxTokenBudget": 10000,
      "allowedTools": ["brave_web_search", "fetch", "query-docs", "sequential_thinking"],
      "sources": ["web", "documentation", "codebase"],
      "summarizeResults": true
    }
  }
}
```

---

### 5. Security Agent

**Purpose:** Security auditing, vulnerability scanning

| Capability | Tools Used | Token Budget |
|------------|------------|--------------|
| Dependency Audit | `read_file` (package.json/requirements.txt) | 1,000-3,000 |
| Code Scanning | `read_file`, pattern matching | 3,000-10,000 |
| Config Review | `read_file`, security best practices | 2,000-6,000 |
| Report Generation | `write_file`, summarization | 2,000-5,000 |

**Configuration:**
```json
{
  "subagents": {
    "security": {
      "enabled": true,
      "maxTokenBudget": 15000,
      "allowedTools": ["read_file", "search_files", "write_file"],
      "scanners": ["dependencies", "code", "config"],
      "severity_threshold": "medium"
    }
  }
}
```

---

## 🚀 Implementation Plan

### Tier 1: Core SubAgent Framework

**Timeline:** Week 1-2

#### Phase 1.1: SubAgent Protocol
- [ ] Define subagent communication protocol
- [ ] Implement task delegation interface
- [ ] Create result aggregation system
- [ ] Build context isolation mechanism

```python
# agent/subagents/protocol.py
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

class SubAgentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class SubAgentTask:
    id: str
    type: str  # code, test, docs, research, security
    description: str
    context: Dict[str, Any]
    token_budget: int
    timeout: int = 300

@dataclass
class SubAgentResult:
    task_id: str
    status: SubAgentStatus
    output: str
    token_usage: int
    error: Optional[str] = None
```

#### Phase 1.2: SubAgent Manager
- [ ] Implement subagent lifecycle management
- [ ] Add parallel execution with concurrency limits
- [ ] Build task queue with priority scheduling
- [ ] Create cancellation and timeout handling

```python
# agent/subagents/manager.py
class SubAgentManager:
    def __init__(self, config: Config):
        self.config = config
        self.agents: Dict[str, SubAgent] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.max_concurrent = config.get('subagents.max_concurrent', 3)
    
    async def delegate(self, task: SubAgentTask) -> SubAgentResult:
        """Delegate task to appropriate subagent"""
        agent = self._get_agent(task.type)
        return await agent.execute(task)
    
    async def delegate_parallel(self, tasks: List[SubAgentTask]) -> List[SubAgentResult]:
        """Execute multiple tasks in parallel (max 3)"""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def run_with_semaphore(task):
            async with semaphore:
                return await self.delegate(task)
        
        return await asyncio.gather(*[run_with_semaphore(t) for t in tasks])
```

#### Phase 1.3: Context Isolation
- [ ] Implement per-subagent context windows
- [ ] Build context snapshot/restore mechanism
- [ ] Add context merging after subagent completion
- [ ] Prevent context thrashing between agents

```python
# agent/subagents/context.py
class SubAgentContext:
    def __init__(self, parent_context: Context, isolation_level: str = "full"):
        self.parent = parent_context
        self.isolation_level = isolation_level
        self.local_context = Context()
        self.shared_symbols: Set[str] = set()
    
    def snapshot(self) -> Dict[str, Any]:
        """Create context snapshot for subagent"""
        if self.isolation_level == "full":
            return {"messages": [], "files": {}}
        elif self.isolation_level == "partial":
            return {"messages": self.parent.messages[-5:], "files": self.parent.active_files}
    
    def merge(self, result: SubAgentResult) -> Context:
        """Merge subagent results back to parent context"""
        self.parent.messages.extend(result.context_updates)
        return self.parent
```

**Deliverables:**
- Working subagent protocol
- Basic code and test agents
- Parallel execution support
- Context isolation

---

### Tier 2: Advanced SubAgent Features

**Timeline:** Week 3-4

#### Phase 2.1: Sequential Thinking Integration
- [ ] Integrate sequential-thinking MCP for task decomposition
- [ ] Build automatic subtask generation
- [ ] Implement dependency-aware scheduling
- [ ] Add progress tracking and reporting

```python
# agent/subagents/decomposition.py
class TaskDecomposer:
    def __init__(self, sequential_thinking_tool):
        self.tool = sequential_thinking_tool
    
    async def decompose(self, task: str) -> List[SubAgentTask]:
        """Decompose complex task into subagent tasks"""
        decomposition = await self.tool.think(
            task=task,
            steps=["identify_components", "assign_agents", "determine_order"]
        )
        
        tasks = []
        for step in decomposition.steps:
            tasks.append(SubAgentTask(
                id=step.id,
                type=step.agent_type,
                description=step.description,
                context=step.context,
                token_budget=step.token_budget,
                dependencies=step.dependencies
            ))
        
        return self._topological_sort(tasks)
```

#### Phase 2.2: Result Aggregation & Conflict Resolution
- [ ] Implement intelligent result merging
- [ ] Build conflict detection for overlapping edits
- [ ] Add consensus mechanism for conflicting results
- [ ] Create unified output formatting

```python
# agent/subagents/aggregation.py
class ResultAggregator:
    def __init__(self):
        self.results: List[SubAgentResult] = []
        self.conflicts: List[Conflict] = []
    
    def add_result(self, result: SubAgentResult):
        self.results.append(result)
        self._detect_conflicts(result)
    
    def _detect_conflicts(self, new_result: SubAgentResult):
        """Detect conflicts with existing results"""
        for existing in self.results:
            if self._has_file_conflict(existing, new_result):
                self.conflicts.append(Conflict(
                    results=[existing, new_result],
                    files=new_result.modified_files & existing.modified_files
                ))
    
    async def resolve_conflicts(self, main_agent) -> List[SubAgentResult]:
        """Use main agent to resolve detected conflicts"""
        for conflict in self.conflicts:
            resolution = await main_agent.resolve_conflict(conflict)
            conflict.apply_resolution(resolution)
        return self.results
```

#### Phase 2.3: SubAgent Specialization
- [ ] Implement docs agent with Context7 integration
- [ ] Build security agent with vulnerability patterns
- [ ] Create research agent with web search
- [ ] Add performance profiling agent

**Deliverables:**
- All 5 subagent types implemented
- Sequential thinking integration
- Conflict resolution
- Result aggregation

---

### Tier 3: Production Features

**Timeline:** Week 5-6

#### Phase 3.1: SubAgent Orchestration
- [ ] Build visual task dependency graph
- [ ] Implement dynamic resource allocation
- [ ] Add adaptive token budget management
- [ ] Create execution timeline optimization

```python
# agent/subagents/orchestrator.py
class SubAgentOrchestrator:
    def __init__(self, manager: SubAgentManager, decomposer: TaskDecomposer):
        self.manager = manager
        self.decomposer = decomposer
        self.execution_graph: nx.DiGraph = nx.DiGraph()
    
    async def execute(self, task_description: str) -> str:
        """Orchestrate full task execution"""
        # Decompose into subtasks
        tasks = await self.decomposer.decompose(task_description)
        
        # Build execution graph
        self._build_execution_graph(tasks)
        
        # Execute with optimal scheduling
        results = await self._execute_graph()
        
        # Aggregate and format results
        return self._format_results(results)
```

#### Phase 3.2: Memory & Learning
- [ ] Store successful subagent patterns in memory
- [ ] Implement pattern-based task routing
- [ ] Build performance metrics tracking
- [ ] Add adaptive agent selection

```python
# agent/subagents/learning.py
class SubAgentLearner:
    def __init__(self, memory_client):
        self.memory = memory_client
        self.metrics: Dict[str, Metric] = {}
    
    async def record_execution(self, task: SubAgentTask, result: SubAgentResult):
        """Record execution for future learning"""
        pattern = {
            "task_type": task.type,
            "description_pattern": self._extract_pattern(task.description),
            "success": result.status == SubAgentStatus.COMPLETED,
            "token_usage": result.token_usage,
            "duration": result.duration
        }
        
        await self.memory.create_entity(
            type="subagent_execution",
            data=pattern
        )
    
    async def recommend_agent(self, task_description: str) -> str:
        """Recommend best agent based on historical patterns"""
        similar_executions = await self.memory.search_nodes(
            query=task_description,
            type="subagent_execution",
            limit=10
        )
        
        # Analyze success rates per agent type
        agent_scores = self._calculate_agent_scores(similar_executions)
        return max(agent_scores, key=agent_scores.get)
```

#### Phase 3.3: Monitoring & Observability
- [ ] Implement subagent execution tracing
- [ ] Add token usage tracking per agent
- [ ] Build performance dashboards
- [ ] Create alerting for failures/timeouts

**Deliverables:**
- Full orchestration system
- Learning from execution history
- Monitoring and observability
- Production-ready reliability

---

## 📊 Configuration Schema

### Complete SubAgent Configuration

```json
{
  "subagents": {
    "enabled": true,
    "max_concurrent": 3,
    "default_token_budget": 10000,
    "default_timeout": 300,
    "context_isolation": "full",
    "agents": {
      "code": {
        "enabled": true,
        "max_token_budget": 20000,
        "allowed_tools": ["read_file", "edit_file", "write_file", "run_shell_command"],
        "lsp_integration": true,
        "parallel_limit": 2
      },
      "test": {
        "enabled": true,
        "max_token_budget": 10000,
        "allowed_tools": ["read_file", "write_file", "run_shell_command"],
        "test_frameworks": ["pytest", "unittest", "jest"],
        "auto_run": true
      },
      "docs": {
        "enabled": true,
        "max_token_budget": 10000,
        "allowed_tools": ["read_file", "write_file", "query-docs"],
        "output_formats": ["markdown", "rst", "docstring"],
        "context7_enabled": true
      },
      "research": {
        "enabled": true,
        "max_token_budget": 10000,
        "allowed_tools": ["brave_web_search", "fetch", "query-docs", "sequential_thinking"],
        "sources": ["web", "documentation", "codebase"],
        "summarize_results": true
      },
      "security": {
        "enabled": true,
        "max_token_budget": 15000,
        "allowed_tools": ["read_file", "search_files", "write_file"],
        "scanners": ["dependencies", "code", "config"],
        "severity_threshold": "medium"
      }
    },
    "orchestration": {
      "sequential_thinking": true,
      "conflict_resolution": "main_agent",
      "result_aggregation": "intelligent",
      "learning_enabled": true
    }
  }
}
```

---

## 🔗 Integration Points

### With MCP Servers

| MCP Server | SubAgent Usage |
|------------|----------------|
| **filesystem** | All agents for file operations |
| **memory** | Learning, pattern storage, cross-session context |
| **sequential-thinking** | Task decomposition, complex problem solving |
| **context7** | Docs agent for API documentation |
| **git** | Code agent for history, docs agent for changelogs |

### With LSP

| LSP Feature | SubAgent Usage |
|-------------|----------------|
| **Definitions** | Code agent for symbol resolution |
| **References** | Code agent for impact analysis |
| **Diagnostics** | Test agent for error detection |
| **Call Hierarchy** | Code agent for dependency tracking |

---

## 📈 Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Task Completion Rate** | >95% | Successful tasks / Total tasks |
| **Average Token Usage** | <15,000/turn | Tokens per subagent execution |
| **Parallel Efficiency** | >2.5x | Speedup vs sequential |
| **Conflict Rate** | <5% | Tasks with conflicts / Total tasks |
| **Context Isolation Overhead** | <10% | Additional tokens for isolation |

---

## 📚 References

| Resource | URL |
|----------|-----|
| **Qwen Code SubAgents Docs** | https://qwenlm.github.io/qwen-code-docs/en/users/features/subagents/ |
| **Sequential Thinking MCP** | https://github.com/modelcontextprotocol/servers/tree/main/src/sequential-thinking |
| **Memory MCP** | https://github.com/modelcontextprotocol/servers/tree/main/src/memory |
