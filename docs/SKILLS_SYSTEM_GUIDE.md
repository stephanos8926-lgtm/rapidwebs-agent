# Qwen Code - Skills System & Implementation Plan

**Version:** 1.0.0  
**Last Updated:** March 4, 2026  
**Status:** Implementation Planning

---

## 📋 Overview

The **Skills System** provides modular capability plugins that extend Qwen Code's functionality. Skills are self-contained modules that encapsulate specific capabilities with defined tools, permissions, and dependencies.

---

## 🏗️ Architecture

### Skills Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                      Skills Manager                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  - Skill loading from .qwen/skills/                     │    │
│  │  - Dependency resolution                                │    │
│  │  - Permission enforcement                               │    │
│  │  - Tool routing                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │  Terminal Skill │ │  Filesystem     │ │    Web Skill    │
    │  ┌───────────┐  │ │  │  Skill      │  │ │  ┌───────────┐  │
    │  │ - Execute │  │ │  │  ┌─────────┐│  │ │  │ - Fetch   │  │
    │  │ - Capture │  │ │  │  │ - Read  ││  │ │  │ - Search  │  │
    │  │ - Validate│  │ │  │  │ - Write ││  │ │  │ - Extract │  │
    │  └───────────┘  │ │  │  │ - Search││  │ │  └───────────┘  │
    │  Permissions:   │ │  │  └─────────┘│  │ │  Permissions:   │
    │  - whitelist    │ │  │  Permissions│  │ │  - domains      │
    │  - timeout      │ │  │  - paths    │  │ │  - rate_limit   │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Skill Schema

```typescript
interface Skill {
  // Metadata
  name: string;                    // Unique identifier
  version: string;                 // Semantic version
  description: string;             // Human-readable description
  author?: string;                 // Skill author
  
  // Capabilities
  tools: ToolDefinition[];         // Available tools
  permissions: PermissionSet;      // Access permissions
  dependencies: Dependency[];      // Required MCP servers, env vars
  
  // Configuration
  config: SkillConfig;             // Skill-specific settings
  enabled: boolean;                // Enable/disable flag
  
  // Execution
  execute: (input: SkillInput) => Promise<SkillOutput>;
  validate: (input: SkillInput) => ValidationResult;
}
```

---

## 🎯 Core Skills

### 1. Terminal Executor Skill

**Purpose:** Safe command execution with whitelisting and output capture

#### Capabilities

| Tool | Description | Permissions |
|------|-------------|-------------|
| `execute_command` | Run whitelisted commands | Command whitelist |
| `capture_output` | Capture stdout/stderr | Output size limit |
| `check_exit_code` | Validate command success | None |
| `timeout_command` | Execute with timeout | Timeout setting |

#### Configuration

```json
{
  "skills": {
    "terminal_executor": {
      "enabled": true,
      "whitelist": [
        "python", "python3",
        "npm", "npx", "yarn", "pnpm",
        "git",
        "ls", "dir", "pwd", "cd",
        "cat", "type", "head", "tail",
        "grep", "find", "rg",
        "pytest", "jest", "unittest",
        "pip", "pip3", "uv",
        "docker", "docker-compose"
      ],
      "blacklist": [
        "rm -rf /",
        "sudo",
        "chmod -R 777",
        "mkfs",
        "dd",
        ":(){ :|:& };:"
      ],
      "max_execution_time": 30,
      "timeout": 10,
      "max_output_size": 100000,
      "shell": "bash",
      "working_directory": ".",
      "env_inheritance": true
    }
  }
}
```

#### Implementation

