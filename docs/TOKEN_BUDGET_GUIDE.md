# Token Budget Guide

**Version:** 2.1.0  
**Date:** March 6, 2026

---

## Quick Start

**Default daily token limit:** 100,000 tokens

If you're hitting your token limit too quickly, configure it using one of three methods:

```bash
# Method 1: Environment Variable (Recommended)
$env:RW_DAILY_TOKEN_LIMIT="100000"  # PowerShell
export RW_DAILY_TOKEN_LIMIT=100000  # Linux/macOS

# Method 2: Config File
# Edit ~/.config/rapidwebs-agent/config.yaml
performance:
  token_budget: 100000

# Method 3: CLI Argument
rw-agent --token-limit 100000
```

---

## Configuration Methods

### Method 1: Environment Variable (Recommended)

**Windows PowerShell:**
```powershell
# Set for current session
$env:RW_DAILY_TOKEN_LIMIT="100000"

# Set permanently (user-level)
[Environment]::SetEnvironmentVariable("RW_DAILY_TOKEN_LIMIT", "100000", "User")
```

**Windows Command Prompt:**
```cmd
REM Set for current session
set RW_DAILY_TOKEN_LIMIT=100000
```

**Linux/macOS:**
```bash
# Set for current session
export RW_DAILY_TOKEN_LIMIT=100000

# Add to ~/.bashrc or ~/.zshrc for permanent
echo 'export RW_DAILY_TOKEN_LIMIT=100000' >> ~/.bashrc
source ~/.bashrc
```

---

### Method 2: Configuration File

**Location:** `~/.config/rapidwebs-agent/config.yaml`

**Windows:** `C:\Users\<YourName>\.config\rapidwebs-agent\config.yaml`  
**Linux/macOS:** `~/.config/rapidwebs-agent/config.yaml`

```yaml
performance:
  token_budget: 100000  # Set your daily limit here
  streaming: true
  parallel_tool_calls: true
  max_concurrent_tools: 5
  cache_responses: true
  cache_ttl: 3600
```

---

### Method 3: CLI Argument

```bash
# For entire session
rw-agent --token-limit 100000

# For single task
rw-agent "Fix bugs in main.py" --token-limit 50000
```

---

## Token Budget Warning System

The agent automatically warns you when approaching your limit:

```
⚠️  Token Budget Warning: 80% of daily budget used
   Remaining: 20,000 tokens
```

**Warning threshold:** 80% of daily limit

**What happens at 100%:**
- Further LLM API calls are blocked
- You receive an error: "Daily token budget exceeded"
- Budget resets at midnight UTC

---

## Monitoring Token Usage

### Check Current Stats

**In interactive mode:**
```
/stats
```

**From CLI:**
```bash
rw-agent --stats
```

### Stats Display Example

```
┌─────────────────────────────────────┐
│ 📊 Usage Statistics                 │
├─────────────────────────────────────┤
│ Qwen_coder Requests    │ 15         │
│ Qwen_coder Tokens      │ 45,230     │
│ Qwen_coder Cost        │ $0.0000    │
│   Cache Size           │ 23/1000    │
│                                     │
│ Total Tokens           │ 45,230     │
│ Total Cost             │ $0.0000    │
└─────────────────────────────────────┘
```

### Check Budget Status

```bash
rw-agent --budget
```

**Output:**
```
Daily Limit: 100,000 tokens
Current Usage: 15,230 tokens (15.2%)
Remaining: 84,770 tokens
```

---

## Recommended Token Limits

| Usage Pattern | Daily Limit | Monthly Estimate | Best For |
|--------------|-------------|------------------|----------|
| **Light** | 20,000 - 50,000 | ~500k tokens | Occasional exploration, simple questions |
| **Moderate** | 50,000 - 100,000 | ~2M tokens | Daily development work |
| **Heavy** | 100,000 - 200,000 | ~4M tokens | Large refactoring projects |
| **Professional** | 200,000+ | ~6M+ tokens | Intensive daily usage |

---

## Token Usage Estimates

| Activity | Approximate Tokens/Turn | Example |
|----------|------------------------|---------|
| Simple question | 500-2,000 | "What is async/await?" |
| Single file edit | 2,000-5,000 | "Fix the bug in utils.py" |
| Multi-file refactor | 5,000-15,000 | "Refactor to use classes" |
| Codebase exploration | 3,000-10,000 | "How does authentication work?" |
| Complex feature (with MCP) | 10,000-30,000 | "Add user registration with email" |

---

## Tips to Reduce Token Usage

### 1. Use Caching (Enabled by Default) ✅

**Savings:** 60-80% on repeated queries

