"""rw-agent Cache MCP Server.

This module provides an MCP (Model Context Protocol) server that exposes
the rw-agent Tier 4 caching system to Qwen Code CLI.

Features:
- Hash-based change detection
- Content-addressable storage
- Response caching with file invalidation
- Token budget enforcement
- Lazy directory loading

Usage:
    rw-agent-cache                    # Production mode
    rw-agent-cache --debug           # Debug logging
    rw-agent-cache --test            # Run self-tests
    python -m tools.mcp_server_caching  # Alternative
"""

import sys
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.caching import create_caching, CachingIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('caching-mcp-server')

# Global caching instance
caching: Optional[CachingIntegration] = None
workspace: Optional[Path] = None


def initialize_caching(daily_token_limit: int = 100000) -> Dict[str, Any]:
    """Initialize the caching system.
    
    Args:
        daily_token_limit: Daily token budget limit
        
    Returns:
        Initialization status dictionary
    """
    global caching, workspace
    
    workspace = Path.cwd()
    caching = create_caching(workspace, daily_token_limit)
    
    logger.info(f"Caching initialized for workspace: {workspace}")
    logger.info(f"Daily token limit: {daily_token_limit}")
    
    return {
        "status": "initialized",
        "workspace": str(workspace),
        "cache_dir": str(caching.cache_dir),
        "daily_token_limit": daily_token_limit
    }


def check_cache(prompt: str, model: str, files: List[str]) -> Dict[str, Any]:
    """Check if response is cached.
    
    Args:
        prompt: The prompt text
        model: Model name
        files: List of file paths the response depends on
        
    Returns:
        Dictionary with cached status and response if available
    """
    if caching is None:
        return {"error": "Caching not initialized", "cached": False}
    
    try:
        cached_response = caching.check_and_get_cached(prompt, model, files)
        return {
            "cached": cached_response is not None,
            "response": cached_response
        }
    except Exception as e:
        logger.error(f"Error checking cache: {e}")
        return {"error": str(e), "cached": False}


def cache_response(prompt: str, model: str, files: List[str], 
                   response: str, tokens: int, 
                   request_type: str = 'completion') -> Dict[str, Any]:
    """Cache LLM response.
    
    Args:
        prompt: The prompt text
        model: Model name
        files: List of file paths the response depends on
        response: LLM response to cache
        tokens: Number of tokens used
        request_type: Type of request (prompt, completion, etc.)
        
    Returns:
        Status dictionary
    """
    if caching is None:
        return {"error": "Caching not initialized", "status": "failed"}
    
    try:
        caching.cache_response_and_record_usage(
            prompt, model, files, response, tokens, request_type
        )
        return {"status": "cached", "tokens": tokens}
    except Exception as e:
        logger.error(f"Error caching response: {e}")
        return {"error": str(e), "status": "failed"}


def invalidate_files(file_paths: List[str]) -> Dict[str, Any]:
    """Invalidate cache for changed files.
    
    Args:
        file_paths: List of file paths that changed
        
    Returns:
        Dictionary with invalidated files
    """
    if caching is None:
        return {"error": "Caching not initialized", "invalidated": []}
    
    try:
        caching.invalidate_files(file_paths)
        logger.info(f"Invalidated cache for {len(file_paths)} files")
        return {"invalidated": file_paths, "count": len(file_paths)}
    except Exception as e:
        logger.error(f"Error invalidating files: {e}")
        return {"error": str(e), "invalidated": []}


def get_stats() -> Dict[str, Any]:
    """Get caching statistics.
    
    Returns:
        Dictionary with comprehensive caching statistics
    """
    if caching is None:
        return {"error": "Caching not initialized"}
    
    try:
        stats = caching.get_all_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {"error": str(e)}