```python
# agent/skills/terminal_executor.py
import subprocess
import shlex
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import asyncio

@dataclass
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int
    duration: float
    timed_out: bool

class TerminalExecutorSkill:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.whitelist = set(config.get('whitelist', []))
        self.blacklist = config.get('blacklist', [])
        self.max_time = config.get('max_execution_time', 30)
        self.max_output = config.get('max_output_size', 100000)
    
    def validate_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """Validate command against whitelist and blacklist"""
        if not command or not command.strip():
            return False, "Empty command"
        
        try:
            parsed = shlex.split(command)
            if not parsed:
                return False, "Failed to parse command"
            
            base_cmd = parsed[0]
            
            # Check blacklist first
            for pattern in self.blacklist:
                if pattern in command:
                    return False, f"Command contains blacklisted pattern: {pattern}"
            
            # Check whitelist
            if base_cmd not in self.whitelist:
                return False, f"Command '{base_cmd}' not in whitelist"
            
            # Block dangerous patterns
            dangerous = ['$', '`', '|', ';', '&', '>', '<']
            for char in dangerous:
                if char in command:
                    return False, f"Shell operator '{char}' not allowed"
            
            return True, None
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    async def execute(self, command: str, timeout: Optional[int] = None) -> CommandResult:
        """Execute validated command with timeout"""
        valid, error = self.validate_command(command)
        if not valid:
            raise PermissionError(error)
        
        timeout = timeout or self.max_time
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config.get('working_directory', '.')
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                # Truncate output if needed
                stdout_str = self._truncate_output(stdout.decode())
                stderr_str = self._truncate_output(stderr.decode())
                
                return CommandResult(
                    stdout=stdout_str,
                    stderr=stderr_str,
                    exit_code=process.returncode,
                    duration=timeout,
                    timed_out=False
                )
            except asyncio.TimeoutError:
                process.kill()
                return CommandResult(
                    stdout="",
                    stderr=f"Command timed out after {timeout}s",
                    exit_code=-1,
                    duration=timeout,
                    timed_out=True
                )
        except Exception as e:
            return CommandResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                duration=0,
                timed_out=False
            )
    
    def _truncate_output(self, output: str) -> str:
        """Truncate output to max size"""
        if len(output) > self.max_output:
            return output[:self.max_output] + "\n... [output truncated]"
        return output
```

---

### 2. Filesystem Skill

**Purpose:** Secure file operations with path validation and access control

#### Capabilities

| Tool | Description | Permissions |
|------|-------------|-------------|
| `read_file` | Read file contents | Read paths |
| `write_file` | Write/create files | Write paths |
| `edit_file` | Patch existing files | Write paths |
| `list_directory` | List directory contents | Read paths |
| `search_files` | Search for files | Read paths |
| `create_directory` | Create directories | Write paths |
| `move_file` | Move/rename files | Write paths |
| `copy_file` | Copy files | Read + Write paths |
| `delete_file` | Delete files | Delete paths (restricted) |

#### Configuration

```json
{
  "skills": {
    "filesystem": {
      "enabled": true,
      "allowed_paths": ["./agent", "./tools", "./docs", "./tests"],
      "restricted_paths": ["./.venv", "./node_modules", "./.git"],
      "max_file_size": 524288,
      "max_files_per_operation": 10,
      "require_confirmation_for": ["delete", "overwrite"],
      "backup_on_write": true,
      "backup_directory": "./.qwen/backups"
    }
  }
}
```

#### Implementation

```python
# agent/skills/filesystem.py
from pathlib import Path
from typing import Dict, Any, List, Optional
import shutil
import json
from datetime import datetime

