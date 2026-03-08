"""Skills and Sub-agents architecture for modular tool execution"""
import subprocess
import shlex
from typing import Dict, Any, List, Optional, Callable, Tuple
from pathlib import Path
import re
import asyncio
from bs4 import BeautifulSoup
import httpx
import socket
import ipaddress
from urllib.parse import urlparse
import json
import os
from abc import ABC, abstractmethod

from .config import Config
from .utilities import sanitize_path, is_safe_path

# Import output management
try:
    from .temp_manager import get_temp_manager, TempManager
    from .output_manager import OutputManager
    OUTPUT_MANAGEMENT_AVAILABLE = True
except ImportError:
    TempManager = None
    OutputManager = None
    OUTPUT_MANAGEMENT_AVAILABLE = False

# Import code tools skill
try:
    from .code_analysis_tools import CodeTools
    CODE_TOOLS_AVAILABLE = True
except ImportError:
    CODE_TOOLS_AVAILABLE = False
    CodeTools = None

# Import subagents for skill
try:
    from .subagents import SubAgentType, SubAgentTask, create_orchestrator
    SUBAGENTS_AVAILABLE = True
except ImportError:
    SUBAGENTS_AVAILABLE = False
    SubAgentType = None
    SubAgentTask = None
    create_orchestrator = None

# Import Git skill
try:
    from .skills.git_skill import GitSkill
    GIT_SKILL_AVAILABLE = True
except ImportError:
    GIT_SKILL_AVAILABLE = False
    GitSkill = None

# Import Memory skill
try:
    from .skills.memory_skill import MemorySkill
    MEMORY_SKILL_AVAILABLE = True
except ImportError:
    MEMORY_SKILL_AVAILABLE = False
    MemorySkill = None