def check_budget(tokens: int) -> Dict[str, Any]:
    """Check token budget.
    
    Args:
        tokens: Estimated tokens for the request
        
    Returns:
        Dictionary with budget status
    """
    if caching is None:
        return {"error": "Caching not initialized", "allowed": False}
    
    try:
        allowed = caching.budget.check_budget(tokens)
        report = caching.budget.get_usage_report()
        return {
            "allowed": allowed,
            "remaining": report.get('remaining', 0),
            "daily_usage": report.get('daily_usage', 0),
            "daily_limit": report.get('daily_limit', 0),
            "usage_percentage": report.get('usage_percentage', 0)
        }
    except Exception as e:
        logger.error(f"Error checking budget: {e}")
        return {"error": str(e), "allowed": False}


def get_lazy_content(path: str) -> Dict[str, Any]:
    """Get file content with lazy loading.
    
    Args:
        path: File path
        
    Returns:
        Dictionary with file content
    """
    if caching is None:
        return {"error": "Caching not initialized"}
    
    try:
        content = caching.get_lazy_content(path)
        return {
            "path": path,
            "content": content,
            "loaded": content is not None
        }
    except Exception as e:
        logger.error(f"Error getting lazy content: {e}")
        return {"error": str(e), "loaded": False}


def is_file_changed(path: str) -> Dict[str, Any]:
    """Check if file has changed.
    
    Args:
        path: File path
        
    Returns:
        Dictionary with change status
    """
    if caching is None:
        return {"error": "Caching not initialized"}
    
    try:
        changed = caching.is_file_changed(path)
        return {
            "path": path,
            "changed": changed
        }
    except Exception as e:
        logger.error(f"Error checking file change: {e}")
        return {"error": str(e), "changed": False}


def cleanup_cache(max_age_days: int = 30) -> Dict[str, Any]:
    """Clean up old cache entries.
    
    Args:
        max_age_days: Maximum age of entries to keep
        
    Returns:
        Dictionary with cleanup results
    """
    if caching is None:
        return {"error": "Caching not initialized"}
    
    try:
        result = caching.cleanup(max_age_days)
        return result
    except Exception as e:
        logger.error(f"Error cleaning up cache: {e}")
        return {"error": str(e)}