class FilesystemSkill:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.allowed_paths = [Path(p).resolve() for p in config.get('allowed_paths', [])]
        self.restricted_paths = [Path(p).resolve() for p in config.get('restricted_paths', [])]
        self.max_size = config.get('max_file_size', 524288)  # 512KB
        self.backup_dir = Path(config.get('backup_directory', './.qwen/backups'))
    
    def _validate_path(self, path: Path, operation: str) -> Tuple[bool, Optional[str]]:
        """Validate path is within allowed boundaries"""
        resolved = path.resolve()
        
        # Check restricted paths
        for restricted in self.restricted_paths:
            try:
                resolved.relative_to(restricted)
                return False, f"Path is within restricted directory: {restricted}"
            except ValueError:
                pass
        
        # Check allowed paths (if specified)
        if self.allowed_paths:
            for allowed in self.allowed_paths:
                try:
                    resolved.relative_to(allowed)
                    return True, None
                except ValueError:
                    continue
            return False, f"Path outside allowed directories"
        
        return True, None
    
    async def read_file(self, path: str, encoding: str = 'utf-8') -> str:
        """Read file contents with size limit"""
        file_path = Path(path)
        valid, error = self._validate_path(file_path, 'read')
        if not valid:
            raise PermissionError(error)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        file_size = file_path.stat().st_size
        if file_size > self.max_size:
            raise ValueError(f"File too large: {file_size} bytes (max: {self.max_size})")
        
        return file_path.read_text(encoding=encoding)
    
    async def write_file(self, path: str, content: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """Write file with backup"""
        file_path = Path(path)
        valid, error = self._validate_path(file_path, 'write')
        if not valid:
            raise PermissionError(error)
        
        # Create backup if file exists
        if file_path.exists() and self.config.get('backup_on_write', True):
            self._create_backup(file_path)
        
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_path.write_text(content, encoding=encoding)
        
        return {
            "path": str(file_path),
            "bytes_written": len(content.encode(encoding)),
            "backup_created": file_path.exists()
        }
    
    def _create_backup(self, path: Path) -> Path:
        """Create timestamped backup of file"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{path.name}.{timestamp}.bak"
        backup_path = self.backup_dir / backup_name
        shutil.copy2(path, backup_path)
        return backup_path
```

---

### 3. Web Skill

**Purpose:** Web fetching, searching, and content extraction

#### Capabilities

| Tool | Description | Permissions |
|------|-------------|-------------|
| `fetch_url` | Fetch web content | Allowed domains |
| `search_web` | Web search (Brave/Google) | API key required |
| `extract_content` | Extract main content from HTML | None |
| `check_link` | Validate URL accessibility | None |

#### Configuration

```json
{
  "skills": {
    "web": {
      "enabled": true,
      "allowed_domains": ["*.github.com", "*.npmjs.com", "*.python.org", "*.readthedocs.io"],
      "blocked_domains": ["*.facebook.com", "*.twitter.com"],
      "max_response_size": 1000000,
      "timeout": 30,
      "user_agent": "RapidWebs-Agent/1.0",
      "respect_robots_txt": true,
      "rate_limit": {
        "requests_per_minute": 10,
        "requests_per_hour": 100
      },
      "api_keys": {
        "brave_search": "${BRAVE_API_KEY}"
      }
    }
  }
}
```

#### Implementation

```python
# agent/skills/web.py
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
import asyncio

class WebSkill:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.allowed_domains = config.get('allowed_domains', [])
        self.blocked_domains = config.get('blocked_domains', [])
        self.max_size = config.get('max_response_size', 1000000)
        self.timeout = config.get('timeout', 30)
        self.rate_limiter = asyncio.Semaphore(
            config.get('rate_limit', {}).get('requests_per_minute', 10)
        )
    
    def _validate_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Validate URL against domain restrictions"""
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Check blocked domains
        for pattern in self.blocked_domains:
            if self._domain_matches(domain, pattern):
                return False, f"Domain blocked: {domain}"
        
        # Check allowed domains (if specified)
        if self.allowed_domains:
            for pattern in self.allowed_domains:
                if self._domain_matches(domain, pattern):
                    return True, None
            return False, f"Domain not in allowed list: {domain}"
        
        return True, None
    
    def _domain_matches(self, domain: str, pattern: str) -> bool:
        """Check if domain matches pattern (supports wildcards)"""
        if pattern.startswith('*.'):
            return domain.endswith(pattern[1:]) or domain == pattern[2:]
        return domain == pattern
    
    async def fetch_url(self, url: str) -> Dict[str, Any]:
        """Fetch URL content with restrictions"""
        valid, error = self._validate_url(url)
        if not valid:
            raise PermissionError(error)
        
        async with self.rate_limiter:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={'User-Agent': self.config.get('user_agent', 'RapidWebs-Agent/1.0')}
            ) as client:
                try:
                    response = await client.get(url, follow_redirects=True)
                    response.raise_for_status()
                    
                    # Check response size
                    content_length = len(response.content)
                    if content_length > self.max_size:
                        raise ValueError(f"Response too large: {content_length} bytes")
                    
                    # Extract content
                    content = self._extract_content(response.text)
                    
                    return {
                        "url": url,
                        "status_code": response.status_code,
                        "content_type": response.headers.get('content-type', ''),
                        "content_length": content_length,
                        "content": content,
                        "title": self._extract_title(response.text)
                    }
                except httpx.HTTPError as e:
                    return {
                        "url": url,
                        "error": str(e),
                        "status_code": getattr(e.response, 'status_code', None)
                    }
    
    def _extract_content(self, html: str) -> str:
        """Extract main content from HTML"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
        
        # Get text content
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return '\n'.join(lines[:1000])  # Limit lines
    
    def _extract_title(self, html: str) -> str:
        """Extract page title"""
        soup = BeautifulSoup(html, 'lxml')
        title = soup.find('title')
        return title.get_text(strip=True) if title else ''
    
    async def search_web(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Search web using Brave Search API"""
        api_key = self.config.get('api_keys', {}).get('brave_search')
        if not api_key:
            raise ValueError("Brave Search API key not configured")
        
        url = "https://api.search.brave.com/res/v1/web/search"
        params = {
            "q": query,
            "count": min(num_results, 20)
        }
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for result in data.get('web', {}).get('results', []):
                results.append({
                    "title": result.get('title'),
                    "url": result.get('url'),
                    "description": result.get('description'),
                    "age": result.get('age')
                })
            
            return results
