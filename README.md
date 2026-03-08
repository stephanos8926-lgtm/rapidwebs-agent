# 🚀 RapidWebs Agent

**Lightweight Python CLI agent for low-resource systems | Qwen Code architecture | 70-85% token savings via caching**

A cross-platform, production-ready agentic command-line interface optimized for **free-tier LLMs** (Qwen Coder + Gemini). Built with minimal dependencies, maximum security, and extreme token efficiency.

## ✨ Features

### 🎯 Why RapidWebs Agent?

- **Low-Resource Optimized**: Designed for 4GB RAM, HDD systems (HP Laptop, Android Termux)
- **Token Efficient**: Caching layer saves 70-85% tokens with smart budget management
- **4 Approval Modes**: From safe `plan` to unrestricted `yolo` - control how much autonomy you trust
- **Skill-Based Architecture**: Extensible tools via `skills_manager.py` (no MCP overhead!)
- **Cross-Platform**: Windows, Linux, macOS, and Android (Termux)

### 🚀 Core Features

- **Free Tier Optimized**: Primary support for Qwen Coder (2000 req/day, no token limits) + Gemini fallback
- **Cross-Platform**: Windows, Linux, macOS, and Android (Termux)
- **Token Efficient**: Built-in token counting, compression, and cost monitoring
- **Modular Skills**: Terminal execution, web scraping, filesystem operations, LSP integration
- **SubAgents Architecture**: Parallel task delegation to specialized agents (Code, Test, Docs, Research, Security)
- **Smart Caching**: 70-85% token savings with response caching and content deduplication
- **Beautiful UI**: Rich terminal interface with `Rich` + `prompt_toolkit`
- **Interactive Configuration**: On-the-fly setup wizard (no YAML editing!)
- **Token Budget Dashboard**: Real-time visual progress tracking
- **Command Autocomplete**: Tab completion for all commands
- **Secure**: Command whitelisting, signal handling, least-privilege execution
- **Minimal Dependencies**: Pure Python, all FOSS packages

## 📋 Requirements

- Python 3.10+
- `uv` package manager (auto-installed by setup script)
- API keys for Qwen Coder or Gemini (free tiers available)

## 🚀 Quick Start

### Option A: Automated Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/stephanos8926-lgtm/rapidwebs-agent.git
cd rapidwebs-agent

# Run the cross-platform setup script
python scripts/setup.py

# Launch the agent
python scripts/rw-agent
```

### Option B: Manual Setup with uv

```bash
# Clone the repository
git clone https://github.com/stephanos8926-lgtm/rapidwebs-agent.git
cd rapidwebs-agent

# Create virtual environment
uv venv

# Install dependencies
uv pip sync uv.lock

# Launch the agent
uv run rw-agent
```

### Option C: Using Launcher Scripts

| Platform | Command |
|----------|---------|
| **Windows** | `python scripts\rw-agent` or `scripts\rw-agent.bat` |
| **macOS/Linux** | `python scripts/rw-agent` or `./scripts/rw-agent.sh` |

### Set API Keys

```bash
# PowerShell (Windows)
$env:RW_QWEN_API_KEY="your_qwen_api_key"
$env:RW_GEMINI_API_KEY="your_gemini_api_key"

# Linux/macOS
export RW_QWEN_API_KEY="your_qwen_api_key"
export RW_GEMINI_API_KEY="your_gemini_api_key"

# Or create a .env file
cp .env.example .env
# Edit .env and add your keys
```

### Configure (Optional)

```bash
# Interactive configuration wizard (recommended for first-time setup)
uv run rw-agent --configure
# or
python scripts/rw-agent --configure

# Or set token budget directly
uv run rw-agent --token-limit 100000
```

### Run the Agent

```bash
# Interactive mode
uv run rw-agent
# or
python scripts/rw-agent

# Single task mode
uv run rw-agent "Create a Python script to parse CSV files"
# or
python scripts/rw-agent "Create a Python script to parse CSV files"

