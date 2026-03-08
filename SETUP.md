# RapidWebs Agent - Setup Guide

Complete setup instructions for all platforms (Windows, macOS, Linux).

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/stephanos8926-lgtm/rapidwebs-agent.git
cd rapidwebs-agent

# Run the setup script
python scripts/setup.py

# Launch the agent
python scripts/rw-agent
```

---

## Prerequisites

### Required

| Component | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.10+ | Runtime environment |
| **uv** | Latest | Package manager (fast pip alternative) |

### Optional

| Component | Purpose |
|-----------|---------|
| **Node.js** | For Prettier (code formatting) |
| **Git** | Version control integration |

---

## Platform-Specific Setup

### Windows

#### 1. Install Python

Download from [python.org](https://www.python.org/downloads/) or use Windows Store:

```powershell
# Windows Store (Python 3.13)
winget install Python.Python.3.13
```

#### 2. Install uv

```powershell
# PowerShell
powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"

# Or with winget
winget install astral-sh.uv
```

#### 3. Run Setup

```powershell
cd rapidwebs-agent
python scripts\setup.py
```

#### 4. Launch

```powershell
# Option A: Use launcher script
python scripts\rw-agent

# Option B: Use batch file
scripts\rw-agent.bat

# Option C: Activate venv and use directly
.\.venv\Scripts\activate
rw-agent

# Option D: Use uv run
uv run rw-agent
```

---

### macOS

#### 1. Install Python

```bash
# Using Homebrew
brew install python@3.13

# Or download from python.org
```

#### 2. Install uv

```bash
# Using Homebrew
brew install uv

# Or using curl
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 3. Run Setup

```bash
cd rapidwebs-agent
python scripts/setup.py
```

#### 4. Launch

```bash
# Option A: Use launcher script
python scripts/rw-agent

# Option B: Use shell script
chmod +x scripts/rw-agent.sh
./scripts/rw-agent.sh

# Option C: Activate venv and use directly
source .venv/bin/activate
rw-agent

# Option D: Use uv run
uv run rw-agent
```

---

### Linux

#### 1. Install Python

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip

# Fedora/RHEL
sudo dnf install python3.10 python3-pip

# Arch Linux
sudo pacman -S python python-pip
```

#### 2. Install uv

```bash
# Using curl
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

#### 3. Run Setup

```bash
cd rapidwebs-agent
python3 scripts/setup.py
```

#### 4. Launch

```bash
# Option A: Use launcher script
python3 scripts/rw-agent

# Option B: Use shell script
chmod +x scripts/rw-agent.sh
./scripts/rw-agent.sh

# Option C: Activate venv and use directly
source .venv/bin/activate
rw-agent

# Option D: Use uv run
uv run rw-agent
```

---

## Configuration

### API Keys

RapidWebs Agent requires API keys for LLM access.

#### Qwen Coder (Required for default model)