class SkillBase(ABC):
    """Base class for all agent skills"""

    def __init__(self, config: Any, name: str):
        self.config = config
        self.name = name
        self.enabled = True

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the skill with given parameters"""

    def validate(self, **kwargs) -> bool:
        """Validate input parameters before execution"""
        return True


class TerminalExecutorSkill(SkillBase):
    """Execute whitelisted shell commands safely using subprocess.exec"""

    def __init__(self, config: Any):
        super().__init__(config, 'terminal_executor')
        self.whitelist = set(config.get('skills.terminal_executor.whitelist', []))
        self.max_time = config.get('skills.terminal_executor.max_execution_time', 30)
        self.timeout = config.get('skills.terminal_executor.timeout', 10)

    def validate(self, command: str) -> Tuple[bool, Optional[str]]:
        """Validate command against whitelist and return error message if invalid"""
        if not command or not command.strip():
            return False, "Empty command"

        try:
            parsed = shlex.split(command)
            if not parsed:
                return False, "Failed to parse command"

            base_cmd = Path(parsed[0]).name

            # Check against whitelist
            if base_cmd not in self.whitelist:
                return False, f"Command '{base_cmd}' not in whitelist. Allowed: {', '.join(sorted(self.whitelist))}"

            # Block dangerous patterns
            dangerous_patterns = ['$', '`', '|', ';', '&', '>', '<', '(', ')', '{', '}', '[', ']']
            for pattern in dangerous_patterns:
                if pattern in command and pattern not in ['-', '_']:
                    # Allow hyphens and underscores in arguments
                    if pattern in ['-', '_']:
                        continue
                    # Check if it's actually being used for shell expansion
                    if pattern in ['|', ';', '&', '>', '<']:
                        return False, f"Shell operator '{pattern}' not allowed for security"

            return True, None
        except Exception as e:
            return False, f"Command parsing error: {str(e)}"

    async def execute(self, command: str) -> Dict[str, Any]:
        """Execute shell command using subprocess.exec for security"""
        valid, error_msg = self.validate(command)
        if not valid:
            return {
                'success': False,
                'error': error_msg,
                'stdout': '',
                'stderr': ''
            }

        try:
            # Parse command into arguments for safe execution
            args = shlex.split(command)
            
            # Use create_subprocess_exec instead of create_subprocess_shell
            # This prevents shell injection attacks
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024  # 1MB buffer limit
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.max_time
                )

                return {
                    'success': process.returncode == 0,
                    'stdout': stdout.decode('utf-8', errors='ignore'),
                    'stderr': stderr.decode('utf-8', errors='ignore'),
                    'returncode': process.returncode
                }
            except asyncio.TimeoutError:
                process.kill()
                return {
                    'success': False,
                    'error': f'Command timeout after {self.max_time}s',
                    'stdout': '',
                    'stderr': ''
                }

        except FileNotFoundError as e:
            return {
                'success': False,
                'error': f'Command not found: {args[0] if args else command}',
                'stdout': '',
                'stderr': ''
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': ''
            }


class WebScraperSkill(SkillBase):
    """Scrape web content with SSRF protection"""

    def __init__(self, config: Any):
        super().__init__(config, 'web_scraper')
        self.user_agent = config.get('skills.web_scraper.user_agent', 'RapidWebs-Agent/1.0')
        self.timeout = config.get('skills.web_scraper.timeout', 10)
        self.client: Optional[httpx.AsyncClient] = None

    def _is_safe_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Validate URL and check for SSRF risks"""
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                return False, f"Invalid scheme: {parsed.scheme}. Only http/https allowed"
            
            # Check hostname
            hostname = parsed.hostname
            if not hostname:
                return False, "No hostname in URL"
            
            # Block localhost/private IPs
            blocked_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
            if hostname.lower() in blocked_hosts:
                return False, f"Access to {hostname} is blocked for security"
            
            # Check if hostname resolves to private IP
            try:
                ip_addresses = socket.getaddrinfo(hostname, None)
                for family, _, _, _, sockaddr in ip_addresses:
                    ip_str = sockaddr[0]
                    try:
                        ip = ipaddress.ip_address(ip_str)
                        if ip.is_private or ip.is_loopback or ip.is_link_local:
                            return False, f"Hostname {hostname} resolves to private IP {ip_str}"
                    except ValueError:
                        continue
            except socket.gaierror:
                return False, f"Could not resolve hostname: {hostname}"
            
            return True, None
        except Exception as e:
            return False, f"URL validation error: {str(e)}"

    def validate(self, url: str) -> Tuple[bool, Optional[str]]:
        """Validate URL format and security"""
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not bool(url_pattern.match(url)):
            return False, "Invalid URL format"
        
        return self._is_safe_url(url)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper lifecycle management"""
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={'User-Agent': self.user_agent},
                follow_redirects=True,
                max_redirects=5
            )
        return self.client

    async def close(self):
        """Close HTTP client to prevent memory leaks"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
            self.client = None

    async def execute(self, url: str, extract_text: bool = True) -> Dict[str, Any]:
        """Scrape web page content with SSRF protection"""
        valid, error_msg = self.validate(url)
        if not valid:
            return {
                'success': False,
                'error': error_msg,
                'url': url
            }

        client = await self._get_client()
        
        try:
            response = await client.get(url)
            response.raise_for_status()

            content = response.text

            if extract_text:
                soup = BeautifulSoup(content, 'lxml')

                for script in soup(['script', 'style', 'meta', 'link', 'noscript']):
                    script.decompose()

                text = soup.get_text(separator='\n', strip=True)

                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)

                return {
                    'success': True,
                    'url': url,
                    'title': soup.title.string if soup.title else 'No title',
                    'text': text[:10000],
                    'content_length': len(text)
                }
            else:
                return {
                    'success': True,
                    'url': url,
                    'html': content[:20000],
                    'content_length': len(content)
                }

        except httpx.HTTPStatusError as e:
            return {
                'success': False,
                'error': f'HTTP error {e.response.status_code}: {str(e)}',
                'url': url
            }
        except httpx.RequestError as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}',
                'url': url
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'url': url
            }


