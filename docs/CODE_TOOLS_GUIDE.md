# Code Tools - Linting & Formatting

**Fast, cross-platform code quality tools for RapidWebs Agent**

RapidWebs Agent includes built-in support for industry-standard linting and formatting tools with **automatic detection and installation**.

---

## Quick Start

### Auto-Detect & Install (Recommended)
```bash
# Scan workspace and install missing tools
rw-agent --install-tools
```

### Manual Commands
```bash
# Check tool availability
rw-agent --check-tools

# Scan workspace for languages
rw-agent --scan-workspace

# Install Tier 1 tools
rw-agent --install-tools

# Install Tier 2 tools (instructions)
rw-agent --install-tier2

# Format a file
rw-agent --format main.py

# Lint a file
rw-agent --lint main.py
```

---

## Installation Tiers

### Tier 1: Core (Auto-Installed) ⭐⭐⭐⭐⭐

These tools are installed automatically or bundled.

| Language | Tool | When Installed | Size |
|----------|------|----------------|------|
| **Python** | `ruff` | ✅ **Bundled** with `pip install rapidwebs-agent` | ~5MB |
| **JavaScript** | `prettier` | ⚠️ **Auto** on first `--install-tools` (requires npm) | ~15MB |
| **TypeScript** | `prettier` | (same as JS) | (same) |
| **JSON** | `prettier` | (same as JS) | (same) |
| **YAML** | `prettier` | (same as JS) | (same) |
| **Markdown** | `prettier` | (same as JS) | (same) |
| **CSS** | `prettier` | (same as JS) | (same) |
| **HTML** | `prettier` | (same as JS) | (same) |

**Auto-Installation Flow:**
```bash
# 1. Install rapidwebs-agent (includes ruff)
pip install rapidwebs-agent

# 2. Scan workspace - detects languages
rw-agent --scan-workspace

# 3. Auto-install missing Tier 1 tools
rw-agent --install-tools
# → Detects workspace languages
# → Installs prettier if JS/TS/JSON/YAML/MD/CSS detected
# → Shows Tier 2 instructions if Go/Rust/Shell/SQL detected
```

### Tier 2: Optional (User Installs When Needed) ⭐⭐⭐⭐

Install these only when working with these languages.

| Language | Tool | Install Command | When to Install |
|----------|------|-----------------|-----------------|
| **Go** | `gofmt` | Built-in with Go | When you write Go code |
| **Rust** | `rustfmt` | `rustup component add rustfmt` | When you write Rust code |
| **Shell** | `shfmt` | `go install mvdan.cc/sh/v3/cmd/shfmt@latest` | When you write shell scripts |
| **SQL** | `sqlfluff` | `pip install sqlfluff` | When you write SQL queries |

**Get Tier 2 Installation Instructions:**
```bash
rw-agent --install-tier2
```

### Tier 3: Future/On-Demand ⭐⭐⭐

Available upon request (contact us or submit a PR):
- Java, C/C++, Ruby, PHP, Swift, Kotlin, TOML, XML, Lua, Dart

---

## Installation

### Tier 1 Tools (Recommended)

**Ruff (Python)** - Bundled with RapidWebs Agent:
```bash
# Already installed with rapidwebs-agent
pip install rapidwebs-agent
# or
uv pip install rapidwebs-agent
```

**Prettier (JS/TS/JSON/YAML/MD/CSS/HTML)** - Install via npm:
```bash
npm install -g prettier
```

Verify installation:
```bash
rw-agent --check-tools
```

### Tier 2 Tools (Optional)

**Go (gofmt)**:
```bash
# Install Go from https://go.dev/
# gofmt is included automatically
go version
```

**Rust (rustfmt)**:
```bash
# Install Rust from https://rustup.rs/
rustup component add rustfmt
```

**Shell (shfmt)**:
```bash
go install mvdan.cc/sh/v3/cmd/shfmt@latest
```

**SQL (sqlfluff)**:
```bash
pip install sqlfluff
```

---

## Usage Examples

### From Command Line

**Format a Python file:**
```bash
rw-agent --format main.py
```

**Lint a TypeScript file:**
```bash
rw-agent --lint app.ts
```

**Check all tools status:**
```bash
rw-agent --check-tools
```

### From Qwen Code CLI

Once configured, Qwen Code can use code tools via MCP:

```
User: "Format main.py"
→ Qwen Code calls: format_file("main.py")
→ Returns: formatted content

User: "Check if my code has issues"
→ Qwen Code calls: lint_file("app.ts")
→ Returns: list of diagnostics
```

### From Python Code

```python
from agent.code_tools import CodeTools

tools = CodeTools()

# Check tool availability
status = tools.get_all_tools_status()
print(status['ruff']['installed'])  # True

# Format Python code
result = tools.format_file('main.py')
if result.success:
    print("Formatted successfully!")

# Lint Python code
result = tools.lint_file('main.py')
for diag in result.diagnostics:
    print(f"Line {diag['line']}: {diag['message']}")

# Auto-detect language and format
result = tools.format_file('config.yaml')  # Uses Prettier
```

### From Agent Skills

```python
from agent.skills import SkillManager
from agent.config import Config

config = Config()
skill_manager = SkillManager(config)

# Use code_tools skill
result = await skill_manager.execute(
    'code_tools',
    action='format',
    file_path='main.py'
)

# Check tool availability
result = await skill_manager.execute(
    'code_tools',
    action='check'
)
```

