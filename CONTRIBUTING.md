# Contributing to RapidWebs Agent

Thank you for your interest in contributing to RapidWebs Agent! This document provides guidelines and instructions for contributing.

## 🌟 How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title**
* **Describe the exact steps to reproduce the problem**
* **Provide specific examples to demonstrate the steps**
* **Describe the behavior you observed and what behavior you expected**
* **Include screenshots if possible**
* **Include system information (OS, Python version, etc.)**

**Bug Report Template:**

```markdown
**Description:**
A clear and concise description of what the bug is.

**To Reproduce:**
Steps to reproduce the behavior:
1. Run command '...'
2. Enter input '...'
3. See error

**Expected Behavior:**
A clear and concise description of what you expected to happen.

**Screenshots:**
If applicable, add screenshots to help explain your problem.

**Environment:**
- OS: [e.g., Windows 11, Ubuntu 22.04, macOS 14]
- Python version: [e.g., 3.11.5]
- Agent version: [e.g., 1.0.0]

**Additional Context:**
Add any other context about the problem here.
```

### Suggesting Features

Feature suggestions are always welcome! Please provide as much detail as possible:

* **Use a clear and descriptive title**
* **Provide a detailed description of the suggested feature**
* **Explain why this feature would be useful**
* **List any similar features in other tools you've used**

### Pull Requests

* Fill in the required template
* Follow the code style guidelines
* Include tests for new features
* Update documentation as needed
* Reference any relevant issues

## 📋 Development Setup

### Prerequisites

* Python 3.10 or higher
* `uv` package manager
* Git

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/stephanos8926-lgtm/rapidwebs-agent.git
cd rapidwebs-agent

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync --dev

# Run tests to verify setup
uv run pytest
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=agent --cov=rapidwebs_agent

# Run specific test file
uv run pytest tests/test_specific.py

# Run tests matching a pattern
uv run pytest -k "test_caching"
```

### Code Style

We use `ruff` for linting and formatting:

```bash
# Check code style
uv run ruff check agent/ rapidwebs_agent/ tests/

# Format code
uv run ruff format agent/ rapidwebs_agent/ tests/
```

## 🏗️ Architecture Overview

### Project Structure

```
rapidwebs-agent/
├── agent/              # Core agent engine
│   ├── agent.py        # Main agent orchestration
│   ├── skills.py       # Skill base classes
│   ├── skills_manager.py  # Skill management
│   ├── models.py       # LLM integration
│   ├── config.py       # Configuration
│   ├── ui.py           # User interface
│   ├── caching/        # Caching system
│   └── subagents/      # SubAgents architecture
├── rapidwebs_agent/    # CLI package
│   └── cli.py          # Command-line interface
├── tools/              # MCP tool servers
├── tests/              # Test suite
└── docs/               # Documentation
```

### Key Components

1. **Agent Core** (`agent/agent.py`) - Main orchestration engine
2. **Skills** (`agent/skills/`) - Modular capabilities (terminal, fs, web, git, etc.)
3. **SubAgents** (`agent/subagents/`) - Parallel task delegation
4. **Caching** (`agent/caching/`) - Token optimization
5. **CLI** (`rapidwebs_agent/cli.py`) - User interface

## 📝 Coding Guidelines

### General Principles

* Write clean, readable code
* Follow PEP 8 style guidelines
* Use type hints for function signatures
* Add docstrings to public functions and classes
* Keep functions focused and small
* Use meaningful variable names

### Type Hints

```python
# Good
def process_file(path: Path, max_lines: int = 100) -> Dict[str, Any]:
    ...

# Avoid
def process_file(path, max_lines=100):
    ...
```

### Docstrings

```python
async def execute(self, **kwargs) -> Dict[str, Any]:
    """Execute the skill with given parameters.

    Args:
        **kwargs: Skill-specific parameters

    Returns:
        Dictionary with execution result containing:
        - success: Boolean indicating success
        - output: Result content
        - error: Error message if failed

    Raises:
        ValueError: If parameters are invalid
    """
```

### Error Handling

```python
# Good
try:
    result = await self._api_call()
except APIError as e:
    logger.error(f"API call failed: {e}")
    return {"success": False, "error": str(e)}
except Exception as e:
    logger.exception("Unexpected error")
    return {"success": False, "error": f"Internal error: {e}"}

# Avoid
try:
    result = await self._api_call()
except:
    return {"error": "failed"}
```

### Logging

Use the logging system for all diagnostic output:

```python
from agent.logging_config import get_logger

logger = get_logger('skills.my_skill')

logger.debug("Debug information")
logger.info("Operation completed")
logger.warning("Potential issue")
logger.error("Error occurred")
logger.exception("Exception with traceback")
```

## 🧪 Testing Guidelines

### Writing Tests

* Name tests descriptively: `test_<function>_<scenario>_<expected_result>`
* Test one thing per test function
* Use fixtures for common setup
* Mock external dependencies
* Include both success and failure cases

### Test Structure

```python
import pytest
from agent.my_module import MyClass

class TestMyClass:
    """Tests for MyClass."""

    def test_initialization(self):
        """Test that MyClass initializes correctly."""
        obj = MyClass()
        assert obj.enabled is True

    def test_execute_success(self):
        """Test successful execution."""
        obj = MyClass()
        result = await obj.execute(param="value")
        assert result['success'] is True

    def test_execute_failure(self):
        """Test execution with invalid parameters."""
        obj = MyClass()
        result = await obj.execute(param=None)
        assert result['success'] is False
        assert 'error' in result
```

### Coverage Goals

* Target: 80%+ code coverage
* Critical paths must be tested
- Error handling paths
- Edge cases

## 📚 Documentation

### Code Documentation

* Add docstrings to all public APIs
* Include type hints
* Add inline comments for complex logic
* Keep comments up to date

### User Documentation

* Update README.md for user-facing changes
* Add examples for new features
* Update configuration documentation
* Include troubleshooting tips

## 🔒 Security Guidelines

* Never commit API keys or secrets
* Use environment variables for sensitive data
* Validate all user inputs
* Follow security best practices for new features
* Report security vulnerabilities privately

## 🚀 Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create pull request
4. Run CI/CD pipeline
5. Merge to main branch
6. Create Git tag
7. Publish to PyPI (automated)

## 💬 Communication

* Use GitHub Issues for bug reports and feature requests
* Use GitHub Discussions for questions and general discussion
* Be respectful and constructive in all communications

## 🎯 Areas Needing Contribution

### High Priority
- [ ] Improve test coverage to 80%
- [ ] Add more code analysis tools
- [ ] Enhance conversation management
- [ ] Create plugin examples

### Medium Priority
- [ ] Add voice input/output support
- [ ] Create Docker integration
- [ ] Add database plugins
- [ ] Improve error messages

### Low Priority
- [ ] Add more themes for UI
- [ ] Create interactive tutorials
- [ ] Add performance benchmarks
- [ ] Create video documentation

## 📜 Code of Conduct

Please note that this project is released with a [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## 📄 License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

Thank you for contributing to RapidWebs Agent! 🚀