# With specific model
uv run rw-agent --model gemini "Explain async/await in Python"
```

## 📖 CLI Commands

### Interactive Mode Commands

Once in interactive mode, use these commands:

| Command | Description | New? |
|---------|-------------|------|
| `help` | Show help message | |
| `exit`, `quit` | Exit the agent (conversation auto-saved) | |
| `clear` | Clear screen | |
| `stats` | Token usage with budget dashboard | ✨ Enhanced |
| `config` | Show current configuration | ✨ Enhanced |
| `configure` | Launch interactive configuration wizard | 🆕 NEW |
| `budget` | Token budget dashboard | 🆕 NEW |
| `history` | Show conversation history (last 10 messages) | |
| `export [format]` | Export conversation (markdown/json) | |
| `cache clear` | Clear response cache | |
| `context` | Show context optimization status | |
| `thrashing check` | Check for context thrashing |

### Model Management

| Command | Description |
|---------|-------------|
| `model list` | List available models |
| `model switch <name>` | Switch to different model |
| `model stats` | Show model usage statistics |

### Skills

| Command | Description |
|---------|-------------|
| `skills list` | List available skills |
| `skills info <name>` | Show skill information |

**Available Skills:**
- `terminal` - Execute whitelisted shell commands
- `fs` - Filesystem operations (read, write, list, explore)
- `web` - Web scraping with SSRF protection
- `search` - Codebase search (grep, file search, symbol search)
- `lsp` - Code analysis and formatting (Ruff, Prettier)

### SubAgents (NEW!)

| Command | Description |
|---------|-------------|
| `subagents list` | List available subagent types |
| `subagents status` | Show orchestrator status |
| `subagents run <type> <task>` | Run a subagent task |

**Available SubAgent Types:**
- `code` - Code refactoring, debugging, implementation
- `test` - Test generation, execution, coverage analysis
- `docs` - API documentation, README generation, code explanation
- `research` - Research and information gathering
- `security` - Security auditing and vulnerability detection

**Examples:**
```
subagents run code Create a FastAPI endpoint for user authentication
subagents run test Write unit tests for app.py
subagents run docs Generate API documentation for utils.py
subagents list
subagents status
```

## 🔧 Configuration

### Command-Line Options

```
rw-agent [task] [options]

Options:
  --model, -m       LLM model (qwen_coder/gemini)
  --config, -c      Config file path
  --workspace, -w   Working directory
  --no-cache        Disable caching
  --no-stream       Disable streaming
  --token-limit     Daily token budget (default: 100000)
  --stats           Show statistics and exit
  --verbose         Enable verbose output
```

### Config File

Location: `~/.config/rapidwebs-agent/config.yaml`

```yaml
default_model: qwen_coder
models:
  qwen_coder:
    enabled: true
    api_key: ""  # Or set via RW_QWEN_API_KEY env var
    base_url: https://dashscope.aliyuncs.com/...
  gemini:
    enabled: false
    api_key: ""  # Or set via RW_GEMINI_API_KEY env var

performance:
  token_budget: 100000  # Daily token budget (default: 100k)
  cache_responses: true
  cache_ttl: 3600
  max_concurrent_tools: 5

agent:
  max_tool_iterations: 15  # Max tool calls per query
```

### Setting Token Budget

**Method 1: Environment Variable (Recommended)**
```bash
# PowerShell
$env:RW_DAILY_TOKEN_LIMIT="50000"

# Linux/macOS
export RW_DAILY_TOKEN_LIMIT=50000
```

**Method 2: Config File**
Edit `~/.config/rapidwebs-agent/config.yaml`:
```yaml
performance:
  token_budget: 50000