```

---

### 4. Code Skill

**Purpose:** Code analysis, LSP integration, AST parsing

#### Capabilities

| Tool | Description | Permissions |
|------|-------------|-------------|
| `analyze_code` | Static analysis with LSP | Read paths |
| `find_symbols` | Find definitions/references | Read paths |
| `get_call_hierarchy` | Get call graph | Read paths |
| `get_type_hierarchy` | Get type inheritance | Read paths |
| `parse_ast` | Parse code to AST | Read paths |
| `check_syntax` | Validate syntax | Read paths |

#### Configuration

```json
{
  "skills": {
    "code": {
      "enabled": true,
      "languages": {
        "python": {
          "lsp_server": "ruff server",
          "extensions": [".py", ".pyi"],
          "max_symbols": 20,
          "max_diagnostics": 10
        },
        "typescript": {
          "lsp_server": "typescript-language-server",
          "extensions": [".ts", ".tsx", ".js", ".jsx"],
          "max_symbols": 20,
          "max_diagnostics": 10
        }
      },
      "ast_parsing": {
        "enabled": true,
        "extract_signatures_only": true,
        "include_docstrings": true
      }
    }
  }
}
```

---

### 5. Memory Skill

**Purpose:** Knowledge graph operations with semantic search

#### Capabilities

| Tool | Description | Permissions |
|------|-------------|-------------|
| `create_entity` | Create knowledge node | Write access |
| `create_relation` | Link entities | Write access |
| `search_nodes` | Semantic search | Read access |
| `read_graph` | Query graph structure | Read access |
| `delete_entity` | Remove nodes | Delete access (restricted) |

#### Configuration

```json
{
  "skills": {
    "memory": {
      "enabled": true,
      "storage_path": "./.qwen/memory",
      "max_entities": 10000,
      "semantic_search": {
        "enabled": true,
        "embedding_model": "all-MiniLM-L6-v2",
        "similarity_threshold": 0.7
      },
      "retention": {
        "enabled": true,
        "max_age_days": 30,
        "auto_compact": true
      }
    }
  }
}
```

---

## 🚀 Implementation Plan

### Tier 1: Core Skills Framework

**Timeline:** Week 1-2

#### Phase 1.1: Skills Manager
- [ ] Define skill loading interface
- [ ] Implement skill discovery from `.qwen/skills/`
- [ ] Build skill registry and routing
- [ ] Create permission enforcement layer

```python
# agent/skills/manager.py
from typing import Dict, Any, List, Optional, Type
from pathlib import Path
import importlib
import yaml

class SkillsManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.skills: Dict[str, Skill] = {}
        self.skills_dir = Path(config.get('skills_dir', './.qwen/skills'))
    
    def load_skills(self):
        """Load all skills from skills directory"""
        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            return
        
        for skill_file in self.skills_dir.glob('*.yaml'):
            skill_config = yaml.safe_load(skill_file.read_text())
            self._load_skill(skill_config)
    
    def _load_skill(self, config: Dict[str, Any]):
        """Load single skill from configuration"""
        skill_name = config['name']
        
        if not config.get('enabled', True):
            return
        
        # Import skill module
        module_path = config.get('module', f'agent.skills.{skill_name}')
        module = importlib.import_module(module_path)
        
        # Instantiate skill
        skill_class = getattr(module, f'{skill_name.capitalize()}Skill')
        skill = skill_class(config.get('config', {}))
        
        self.skills[skill_name] = skill
    
    def get_skill(self, name: str) -> Optional[Skill]:
        """Get skill by name"""
        return self.skills.get(name)
    
    def list_skills(self) -> List[Dict[str, Any]]:
        """List all loaded skills"""
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "tools": skill.tools,
                "enabled": skill.enabled
            }
            for skill in self.skills.values()
        ]
```

#### Phase 1.2: Permission System
- [ ] Implement path-based permissions
- [ ] Build command whitelist/blacklist
- [ ] Create domain restrictions for web
- [ ] Add rate limiting

#### Phase 1.3: Core Skills Implementation
- [ ] Terminal Executor (complete)
- [ ] Filesystem (complete)
- [ ] Web Skill (complete)

**Deliverables:**
- Working skills manager
- 3 core skills implemented
- Permission enforcement

---

### Tier 2: Advanced Skills

**Timeline:** Week 3-4

#### Phase 2.1: Code Skill with LSP
- [ ] Implement LSP client integration
- [ ] Build AST parser for Python/TypeScript
- [ ] Create symbol extraction
- [ ] Add call/type hierarchy support

#### Phase 2.2: Memory Skill
- [ ] Implement knowledge graph storage
- [ ] Build semantic search with embeddings
- [ ] Add entity/relation CRUD
- [ ] Create retention policies

#### Phase 2.3: Skill Composition
- [ ] Enable skill chaining
- [ ] Build skill dependency resolution
- [ ] Create composite skills
- [ ] Add skill templates

```python
# agent/skills/composition.py
class CompositeSkill(Skill):
    """Skill composed of multiple sub-skills"""
    
    def __init__(self, name: str, skills: List[Skill], workflow: List[Step]):
        self.name = name
        self.skills = {s.name: s for s in skills}
        self.workflow = workflow
    
    async def execute(self, input: SkillInput) -> SkillOutput:
        """Execute skill workflow"""
        context = SkillContext(input)
        
        for step in self.workflow:
            skill = self.skills.get(step.skill_name)
            if not skill:
                raise ValueError(f"Skill not found: {step.skill_name}")
            
            step_input = step.transform_input(context)
            step_output = await skill.execute(step_input)
            context = step.transform_output(context, step_output)
        
        return context.to_output()
