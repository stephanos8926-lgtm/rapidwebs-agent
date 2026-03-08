"""Utility functions for token counting, path safety, and prompt compression.

All functions in this module are internal utilities.
Public API is exposed through agent.__init__.py
"""
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import tiktoken


def get_token_count(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count tokens using tiktoken.
    
    Args:
        text: Text to count tokens for
        model: Model name for tokenization
        
    Returns:
        Approximate token count
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        return len(text) // 4


def compress_prompt(prompt: str, max_tokens: int = 2000) -> str:
    """Compress prompt to fit within token limit.
    
    Strategies (in order):
    1. Remove extra whitespace
    2. Condense system prompt
    3. Truncate older messages
    4. Truncate content
    
    Args:
        prompt: Original prompt text
        max_tokens: Maximum token limit
        
    Returns:
        Compressed prompt
    """
    current_tokens = get_token_count(prompt)

    if current_tokens <= max_tokens:
        return prompt

    # Strategy 1: Remove extra whitespace
    compressed = re.sub(r'\n\s*\n', '\n\n', prompt)
    compressed = re.sub(r' +', ' ', compressed)

    if get_token_count(compressed) <= max_tokens:
        return compressed

    # Strategy 2: Condense system prompt
    if '\n\nConversation History:\n' in compressed:
        parts = compressed.split('\n\nConversation History:\n')
        if len(parts) == 2:
            compressed = f"[System instructions condensed]\n\nConversation History:\n{parts[1]}"

    if get_token_count(compressed) <= max_tokens:
        return compressed

    # Strategy 3: Truncate older messages
    if '\n\nConversation History:\n' in compressed:
        parts = compressed.split('\n\nConversation History:\n')
        if len(parts) == 2:
            system_prompt = parts[0]
            history = parts[1]
            messages = re.split(r'(User: |Agent: )', history)

            while get_token_count(system_prompt + '\n\nConversation History:\n' + ''.join(messages)) > max_tokens:
                if len(messages) <= 4:
                    break
                messages = messages[2:]

            compressed = system_prompt + '\n\nConversation History:\n' + ''.join(messages)

    # Strategy 4: Truncate content
    if get_token_count(compressed) > max_tokens:
        words = compressed.split()
        compressed = ' '.join(words[:max(100, int(len(words) * max_tokens / get_token_count(compressed)))])

    return compressed


def sanitize_path(path: str, allowed_dirs: Optional[List[str]] = None) -> Path:
    """Sanitize and resolve path safely.
    
    Args:
        path: Path string to sanitize
        allowed_dirs: Optional list of allowed directories
        
    Returns:
        Resolved Path object
        
    Raises:
        ValueError: If path is outside allowed directories
    """
    path_obj = Path(path).expanduser().resolve()

    if allowed_dirs:
        allowed_paths = [Path(d).expanduser().resolve() for d in allowed_dirs]
        if not any(str(path_obj).startswith(str(allowed)) for allowed in allowed_paths):
            raise ValueError(f"Path outside allowed directories: {path}")

    return path_obj


def is_safe_path(path: Path, allowed_dirs: List[str]) -> bool:
    """Check if path is within allowed directories.

    Args:
        path: Path object to check
        allowed_dirs: List of allowed directory paths

    Returns:
        True if path is safe, False otherwise
    """
    try:
        resolved = path.resolve()
        allowed_paths = [Path(d).expanduser().resolve() for d in allowed_dirs]
        return any(str(resolved).startswith(str(allowed)) for allowed in allowed_paths)
    except Exception:
        return False


# =============================================================================
# Code Analysis Utilities (Lightweight LSP Alternatives)
# =============================================================================

def find_callers(symbol_name: str, workspace: Path, 
                 max_results: int = 20) -> List[Tuple[str, int, str]]:
    """Find where a function/method is called using grep.
    
    Lightweight alternative to LSP "find references". Works for any language.
    
    Args:
        symbol_name: Function/method name to search for
        workspace: Workspace root directory
        max_results: Maximum number of results to return
        
    Returns:
        List of (file_path, line_number, line_content) tuples

    Example:
        >>> from agent.utilities import find_callers
        >>> callers = find_callers("process_data", Path("/workspace"))
        >>> print(callers)
        [('main.py', 42, '    result = process_data(items)'), ...]
    """
    callers = []
    
    try:
        # Search for function calls: symbol_name(
        # Using grep for speed and simplicity
        result = subprocess.run(
            ['grep', '-rn', '--include=*.py', f'{symbol_name}(', str(workspace)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            for line in result.stdout.splitlines()[:max_results]:
                # Parse grep output: file:line:content
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    file_path = parts[0]
                    try:
                        line_num = int(parts[1])
                    except ValueError:
                        line_num = 0
                    content = parts[2].strip()
                    callers.append((file_path, line_num, content))
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # grep not available or timed out - return empty list
        pass
    
    return callers


def find_symbol_definition(symbol_name: str, workspace: Path,
                           language: str = 'python') -> Optional[Dict[str, Any]]:
    """Find where a symbol is defined using grep.
    
    Lightweight alternative to LSP "go to definition".
    
    Args:
        symbol_name: Symbol name to search for
        workspace: Workspace root directory
        language: Programming language ('python', 'javascript', etc.)

    Returns:
        Dictionary with file, line, content or None if not found

    Example:
        >>> from agent.utilities import find_symbol_definition
        >>> defn = find_symbol_definition("Agent", Path("/workspace"))
        >>> print(defn)
        {'file': 'agent/agent.py', 'line': 50, 'content': 'class Agent:'}
    """
    # Patterns for different languages
    patterns = {
        'python': [
            f'def {symbol_name}\\s*\\(',  # Function definition
            f'class {symbol_name}\\s*[:\\(]',  # Class definition
        ],
        'javascript': [
            f'function\\s+{symbol_name}\\s*\\(',
            f'const\\s+{symbol_name}\\s*=\\s*(?:async\\s+)?\\(',
            f'{symbol_name}\\s*[:=]\\s*(?:async\\s+)?function',
        ],
        'typescript': [
            f'function\\s+{symbol_name}\\s*\\(',
            f'(?:const|let|var)\\s+{symbol_name}\\s*[:=]',
            f'interface\\s+{symbol_name}\\s*',
            f'type\\s+{symbol_name}\\s*=',
        ],
    }
    
    search_patterns = patterns.get(language, patterns['python'])
    extensions = {
        'python': '*.py',
        'javascript': '*.{js,jsx}',
        'typescript': '*.{ts,tsx}',
    }.get(language, '*.py')
    
    for pattern in search_patterns:
        try:
            result = subprocess.run(
                ['grep', '-rn', '--include', extensions, pattern, str(workspace)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Return first match
                line = result.stdout.splitlines()[0]
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    return {
                        'file': parts[0],
                        'line': int(parts[1]) if parts[1].isdigit() else 0,
                        'content': parts[2].strip()
                    }
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError, ValueError):
            continue
    
    return None


def get_import_graph(file_path: Path, workspace: Path) -> Dict[str, List[str]]:
    """Extract import relationships from a Python file.
    
    Returns a simple dependency graph showing what the file imports.
    
    Args:
        file_path: Path to Python file
        workspace: Workspace root directory

    Returns:
        Dictionary mapping import names to source modules

    Example:
        >>> from agent.utilities import get_import_graph
        >>> imports = get_import_graph(Path("agent/agent.py"), Path("/workspace"))
        >>> print(imports)
        {'Config': 'agent.config', 'ModelManager': 'agent.llm_models'}
    """
    imports = {}
    
    if not file_path.exists() or file_path.suffix != '.py':
        return imports
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # from X import Y
                if line.startswith('from ') and ' import ' in line:
                    parts = line.split(' import ')
                    if len(parts) == 2:
                        module = parts[0].replace('from ', '').strip()
                        names = parts[1].strip()
                        # Handle multiple imports
                        for name in names.split(','):
                            name = name.strip().split(' as ')[0].strip()
                            if name and name != '*':
                                imports[name] = module
                
                # import X
                elif line.startswith('import '):
                    names = line.replace('import ', '').strip()
                    for name in names.split(','):
                        name = name.strip().split(' as ')[0].strip()
                        if name:
                            imports[name] = name
    except (OSError, IOError, UnicodeDecodeError):
        pass
    
    return imports