```

**Method 3: CLI Argument**
```bash
rw-agent --token-limit 50000
```

📚 **See also:** [`docs/TOKEN_BUDGET_CONFIG.md`](docs/TOKEN_BUDGET_CONFIG.md) for complete configuration guide

## 🏗️ Architecture

### Core Components

```
rapidwebs-agent/
├── agent/
│   ├── core.py           # Main agent orchestration
│   ├── skills.py         # Modular skills system
│   ├── models.py         # LLM management + token tracking
│   ├── config.py         # Configuration management
│   ├── ui.py             # Rich terminal UI
│   ├── context_optimization.py  # Smart context window management
│   ├── caching/          # Tier 4 caching system
│   │   ├── change_detector.py
│   │   ├── content_addressable.py
│   │   ├── response_cache.py
│   │   └── token_budget.py
│   └── subagents/        # Tier 3 subagents architecture
│       ├── orchestrator.py
│       ├── code_agent.py
│       ├── test_agent.py
│       └── docs_agent.py
└── rapidwebs_agent/
    ├── cli.py            # CLI entry point
    └── __main__.py       # Module runner
```

### Token Optimization Tiers

| Tier | Scope | Token Budget |
|------|-------|--------------|
| Tier 0 (Always) | Current focus | 300 tokens |
| Tier 1 (High) | Immediate context | 1,500 tokens |
| Tier 2 (Medium) | Dependencies | 2,500 tokens |
| Tier 3 (Low) | Peripheral | 1,700 tokens |
| **Total** | | **6,000 tokens** |

## 🔒 Security

- **Command Whitelisting**: Only allowed commands can be executed
- **File System Sandboxing**: Restricted to workspace directories
- **SSRF Protection**: Web scraper blocks localhost/private IPs
- **No Shell Injection**: Uses `subprocess.exec` instead of `subprocess.shell`
- **API Key Security**: Keys stored in environment variables only

## 📊 Token Usage Estimates

| Activity | Approximate Tokens/Turn |
|----------|------------------------|
| Simple question | 500-2,000 |
| Single file edit | 2,000-5,000 |
| Multi-file refactor | 5,000-15,000 |
| Codebase exploration | 3,000-10,000 |
| Complex feature (with SubAgents) | 10,000-30,000 |

## 🛠️ Development

```bash
# Install dependencies
uv sync

# Run tests (when available)
uv run pytest

# Run the agent
uv run rw-agent
# or
python scripts/rw-agent

# Build package
uv build
```

## 📜 Setup Scripts

RapidWebs Agent includes cross-platform setup scripts for easy installation:

### Setup Script

```bash
# Standard setup
python scripts/setup.py

# Force recreate virtual environment
python scripts/setup.py --force

# Install development dependencies
python scripts/setup.py --dev

# Skip configuration (use existing config)
python scripts/setup.py --skip-config

# Show all options
python scripts/setup.py --help
```

### Launcher Scripts

| Script | Platform | Description |
|--------|----------|-------------|
| `scripts/rw-agent.py` | All | Python launcher (works everywhere) |
| `scripts/rw-agent.bat` | Windows | Batch file launcher |
| `scripts/rw-agent.sh` | macOS/Linux | Shell script launcher |

**Usage:**
```bash
# Python launcher (cross-platform)
python scripts/rw-agent "your task"

# Windows batch file
scripts\rw-agent.bat "your task"

# Linux/macOS shell script
chmod +x scripts/rw-agent.sh
./scripts/rw-agent.sh "your task"
```

📚 **See also:** [`SETUP.md`](SETUP.md) for complete setup instructions and troubleshooting.

## 📚 Documentation

- [QWEN.md](QWEN.md) - Comprehensive integration guide
- [docs/qwen_code_optimization.md](docs/qwen_code_optimization.md) - Performance tuning
- [docs/qwen_code_subagents.md](docs/qwen_code_subagents.md) - SubAgents architecture
- [docs/qwen_code_skills.md](docs/qwen_code_skills.md) - Skills system

## 🆘 Troubleshooting

### "Skill not found" Error
Ensure the skill is enabled in your config file.

### High Token Usage
1. Use `/mode plan` for exploration (read-only)
2. Run `/clear` when switching tasks
3. Reference files with `@filename` instead of pasting
4. Enable caching for 70-85% token savings

### SubAgents Not Available
Make sure the `agent.subagents` module is properly installed:
```bash
uv sync
```

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🙏 Credits

Built with:
- [Qwen Coder](https://qwenlm.github.io/) - Primary LLM
- [Rich](https://github.com/Textualize/rich) - Terminal UI
- [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) - Interactive prompts