class FilesystemSkill(SkillBase):
    """Safe filesystem operations with directory restrictions and lazy loading"""

    def __init__(self, config: Any):
        super().__init__(config, 'filesystem')
        self.allowed_dirs = config.get('skills.filesystem.allowed_directories', ['~', './'])
        self.max_file_size = config.get('skills.filesystem.max_file_size', 1024 * 1024)  # 1MB default
        self.operation_timeout = config.get('skills.filesystem.operation_timeout', 30)  # 30s timeout
        self.logger = None
        try:
            from .logging_config import get_logger
            self.logger = get_logger('skills.filesystem')
        except ImportError:
            pass

    def _resolve_path(self, path: str) -> Path:
        return sanitize_path(path, allowed_dirs=self.allowed_dirs)

    def validate(self, path: str, operation: str = 'read') -> Tuple[bool, Optional[str]]:
        try:
            resolved = self._resolve_path(path)

            if not is_safe_path(resolved, self.allowed_dirs):
                return False, f"Path '{path}' is outside allowed directories"

            if operation in ['read', 'delete'] and not resolved.exists():
                return False, f"Path does not exist: {path}"

            if operation == 'write' and resolved.exists() and resolved.is_dir():
                return False, f"Cannot write to existing directory: {path}"

            return True, None
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    async def execute(self, operation: str, path: str, content: Optional[str] = None,
                     max_lines: Optional[int] = None) -> Dict[str, Any]:
        """Execute filesystem operation with timeout protection and logging"""
        if self.logger:
            self.logger.info(f"Filesystem operation: {operation} on {path}")
        
        valid, error_msg = self.validate(path, operation)
        if not valid:
            if self.logger:
                self.logger.warning(f"Validation failed: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'operation': operation
            }

        resolved_path = self._resolve_path(path)

        try:
            # Wrap operation with timeout
            if operation == 'read':
                result = await asyncio.wait_for(
                    self._execute_read(resolved_path, max_lines),
                    timeout=self.operation_timeout
                )
            elif operation == 'list':
                result = await asyncio.wait_for(
                    self._execute_list(resolved_path),
                    timeout=self.operation_timeout
                )
            elif operation == 'explore':
                result = await asyncio.wait_for(
                    self._execute_explore(resolved_path),
                    timeout=min(self.operation_timeout * 3, 120)  # Longer timeout for explore
                )
            elif operation == 'write':
                result = await asyncio.wait_for(
                    self._execute_write(resolved_path, content),
                    timeout=self.operation_timeout
                )
            elif operation == 'delete':
                result = await asyncio.wait_for(
                    self._execute_delete(resolved_path),
                    timeout=self.operation_timeout
                )
            else:
                return {
                    'success': False,
                    'error': f'Unknown operation: {operation}',
                    'operation': operation
                }

            if self.logger:
                self.logger.info(f"Filesystem operation completed: {operation} - success: {result.get('success', True)}")
            
            return result

        except asyncio.TimeoutError:
            error_msg = f"Operation timeout after {self.operation_timeout}s"
            if self.logger:
                self.logger.error(f"Filesystem operation timed out: {operation} on {path}")
            return {
                'success': False,
                'error': error_msg,
                'operation': operation,
                'path': str(resolved_path)
            }
        except Exception as e:
            error_msg = f"Operation failed: {str(e)}"
            if self.logger:
                self.logger.error(f"Filesystem operation error: {operation} on {path} - {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'operation': operation
            }

    async def _execute_read(self, resolved_path: Path, max_lines: Optional[int] = None) -> Dict[str, Any]:
        """Execute read operation with non-blocking I/O."""
        if not resolved_path.is_file():
            return {'success': False, 'error': 'Path is not a file'}

        file_size = resolved_path.stat().st_size
        if file_size > self.max_file_size:
            return {
                'success': False,
                'error': f'File too large ({file_size} bytes). Max: {self.max_file_size} bytes'
            }

        # Use asyncio.to_thread for non-blocking file I/O
        def read_file():
            with open(resolved_path, 'r', encoding='utf-8') as f:
                if max_lines:
                    # Lazy loading - read only specified number of lines
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line)
                    return ''.join(lines), True
                else:
                    return f.read(), False
        
        try:
            data, truncated = await asyncio.to_thread(read_file)
        except (IOError, OSError, UnicodeDecodeError) as e:
            return {
                'success': False,
                'error': f'Failed to read file: {str(e)}'
            }

        return {
            'success': True,
            'operation': 'read',
            'path': str(resolved_path),
            'content': data,
            'size': len(data),
            'file_size': file_size,
            'truncated': truncated,
            'lines_read': max_lines if max_lines else len(data.splitlines())
        }

    async def _execute_list(self, resolved_path: Path) -> Dict[str, Any]:
        """Execute list operation"""
        if not resolved_path.is_dir():
            return {'success': False, 'error': 'Path is not a directory'}

        items = []
        for item in sorted(resolved_path.iterdir(), key=lambda x: x.name.lower()):
            if item.name.startswith('.'):
                continue
            items.append({
                'name': item.name,
                'type': 'directory' if item.is_dir() else 'file',
                'size': item.stat().st_size if item.is_file() else None
            })

        return {
            'success': True,
            'operation': 'list',
            'path': str(resolved_path),
            'items': items,
            'count': len(items)
        }

    async def _execute_explore(self, resolved_path: Path) -> Dict[str, Any]:
        """Execute explore operation with depth limiting"""
        if not resolved_path.is_dir():
            return {'success': False, 'error': 'Path is not a directory'}

        max_depth = 2
        result = {'success': True, 'operation': 'explore', 'path': str(resolved_path), 'structure': []}

        def scan_dir(dir_path: Path, depth: int = 0):
            if depth > max_depth:
                return
            try:
                for item in sorted(dir_path.iterdir(), key=lambda x: x.name.lower()):
                    if item.name.startswith('.'):
                        continue
                    if item.is_file():
                        result['structure'].append({
                            'path': str(item),
                            'type': 'file',
                            'size': item.stat().st_size,
                            'extension': item.suffix
                        })
                    elif item.is_dir():
                        result['structure'].append({
                            'path': str(item),
                            'type': 'directory'
                        })
                        scan_dir(item, depth + 1)
            except (PermissionError, OSError) as e:
                # Log permission errors but continue
                if self.logger:
                    self.logger.debug(f"Permission denied scanning: {dir_path} - {e}")
                pass

        scan_dir(resolved_path)
        result['file_count'] = len([x for x in result['structure'] if x['type'] == 'file'])
        result['dir_count'] = len([x for x in result['structure'] if x['type'] == 'directory'])
        return result

    async def _execute_write(self, resolved_path: Path, content: Optional[str] = None) -> Dict[str, Any]:
        """Execute write operation with non-blocking I/O and syntax validation."""
        if resolved_path.exists() and not resolved_path.is_file():
            return {'success': False, 'error': 'Path exists and is not a file'}

        # SYNTAX VALIDATION: Validate Python syntax before writing
        if resolved_path.suffix == '.py' and content:
            import ast
            try:
                ast.parse(content)
            except SyntaxError as e:
                return {
                    'success': False,
                    'error': f'Python syntax error: {e.msg}',
                    'details': f'Line {e.lineno}, column {e.offset if e.offset else 0}',
                    'suggestion': 'Please review the code and fix syntax errors before writing. The LLM may have generated incomplete or malformed Python code.'
                }

        # Use asyncio.to_thread for non-blocking file I/O
        def write_file():
            # Read original content for diff
            original_content = ""
            if resolved_path.exists():
                with open(resolved_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()

            # Generate diff before writing
            diff_output = ""
            if original_content and original_content != content:
                import difflib
                diff = difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=f'a/{resolved_path.name}',
                    tofile=f'b/{resolved_path.name}'
                )
                diff_output = ''.join(diff)

            resolved_path.parent.mkdir(parents=True, exist_ok=True)

            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(content or '')

            return diff_output, original_content != content
        
        try:
            diff_output, modified = await asyncio.to_thread(write_file)
        except (IOError, OSError, UnicodeDecodeError) as e:
            return {
                'success': False,
                'error': f'Failed to write file: {str(e)}'
            }

        return {
            'success': True,
            'operation': 'write',
            'path': str(resolved_path),
            'size': len(content or ''),
            'diff': diff_output,  # Include diff for display
            'modified': modified
        }

    async def _execute_delete(self, resolved_path: Path) -> Dict[str, Any]:
        """Execute delete operation"""
        if not resolved_path.exists():
            return {'success': False, 'error': 'File does not exist'}

        if resolved_path.is_dir():
            return {'success': False, 'error': 'Cannot delete directories'}

        resolved_path.unlink()
        return {
            'success': True,
            'operation': 'delete',
            'path': str(resolved_path)
        }


