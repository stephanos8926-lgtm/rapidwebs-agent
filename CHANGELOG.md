# Changelog

All notable changes to RapidWebs Agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Expand/Collapse Tool Output** - Press `e` to expand, `c` to collapse large tool outputs
- **Output Management Commands** - `/expand-output` and `/collapse-output` commands
- **TODO System Integration** - Full keyboard shortcut (`Ctrl+T`) and command support
- **Test Suite** - `test_subagent_fixes.py` for validating SubAgent error handling

### Changed
- **Help Command** - Updated `/help` with output management and expanded keyboard shortcuts
- **Tab Completion** - Added `expand-output`, `collapse-output` to autocompletion
- **Configuration Wizard** - Added output management preferences (collapse by default, preview lines)
- **README.md** - Updated with new commands and keyboard shortcuts

### Fixed
- **SubAgent Error Handling** - SubAgents now return proper FAILED status instead of placeholder content (Bug 1.1-1.4)
- **CodeAgent Metadata Bug** - Fixed dict vs object access for `files_modified`
- **DocsAgent Language Parameter** - Added missing `language` parameter to API_DOCS_PROMPT
- **SQLite Connection Leaks** - Added `close()` and `__del__()` to all SQLite-backed classes
- **ResourceWarnings** - Eliminated 20+ SQLite connection warnings in tests

### Performance
- **Test Suite** - 211 passed, 1 skipped (25.71% coverage)
- **Zero SQLite Warnings** - Down from 20+ warnings

### Security
- None

---

## [2.3.0] - 2026-03-07

### Added
- **ResearchAgent Timeout Protection** - 60s timeout on all LLM operations (5 methods)

### Changed
- **SecurityAgent Classification** - Improved keyword matching with partial matching for plurals
- **Documentation** - Consolidated from 24 files to 13 (46% reduction)

### Fixed
- **ResearchAgent** - Timeout protection for web search, documentation, codebase research, summarization
- **Test Classification** - Fixed keyword matching for "dependencies" vs "dependency"

### Security
- None

---

## [2.2.0] - 2026-03-07

### Added
- **ResearchAgent** - New subagent for web research, documentation lookup, and information synthesis
- **SecurityAgent** - New subagent for dependency auditing, OWASP Top 10 scanning, and secret detection
- **CLI Security Commands** - `--security-audit`, `--scan-secrets`, `--audit-deps`, `--research`
- **9 Secret Detection Patterns** - AWS, GitHub, Google API keys, private keys, bearer tokens, etc.
- **OWASP Top 10 Scanning** - Automated vulnerability detection for all 10 categories

### Changed
- Updated SubAgents orchestrator to support 5 agent types (was 3)
- Enhanced SecurityAgent keyword matching for task classification

### Fixed
- ResearchAgent task classification for codebase searches
- SecurityAgent task classification with plural keyword support

### Security
- Dependency vulnerability scanning with CVE detection
- Code security analysis with OWASP Top 10 patterns
- Configuration security review

---

## [2.1.1] - 2026-03-07

### Fixed
- **Test Import Errors** - Fixed 6 MCP server test imports (`caching_mcp_server` → `mcp_server_caching`)
- **Test Assertions** - Fixed Research/Security agent classification test assertions
- **Test Suite** - All 212 tests now passing (was 204/212)

---

## [2.1.0] - 2026-03-06

### Added
- **Module Refactoring** - Renamed core modules for clarity:
  - `core.py` → `agent.py`
  - `skills.py` → `skills_manager.py`
  - `ui.py` → `user_interface.py`
  - `utils.py` → `utilities.py`
  - `models.py` → `llm_models.py`
  - `context_optimization.py` → `context_manager.py`
  - `code_tools.py` → `code_analysis_tools.py`
  - `config_wizard.py` → `configuration_wizard.py`
  - `approval.py` → `approval_workflow.py`
- **Compatibility Shims** - All old imports still work via re-export modules
- **Documentation Consolidation** - Merged 22 docs into 11 organized guides

### Changed
- Updated `pyproject.toml` MCP server entry points
- Updated all internal imports to new module names

### Fixed
- Import paths in CLI, agent, and test files

---

## [2.0.0] - 2026-03-06

### Added
- **Hanging Condition Fixes** - 7 critical/high/medium issues resolved:
  - TestAgent subprocess timeout (300s default) - CRITICAL
  - SearchSkill grep/find timeouts (30s) - HIGH
  - FilesystemSkill async I/O with `asyncio.to_thread()` - HIGH
  - ResponseCache async file hashing with size limits - HIGH
  - ContentAddressableCache bounded eviction (100 iterations max) - MEDIUM
  - GitSkill overall timeout protection - MEDIUM
  - ResearchAgent LLM timeout (60s outer wrapper)
- **Windows Compatibility Fixes**:
  - Approval workflow uses dedicated thread (no thread pool exhaustion)
  - 60-second input timeout protection
  - Enhanced exception logging in `_build_context()`