1. Visit [DashScope Console](https://dashscope.console.aliyun.com/)
2. Create an account / sign in
3. Generate API key
4. Set environment variable:

```bash
# Windows (PowerShell)
$env:RW_QWEN_API_KEY="your_api_key_here"

# macOS/Linux
export RW_QWEN_API_KEY="your_api_key_here"

# Or create .env file
cp .env.example .env
# Edit .env and add your key
```

#### Google Gemini (Optional)

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Generate API key
3. Set environment variable:

```bash
# Windows (PowerShell)
$env:RW_GEMINI_API_KEY="your_api_key_here"

# macOS/Linux
export RW_GEMINI_API_KEY="your_api_key_here"
```

#### Brave Search (Optional, for web search)

1. Visit [Brave Search API](https://brave.com/search/api/)
2. Generate API key
3. Set environment variable:

```bash
# Windows (PowerShell)
$env:BRAVE_API_KEY="your_api_key_here"

# macOS/Linux
export BRAVE_API_KEY="your_api_key_here"
```

---

## Verification

After setup, verify everything works:

```bash
# Check version
rw-agent --version

# Show statistics
rw-agent --stats

# Show help
rw-agent --help

# Test run (requires API key)
rw-agent "Hello, are you working?"
```

---

## Troubleshooting

### Python Version Error

**Error:** `Python 3.10+ required`

**Solution:**
```bash
# Check installed version
python --version

# Install Python 3.10+ from python.org or your package manager
```

### uv Not Found

**Error:** `uv is not installed or not in PATH`

**Solution:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Restart terminal or add to PATH
```

### Virtual Environment Not Found

**Error:** `Virtual environment not found`

**Solution:**
```bash
# Run setup to create venv
python scripts/setup.py

# Or create manually
uv venv
uv pip sync uv.lock
```

### API Key Error

**Error:** `API key not configured` or `401 Unauthorized`

**Solution:**
1. Check environment variables are set
2. Verify API key is valid
3. Check API key hasn't expired

```bash
# Verify environment variable
echo $RW_QWEN_API_KEY  # macOS/Linux
echo %RW_QWEN_API_KEY%  # Windows CMD
$env:RW_QWEN_API_KEY  # Windows PowerShell
```

### Dependencies Installation Failed

**Error:** `Failed to install dependencies`

**Solution:**
```bash
# Clear uv cache
uv cache clean

# Reinstall dependencies
uv pip sync uv.lock --force-reinstall

# Or use setup script with force
python scripts/setup.py --force
```

### Permission Denied (Unix)

**Error:** `Permission denied`

**Solution:**
```bash
# Make scripts executable
chmod +x scripts/rw-agent.sh
chmod +x scripts/setup.py

# Or run with python directly
python scripts/rw-agent
```

---

## Advanced Configuration

### Custom Configuration File

Create/edit `~/.config/rapidwebs-agent/config.yaml`:

```yaml
# LLM Configuration
llm:
  default_model: qwen_coder
  models:
    qwen_coder:
      enabled: true
    gemini:
      enabled: true

# Logging
logging:
  enabled: true
  level: INFO
  console: true

# Performance
performance:
  token_budget: 100000

# Output Management
output_management:
  enabled: true
  inline_max_bytes: 10240

# SubAgents
subagents:
  max_concurrent: 3
  enabled: true
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RW_QWEN_API_KEY` | Qwen Coder API key | Required |
| `RW_GEMINI_API_KEY` | Google Gemini API key | Optional |
| `RW_DAILY_TOKEN_LIMIT` | Daily token budget | 100000 |
| `BRAVE_API_KEY` | Brave Search API key | Optional |

---

## Development Setup

For contributing to RapidWebs Agent:

```bash
# Clone repository
git clone https://github.com/stephanos8926-lgtm/rapidwebs-agent.git
cd rapidwebs-agent

# Run setup with dev dependencies
python scripts/setup.py --dev

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
.\.venv\Scripts\activate   # Windows

# Run tests
pytest

# Run with linting
ruff check .
```

---

## Uninstall

```bash
# Remove virtual environment
rm -rf .venv  # macOS/Linux
rmdir /s .venv  # Windows

# Remove configuration
rm -rf ~/.config/rapidwebs-agent  # macOS/Linux
rmdir /s %APPDATA%\rapidwebs-agent  # Windows

# Remove logs
rm -rf ~/.local/share/rapidwebs-agent/logs  # Linux
rm -rf ~/Library/Logs/rapidwebs-agent  # macOS
rmdir /s %LOCALAPPDATA%\rapidwebs-agent\logs  # Windows

# Uninstall uv (optional)
uv self uninstall
```

---

## Getting Help

- **Documentation:** See `README.md` and `docs/`
- **Issues:** [GitHub Issues](https://github.com/stephanos8926-lgtm/rapidwebs-agent/issues)
- **Discussions:** [GitHub Discussions](https://github.com/stephanos8926-lgtm/rapidwebs-agent/discussions)

---

## Next Steps

After successful setup:

1. **Read the [README.md](README.md)** for usage examples
2. **Check [QWEN.md](QWEN.md)** for Qwen Code integration details
3. **Explore [docs/](docs/)** for advanced features
4. **Try your first task:**
   ```bash
   rw-agent "Explain the project structure"
   ```
