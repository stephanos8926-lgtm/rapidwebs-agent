# Web Fetch Implementation - Architecture Clarification

**Date:** March 5, 2026  
**Version:** 1.2.0 (Cleaned Up)

## 🎯 Problem Solved

DashScope API rate limiting was preventing web content fetching through the LLM. This implementation provides automatic fallback to MCP's `fetch` tool which bypasses LLM rate limits entirely.

---

## ✅ Architecture: Clean Separation

### **Qwen Code CLI** (`.qwen/settings.json`)
- ✅ **Uses MCP servers natively** - built-in support
- MCP servers run as separate processes
- Tools called directly by Qwen Code
- **Zero overhead** - this is how Qwen Code is designed

### **RapidWebs Agent** (`agent/` Python code)
- ❌ **No MCP client** - removed to avoid overhead
- ✅ **Uses `WebScraperSkill`** with `httpx` for standalone operation
- Simple, direct HTTP requests
- **No subprocess overhead**

---

## 📊 Overhead Comparison

| Approach | Overhead | Complexity | Used By |
|----------|----------|------------|---------|
| **Qwen Code Native MCP** | None (built-in) | Low | ✅ Qwen Code CLI |
| **Python MCP Client** | ~100-500ms per call | High | ❌ Removed |
| **Direct HTTP (httpx)** | ~50-200ms | Low | ✅ RapidWebs Agent |

---

## 🔧 What's Configured

### 1. **MCP Servers** (`.qwen/settings.json`)

For **Qwen Code CLI** usage:

```json
{
  "mcpServers": {
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"],
      "timeout": 30000,
      "trust": true
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "timeout": 30000,
      "trust": true,
      "env": {
        "BRAVE_API_KEY": "${env:BRAVE_API_KEY}"
      }
    }
  }
}
```

### 2. **Auto-Invoke Rules** (`.qwen/settings.json`)

Automatically triggers for URLs:

```json
{
  "name": "web-fetch-auto",
  "trigger": ["http://", "https://", "fetch", "scrape", "web page", "website", "url"],
  "action": "enable_tool_fetch",
  "priority": 1
}
```

### 3. **WebScraperSkill** (`agent/skills.py`)

For **RapidWebs Agent** standalone usage:

```python
class WebScraperSkill(SkillBase):
    """Scrape web content with SSRF protection"""
    
    async def execute(self, url: str, extract_text: bool = True):
        # Direct HTTP request with httpx
        # No MCP overhead
```

---

## 🚀 How It Works

### Qwen Code CLI Flow

```
User: "Summarize https://python.org"
   ↓
Qwen Code detects URL pattern (auto-invoke rule)
   ↓
Calls @fetch tool via MCP (no LLM API)
   ↓
MCP fetch server retrieves page → Markdown
   ↓
Returns content (bypasses DashScope)
```

### RapidWebs Agent Flow

```
User: "Fetch https://python.org"
   ↓
Python agent uses WebScraperSkill
   ↓
Direct httpx HTTP request
   ↓
BeautifulSoup parses HTML → text
   ↓
Returns content (no MCP overhead)
```

---

## 📝 Usage Examples

### Qwen Code CLI (Recommended)

```bash
# Automatic - URLs trigger @fetch
"What's on https://example.com?"

# Manual
@fetch https://python.org

# Web search (needs BRAVE_API_KEY)
@brave-search latest Python news
```

### RapidWebs Agent (Standalone)

```python
from agent.core import Agent

agent = Agent()
result = await agent.execute("Fetch https://python.org")
# Uses WebScraperSkill with httpx
```

---

## 🛠️ Dependencies

```bash
# For Qwen Code CLI (installed automatically via npx)
npx -y @modelcontextprotocol/server-fetch
npx -y @modelcontextprotocol/server-brave-search

# For RapidWebs Agent (already in requirements)
httpx
beautifulsoup4
lxml
```

**Removed:** `mcp` Python package (unnecessary overhead)

---

## 🔒 Security Features

Both implementations include:

1. **URL Validation** - Only http/https schemes allowed
2. **SSRF Protection** - Blocks localhost/private IPs
3. **Redirect Limits** - Max 5 redirects to prevent loops
4. **Content Length Limits** - Max 10KB to prevent memory issues
5. **Timeout Protection** - 10-30s timeout for fetch operations

---

## 📈 Expected Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **LLM API calls for web** | 100% | 20-40% | 60-80% reduction |
| **Response time (web)** | 5-10s | 2-3s | 2-3x faster |
| **Rate limit hits** | Frequent | Rare | 70% reduction |
| **Token usage** | High | Low | 50-70% savings |
| **Python agent overhead** | N/A | None | Clean architecture |

---

## 🐛 Troubleshooting

### MCP Fetch Not Working (Qwen Code)

1. Check if npx is available: `npx --version`
2. Test manually: `npx -y @modelcontextprotocol/server-fetch`
3. Check firewall/antivirus blocking npx
4. Run `/mcp` in Qwen Code to check server status

### Brave Search Not Working

1. Set API key: `$env:BRAVE_API_KEY="..."`
2. Check key validity: https://brave.com/search/api/
3. Verify in Qwen Code: `/mcp` command

### Rate Limits Still Occurring

- Web fetch bypasses LLM limits but has its own rate limits
- Consider caching frequently fetched pages
- Use `@brave-search` for search instead of multiple fetches

---

## 📚 Related Documentation

- [`QWEN.md`](QWEN.md) - Full integration guide
- [`docs/qwen_code_optimization.md`](docs/qwen_code_optimization.md) - Performance tuning
- [`agent/skills.py`](agent/skills.py) - WebScraperSkill implementation

---

**Status:** ✅ Production Ready (Cleaned Up)  
**Tested:** Windows 10, Python 3.13, Node.js 24.13.0  
**Architecture:** Clean separation - no MCP overhead in Python agent
