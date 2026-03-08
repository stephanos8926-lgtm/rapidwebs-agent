# rw-agent MCP Servers - Complete Guide

**Version:** 2.1.0  
**Date:** March 6, 2026  
**Compatible with:** Qwen Code CLI v0.11.1+

---

## Quick Start

rw-agent provides **two standalone MCP servers** for token caching and code analysis:

| Server | Command | Purpose | Token Savings |
|--------|---------|---------|---------------|
| **rw-agent-cache** | `rw-agent-cache` | Token caching, budget management | 70-85% |
| **rw-agent-code** | `rw-agent-code` | Code linting, formatting, analysis | N/A |

### Installation

```bash
# Install rw-agent (includes both MCP servers)
cd e:\Projects\rapidwebs-agent
pip install -e .

# Verify installation
rw-agent-cache --help
rw-agent-code --help

# Test servers
rw-agent-cache --test
rw-agent-code --test
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│              Qwen Code CLI                      │
│  (uses .qwen/settings.json for MCP config)      │
│                                                 │
│  ┌─────────────┐  ┌─────────────┐              │
│  │ filesystem  │  │ fetch       │              │
│  │ (Qwen MCP)  │  │ (Qwen MCP)  │              │
│  └─────────────┘  └─────────────┘              │
│                                                 │
│  ┌─────────────┐  ┌─────────────┐              │
│  │ rw-agent-   │  │ rw-agent-   │              │
│  │ cache       │  │ code        │              │
│  │ (rw-agent)  │  │ (rw-agent)  │              │
│  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────┘
         │                    │
         │ stdio              │ stdio
┌────────▼─────────┐  ┌──────▼──────────────────┐
│ Caching MCP      │  │ Code Tools MCP          │
│ Server           │  │ Server                  │
│                  │  │                         │
│ - Response cache │  │ - Linting (ruff)        │
│ - Token budget   │  │ - Formatting (prettier) │
│ - File tracking  │  │ - Code analysis         │
│ - Lazy loading   │  │ - Symbol extraction     │
└──────────────────┘  └─────────────────────────┘
```

### What's Exposed via MCP

| Capability | rw-agent Skill | MCP Server | Qwen Code CLI Equivalent |
|------------|----------------|------------|-------------------------|
| **Caching** | ✅ Internal | ✅ `rw-agent-cache` | ❌ No |
| **Code Linting** | ✅ code_tools | ✅ `rw-agent-code` | ❌ No |
| **Code Formatting** | ✅ code_tools | ✅ `rw-agent-code` | ❌ No |
| **Code Analysis** | ✅ code_tools | ✅ `rw-agent-code` | ❌ No |
| **Filesystem** | ✅ fs | ❌ No | ✅ `@filesystem` |
| **Terminal** | ✅ terminal | ❌ No | ✅ Built-in |
| **Web Scraping** | ✅ web | ❌ No | ✅ `@fetch` |
| **Search** | ✅ search | ❌ No | ✅ Built-in |

**Why not duplicate?** Qwen Code CLI already provides mature MCP servers for filesystem, web, and terminal operations. We focus on unique value: caching and code analysis.

---

## rw-agent-cache Server

**Module:** `tools.mcp_server_caching`  
**Command:** `rw-agent-cache`

### Features

- **Response Caching** - Cache LLM responses with file-based invalidation
- **Token Budget** - Daily token limit enforcement with warnings
- **Change Detection** - Hash-based file change tracking
- **Content Deduplication** - SQLite-backed storage for efficiency
- **Lazy Loading** - On-demand file loading with LRU eviction

### Available Tools

| Tool | Description | Use Case |
|------|-------------|----------|
| `initialize_caching` | Initialize with workspace and token budget | Session startup |
| `check_cache` | Check if response is cached | Before LLM call |
| `cache_response` | Cache LLM response with file dependencies | After LLM call |
| `invalidate_files` | Invalidate cache for changed files | On file edit |
| `get_caching_stats` | Get comprehensive statistics | Monitoring |
| `check_token_budget` | Check if within token budget | Before API call |
| `get_lazy_content` | Get file content with lazy loading | On-demand reading |
| `is_file_changed` | Check if file has changed | Cache validation |
| `cleanup_cache` | Clean up old cache entries | Maintenance |
| `clear_all_cache` | Clear all caches | Reset |

### Usage Examples

```bash
# Production mode (stdio server for MCP)
rw-agent-cache

# Debug mode (verbose logging)
rw-agent-cache --debug

# Test mode (run self-tests)
rw-agent-cache --test
```

