"""
CLI-based code analysis and formatting tools.

Fast, cross-platform wrappers for industry-standard linting/formatting tools.
Tools are bundled for Tier 1 languages (Python, JS/TS, JSON, YAML, Markdown, CSS).

Tier 1 (Bundled):
- Python: ruff (lint + format)
- JavaScript/TypeScript/JSON/YAML/Markdown/CSS: prettier (format)

Tier 2 (Optional - user installs):
- Go: gofmt (built-in with Go)
- Rust: rustfmt (built-in with Rust)
- Shell: shfmt
- SQL: sqlfluff
"""

import subprocess
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import time


@dataclass
class ToolResult:
    """Result from a code tool execution."""
    success: bool
    output: str = ""
    errors: str = ""
    returncode: int = 0
    files_modified: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'success': self.success,
            'output': self.output,
            'errors': self.errors,
            'returncode': self.returncode,
            'files_modified': self.files_modified,
            'duration_ms': self.duration_ms,
            'diagnostics': self.diagnostics
        }


class CodeTools:
    """
    Cross-platform code linting and formatting tools.

    Provides unified interface to industry-standard CLI tools:
    - Ruff: Python linting and formatting (10-100x faster than pylint)
    - Prettier: JS/TS/JSON/YAML/Markdown/CSS formatting

    All tools are optional - graceful degradation if not installed.
    """

    # Language to file extension mapping
    LANGUAGE_EXTENSIONS = {
        'python': ['.py', '.pyi', '.pyw'],
        'javascript': ['.js', '.mjs', '.cjs', '.jsx'],
        'typescript': ['.ts', '.tsx', '.mts', '.cts'],
        'json': ['.json', '.jsonc', '.json5'],
        'yaml': ['.yml', '.yaml'],
        'markdown': ['.md', '.mdx', '.markdown'],
        'css': ['.css', '.scss', '.sass', '.less'],
        'html': ['.html', '.htm'],
        'go': ['.go'],
        'rust': ['.rs'],
        'shell': ['.sh', '.bash', '.zsh', '.fish'],
        'sql': ['.sql'],
    }

    def __init__(self):
        """Initialize code tools with caching for tool availability checks."""
        self._tool_cache: Dict[str, bool] = {}
        self._version_cache: Dict[str, str] = {}

    # =========================================================================
    # Tool Detection Utilities
    # =========================================================================

    def get_tool_command(self, tool_name: str) -> List[str]:
        """
        Get the correct command to run a tool (direct or via Python module).

        Args:
            tool_name: Name of the tool (e.g., 'ruff', 'sqlfluff')

        Returns:
            List of command arguments for subprocess
        """
        # Check if tool is available directly in PATH
        if shutil.which(tool_name) is not None:
            return [tool_name]
        
        # Fall back to Python module for tools installed as packages
        if tool_name in ['ruff', 'sqlfluff']:
            return [sys.executable, '-m', tool_name]
        
        # Default to direct command
        return [tool_name]

    def check_tool_installed(self, tool_name: str) -> bool:
        """
        Check if a command-line tool is installed and available.

        Args:
            tool_name: Name of the tool (e.g., 'ruff', 'prettier')

        Returns:
            True if tool is available in PATH or as Python module
        """
        # Check cache first
        if tool_name in self._tool_cache:
            return self._tool_cache[tool_name]

        # Check if tool exists in PATH
        if shutil.which(tool_name) is not None:
            self._tool_cache[tool_name] = True
            return True
        
        # Check if it's available as a Python module (e.g., ruff, sqlfluff)
        if tool_name in ['ruff', 'sqlfluff']:
            try:
                result = subprocess.run(
                    [sys.executable, '-m', tool_name, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self._tool_cache[tool_name] = True
                    return True
            except (subprocess.TimeoutExpired, Exception):
                pass
        
        self._tool_cache[tool_name] = False
        return False

    def get_tool_version(self, tool_name: str) -> Optional[str]:
        """
        Get version string for an installed tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Version string or None if not installed
        """
        # Check cache first
        if tool_name in self._version_cache:
            return self._version_cache[tool_name]

        try:
            # Try --version flag (works for most tools)
            # First try direct command
            cmd = [tool_name, '--version']
            
            # Use Python module for tools installed as packages
            if tool_name in ['ruff', 'sqlfluff'] and shutil.which(tool_name) is None:
                cmd = [sys.executable, '-m', tool_name, '--version']
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            version = result.stdout.strip() or result.stderr.strip()
            self._version_cache[tool_name] = version
            return version
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return None

    def get_all_tools_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all supported code tools.

        Returns:
            Dictionary with tool names as keys and status info as values
        """
        tools = {
            'ruff': {'name': 'Ruff', 'language': 'Python', 'purpose': 'Lint + Format'},
            'prettier': {'name': 'Prettier', 'language': 'JS/TS/JSON/YAML/MD/CSS', 'purpose': 'Format'},
            'gofmt': {'name': 'gofmt', 'language': 'Go', 'purpose': 'Format'},
            'rustfmt': {'name': 'rustfmt', 'language': 'Rust', 'purpose': 'Format'},
            'shfmt': {'name': 'shfmt', 'language': 'Shell', 'purpose': 'Format'},
            'sqlfluff': {'name': 'SQLFluff', 'language': 'SQL', 'purpose': 'Lint + Format'},
        }

        status = {}
        for tool_name, info in tools.items():
            installed = self.check_tool_installed(tool_name)
            version = self.get_tool_version(tool_name) if installed else None
            status[tool_name] = {
                'installed': installed,
                'version': version,
                'name': info['name'],
                'language': info['language'],
                'purpose': info['purpose']
            }

        return status

    # =========================================================================
    # Language Detection
    # =========================================================================

    def detect_language(self, file_path: str) -> Optional[str]:
        """
        Detect programming language from file extension.

        Args:
            file_path: Path to the file

        Returns:
            Language name (lowercase) or None if unknown
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        for language, extensions in self.LANGUAGE_EXTENSIONS.items():
            if ext in extensions:
                return language

        return None

    def _get_language_from_path(self, file_path: Optional[str],
                                 language: Optional[str]) -> Optional[str]:
        """Get language from explicit parameter or auto-detect from path."""
        if language:
            return language.lower()
        if file_path:
            return self.detect_language(file_path)
        return None

    # =========================================================================
    # Python Tools (Ruff)
    # =========================================================================

    def lint_python(self, file_path: str, content: Optional[str] = None) -> ToolResult:
        """
        Lint Python code using Ruff.

        Args:
            file_path: Path to Python file
            content: Optional content to lint (writes to temp file)

        Returns:
            ToolResult with linting diagnostics
        """
        start_time = time.time()

        if not self.check_tool_installed('ruff'):
            return ToolResult(
                success=False,
                errors='Ruff not installed. Install with: pip install ruff',
                duration_ms=(time.time() - start_time) * 1000
            )

        try:
            # If content provided, write to temp file
            target_path = file_path
            temp_file = None

            if content:
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.py', delete=False, encoding='utf-8'
                )
                temp_file.write(content)
                temp_file.close()
                target_path = temp_file.name

            try:
                # Run ruff check with JSON output
                ruff_cmd = self.get_tool_command('ruff')
                result = subprocess.run(
                    ruff_cmd + ['check', '--output-format', 'json', target_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                # Parse diagnostics
                diagnostics = []
                if result.stdout.strip():
                    try:
                        import json
                        ruff_diagnostics = json.loads(result.stdout)
                        for diag in ruff_diagnostics:
                            diagnostics.append({
                                'type': 'error' if diag.get('severity') == 'error' else 'warning',
                                'code': diag.get('code'),
                                'message': diag.get('message'),
                                'line': diag.get('location', {}).get('row'),
                                'column': diag.get('location', {}).get('column'),
                                'end_line': diag.get('end_location', {}).get('row'),
                                'end_column': diag.get('end_location', {}).get('column'),
                            })
                    except json.JSONDecodeError:
                        pass

                # Returncode 0 = no issues, 1 = issues found
                success = result.returncode in [0, 1]

                return ToolResult(
                    success=success,
                    output=result.stdout,
                    errors=result.stderr,
                    returncode=result.returncode,
                    diagnostics=diagnostics,
                    duration_ms=(time.time() - start_time) * 1000
                )
            finally:
                if temp_file:
                    Path(temp_file.name).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                errors='Ruff timed out after 30 seconds',
                duration_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                success=False,
                errors=f'Ruff error: {str(e)}',
                duration_ms=(time.time() - start_time) * 1000
            )

    def format_python(self, file_path: str, content: Optional[str] = None,
                      check_only: bool = False) -> ToolResult:
        """
        Format Python code using Ruff.

        Args:
            file_path: Path to Python file
            content: Optional content to format
            check_only: If True, only check formatting (don't modify)

        Returns:
            ToolResult with formatted content or check results
        """
        start_time = time.time()

        if not self.check_tool_installed('ruff'):
            return ToolResult(
                success=False,
                errors='Ruff not installed. Install with: pip install ruff',
                duration_ms=(time.time() - start_time) * 1000
            )

        try:
            # If content provided, write to temp file
            target_path = file_path
            temp_file = None
            is_temp = False

            if content:
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.py', delete=False, encoding='utf-8'
                )
                temp_file.write(content)
                temp_file.close()
                target_path = temp_file.name
                is_temp = True

            try:
                # Build command
                ruff_cmd = self.get_tool_command('ruff')
                cmd = ruff_cmd + ['format']
                if check_only:
                    cmd.extend(['--check', '--diff'])
                cmd.append(target_path)

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                # For check mode, return diff in output
                output = result.stdout
                if check_only and result.returncode == 0:
                    output = 'Code is properly formatted'

                # For temp files with content, read formatted result
                formatted_content = None
                if content and not check_only:
                    with open(target_path, 'r', encoding='utf-8') as f:
                        formatted_content = f.read()
                    output = formatted_content

                files_modified = [target_path] if result.returncode == 0 and not check_only else []

                return ToolResult(
                    success=result.returncode in [0, 1],  # 0 = formatted, 1 = would format
                    output=output,
                    errors=result.stderr,
                    returncode=result.returncode,
                    files_modified=files_modified,
                    duration_ms=(time.time() - start_time) * 1000
                )
            finally:
                if temp_file:
                    Path(temp_file.name).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                errors='Ruff format timed out after 30 seconds',
                duration_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                success=False,
                errors=f'Ruff format error: {str(e)}',
                duration_ms=(time.time() - start_time) * 1000
            )

    def fix_python(self, file_path: str, content: Optional[str] = None) -> ToolResult:
        """
        Auto-fix Python linting issues using Ruff.

        Args:
            file_path: Path to Python file
            content: Optional content to fix

        Returns:
            ToolResult with fixed content
        """
        start_time = time.time()

        if not self.check_tool_installed('ruff'):
            return ToolResult(
                success=False,
                errors='Ruff not installed. Install with: pip install ruff',
                duration_ms=(time.time() - start_time) * 1000
            )

        try:
            # If content provided, write to temp file
            target_path = file_path
            temp_file = None

            if content:
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.py', delete=False, encoding='utf-8'
                )
                temp_file.write(content)
                temp_file.close()
                target_path = temp_file.name

            try:
                # Run ruff check with --fix
                ruff_cmd = self.get_tool_command('ruff')
                result = subprocess.run(
                    ruff_cmd + ['check', '--fix', target_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                # Read fixed content
                fixed_content = None
                if content:
                    with open(target_path, 'r', encoding='utf-8') as f:
                        fixed_content = f.read()

                return ToolResult(
                    success=result.returncode in [0, 1],
                    output=fixed_content or result.stdout,
                    errors=result.stderr,
                    returncode=result.returncode,
                    files_modified=[target_path] if result.returncode == 0 else [],
                    duration_ms=(time.time() - start_time) * 1000
                )
            finally:
                if temp_file:
                    Path(temp_file.name).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                errors='Ruff fix timed out after 30 seconds',
                duration_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                success=False,
                errors=f'Ruff fix error: {str(e)}',
                duration_ms=(time.time() - start_time) * 1000
            )

    # =========================================================================
    # JavaScript/TypeScript/JSON/YAML/Markdown/CSS Tools (Prettier)
    # =========================================================================

    def _run_prettier(self, file_path: str, content: Optional[str] = None,
                      check_only: bool = False, parser: Optional[str] = None) -> ToolResult:
        """
        Internal method to run Prettier on a file.

        Args:
            file_path: Path to file
            content: Optional content to format
            check_only: If True, only check formatting
            parser: Optional parser override

        Returns:
            ToolResult with formatting results
        """
        start_time = time.time()

        if not self.check_tool_installed('prettier'):
            return ToolResult(
                success=False,
                errors='Prettier not installed. Install with: npm install -g prettier',
                duration_ms=(time.time() - start_time) * 1000
            )

        try:
            # If content provided, write to temp file
            target_path = file_path
            temp_file = None

            if content:
                # Determine extension from parser or file_path
                ext_map = {
                    'babel': '.js', 'typescript': '.ts', 'json': '.json',
                    'yaml': '.yaml', 'markdown': '.md', 'css': '.css',
                    'html': '.html', 'babel-ts': '.tsx'
                }
                suffix = ext_map.get(parser, Path(file_path).suffix if file_path else '.js')
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w', suffix=suffix, delete=False, encoding='utf-8'
                )
                temp_file.write(content)
                temp_file.close()
                target_path = temp_file.name

            try:
                # Build command
                cmd = ['prettier']
                if check_only:
                    cmd.append('--check')
                else:
                    cmd.extend(['--write', '--log-level', 'warn'])

                if parser:
                    cmd.extend(['--parser', parser])

                cmd.append(target_path)

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                # Read formatted content
                formatted_content = None
                if content:
                    with open(target_path, 'r', encoding='utf-8') as f:
                        formatted_content = f.read()

                # Determine success
                success = result.returncode == 0
                if check_only and result.returncode == 1:
                    success = True  # Check found issues but ran successfully

                return ToolResult(
                    success=success,
                    output=formatted_content or result.stdout,
                    errors=result.stderr,
                    returncode=result.returncode,
                    files_modified=[target_path] if not check_only and success else [],
                    duration_ms=(time.time() - start_time) * 1000
                )
            finally:
                if temp_file:
                    Path(temp_file.name).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                errors='Prettier timed out after 30 seconds',
                duration_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ToolResult(
                success=False,
                errors=f'Prettier error: {str(e)}',
                duration_ms=(time.time() - start_time) * 1000
            )

    def format_javascript(self, file_path: str, content: Optional[str] = None,
                          check_only: bool = False) -> ToolResult:
        """Format JavaScript code using Prettier."""
        return self._run_prettier(file_path, content, check_only, parser='babel')

    def format_typescript(self, file_path: str, content: Optional[str] = None,
                          check_only: bool = False) -> ToolResult:
        """Format TypeScript code using Prettier."""
        return self._run_prettier(file_path, content, check_only, parser='typescript')

    def format_json(self, file_path: str, content: Optional[str] = None,
                    check_only: bool = False) -> ToolResult:
        """Format JSON code using Prettier."""
        return self._run_prettier(file_path, content, check_only, parser='json')

    def format_yaml(self, file_path: str, content: Optional[str] = None,
                    check_only: bool = False) -> ToolResult:
        """Format YAML code using Prettier."""
        return self._run_prettier(file_path, content, check_only, parser='yaml')

    def format_markdown(self, file_path: str, content: Optional[str] = None,
                        check_only: bool = False) -> ToolResult:
        """Format Markdown code using Prettier."""
        return self._run_prettier(file_path, content, check_only, parser='markdown')

    def format_css(self, file_path: str, content: Optional[str] = None,
                   check_only: bool = False) -> ToolResult:
        """Format CSS code using Prettier."""
        return self._run_prettier(file_path, content, check_only, parser='css')

    def format_html(self, file_path: str, content: Optional[str] = None,
                    check_only: bool = False) -> ToolResult:
        """Format HTML code using Prettier."""
        return self._run_prettier(file_path, content, check_only, parser='html')

    # =========================================================================
    # Tier 2 Language Tools (Optional)
    # =========================================================================

    def format_go(self, file_path: str, content: Optional[str] = None) -> ToolResult:
        """Format Go code using gofmt."""
        start_time = time.time()

        if not self.check_tool_installed('gofmt'):
            return ToolResult(
                success=False,
                errors='gofmt not installed. Install Go from https://go.dev/',
                duration_ms=(time.time() - start_time) * 1000
            )

        try:
            target_path = file_path
            temp_file = None

            if content:
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.go', delete=False, encoding='utf-8'
                )
                temp_file.write(content)
                temp_file.close()
                target_path = temp_file.name

            try:
                # gofmt -w writes to file, gofmt without -w outputs to stdout
                if content:
                    result = subprocess.run(
                        ['gofmt', target_path],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    return ToolResult(
                        success=result.returncode == 0,
                        output=result.stdout,
                        errors=result.stderr,
                        returncode=result.returncode,
                        duration_ms=(time.time() - start_time) * 1000
                    )
                else:
                    result = subprocess.run(
                        ['gofmt', '-w', target_path],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    return ToolResult(
                        success=result.returncode == 0,
                        output='Formatted successfully',
                        errors=result.stderr,
                        returncode=result.returncode,
                        files_modified=[target_path],
                        duration_ms=(time.time() - start_time) * 1000
                    )
            finally:
                if temp_file:
                    Path(temp_file.name).unlink(missing_ok=True)

        except Exception as e:
            return ToolResult(
                success=False,
                errors=f'gofmt error: {str(e)}',
                duration_ms=(time.time() - start_time) * 1000
            )

    def format_rust(self, file_path: str, content: Optional[str] = None) -> ToolResult:
        """Format Rust code using rustfmt."""
        start_time = time.time()

        if not self.check_tool_installed('rustfmt'):
            return ToolResult(
                success=False,
                errors='rustfmt not installed. Install Rust from https://rustup.rs/',
                duration_ms=(time.time() - start_time) * 1000
            )

        try:
            target_path = file_path
            temp_file = None

            if content:
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.rs', delete=False, encoding='utf-8'
                )
                temp_file.write(content)
                temp_file.close()
                target_path = temp_file.name

            try:
                if content:
                    result = subprocess.run(
                        ['rustfmt', '--emit', 'stdout', target_path],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    return ToolResult(
                        success=result.returncode == 0,
                        output=result.stdout,
                        errors=result.stderr,
                        returncode=result.returncode,
                        duration_ms=(time.time() - start_time) * 1000
                    )
                else:
                    result = subprocess.run(
                        ['rustfmt', target_path],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    return ToolResult(
                        success=result.returncode == 0,
                        output='Formatted successfully',
                        errors=result.stderr,
                        returncode=result.returncode,
                        files_modified=[target_path],
                        duration_ms=(time.time() - start_time) * 1000
                    )
            finally:
                if temp_file:
                    Path(temp_file.name).unlink(missing_ok=True)

        except Exception as e:
            return ToolResult(
                success=False,
                errors=f'rustfmt error: {str(e)}',
                duration_ms=(time.time() - start_time) * 1000
            )

    def format_shell(self, file_path: str, content: Optional[str] = None) -> ToolResult:
        """Format Shell script using shfmt."""
        start_time = time.time()

        if not self.check_tool_installed('shfmt'):
            return ToolResult(
                success=False,
                errors='shfmt not installed. Install with: go install mvdan.cc/sh/v3/cmd/shfmt@latest',
                duration_ms=(time.time() - start_time) * 1000
            )

        try:
            target_path = file_path
            temp_file = None

            if content:
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.sh', delete=False, encoding='utf-8'
                )
                temp_file.write(content)
                temp_file.close()
                target_path = temp_file.name

            try:
                if content:
                    result = subprocess.run(
                        ['shfmt', target_path],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    return ToolResult(
                        success=result.returncode == 0,
                        output=result.stdout,
                        errors=result.stderr,
                        returncode=result.returncode,
                        duration_ms=(time.time() - start_time) * 1000
                    )
                else:
                    result = subprocess.run(
                        ['shfmt', '-w', target_path],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    return ToolResult(
                        success=result.returncode == 0,
                        output='Formatted successfully',
                        errors=result.stderr,
                        returncode=result.returncode,
                        files_modified=[target_path],
                        duration_ms=(time.time() - start_time) * 1000
                    )
            finally:
                if temp_file:
                    Path(temp_file.name).unlink(missing_ok=True)

        except Exception as e:
            return ToolResult(
                success=False,
                errors=f'shfmt error: {str(e)}',
                duration_ms=(time.time() - start_time) * 1000
            )

    def lint_sql(self, file_path: str, content: Optional[str] = None) -> ToolResult:
        """Lint SQL code using sqlfluff."""
        start_time = time.time()

        if not self.check_tool_installed('sqlfluff'):
            return ToolResult(
                success=False,
                errors='SQLFluff not installed. Install with: pip install sqlfluff',
                duration_ms=(time.time() - start_time) * 1000
            )

        try:
            target_path = file_path
            temp_file = None

            if content:
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.sql', delete=False, encoding='utf-8'
                )
                temp_file.write(content)
                temp_file.close()
                target_path = temp_file.name

            try:
                result = subprocess.run(
                    ['sqlfluff', 'lint', '--format', 'json', target_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                diagnostics = []
                if result.stdout.strip():
                    try:
                        import json
                        sqlfluff_diagnostics = json.loads(result.stdout)
                        for violation in sqlfluff_diagnostics.get('violations', []):
                            diagnostics.append({
                                'type': 'warning',
                                'code': violation.get('code'),
                                'message': violation.get('description'),
                                'line': violation.get('line_no'),
                                'position': violation.get('line_pos'),
                            })
                    except json.JSONDecodeError:
                        pass

                return ToolResult(
                    success=result.returncode in [0, 1],
                    output=result.stdout,
                    errors=result.stderr,
                    returncode=result.returncode,
                    diagnostics=diagnostics,
                    duration_ms=(time.time() - start_time) * 1000
                )
            finally:
                if temp_file:
                    Path(temp_file.name).unlink(missing_ok=True)

        except Exception as e:
            return ToolResult(
                success=False,
                errors=f'SQLFluff error: {str(e)}',
                duration_ms=(time.time() - start_time) * 1000
            )

    # =========================================================================
    # Unified API - Auto-detect language and route to appropriate tool
    # =========================================================================

    def format_file(self, file_path: str, content: Optional[str] = None,
                    check_only: bool = False, language: Optional[str] = None) -> ToolResult:
        """
        Format a code file, auto-detecting language.

        Args:
            file_path: Path to file
            content: Optional content to format (returns formatted string)
            check_only: If True, only check formatting
            language: Optional language override

        Returns:
            ToolResult with formatted content
        """
        detected_lang = self._get_language_from_path(file_path, language)

        if not detected_lang:
            return ToolResult(
                success=False,
                errors=f'Unknown language for file: {file_path}. Specify language explicitly.'
            )

        # Route to appropriate formatter
        formatters = {
            'python': lambda: self.format_python(file_path, content, check_only),
            'javascript': lambda: self.format_javascript(file_path, content, check_only),
            'typescript': lambda: self.format_typescript(file_path, content, check_only),
            'json': lambda: self.format_json(file_path, content, check_only),
            'yaml': lambda: self.format_yaml(file_path, content, check_only),
            'markdown': lambda: self.format_markdown(file_path, content, check_only),
            'css': lambda: self.format_css(file_path, content, check_only),
            'html': lambda: self.format_html(file_path, content, check_only),
            'go': lambda: self.format_go(file_path, content),
            'rust': lambda: self.format_rust(file_path, content),
            'shell': lambda: self.format_shell(file_path, content),
        }

        formatter = formatters.get(detected_lang)
        if formatter:
            return formatter()

        return ToolResult(
            success=False,
            errors=f'No formatter available for language: {detected_lang}'
        )

    def lint_file(self, file_path: str, content: Optional[str] = None,
                  language: Optional[str] = None) -> ToolResult:
        """
        Lint a code file, auto-detecting language.

        Args:
            file_path: Path to file
            content: Optional content to lint
            language: Optional language override

        Returns:
            ToolResult with linting diagnostics
        """
        detected_lang = self._get_language_from_path(file_path, language)

        if not detected_lang:
            return ToolResult(
                success=False,
                errors=f'Unknown language for file: {file_path}. Specify language explicitly.'
            )

        # Route to appropriate linter
        linters = {
            'python': lambda: self.lint_python(file_path, content),
            'sql': lambda: self.lint_sql(file_path, content),
        }

        linter = linters.get(detected_lang)
        if linter:
            return linter()

        # For languages without dedicated linters, try format check
        if detected_lang in ['javascript', 'typescript', 'json', 'yaml', 'markdown', 'css', 'html']:
            return self.format_file(file_path, content, check_only=True, language=detected_lang)

        return ToolResult(
            success=False,
            errors=f'No linter available for language: {detected_lang}'
        )

    def fix_file(self, file_path: str, content: Optional[str] = None,
                 language: Optional[str] = None) -> ToolResult:
        """
        Auto-fix issues in a code file.

        Args:
            file_path: Path to file
            content: Optional content to fix
            language: Optional language override

        Returns:
            ToolResult with fixed content
        """
        detected_lang = self._get_language_from_path(file_path, language)

        if detected_lang == 'python':
            return self.fix_python(file_path, content)

        # For other languages, formatting often fixes issues
        return self.format_file(file_path, content, language=detected_lang)

    # =========================================================================
    # Workspace Language Detection
    # =========================================================================

    def detect_workspace_languages(self, directory: str = '.',
                                    max_files: int = 100) -> Dict[str, int]:
        """
        Detect programming languages used in a workspace.

        Scans directory for code files and counts by language.

        Args:
            directory: Directory to scan
            max_files: Maximum files to scan

        Returns:
            Dictionary mapping language to file count
        """
        from pathlib import Path

        languages: Dict[str, int] = {}
        dir_path = Path(directory)

        files_scanned = 0
        for ext_group in dir_path.rglob('*'):
            if files_scanned >= max_files:
                break

            if not ext_group.is_file():
                continue

            # Skip hidden directories and common non-code directories
            if any(part.startswith('.') for part in ext_group.parts):
                continue
            if any(part in ['node_modules', '__pycache__', 'venv', '.venv',
                           'dist', 'build', '.git', 'target'] for part in ext_group.parts):
                continue

            files_scanned += 1
            lang = self.detect_language(str(ext_group))
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

        return languages

    def get_missing_tools(self, languages: Optional[List[str]] = None,
                          directory: str = '.') -> Dict[str, List[str]]:
        """
        Get list of missing tools for detected or specified languages.

        Args:
            languages: Optional list of languages to check
            directory: Directory to scan if languages not specified

        Returns:
            Dictionary with 'missing' and 'installed' tool lists
        """
        # If no languages specified, detect from workspace
        if not languages:
            detected = self.detect_workspace_languages(directory)
            languages = list(detected.keys())

        # Map languages to required tools
        language_tools = {
            'python': ['ruff'],
            'javascript': ['prettier'],
            'typescript': ['prettier'],
            'json': ['prettier'],
            'yaml': ['prettier'],
            'markdown': ['prettier'],
            'css': ['prettier'],
            'html': ['prettier'],
            'go': ['gofmt'],
            'rust': ['rustfmt'],
            'shell': ['shfmt'],
            'sql': ['sqlfluff'],
        }

        missing = []
        installed = []

        for lang in languages:
            tools = language_tools.get(lang, [])
            for tool in tools:
                if self.check_tool_installed(tool):
                    if tool not in installed:
                        installed.append(tool)
                else:
                    if tool not in missing:
                        missing.append(tool)

        return {
            'missing': missing,
            'installed': installed,
            'languages': languages
        }

    # =========================================================================
    # Tool Installation Helpers
    # =========================================================================

    @staticmethod
    def get_install_command(tool: str) -> Optional[str]:
        """
        Get installation command for a tool.

        Args:
            tool: Tool name

        Returns:
            Installation command or None if unknown
        """
        commands = {
            'prettier': 'npm install -g prettier',
            'gofmt': 'Install Go from https://go.dev/ (gofmt included)',
            'rustfmt': 'rustup component add rustfmt',
            'shfmt': 'go install mvdan.cc/sh/v3/cmd/shfmt@latest',
            'sqlfluff': 'pip install sqlfluff',
        }
        return commands.get(tool)

    @staticmethod
    def get_tool_tier(tool: str) -> int:
        """
        Get tool tier (1 = core, 2 = optional).

        Args:
            tool: Tool name

        Returns:
            Tier number
        """
        tier1 = ['ruff', 'prettier']
        tier2 = ['gofmt', 'rustfmt', 'shfmt', 'sqlfluff']

        if tool in tier1:
            return 1
        elif tool in tier2:
            return 2
        return 0

    def install_tool(self, tool: str, auto_confirm: bool = False) -> Dict[str, Any]:
        """
        Install a code tool.

        Args:
            tool: Tool name to install
            auto_confirm: If True, skip confirmation prompts

        Returns:
            Installation result dictionary
        """
        import subprocess

        tier = self.get_tool_tier(tool)
        install_cmd = self.get_install_command(tool)

        if not install_cmd:
            return {
                'success': False,
                'error': f'Unknown tool: {tool}',
                'tier': tier
            }

        # Check if already installed
        if self.check_tool_installed(tool):
            return {
                'success': True,
                'already_installed': True,
                'tool': tool,
                'tier': tier
            }

        # Tier 1 tools (prettier)
        if tool == 'prettier':
            try:
                result = subprocess.run(
                    ['npm', 'install', '-g', 'prettier'],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if result.returncode == 0:
                    # Clear cache
                    self._tool_cache.pop('prettier', None)
                    return {
                        'success': True,
                        'tool': tool,
                        'tier': tier,
                        'message': 'Prettier installed successfully'
                    }
                else:
                    return {
                        'success': False,
                        'tool': tool,
                        'tier': tier,
                        'error': f'npm install failed: {result.stderr[:200]}'
                    }
            except FileNotFoundError:
                return {
                    'success': False,
                    'tool': tool,
                    'tier': tier,
                    'error': 'npm not found. Please install Node.js from https://nodejs.org/'
                }
            except subprocess.TimeoutExpired:
                return {
                    'success': False,
                    'tool': tool,
                    'tier': tier,
                    'error': 'Installation timed out after 120 seconds'
                }

        # Tier 2 tools - provide instructions
        return {
            'success': False,
            'tool': tool,
            'tier': tier,
            'manual_install': True,
            'command': install_cmd,
            'message': f'Please install manually: {install_cmd}'
        }

    def install_missing_tools(self, languages: Optional[List[str]] = None,
                               directory: str = '.',
                               auto_confirm: bool = False) -> Dict[str, Any]:
        """
        Install all missing tools for detected languages.

        Args:
            languages: Optional list of languages
            directory: Directory to scan
            auto_confirm: If True, install without prompting

        Returns:
            Installation results
        """
        missing_info = self.get_missing_tools(languages, directory)
        results = {
            'languages_detected': missing_info['languages'],
            'tools_installed': [],
            'tools_failed': [],
            'tools_manual': []
        }

        # Install Tier 1 tools automatically
        for tool in missing_info['missing']:
            tier = self.get_tool_tier(tool)

            if tier == 1:
                # Auto-install Tier 1
                result = self.install_tool(tool, auto_confirm)
                if result['success']:
                    results['tools_installed'].append(tool)
                else:
                    results['tools_failed'].append({
                        'tool': tool,
                        'error': result.get('error', 'Unknown error')
                    })
            elif tier == 2:
                # Tier 2 requires manual install
                results['tools_manual'].append({
                    'tool': tool,
                    'command': self.get_install_command(tool)
                })

        return results