---

## Tool Comparison

### Why Ruff for Python?

| Metric | Ruff | Pylint + Black |
|--------|------|----------------|
| Speed | 10-100x faster | Slower |
| Memory | ~10MB | ~50MB+ |
| Installation | Single binary | Multiple packages |
| Features | Lint + Format | Separate tools |
| Compatibility | Pylint rules | Native |

**Ruff** is written in Rust and provides:
- 10-100x faster linting than pylint
- Built-in formatting (replaces black)
- Pylint rule compatibility
- Single binary installation

### Why Prettier for Web?

**Prettier** handles 6+ languages with one tool:
- JavaScript/TypeScript
- JSON
- YAML
- Markdown
- CSS/SCSS/LESS
- HTML

Benefits:
- Consistent formatting across languages
- Opinionated (no configuration needed)
- Fast and reliable
- Industry standard

---

## Configuration

### Ruff Configuration (Optional)

Create `pyproject.toml` or `ruff.toml`:

```toml
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I"]  # Error, Falsy, isort
ignore = ["E501"]  # Line length (handled by formatter)
```

### Prettier Configuration (Optional)

Create `.prettierrc`:

```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5"
}
```

---

## Troubleshooting

### "Tool not installed" Error

**Python (ruff):**
```bash
pip install ruff
# or reinstall rapidwebs-agent
pip install --upgrade rapidwebs-agent
```

**JavaScript (prettier):**
```bash
npm install -g prettier
```

### "Command not found" after Installation

1. Ensure the tool is in your PATH
2. Restart your terminal
3. Check installation:
   ```bash
   ruff --version
   prettier --version
   ```

### Formatting Not Working

1. Check file extension is supported
2. Verify tool is installed: `rw-agent --check-tools`
3. Check for syntax errors in code first

### Linting Shows False Positives

1. Some rules may be too strict for your project
2. Configure ruff with `pyproject.toml`
3. Use `# noqa` comments to ignore specific lines

---

## API Reference

### CodeTools Class

```python
from agent.code_tools import CodeTools

tools = CodeTools()
```

#### Tool Detection
- `check_tool_installed(tool_name: str) -> bool`
- `get_tool_version(tool_name: str) -> Optional[str]`
- `get_all_tools_status() -> Dict[str, Dict]`

#### Language Detection
- `detect_language(file_path: str) -> Optional[str]`

#### Python Tools
- `lint_python(file_path: str, content: Optional[str]) -> ToolResult`
- `format_python(file_path: str, content: Optional[str], check_only: bool) -> ToolResult`
- `fix_python(file_path: str, content: Optional[str]) -> ToolResult`

#### Prettier Tools
- `format_javascript(file_path: str, content: Optional[str]) -> ToolResult`
- `format_typescript(file_path: str, content: Optional[str]) -> ToolResult`
- `format_json(file_path: str, content: Optional[str]) -> ToolResult`
- `format_yaml(file_path: str, content: Optional[str]) -> ToolResult`
- `format_markdown(file_path: str, content: Optional[str]) -> ToolResult`
- `format_css(file_path: str, content: Optional[str]) -> ToolResult`
- `format_html(file_path: str, content: Optional[str]) -> ToolResult`

#### Tier 2 Tools
- `format_go(file_path: str, content: Optional[str]) -> ToolResult`
- `format_rust(file_path: str, content: Optional[str]) -> ToolResult`
- `format_shell(file_path: str, content: Optional[str]) -> ToolResult`
- `lint_sql(file_path: str, content: Optional[str]) -> ToolResult`

#### Unified API
- `format_file(file_path: str, content: Optional[str], check_only: bool, language: Optional[str]) -> ToolResult`
- `lint_file(file_path: str, content: Optional[str], language: Optional[str]) -> ToolResult`
- `fix_file(file_path: str, content: Optional[str], language: Optional[str]) -> ToolResult`

### ToolResult Class

```python
@dataclass
class ToolResult:
    success: bool
    output: str
    errors: str
    returncode: int
    files_modified: List[str]
    duration_ms: float
    diagnostics: List[Dict[str, Any]]
```

---

## MCP Server Integration

### Configure in `.qwen/settings.json`

```json
{
  "mcpServers": {
    "code-tools": {
      "command": "python",
      "args": ["-m", "tools.code_tools_mcp_server"],
      "cwd": ".",
      "timeout": 30000,
      "trust": true,
      "includeTools": [
        "lint_file",
        "format_file",
        "fix_file",
        "check_tools",
        "get_supported_languages",
        "detect_language"
      ]
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `lint_file` | Lint a code file for issues |
| `format_file` | Format a code file |
| `fix_file` | Auto-fix issues (Python) |
| `check_tools` | Check tool availability |
| `get_supported_languages` | Get supported languages list |
| `detect_language` | Detect language from file extension |

---

## Performance Benchmarks

| Tool | Typical Speed | Memory |
|------|--------------|--------|
| **Ruff** | 10-100ms per file | ~10MB |
| **Prettier** | 200-500ms per file | ~50MB |
| **gofmt** | <10ms per file | ~5MB |
| **rustfmt** | 100-200ms per file | ~20MB |

---

## Related Documentation

- [QWEN.md](QWEN.md) - Qwen Code integration guide
- [README.md](README.md) - Project overview
- [MIGRATION.md](MIGRATION.md) - Migration guide

---

**Last Updated:** March 5, 2026  
**Version:** 1.0.0