- **Filesystem Timeout Protection**:
  - Configurable `operation_timeout` (default: 30s)
  - Longer timeout for `explore` (90s max)
  - Comprehensive operation logging
- **TUI Output Management**:
  - Reduced inline display: 10KB → 2KB
  - Reduced line limit: 50 → 20 lines
  - Auto-summarization for large outputs
- **Enhanced Tool Execution Logging**:
  - Logging at all stages (request, approval, execution, result)
  - Fallback auto-approve if approval workflow fails
  - Clear error messages with suggestions

### Changed
- **Approval Workflow** - Windows-compatible async input handling
- **Output Thresholds** - More conservative inline display limits
- **Keyword Matching** - SecurityAgent uses partial matching for plurals

### Fixed
- RuntimeWarning for unawaited coroutine in `_build_context()`
- Approval workflow hanging on Windows (thread pool exhaustion)
- Filesystem operations without timeout protection
- Event loop blocking during file I/O operations
- Cache operations blocking on large files
- Potential infinite loop in cache eviction

### Security
- Command timeout protection prevents resource exhaustion
- File size limits on hashing operations (10MB max)
- Bounded iteration limits prevent infinite loops

---

## [1.1.0] - 2026-03-06

### Added
- **Logging System** - Comprehensive logging with file rotation, JSON formatting, and session-based logs
- **Git Integration** - Full Git skill with status, diff, commit, branch, and log operations
- **CI/CD Pipeline** - GitHub Actions workflow with testing, linting, security scanning, and publishing
- **CLI Enhancement Commands**:
  - `/mode` - Switch approval modes (plan/default/auto-edit/yolo)
  - Keyboard shortcuts: Ctrl+P/D/A/Y for modes, Ctrl+L clear
- **Approval Mode System** - 4 modes with different confirmation levels

### Changed
- Updated configuration to include logging settings
- Integrated logging into core agent module
- Enhanced help message with approval modes and shortcuts

### Fixed
- None

### Security
- Added security scanning to CI/CD (safety, bandit)

---

## [1.0.0] - 2026-03-06

### Added
- **Core Agent Features**
  - Cross-platform agentic CLI (Windows, Linux, macOS)
  - Free-tier LLM optimization (Qwen Coder + Gemini)
  - Token budget enforcement with daily limits
  - Approval workflow (Plan/Default/Auto-Edit/YOLO modes)
  
- **Skills System**
  - Terminal execution with command whitelisting
  - Filesystem operations (read, write, list, explore)
  - Web scraping with SSRF protection
  - Codebase search (grep, file search)
  - Code tools (linting/formatting with Ruff)

- **SubAgents Architecture**
  - Code Agent for refactoring and debugging
  - Test Agent for test generation
  - Docs Agent for documentation
  - Research Agent for web research
  - Security Agent for vulnerability scanning
  - Parallel task execution with result aggregation

- **Caching System (Tier 4)**
  - Hash-based change detection
  - Content-addressable storage
  - Response caching with TTL
  - Token budget enforcement
  - Lazy directory loading
  - 70-85% token savings

- **Context Optimization**
  - AST-based semantic chunking
  - Delta updates for context changes
  - Symbol extraction
  - File recommendations
  - Call hierarchy analysis
  - Import graph tracking

- **User Interface**
  - Rich terminal UI with `prompt_toolkit`
  - Token budget dashboard
  - Command autocomplete
  - Streaming responses
  - Conversation persistence

### Changed
- None (initial release)

### Deprecated
- None

### Removed
- LSP integration (replaced with lightweight grep-based alternatives)

### Fixed
- Race conditions in SubAgents orchestrator
- Timeout protection in ResearchAgent
- False positives in secret detection patterns
- File encoding issues in SecurityAgent

### Security
- Command whitelisting for terminal execution
- SSRF protection for web scraping
- Secret detection patterns (AWS, GitHub, Google, etc.)
- OWASP Top 10 vulnerability scanning
- File system sandboxing

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 2.3.0 | 2026-03-07 | Codebase cleanup, shim removal, doc consolidation |
| 2.2.0 | 2026-03-07 | Research & Security SubAgents |
| 2.1.1 | 2026-03-07 | Test fixes (212/212 passing) |
| 2.1.0 | 2026-03-06 | Module refactoring + compatibility shims |
| 2.0.0 | 2026-03-06 | Hanging condition fixes + Windows compatibility |
| 1.1.0 | 2026-03-06 | Logging, Git, CI/CD, CLI enhancements |
| 1.0.0 | 2026-03-06 | Initial production release |

---

## Upcoming Features

### Planned for v2.4.0
- [ ] Conversation search and branching
- [ ] Plugin/extension system
- [ ] PDF/HTML conversation export
- [ ] Per-project configuration overrides
- [ ] Improved test coverage (target: 80%)

### Under Consideration
- [ ] Voice input/output
- [ ] Docker integration
- [ ] Database plugin
- [ ] Cloud deployment helpers
- [ ] Real-time collaboration features

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/stephanos8926-lgtm/rapidwebs-agent/issues) page.