### Configuration

Add to `.qwen/settings.json`:

```json
{
  "mcpServers": {
    "rw-agent-cache": {
      "command": "rw-agent-cache",
      "cwd": ".",
      "timeout": 30000,
      "trust": true
    }
  }
}
```

### Expected Token Savings

| Scenario | Without Cache | With Cache | Savings |
|----------|---------------|------------|---------|
| Repeated query | 5,000 tokens | 0 tokens | 100% |
| File unchanged | 3,000 tokens | 0 tokens | 100% |
| Similar context | 8,000 tokens | 2,000 tokens | 75% |
| **Average** | - | - | **70-85%** |

---

## rw-agent-code Server

**Module:** `tools.mcp_server_code_tools`  
**Command:** `rw-agent-code`

### Features

- **Code Linting** - Python (ruff), SQL (sqlfluff)
- **Code Formatting** - 10+ languages (ruff, prettier)
- **Code Analysis** - Symbols, imports, callers detection
- **Related Files** - Smart file relationship detection
- **Tool Detection** - Automatic tool availability checking

### Available Tools

| Tool | Description | Languages |
|------|-------------|-----------|
| `lint_file` | Lint code file for issues | Python, SQL |
| `format_file` | Format code file | Python, JS/TS, JSON, YAML, MD, CSS |
| `fix_file` | Auto-fix linting issues | Python |
| `check_tools` | Check installed tools status | All |
| `get_supported_languages` | Get supported languages list | All |
| `detect_language` | Detect language from file extension | All |
| `get_symbols` | Extract symbols (functions, classes, imports) | Python |
| `show_related_files` | Find related files | Python |
| `find_callers` | Find function callers | Python |

### Usage Examples

```bash
# Production mode (stdio server for MCP)
rw-agent-code

# Debug mode (verbose logging)
rw-agent-code --debug

# Test mode (check tool availability)
rw-agent-code --test
```

### Configuration

Add to `.qwen/settings.json`:

```json
{
  "mcpServers": {
    "rw-agent-code": {
      "command": "rw-agent-code",
      "cwd": ".",
      "timeout": 30000,
      "trust": true
    }
  }
}
```

### Supported Languages

| Tier | Language | Lint | Format | Tools Required |
|------|----------|------|--------|----------------|
| **Tier 1** | Python | ✅ ruff | ✅ ruff | Bundled |
| **Tier 1** | JavaScript | ❌ | ✅ prettier | User installs |
| **Tier 1** | TypeScript | ❌ | ✅ prettier | User installs |
| **Tier 1** | JSON | ❌ | ✅ prettier | User installs |
| **Tier 1** | YAML | ❌ | ✅ prettier | User installs |
| **Tier 1** | Markdown | ❌ | ✅ prettier | User installs |
| **Tier 1** | CSS | ❌ | ✅ prettier | User installs |
| **Tier 2** | SQL | ✅ sqlfluff | ✅ sqlfluff | User installs |
| **Tier 2** | Go | ❌ | ✅ gofmt | Built-in with Go |
| **Tier 2** | Rust | ❌ | ✅ rustfmt | Built-in with Rust |
| **Tier 2** | Shell | ❌ | ✅ shfmt | User installs |

---

## Complete Configuration Example

```json
{
  "mcpServers": {
    "rw-agent-cache": {
      "command": "rw-agent-cache",
      "cwd": ".",
      "timeout": 30000,
      "trust": true
    },
    "rw-agent-code": {
      "command": "rw-agent-code",
      "cwd": ".",
      "timeout": 30000,
      "trust": true
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
      "timeout": 30000,
      "trust": true
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"],
      "timeout": 30000,
      "trust": true
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "cwd": "./.qwen/memory",
      "timeout": 30000,
      "trust": true
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
      "timeout": 30000,
      "trust": true
    }
  },
  "mcp": {
    "allowed": [
      "rw-agent-cache",
      "rw-agent-code",
      "filesystem",
      "fetch",
      "memory",
      "sequential-thinking"
    ]
  },
  "tools": {
    "approvalMode": "default",
    "parallelToolCalls": true,
    "maxConcurrentTools": 3,
    "enableToolOutputTruncation": true,
    "truncateToolOutputThreshold": 10000
  }
}
```

---

## Testing

### Test Cache Server

```bash
rw-agent-cache --test
```