```

**Deliverables:**
- Code skill with LSP
- Memory skill with semantic search
- Skill composition system

---

### Tier 3: Production Skills

**Timeline:** Week 5-6

#### Phase 3.1: Specialized Skills
- [ ] Security auditing skill
- [ ] Performance profiling skill
- [ ] Documentation generation skill
- [ ] Test generation skill

#### Phase 3.2: Skill Marketplace
- [ ] Define skill packaging format
- [ ] Build skill installation system
- [ ] Create skill versioning
- [ ] Add skill sharing mechanism

#### Phase 3.3: Observability
- [ ] Implement skill execution tracing
- [ ] Add skill performance metrics
- [ ] Build skill usage analytics
- [ ] Create skill debugging tools

**Deliverables:**
- 4+ specialized skills
- Skill installation system
- Full observability

---

## 📊 Skill Configuration Schema

### Complete Skills Configuration

```json
{
  "skills": {
    "enabled": true,
    "skills_directory": "./.qwen/skills",
    "auto_load": true,
    "terminal_executor": {
      "enabled": true,
      "whitelist": ["python", "npm", "git", "pytest"],
      "blacklist": ["rm -rf /", "sudo"],
      "max_execution_time": 30,
      "timeout": 10,
      "max_output_size": 100000
    },
    "filesystem": {
      "enabled": true,
      "allowed_paths": ["./agent", "./tools", "./docs"],
      "restricted_paths": ["./.venv", "./node_modules"],
      "max_file_size": 524288,
      "backup_on_write": true
    },
    "web": {
      "enabled": true,
      "allowed_domains": ["*.github.com", "*.python.org"],
      "blocked_domains": [],
      "max_response_size": 1000000,
      "timeout": 30,
      "rate_limit": {
        "requests_per_minute": 10
      }
    },
    "code": {
      "enabled": true,
      "languages": {
        "python": {
          "lsp_server": "ruff server",
          "max_symbols": 20
        }
      }
    },
    "memory": {
      "enabled": true,
      "storage_path": "./.qwen/memory",
      "semantic_search": {
        "enabled": true,
        "similarity_threshold": 0.7
      }
    }
  }
}
```

---

## 📁 Skill Definition Format

### YAML Skill Definition

```yaml
# .qwen/skills/code_review.yaml
name: code_review
version: 1.0.0
description: Automated code review with security and best practices checks
author: RapidWebs

enabled: true

tools:
  - name: review_file
    description: Review a single file for issues
    input_schema:
      type: object
      properties:
        path: { type: string }
        check_types: { type: array, items: { type: string } }
    output_schema:
      type: object
      properties:
        issues: { type: array }
        summary: { type: string }

permissions:
  read_paths:
    - ./agent
    - ./tools
  write_paths: []
  allowed_commands: []
  allowed_domains: []

dependencies:
  mcp_servers:
    - filesystem
    - memory
  env_vars: []
  python_packages:
    - ast
    - pylint

config:
  check_types:
    - security
    - performance
    - style
    - best_practices
  severity_threshold: warning
  max_issues: 50

execute: agent.skills.code_review:CodeReviewSkill.execute
validate: agent.skills.code_review:CodeReviewSkill.validate
```

---

## 🔗 Integration Points

### With SubAgents

| SubAgent | Skills Used |
|----------|-------------|
| **Code Agent** | Terminal, Filesystem, Code |
| **Test Agent** | Terminal, Filesystem |
| **Docs Agent** | Filesystem, Web, Memory |
| **Research Agent** | Web, Memory |
| **Security Agent** | Filesystem, Code, Terminal |

### With MCP Servers

| MCP Server | Skills Used |
|------------|-------------|
| **filesystem** | Filesystem skill (alternative implementation) |
| **memory** | Memory skill (alternative implementation) |
| **sequential-thinking** | All skills for complex workflows |

---

## 📈 Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Skill Load Time** | <100ms/skill | Time to initialize skill |
| **Permission Check** | <1ms | Time to validate permission |
| **Terminal Execution** | <30s | Max command duration |
| **File Operations** | <1s | Typical file read/write |
| **Web Fetch** | <5s | Typical URL fetch |
| **Memory Search** | <500ms | Semantic search latency |

---

## 📚 References

| Resource | URL |
|----------|-----|
| **Qwen Code Skills Docs** | https://qwenlm.github.io/qwen-code-docs/en/users/features/skills/ |
| **MCP Specification** | https://modelcontextprotocol.io/ |
| **LSP Specification** | https://microsoft.github.io/language-server-protocol/ |
