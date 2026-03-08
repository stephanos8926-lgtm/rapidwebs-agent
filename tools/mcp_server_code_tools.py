"""rw-agent Code MCP Server.

This module provides an MCP (Model Context Protocol) server that exposes
code linting, formatting, and analysis tools to Qwen Code CLI.

Features:
- Lint code files for issues
- Format code files
- Analyze code structure (symbols, imports, callers)
- Find related files
- Check tool availability
- Get supported languages

Usage:
    rw-agent-code                    # Production mode
    rw-agent-code --debug           # Debug logging
    rw-agent-code --test            # Run self-tests
    python -m tools.mcp_server_code_tools  # Alternative
"""

import sys
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.code_analysis_tools import CodeTools

# NEW: Import code analysis utilities
from agent.context_manager import get_file_symbols, get_symbols_summary, suggest_related_files
from agent.utilities import find_callers, find_symbol_definition, get_import_graph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('code-tools-mcp-server')

# Global code tools instance
code_tools: Optional[CodeTools] = None


def get_code_tools() -> CodeTools:
    """Get or create code tools instance."""
    global code_tools
    if code_tools is None:
        code_tools = CodeTools()
    return code_tools


def lint_file(file_path: str, content: Optional[str] = None) -> Dict[str, Any]:
    """Lint a code file for issues.

    Args:
        file_path: Path to the file
        content: Optional file content

    Returns:
        Dictionary with linting results
    """
    tools = get_code_tools()
    result = tools.lint_file(file_path, content)
    return result.to_dict()


def format_file(file_path: str, content: Optional[str] = None,
                check_only: bool = False) -> Dict[str, Any]:
    """Format a code file.

    Args:
        file_path: Path to the file
        content: Optional file content
        check_only: If True, only check formatting

    Returns:
        Dictionary with formatting results
    """
    tools = get_code_tools()
    result = tools.format_file(file_path, content, check_only)
    return result.to_dict()


def fix_file(file_path: str, content: Optional[str] = None) -> Dict[str, Any]:
    """Auto-fix issues in a code file.

    Args:
        file_path: Path to the file
        content: Optional file content

    Returns:
        Dictionary with fix results
    """
    tools = get_code_tools()
    result = tools.fix_file(file_path, content)
    return result.to_dict()


def check_tools() -> Dict[str, Any]:
    """Check which code tools are installed.

    Returns:
        Dictionary with tool status
    """
    tools = get_code_tools()
    return {
        'success': True,
        'tools': tools.get_all_tools_status()
    }


def get_supported_languages() -> Dict[str, Any]:
    """Get list of supported programming languages.

    Returns:
        Dictionary with language support info
    """
    return {
        'success': True,
        'languages': {
            'python': {
                'extensions': ['.py', '.pyi', '.pyw'],
                'tools': {'lint': 'ruff', 'format': 'ruff', 'fix': 'ruff'},
                'tier': 1
            },
            'javascript': {
                'extensions': ['.js', '.mjs', '.cjs', '.jsx'],
                'tools': {'format': 'prettier'},
                'tier': 1
            },
            'typescript': {
                'extensions': ['.ts', '.tsx', '.mts', '.cts'],
                'tools': {'format': 'prettier'},
                'tier': 1
            },
            'json': {
                'extensions': ['.json', '.jsonc', '.json5'],
                'tools': {'format': 'prettier'},
                'tier': 1
            },
            'yaml': {
                'extensions': ['.yml', '.yaml'],
                'tools': {'format': 'prettier'},
                'tier': 1
            },
            'markdown': {
                'extensions': ['.md', '.mdx', '.markdown'],
                'tools': {'format': 'prettier'},
                'tier': 1
            },
            'css': {
                'extensions': ['.css', '.scss', '.sass', '.less'],
                'tools': {'format': 'prettier'},
                'tier': 1
            },
            'html': {
                'extensions': ['.html', '.htm'],
                'tools': {'format': 'prettier'},
                'tier': 1
            },
            'go': {
                'extensions': ['.go'],
                'tools': {'format': 'gofmt'},
                'tier': 2
            },
            'rust': {
                'extensions': ['.rs'],
                'tools': {'format': 'rustfmt'},
                'tier': 2
            },
            'shell': {
                'extensions': ['.sh', '.bash', '.zsh', '.fish'],
                'tools': {'format': 'shfmt'},
                'tier': 2
            },
            'sql': {
                'extensions': ['.sql'],
                'tools': {'lint': 'sqlfluff'},
                'tier': 2
            }
        }
    }


def detect_language(file_path: str) -> Dict[str, Any]:
    """Detect programming language from file extension.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with detected language
    """
    tools = get_code_tools()
    language = tools.detect_language(file_path)
    return {
        'success': True,
        'file_path': file_path,
        'language': language
    }


# =============================================================================
# NEW: Code Analysis Tools (Phase 2)
# =============================================================================