class SearchSkill(SkillBase):
    """Codebase search capabilities - NEW FEATURE"""

    def __init__(self, config: Any):
        super().__init__(config, 'search')
        self.allowed_dirs = config.get('skills.filesystem.allowed_directories', ['~', './'])

    def _resolve_path(self, path: str) -> Path:
        return sanitize_path(path, allowed_dirs=self.allowed_dirs)

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute search operation"""
        try:
            if action == 'grep':
                return await self._grep_content(
                    kwargs.get('pattern', ''),
                    kwargs.get('path', '.'),
                    kwargs.get('include', '*.py')
                )
            elif action == 'find_files':
                return await self._find_files(
                    kwargs.get('pattern', '*'),
                    kwargs.get('path', '.')
                )
            elif action == 'symbol':
                return await self._find_symbol(
                    kwargs.get('name', ''),
                    kwargs.get('path', '.'),
                    kwargs.get('language', 'python')
                )
            else:
                return {'success': False, 'error': f'Unknown search action: {action}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _grep_content(self, pattern: str, path: str, include: str) -> Dict[str, Any]:
        """Search for pattern in files with timeout protection."""
        import fnmatch

        resolved_path = self._resolve_path(path)
        if not resolved_path.is_dir():
            resolved_path = resolved_path.parent

        results = []
        total_matches = 0
        operation_timeout = 30  # seconds
        max_matches = 100
        start_time = asyncio.get_event_loop().time()

        # Run blocking os.walk in thread pool with timeout
        def walk_and_search():
            """Blocking file system walk and search."""
            nonlocal total_matches
            local_results = []
            import time
            thread_start_time = time.time()
            
            for root, dirs, files in os.walk(resolved_path):
                # Check timeout
                if time.time() - thread_start_time > operation_timeout:
                    break
                
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if total_matches >= max_matches:
                        break
                    
                    if not fnmatch.fnmatch(file, include) or file.startswith('.'):
                        continue

                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_num, line in enumerate(f, 1):
                                if re.search(pattern, line, re.IGNORECASE):
                                    local_results.append({
                                        'file': str(file_path),
                                        'line': line_num,
                                        'content': line.strip()[:200]
                                    })
                                    total_matches += 1
                                    if total_matches >= max_matches:
                                        break
                    except (PermissionError, OSError, UnicodeDecodeError):
                        continue
                
                if total_matches >= max_matches:
                    break
            
            return local_results

        try:
            results = await asyncio.wait_for(
                asyncio.to_thread(walk_and_search),
                timeout=operation_timeout
            )
            
            return {
                'success': True,
                'action': 'grep',
                'pattern': pattern,
                'include': include,
                'matches': results[:100],
                'total_matches': len(results),
                'truncated': len(results) > 100
            }
        except asyncio.TimeoutError:
            return {
                'success': True,
                'action': 'grep',
                'pattern': pattern,
                'include': include,
                'matches': results,
                'total_matches': len(results),
                'truncated': True,
                'warning': f'Search timed out after {operation_timeout}s'
            }

    async def _find_files(self, pattern: str, path: str) -> Dict[str, Any]:
        """Find files matching pattern with timeout protection."""
        import fnmatch

        resolved_path = self._resolve_path(path)
        if not resolved_path.is_dir():
            resolved_path = resolved_path.parent

        results = []
        operation_timeout = 30  # seconds
        max_files = 100
        start_time = asyncio.get_event_loop().time()

        # Run blocking os.walk in thread pool with timeout
        def walk_and_find():
            """Blocking file system walk and find."""
            local_results = []
            import time
            thread_start_time = time.time()
            
            for root, dirs, files in os.walk(resolved_path):
                # Check timeout
                if time.time() - thread_start_time > operation_timeout:
                    break
                
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if len(local_results) >= max_files:
                        break
                    
                    if fnmatch.fnmatch(file, pattern) and not file.startswith('.'):
                        file_path = Path(root) / file
                        try:
                            local_results.append({
                                'name': file,
                                'path': str(file_path),
                                'size': file_path.stat().st_size,
                                'extension': file_path.suffix
                            })
                        except (PermissionError, OSError):
                            continue
                
                if len(local_results) >= max_files:
                    break
            
            return local_results

        try:
            results = await asyncio.wait_for(
                asyncio.to_thread(walk_and_find),
                timeout=operation_timeout
            )
            
            return {
                'success': True,
                'action': 'find_files',
                'pattern': pattern,
                'files': results[:100],
                'total_found': len(results),
                'truncated': len(results) > 100
            }
        except asyncio.TimeoutError:
            return {
                'success': True,
                'action': 'find_files',
                'pattern': pattern,
                'files': results,
                'total_found': len(results),
                'truncated': True,
                'warning': f'Search timed out after {operation_timeout}s'
            }

    async def _find_symbol(self, name: str, path: str, language: str) -> Dict[str, Any]:
        """Find symbol definitions in code"""
        # Simple implementation - search for function/class definitions
        if language == 'python':
            patterns = [
                rf'def\s+{re.escape(name)}\s*\(',
                rf'class\s+{re.escape(name)}\s*[:(]',
            ]
            include = '*.py'
        elif language in ['javascript', 'typescript']:
            patterns = [
                rf'(?:function|const|let|var)\s+{re.escape(name)}\s*[=(]',
                rf'class\s+{re.escape(name)}\s+',
            ]
            include = '*.{js,ts,jsx,tsx}'
        else:
            return {'success': False, 'error': f'Unsupported language: {language}'}

        results = []
        for pattern in patterns:
            grep_result = await self._grep_content(pattern, path, include)
            if grep_result['success']:
                results.extend(grep_result['matches'])

        return {
            'success': True,
            'action': 'symbol',
            'name': name,
            'language': language,
            'occurrences': results[:50]
        }


# Import os for SearchSkill
import os


class CodeToolsSkill(SkillBase):
    """Code linting and formatting skill using CLI tools.

    Provides unified interface to industry-standard tools:
    - Ruff: Python linting and formatting
    - Prettier: JavaScript/TypeScript/JSON/YAML/Markdown/CSS formatting
    - gofmt: Go formatting
    - rustfmt: Rust formatting
    - shfmt: Shell formatting
    - sqlfluff: SQL linting

    Tools are optional - graceful degradation if not installed.
    """

    def __init__(self, config: Any):
        super().__init__(config, 'code_tools')
        self.tools = CodeTools() if CODE_TOOLS_AVAILABLE else None
        self.enabled = CODE_TOOLS_AVAILABLE

    def validate(self, **kwargs) -> Tuple[bool, Optional[str]]:
        """Validate parameters."""
        if not CODE_TOOLS_AVAILABLE:
            return False, "Code tools module not available"

        action = kwargs.get('action')
        valid_actions = ['lint', 'format', 'fix', 'check', 'detect']
        if action not in valid_actions:
            return False, f"Invalid action: {action}. Valid: {', '.join(valid_actions)}"

        return True, None

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Execute code tool action.

        Actions:
        - lint: Check code for issues
        - format: Format code
        - fix: Auto-fix issues (if supported)
        - check: Check tool availability
        - detect: Detect language from file
        """
        if not self.tools:
            return {
                'success': False,
                'error': 'Code tools not available. Ensure code_tools module is installed.'
            }

        file_path = kwargs.get('file_path')
        content = kwargs.get('content')
        language = kwargs.get('language')
        check_only = kwargs.get('check_only', False)

        try:
            if action == 'check':
                return {
                    'success': True,
                    'action': 'check',
                    'tools': self.tools.get_all_tools_status()
                }

            if action == 'detect':
                if not file_path:
                    return {'success': False, 'error': 'file_path required for detection'}
                lang = self.tools.detect_language(file_path)
                return {
                    'success': True,
                    'action': 'detect',
                    'language': lang,
                    'file_path': file_path
                }

            if action == 'lint':
                result = self.tools.lint_file(file_path, content, language)
                return {
                    'success': result.success,
                    'action': 'lint',
                    'file_path': file_path,
                    'language': language,
                    'output': result.output,
                    'errors': result.errors,
                    'diagnostics': result.diagnostics,
                    'duration_ms': result.duration_ms
                }

            if action == 'format':
                result = self.tools.format_file(file_path, content, check_only, language)
                return {
                    'success': result.success,
                    'action': 'format',
                    'file_path': file_path,
                    'language': language,
                    'output': result.output,
                    'errors': result.errors,
                    'files_modified': result.files_modified,
                    'duration_ms': result.duration_ms
                }

            if action == 'fix':
                result = self.tools.fix_file(file_path, content, language)
                return {
                    'success': result.success,
                    'action': 'fix',
                    'file_path': file_path,
                    'language': language,
                    'output': result.output,
                    'errors': result.errors,
                    'files_modified': result.files_modified,
                    'duration_ms': result.duration_ms
                }

            return {
                'success': False,
                'error': f'Unknown action: {action}'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Code tools error: {str(e)}'
            }