```bash
# Cache is automatic - same queries return cached results
# Check cache stats:
@rw-agent-cache get_caching_stats

# Clear cache if needed:
cache clear
```

---

### 2. Use Context Optimization ✅

**Savings:** 40-60% via smart context selection

```bash
# Check context status:
context

# Check for thrashing:
thrashing check
```

---

### 3. Use Approval Mode ✅

**Savings:** Prevents accidental expensive operations

**In Qwen Code CLI:**
```
/approval-mode plan
```

**Modes:**
- `plan` - Read-only, no changes
- `default` - Confirm all write operations
- `auto-edit` - Auto-accept edits
- `yolo` - No confirmations

---

### 4. Reference Files Instead of Pasting ✅

**Savings:** 50-70% on context tokens

```bash
# ❌ Don't paste entire files
# ✅ Reference files with @
"Look at @main.py and fix the bug"

# Agent will read the file automatically
```

---

### 5. Clear History When Switching Tasks ✅

**Savings:** Reduces context window size

```bash
# Clear conversation:
/clear
```

---

### 6. Use SubAgents for Complex Tasks ✅

**Savings:** Parallel execution reduces total turns

```bash
# Delegate multiple tasks at once:
subagents run code "Refactor main.py"
subagents run test "Write tests for main.py"
subagents run docs "Document the API"
```

---

## Troubleshooting

### "Daily token budget exceeded"

**Solutions:**

1. **Wait for reset** - Budget resets at midnight UTC
2. **Increase limit:**
   ```bash
   rw-agent --token-limit 200000
   ```
3. **Check what's using tokens:**
   ```bash
   /stats
   ```
4. **Clear cache if corrupted:**
   ```bash
   cache clear
   ```

---

### High token usage unexpectedly

**Check:**
1. Context optimization status: `context`
2. Cache efficiency: `model stats`
3. Conversation length: `history`

**Fix:**
```bash
# Clear cache
cache clear

# Reset session
/clear

# Lower token budget
rw-agent --token-limit 50000
```

---

### Want to disable budget entirely

**Set a very high limit:**
```bash
rw-agent --token-limit 999999999
```

**Or in config:**
```yaml
performance:
  token_budget: 999999999
```

---

## Advanced Configuration

### Per-Request Limits

For fine-grained control, edit config:

```yaml
performance:
  token_budget: 100000  # Daily limit
  # Advanced settings
  per_request_limit: 8000  # Max per single request
  warning_threshold: 0.8   # Warn at 80%
```

---

### Budget Analytics

Track usage over time:

```bash
# Export usage stats
/stats > usage_log.txt

# Monitor with scripts
@rw-agent-cache get_caching_stats
```

---

## Environment Variables Reference

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `RW_DAILY_TOKEN_LIMIT` | Daily token budget | 100,000 | No |
| `RW_QWEN_API_KEY` | Qwen API key | - | Yes |
| `RW_GEMINI_API_KEY` | Gemini API key | - | No (fallback) |
| `BRAVE_API_KEY` | Brave Search API | - | No (optional) |

---

## Integration with Caching

The token budget system integrates with rw-agent's caching layer:

```python
from agent.caching import create_caching

# Initialize with budget
caching = create_caching('/workspace', daily_token_limit=100000)

# Check budget before API call
allowed = caching.check_token_budget(estimated_tokens=5000)
if not allowed:
    print("Budget exceeded!")

# Get usage stats
stats = caching.get_all_stats()
print(f"Daily usage: {stats['token_budget']['daily_usage']}")
```

---

## Related Documentation

- [`MCP_SERVERS_GUIDE.md`](MCP_SERVERS_GUIDE.md) - MCP server configuration
- [`CACHING_TESTING_GUIDE.md`](CACHING_TESTING_GUIDE.md) - Test caching functionality
- [`CONTEXT_OPTIMIZATION_GUIDE.md`](CONTEXT_OPTIMIZATION_GUIDE.md) - Context window optimization
- [`QWEN.md`](../QWEN.md) - Complete integration guide

---

## Quick Reference Card

```bash
# Check budget
rw-agent --budget

# Check stats
rw-agent --stats

# Set budget (3 methods)
$env:RW_DAILY_TOKEN_LIMIT="100000"  # Env var
# Edit ~/.config/rapidwebs-agent/config.yaml  # Config
rw-agent --token-limit 100000  # CLI

# Monitor usage
/stats  # Interactive
@rw-agent-cache get_caching_stats  # MCP

# Reduce usage
cache clear  # Clear cache
/clear  # Clear history
context  # Check optimization
```

---

**Last Updated:** March 6, 2026  
**Version:** 2.1.0