def get_symbols(file_path: str, summary: bool = False) -> Dict[str, Any]:
    """Extract symbols from a Python file.

    Args:
        file_path: Path to the Python file
        summary: If True, return formatted summary instead of raw symbols

    Returns:
        Dictionary with symbols or summary
    """
    path = Path(file_path)
    if not path.exists():
        return {'success': False, 'error': f'File not found: {file_path}'}

    if summary:
        result = get_symbols_summary(path)
        return {'success': True, 'summary': result}
    else:
        symbols = get_file_symbols(path)
        return {'success': True, 'symbols': symbols}


def get_related_files_cli(file_path: str, max_suggestions: int = 5) -> Dict[str, Any]:
    """Find files related to a given file.

    Args:
        file_path: Path to the file
        max_suggestions: Maximum number of suggestions

    Returns:
        Dictionary with related files
    """
    path = Path(file_path)
    if not path.exists():
        return {'success': False, 'error': f'File not found: {file_path}'}

    workspace = Path.cwd()
    suggestions = suggest_related_files(path, workspace, max_suggestions)

    return {
        'success': True,
        'related_files': [str(f) for f in suggestions]
    }


def find_callers_cli(function_name: str, workspace: str = '.',
                     max_results: int = 20) -> Dict[str, Any]:
    """Find callers of a function.

    Args:
        function_name: Name of the function
        workspace: Workspace root directory
        max_results: Maximum number of results

    Returns:
        Dictionary with caller information
    """
    workspace_path = Path(workspace)
    callers = find_callers(function_name, workspace_path, max_results)

    if not callers:
        return {
            'success': True,
            'callers': [],
            'message': f'No callers found for {function_name}'
        }

    # Format callers
    formatted = []
    for file_path, line_num, content in callers:
        formatted.append({
            'file': file_path,
            'line': line_num,
            'content': content
        })

    return {'success': True, 'callers': formatted}


def find_definition_cli(symbol_name: str, language: str = 'python',
                        workspace: str = '.') -> Dict[str, Any]:
    """Find definition of a symbol.

    Args:
        symbol_name: Name of the symbol
        language: Programming language
        workspace: Workspace root directory

    Returns:
        Dictionary with definition information
    """
    workspace_path = Path(workspace)
    definition = find_symbol_definition(symbol_name, workspace_path, language)

    if not definition:
        return {
            'success': True,
            'definition': None,
            'message': f'Definition not found for {symbol_name}'
        }

    return {'success': True, 'definition': definition}


def get_imports_cli(file_path: str) -> Dict[str, Any]:
    """Get import graph for a Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        Dictionary with import information
    """
    path = Path(file_path)
    if not path.exists():
        return {'success': False, 'error': f'File not found: {file_path}'}

    workspace = Path.cwd()
    imports = get_import_graph(path, workspace)

    return {
        'success': True,
        'imports': imports
    }


# MCP Protocol Implementation

MCP_VERSION = "2024-11-05"
SERVER_NAME = "rw-agent-code"
SERVER_VERSION = "1.0.0"