**Expected Output:**
```
Testing rw-agent caching MCP server...
==================================================

1. Testing initialization...
   Status: initialized
   Workspace: e:\Projects\rapidwebs-agent
   Cache Dir: C:\Users\Bratp\.cache\rapidwebs-agent

2. Testing cache check (expect miss)...
   Cached: False

3. Testing cache response...
   Status: cached

4. Testing cache check (expect hit)...
   Cached: True
   Response: test response

5. Testing budget check...
   Allowed: True
   Remaining: 99900

All tests completed successfully!
```

### Test Code Server

```bash
rw-agent-code --test
```

**Expected Output:**
```
Running code tools MCP server in test mode...

Code tools status:
  ✓ ruff: ruff 0.15.5
  ✗ prettier: None
  ✗ gofmt: None
  ✗ rustfmt: None
  ✗ shfmt: None
  ✗ sqlfluff: None

Supported languages:
  - Python (lint + format)
  - JavaScript (format only)
  - TypeScript (format only)
  - JSON (format only)
  - YAML (format only)
  - Markdown (format only)
  - CSS (format only)

Test mode complete
```

---

## Troubleshooting

### Command Not Found

```bash
# Reinstall rw-agent
pip uninstall rapidwebs-agent
pip install -e .

# Verify installation (Windows)
where rw-agent-cache
where rw-agent-code

# Verify installation (Linux/Mac)
which rw-agent-cache
which rw-agent-code
```

### MCP Server Not Connecting

1. **Check server is running:**
   ```bash
   rw-agent-cache --debug
   rw-agent-code --debug
   ```

2. **Verify configuration:**
   ```json
   {
     "mcpServers": {
       "rw-agent-cache": {
         "command": "rw-agent-cache",
         "cwd": ".",
         "trust": true
       }
     }
   }
   ```

3. **Check logs:**
   - Look for "Caching initialized" or "Code tools initialized"
   - Check for error messages in stderr

### Windows-Specific Issues

1. **Enable VT100 mode:**
   ```powershell
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   ```

2. **Use Windows Terminal** for best results

3. **Run as Administrator** if permission errors occur

### High Token Usage Despite Caching

1. **Check cache hit rate:**
   ```bash
   @rw-agent-cache get_caching_stats
   ```

2. **Verify files are tracked:**
   - Ensure files are not in `.qwenignore`
   - Check file permissions

3. **Clear and reinitialize cache:**
   ```bash
   @rw-agent-cache clear_all_cache
   @rw-agent-cache initialize_caching
   ```

---

## Performance Tips

### Optimize Caching

1. **Set appropriate token budget:**
   ```json
   {
     "performance": {
       "token_budget": 100000
     }
   }
   ```

2. **Enable cache compression:**
   ```bash
   @rw-agent-cache initialize_caching(daily_token_limit=100000)
   ```

3. **Clean up old entries weekly:**
   ```bash
   @rw-agent-cache cleanup_cache(max_age_days=7)
   ```

### Optimize Code Analysis

1. **Install Tier 1 tools:**
   ```bash
   pip install ruff
   npm install -g prettier
   ```

2. **Use language detection:**
   ```bash
   @rw-agent-code detect_language(file_path="src/main.py")
   ```

3. **Batch lint multiple files:**
   ```bash
   @rw-agent-code lint_file(file_path="src/")
   ```

---

## Related Documentation

- [`CACHING_TESTING_GUIDE.md`](CACHING_TESTING_GUIDE.md) - How to test caching works
- [`CODE_TOOLS_GUIDE.md`](CODE_TOOLS_GUIDE.md) - Code linting and formatting
- [`TOKEN_BUDGET_GUIDE.md`](TOKEN_BUDGET_GUIDE.md) - Token budget configuration
- [`CONTEXT_OPTIMIZATION_GUIDE.md`](CONTEXT_OPTIMIZATION_GUIDE.md) - Context window optimization

---

## Quick Reference

```bash
# Install
pip install -e .

# Test servers
rw-agent-cache --test
rw-agent-code --test

# Run servers (production)
rw-agent-cache
rw-agent-code

# Debug servers
rw-agent-cache --debug
rw-agent-code --debug

# Check tools
rw-agent-code --check-tools

# Install Tier 1 tools
rw-agent-code --install-tools
```

---

**Summary:** Two MCP servers for unique capabilities: `rw-agent-cache` (70-85% token savings) and `rw-agent-code` (code analysis). Install once, use globally across all projects.