def clear_all_cache() -> Dict[str, Any]:
    """Clear all caches and reset statistics.
    
    Returns:
        Status dictionary
    """
    if caching is None:
        return {"error": "Caching not initialized"}
    
    try:
        caching.clear_all()
        logger.info("All caches cleared")
        return {"status": "cleared"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return {"error": str(e)}


# MCP Protocol Implementation

MCP_VERSION = "2024-11-05"
SERVER_NAME = "rw-agent-cache"
SERVER_VERSION = "1.0.0"

# Tool definitions for MCP
TOOLS = [
    {
        "name": "initialize_caching",
        "description": "Initialize the caching system with workspace and token budget",
        "inputSchema": {
            "type": "object",
            "properties": {
                "daily_token_limit": {
                    "type": "integer",
                    "description": "Daily token budget limit",
                    "default": 100000
                }
            }
        }
    },
    {
        "name": "check_cache",
        "description": "Check if a response is cached for the given prompt, model, and files",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The prompt text"},
                "model": {"type": "string", "description": "Model name"},
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths"
                }
            },
            "required": ["prompt", "model", "files"]
        }
    },
    {
        "name": "cache_response",
        "description": "Cache an LLM response with file dependencies",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The prompt text"},
                "model": {"type": "string", "description": "Model name"},
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths"
                },
                "response": {"type": "string", "description": "LLM response to cache"},
                "tokens": {"type": "integer", "description": "Number of tokens used"},
                "request_type": {
                    "type": "string",
                    "description": "Type of request",
                    "default": "completion"
                }
            },
            "required": ["prompt", "model", "files", "response", "tokens"]
        }
    },
    {
        "name": "invalidate_files",
        "description": "Invalidate cache entries for changed files",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths that changed"
                }
            },
            "required": ["file_paths"]
        }
    },
    {
        "name": "get_caching_stats",
        "description": "Get comprehensive caching statistics",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "check_token_budget",
        "description": "Check if a request is within the token budget",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tokens": {
                    "type": "integer",
                    "description": "Estimated tokens for the request"
                }
            },
            "required": ["tokens"]
        }
    },
    {
        "name": "get_lazy_content",
        "description": "Get file content with lazy loading",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "is_file_changed",
        "description": "Check if a file has changed since last tracked",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "cleanup_cache",
        "description": "Clean up old cache entries",
        "inputSchema": {
            "type": "object",
            "properties": {
                "max_age_days": {
                    "type": "integer",
                    "description": "Maximum age of entries to keep",
                    "default": 30
                }
            }
        }
    },
    {
        "name": "clear_all_cache",
        "description": "Clear all caches and reset statistics",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


def create_response(id: Any, result: Any = None, error: Dict = None) -> Dict:
    """Create an MCP response message.
    
    Args:
        id: Request ID
        result: Result data (if successful)
        error: Error dictionary (if failed)
        
    Returns:
        MCP response message
    """
    response = {
        "jsonrpc": "2.0",
        "id": id
    }
    
    if error:
        response["error"] = error
    else:
        response["result"] = result
    
    return response


def create_notification(method: str, params: Dict = None) -> Dict:
    """Create an MCP notification message.
    
    Args:
        method: Notification method name
        params: Notification parameters
        
    Returns:
        MCP notification message
    """
    notification = {
        "jsonrpc": "2.0",
        "method": method
    }
    
    if params:
        notification["params"] = params
    
    return notification


def handle_initialize(params: Dict) -> Dict:
    """Handle initialize request.
    
    Args:
        params: Initialize parameters
        
    Returns:
        Server capabilities
    """
    return {
        "protocolVersion": MCP_VERSION,
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": SERVER_NAME,
            "version": SERVER_VERSION
        }
    }


def handle_tools_list() -> Dict:
    """Handle tools/list request.
    
    Returns:
        List of available tools
    """
    return {"tools": TOOLS}


def handle_tools_call(name: str, arguments: Dict) -> Dict:
    """Handle tools/call request.
    
    Args:
        name: Tool name to call
        arguments: Tool arguments
        
    Returns:
        Tool execution result
    """
    logger.info(f"Calling tool: {name} with args: {arguments}")
    
    try:
        if name == "initialize_caching":
            result = initialize_caching(
                arguments.get("daily_token_limit", 100000)
            )
        elif name == "check_cache":
            result = check_cache(
                arguments.get("prompt", ""),
                arguments.get("model", ""),
                arguments.get("files", [])
            )
        elif name == "cache_response":
            result = cache_response(
                arguments.get("prompt", ""),
                arguments.get("model", ""),
                arguments.get("files", []),
                arguments.get("response", ""),
                arguments.get("tokens", 0),
                arguments.get("request_type", "completion")
            )
        elif name == "invalidate_files":
            result = invalidate_files(arguments.get("file_paths", []))
        elif name == "get_caching_stats":
            result = get_stats()
        elif name == "check_token_budget":
            result = check_budget(arguments.get("tokens", 0))
        elif name == "get_lazy_content":
            result = get_lazy_content(arguments.get("path", ""))
        elif name == "is_file_changed":
            result = is_file_changed(arguments.get("path", ""))
        elif name == "cleanup_cache":
            result = cleanup_cache(arguments.get("max_age_days", 30))
        elif name == "clear_all_cache":
            result = clear_all_cache()
        else:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Unknown tool: {name}"
                    }
                ],
                "isError": True
            }
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }
            ],
            "isError": "error" in result
        }
        
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error: {str(e)}"
                }
            ],
            "isError": True
        }