class SubAgentsSkill(SkillBase):
    """Delegate tasks to subagents for parallel execution"""

    def __init__(self, config: Any):
        super().__init__(config, 'subagents')
        self.orchestrator = None
        if SUBAGENTS_AVAILABLE:
            self.orchestrator = create_orchestrator(max_concurrent=3)

    async def execute(self, type: str, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute subagent delegation.

        Args:
            type: Subagent type (code, test, docs, research, security)
            task: Task description
            context: Optional context dictionary

        Returns:
            Execution result with output and stats
        """
        if not SUBAGENTS_AVAILABLE or not self.orchestrator:
            return {
                'success': False,
                'error': 'SubAgents not available'
            }

        try:
            # Map string type to SubAgentType enum
            type_map = {
                'code': SubAgentType.CODE,
                'test': SubAgentType.TEST,
                'docs': SubAgentType.DOCS,
                'research': SubAgentType.RESEARCH,
                'security': SubAgentType.SECURITY,
            }

            agent_type = type_map.get(type.lower(), SubAgentType.GENERIC)

            # Create task
            subagent_task = SubAgentTask.create(
                type=agent_type,
                description=task,
                context=context or {},
                token_budget=10000,
                timeout=300
            )

            # Execute task with error logging
            from .logging_config import get_logger
            logger = get_logger('subagents_skill')
            logger.info(f'Executing subagent task: type={type}, description={task[:100]}')

            try:
                results = await self.orchestrator.execute_parallel([subagent_task])
                combined = self.orchestrator.get_combined_output()
                stats = self.orchestrator.get_stats()

                logger.info(f'Subagent task completed: tasks={stats.get("tasks_completed", 0)}, failed={stats.get("tasks_failed", 0)}')

                return {
                    'success': True,
                    'type': type,
                    'task': task,
                    'output': combined,
                    'stats': stats,
                    'results': {k: v.to_dict() for k, v in results.items()}
                }
            except asyncio.CancelledError:
                logger.error('Subagent task was cancelled')
                raise
            except Exception as exec_error:
                logger.error(f'Subagent execution failed: {type(exec_error).__name__}: {str(exec_error)}')
                import traceback
                logger.debug(f'Traceback: {traceback.format_exc()}')
                raise

        except Exception as e:
            error_msg = f'SubAgents error: {str(e)}'
            # Log the full error with traceback
            from .logging_config import get_logger
            logger = get_logger('subagents_skill')
            logger.error(error_msg)
            import traceback
            logger.debug(f'Traceback: {traceback.format_exc()}')

            return {
                'success': False,
                'error': error_msg,
                'error_type': type(e).__name__
            }


class SkillManager:
    """Manage and orchestrate all agent skills with parallel execution support.
    
    Integrates output management for intelligent routing of large outputs.
    """

    def __init__(self, config: Config):
        self.config = config
        self.skills: Dict[str, SkillBase] = {}
        # Limit concurrent tool executions to prevent resource exhaustion
        self.max_concurrent_tools = config.get('performance.max_concurrent_tools', 5)
        self._tool_semaphore = asyncio.Semaphore(self.max_concurrent_tools)
        
        # Initialize output management if enabled
        self.output_manager: Optional[OutputManager] = None
        self.temp_manager: Optional[TempManager] = None
        if OUTPUT_MANAGEMENT_AVAILABLE and config.get('output_management.enabled', True):
            self._init_output_management(config)
        
        self._initialize_skills()
    
    def _init_output_management(self, config: Config):
        """Initialize output management system."""
        try:
            # Create temp manager
            self.temp_manager = get_temp_manager()
            
            # Create output manager with config settings
            self.output_manager = OutputManager(
                temp_manager=self.temp_manager,
                inline_max_bytes=config.get('output_management.inline_max_bytes', 10 * 1024),
                summary_max_bytes=config.get('output_management.summary_max_bytes', 1024 * 1024),
                max_inline_lines=config.get('output_management.max_inline_lines', 50),
                context_lines=config.get('output_management.context_lines', 50),
                enable_summarization=config.get('output_management.enable_summarization', True)
            )
        except Exception as e:
            print(f"Warning: Failed to initialize output management: {e}")
            self.output_manager = None
            self.temp_manager = None

    def _initialize_skills(self):
        """Initialize all configured skills"""
        if self.config.get('skills.terminal_executor.enabled', True):
            self.skills['terminal'] = TerminalExecutorSkill(self.config)

        if self.config.get('skills.web_scraper.enabled', True):
            self.skills['web'] = WebScraperSkill(self.config)

        if self.config.get('skills.filesystem.enabled', True):
            self.skills['fs'] = FilesystemSkill(self.config)

        # Search skill
        self.skills['search'] = SearchSkill(self.config)

        # Code tools skill (linting/formatting)
        if CODE_TOOLS_AVAILABLE:
            self.skills['code_tools'] = CodeToolsSkill(self.config)

        # Git skill (version control)
        if GIT_SKILL_AVAILABLE and self.config.get('skills.git.enabled', True):
            self.skills['git'] = GitSkill(self.config)

        # SubAgents skill (parallel task delegation)
        if SUBAGENTS_AVAILABLE:
            self.skills['subagents'] = SubAgentsSkill(self.config)

        # Memory skill (persistent context storage)
        if MEMORY_SKILL_AVAILABLE:
            self.skills['memory'] = MemorySkill(self.config)

    async def execute(self, skill_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a skill by name and process output through output manager.
        
        Args:
            skill_name: Name of the skill to execute
            **kwargs: Skill parameters
            
        Returns:
            Skill result dictionary (possibly with output manager formatting)
        """
        if skill_name not in self.skills:
            return {
                'success': False,
                'error': f'Skill not found or disabled: {skill_name}'
            }

        skill = self.skills[skill_name]
        result = await skill.execute(**kwargs)
        
        # Process output through output manager if available
        if self.output_manager and result.get('success', False):
            # Extract output content based on skill type
            output_content = self._extract_output_content(result, skill_name)
            
            if output_content:
                try:
                    output_result = await self.output_manager.process_output(
                        tool_name=skill_name,
                        output=output_content,
                        success=result.get('success', False),
                        metadata={'original_result_keys': list(result.keys())}
                    )
                    
                    # Merge output manager result with original result
                    result['output_manager'] = output_result.to_dict()
                    result['display_text'] = output_result.display_text
                    result['routing_decision'] = output_result.routing_decision
                    
                    # Add summary if available
                    if output_result.summary:
                        result['summary'] = output_result.summary
                    
                    # Add file path if stored
                    if output_result.file_path:
                        result['file_path'] = str(output_result.file_path)
                except Exception as e:
                    # Log error but don't fail the skill execution
                    print(f"Warning: Output manager failed: {e}")
        
        return result
    
    def _extract_output_content(self, result: Dict[str, Any], skill_name: str) -> Optional[str]:
        """Extract output content from skill result for processing.
        
        Args:
            result: Skill result dictionary
            skill_name: Name of the skill
            
        Returns:
            Output content string or None
        """
        # Terminal output
        if 'stdout' in result and result['stdout']:
            return result['stdout']
        
        # Web scraper output
        if 'text' in result and result['text']:
            return result['text']
        
        # Filesystem read output
        if 'content' in result and result['content']:
            return result['content']
        
        # Search output - convert matches to text
        if 'matches' in result and result['matches']:
            lines = []
            for match in result['matches'][:100]:
                file_path = match.get('file', 'unknown')
                line_num = match.get('line', 0)
                content = match.get('content', '')
                lines.append(f"{file_path}:{line_num}: {content}")
            return '\n'.join(lines)
        
        # Diff output
        if 'diff' in result and result['diff']:
            return result['diff']
        
        return None

    async def execute_parallel(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multiple tool calls in parallel with concurrency limiting - NEW FEATURE"""
        async def execute_one(call: Dict) -> Dict[str, Any]:
            tool_name = call.get('tool')
            params = call.get('params', {})

            if tool_name not in self.skills:
                return {
                    'success': False,
                    'error': f'Skill not found: {tool_name}',
                    'tool': tool_name
                }

            # Acquire semaphore to limit concurrent executions
            async with self._tool_semaphore:
                try:
                    result = await self.skills[tool_name].execute(**params)
                    result['tool'] = tool_name
                    return result
                except Exception as e:
                    return {
                        'success': False,
                        'error': str(e),
                        'tool': tool_name
                    }

        return await asyncio.gather(*[execute_one(call) for call in tool_calls])

    async def close(self):
        """Cleanup resources - close web scraper HTTP client"""
        if 'web' in self.skills:
            await self.skills['web'].close()

    def list_skills(self) -> List[str]:
        return list(self.skills.keys())

    def get_skill_info(self, skill_name: str) -> Dict[str, Any]:
        if skill_name not in self.skills:
            return {'name': skill_name, 'enabled': False}

        skill = self.skills[skill_name]
        return {
            'name': skill.name,
            'enabled': skill.enabled,
            'type': skill.__class__.__name__
        }