# Tool definitions for MCP
TOOLS = [
    {
        "name": "lint_file",
        "description": "Lint a code file for issues (Python, SQL). Returns diagnostics with line numbers, error codes, and messages.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the code file"
                },
                "content": {
                    "type": "string",
                    "description": "Optional file content (if not reading from disk)"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "format_file",
        "description": "Format a code file (Python, JS, TS, JSON, YAML, Markdown, CSS, HTML, Go, Rust, Shell). Returns formatted content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the code file"
                },
                "content": {
                    "type": "string",
                    "description": "Optional file content (if not reading from disk)"
                },
                "check_only": {
                    "type": "boolean",
                    "description": "If true, only check formatting without modifying",
                    "default": False
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "fix_file",
        "description": "Auto-fix issues in a code file. Currently supports Python (ruff --fix).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the code file"
                },
                "content": {
                    "type": "string",
                    "description": "Optional file content"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "check_tools",
        "description": "Check which code tools are installed and available. Returns status of ruff, prettier, gofmt, rustfmt, shfmt, sqlfluff.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_supported_languages",
        "description": "Get list of supported programming languages with file extensions and required tools.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "detect_language",
        "description": "Detect programming language from file extension.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file"
                }
            },
            "required": ["file_path"]
        }
    },
    # NEW: Code Analysis Tools (Phase 2)
    {
        "name": "get_symbols",
        "description": "Extract symbols (functions, classes, imports) from a Python file using AST. Returns symbol list or formatted summary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the Python file"
                },
                "summary": {
                    "type": "boolean",
                    "description": "If true, return formatted summary instead of raw symbols",
                    "default": False
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "get_related_files",
        "description": "Find files related to a given file (test files, siblings, similar names). Excludes .venv, node_modules, etc.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file"
                },
                "max_suggestions": {
                    "type": "integer",
                    "description": "Maximum number of suggestions",
                    "default": 5
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "find_callers",
        "description": "Find where a function/method is called in the codebase using grep. Returns file, line, and content for each caller.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "function_name": {
                    "type": "string",
                    "description": "Name of the function to search for"
                },
                "workspace": {
                    "type": "string",
                    "description": "Workspace root directory",
                    "default": "."
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 20
                }
            },
            "required": ["function_name"]
        }
    },
    {
        "name": "find_definition",
        "description": "Find where a symbol is defined in the codebase using grep. Supports Python, JavaScript, TypeScript.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol_name": {
                    "type": "string",
                    "description": "Name of the symbol to find"
                },
                "language": {
                    "type": "string",
                    "description": "Programming language",
                    "default": "python"
                },
                "workspace": {
                    "type": "string",
                    "description": "Workspace root directory",
                    "default": "."
                }
            },
            "required": ["symbol_name"]
        }
    },
    {
        "name": "get_imports",
        "description": "Extract import dependencies from a Python file. Returns mapping of import names to source modules.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the Python file"
                }
            },
            "required": ["file_path"]
        }
    }
]


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP protocol request.

    Args:
        request: MCP request dictionary

    Returns:
        MCP response dictionary
    """
    method = request.get('method')
    params = request.get('params', {})
    request_id = request.get('id')

    try:
        if method == 'initialize':
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'protocolVersion': MCP_VERSION,
                    'serverInfo': {
                        'name': SERVER_NAME,
                        'version': SERVER_VERSION
                    },
                    'capabilities': {
                        'tools': {}
                    }
                }
            }

        elif method == 'tools/list':
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'tools': TOOLS
                }
            }

        elif method == 'tools/call':
            tool_name = params.get('name')
            tool_args = params.get('arguments', {})

            if tool_name == 'lint_file':
                result = lint_file(
                    tool_args.get('file_path', ''),
                    tool_args.get('content')
                )
            elif tool_name == 'format_file':
                result = format_file(
                    tool_args.get('file_path', ''),
                    tool_args.get('content'),
                    tool_args.get('check_only', False)
                )
            elif tool_name == 'fix_file':
                result = fix_file(
                    tool_args.get('file_path', ''),
                    tool_args.get('content')
                )
            elif tool_name == 'check_tools':
                result = check_tools()
            elif tool_name == 'get_supported_languages':
                result = get_supported_languages()
            elif tool_name == 'detect_language':
                result = detect_language(tool_args.get('file_path', ''))
            # NEW: Code Analysis Tools (Phase 2)
            elif tool_name == 'get_symbols':
                result = get_symbols(
                    tool_args.get('file_path', ''),
                    tool_args.get('summary', False)
                )
            elif tool_name == 'get_related_files':
                result = get_related_files_cli(
                    tool_args.get('file_path', ''),
                    tool_args.get('max_suggestions', 5)
                )
            elif tool_name == 'find_callers':
                result = find_callers_cli(
                    tool_args.get('function_name', ''),
                    tool_args.get('workspace', '.'),
                    tool_args.get('max_results', 20)
                )
            elif tool_name == 'find_definition':
                result = find_definition_cli(
                    tool_args.get('symbol_name', ''),
                    tool_args.get('language', 'python'),
                    tool_args.get('workspace', '.')
                )
            elif tool_name == 'get_imports':
                result = get_imports_cli(tool_args.get('file_path', ''))
            else:
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {
                        'code': -32601,
                        'message': f'Unknown tool: {tool_name}'
                    }
                }

            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'content': [
                        {
                            'type': 'text',
                            'text': json.dumps(result, indent=2)
                        }
                    ]
                }
            }

        else:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32601,
                    'message': f'Unknown method: {method}'
                }
            }

    except Exception as e:
        logger.error(f"Error handling request: {e}")
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': {
                'code': -32603,
                'message': f'Internal error: {str(e)}'
            }
        }


def main():
    """Main entry point for MCP server."""
    import argparse

    parser = argparse.ArgumentParser(
        description='rw-agent Code MCP Server'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.test:
        # Run test mode
        logger.info("Running code tools MCP server in test mode...")
        tools = get_code_tools()
        status = tools.get_all_tools_status()
        logger.info("Code tools status:")
        for tool_name, info in status.items():
            status_str = "✓" if info['installed'] else "✗"
            logger.info(f"  {status_str} {tool_name}: {info.get('version', 'not installed')}")
        logger.info("Test mode complete")
        return

    logger.info("rw-agent Code MCP Server starting...")

    # Initialize code tools
    tools = get_code_tools()
    logger.info("Code tools initialized")

    # Check tool availability
    status = tools.get_all_tools_status()
    for tool_name, info in status.items():
        status_str = "✓" if info['installed'] else "✗"
        logger.info(f"  {status_str} {tool_name}: {info.get('version', 'not installed')}")

    # Run stdio server loop
    logger.info("Waiting for requests on stdin...")

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                error_response = {
                    'jsonrpc': '2.0',
                    'error': {
                        'code': -32700,
                        'message': 'Parse error: Invalid JSON'
                    }
                }
                print(json.dumps(error_response), flush=True)

    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