async def process_message(message: Dict) -> Optional[Dict]:
    """Process an incoming MCP message.
    
    Args:
        message: Incoming JSON-RPC message
        
    Returns:
        Response message or None for notifications
    """
    method = message.get("method", "")
    params = message.get("params", {})
    msg_id = message.get("id")
    
    logger.debug(f"Processing method: {method}")
    
    # Handle requests
    if method == "initialize":
        result = handle_initialize(params)
        return create_response(msg_id, result)
    
    elif method == "tools/list":
        result = handle_tools_list()
        return create_response(msg_id, result)
    
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = handle_tools_call(tool_name, arguments)
        return create_response(msg_id, result)
    
    elif method == "initialized":
        # Notification only, no response needed
        logger.info("Client initialized")
        return None
    
    elif method == "notifications/cancelled":
        logger.info("Request cancelled")
        return None
    
    else:
        logger.warning(f"Unknown method: {method}")
        return create_response(
            msg_id,
            error={
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        )


async def run_server():
    """Run the MCP server using stdio."""
    logger.info("Starting rw-agent caching MCP server")
    
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    
    await asyncio.get_event_loop().connect_read_pipe(
        lambda: protocol, sys.stdin
    )
    
    writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, asyncio.get_event_loop())
    
    buffer = ""
    
    while True:
        try:
            # Read from stdin
            chunk = await reader.read(4096)
            if not chunk:
                break
            
            buffer += chunk.decode('utf-8')
            
            # Process complete messages
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                
                if not line:
                    continue
                
                try:
                    message = json.loads(line)
                    response = await process_message(message)
                    
                    if response:
                        response_line = json.dumps(response) + '\n'
                        writer.write(response_line.encode('utf-8'))
                        await writer.drain()
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Server error: {e}")
    
    logger.info("Server shutting down")


def run_test_mode():
    """Run in test mode to verify functionality."""
    print("Testing rw-agent caching MCP server...")
    print("=" * 50)
    
    # Test initialization
    print("\n1. Testing initialization...")
    result = initialize_caching(100000)
    print(f"   Status: {result.get('status')}")
    print(f"   Workspace: {result.get('workspace')}")
    print(f"   Cache Dir: {result.get('cache_dir')}")
    
    # Test check cache (should miss)
    print("\n2. Testing cache check (expect miss)...")
    result = check_cache("test prompt", "test-model", ["test.py"])
    print(f"   Cached: {result.get('cached')}")
    
    # Test cache response
    print("\n3. Testing cache response...")
    result = cache_response(
        "test prompt", 
        "test-model", 
        ["test.py"], 
        "test response", 
        100
    )
    print(f"   Status: {result.get('status')}")
    
    # Test check cache (should hit)
    print("\n4. Testing cache check (expect hit)...")
    result = check_cache("test prompt", "test-model", ["test.py"])
    print(f"   Cached: {result.get('cached')}")
    print(f"   Response: {result.get('response')}")
    
    # Test budget check
    print("\n5. Testing budget check...")
    result = check_budget(5000)
    print(f"   Allowed: {result.get('allowed')}")
    print(f"   Remaining: {result.get('remaining')}")
    
    # Test stats
    print("\n6. Testing stats...")
    stats = get_stats()
    print(f"   Response Cache Hits: {stats.get('response_cache', {}).get('hits', 0)}")
    print(f"   Response Cache Misses: {stats.get('response_cache', {}).get('misses', 0)}")
    print(f"   Token Budget Usage: {stats.get('token_budget', {}).get('daily_usage', 0)}")
    
    # Test file invalidation
    print("\n7. Testing file invalidation...")
    result = invalidate_files(["test.py"])
    print(f"   Invalidated: {result.get('invalidated')}")
    
    # Test cache check after invalidation (should miss)
    print("\n8. Testing cache check after invalidation (expect miss)...")
    result = check_cache("test prompt", "test-model", ["test.py"])
    print(f"   Cached: {result.get('cached')}")
    
    print("\n" + "=" * 50)
    print("All tests completed!")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='rw-agent caching MCP server'
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
        run_test_mode()
    else:
        # Use synchronous stdio server for Windows compatibility
        run_sync_server()


def run_sync_server():
    """Run the MCP server using synchronous stdio (Windows-compatible)."""
    logger.info("Starting rw-agent caching MCP server (sync mode)")
    
    # Initialize caching
    global caching, workspace
    workspace = Path.cwd()
    caching = create_caching(workspace, 100000)
    logger.info(f"Caching initialized for workspace: {workspace}")
    
    logger.info("Waiting for requests on stdin...")
    
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                
                # Handle initialize
                if request.get('method') == 'initialize':
                    response = {
                        'jsonrpc': '2.0',
                        'id': request.get('id'),
                        'result': {
                            'protocolVersion': '2024-11-05',
                            'serverInfo': {
                                'name': 'rw-agent-caching',
                                'version': '1.0.0'
                            },
                            'capabilities': {
                                'tools': {}
                            }
                        }
                    }
                
                # Handle tools/list
                elif request.get('method') == 'tools/list':
                    # Get all functions that return Dict[str, Any]
                    tool_names = [
                        'initialize_caching', 'check_cache', 'cache_response',
                        'invalidate_files', 'get_caching_stats', 'check_token_budget',
                        'get_lazy_content', 'is_file_changed', 'cleanup_cache',
                        'clear_all_cache'
                    ]
                    
                    tools = []
                    for name in tool_names:
                        tools.append({
                            'name': name,
                            'description': f'Tool {name}',
                            'inputSchema': {'type': 'object', 'properties': {}}
                        })
                    
                    response = {
                        'jsonrpc': '2.0',
                        'id': request.get('id'),
                        'result': {'tools': tools}
                    }
                
                # Handle tools/call
                elif request.get('method') == 'tools/call':
                    tool_name = request.get('params', {}).get('name')
                    tool_args = request.get('params', {}).get('arguments', {})
                    
                    result = None
                    if tool_name == 'initialize_caching':
                        result = initialize_caching(
                            tool_args.get('daily_token_limit', 100000)
                        )
                    elif tool_name == 'check_cache':
                        result = check_cache(
                            tool_args.get('prompt', ''),
                            tool_args.get('model', ''),
                            tool_args.get('files', [])
                        )
                    elif tool_name == 'cache_response':
                        result = cache_response(
                            tool_args.get('prompt', ''),
                            tool_args.get('model', ''),
                            tool_args.get('files', []),
                            tool_args.get('response', ''),
                            tool_args.get('tokens', 0)
                        )
                    elif tool_name == 'get_caching_stats' or tool_name == 'get_stats':
                        result = get_stats()
                    elif tool_name == 'check_token_budget':
                        result = check_budget(tool_args.get('tokens', 0))
                    elif tool_name == 'invalidate_files':
                        result = invalidate_files(tool_args.get('files', []))
                    elif tool_name == 'get_lazy_content':
                        result = get_lazy_content(tool_args.get('path', ''))
                    elif tool_name == 'is_file_changed':
                        result = is_file_changed(tool_args.get('path', ''))
                    elif tool_name == 'cleanup_cache':
                        result = cleanup_cache()
                    elif tool_name == 'clear_all_cache':
                        result = clear_all_cache()
                    else:
                        response = {
                            'jsonrpc': '2.0',
                            'id': request.get('id'),
                            'error': {
                                'code': -32601,
                                'message': f'Unknown tool: {tool_name}'
                            }
                        }
                        print(json.dumps(response), flush=True)
                        continue
                    
                    response = {
                        'jsonrpc': '2.0',
                        'id': request.get('id'),
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
                    response = {
                        'jsonrpc': '2.0',
                        'id': request.get('id'),
                        'error': {
                            'code': -32601,
                            'message': f'Unknown method: {request.get("method")}'
                        }
                    }
                
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
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
