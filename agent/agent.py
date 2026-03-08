"""Core agentic engine with orchestration, memory management, and conversation persistence."""
import asyncio
import json
import os
import re
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import Config
from .context_manager import ContextManager
from .llm_models import ModelManager
from .skills_manager import SkillManager
from .user_interface import AgentUI
from .utilities import compress_prompt, get_token_count
from .logging_config import get_logger, setup_logging

# Import streaming renderer
try:
    from .streaming_renderer import StreamingRenderer, stream_with_rendering
    STREAMING_RENDERER_AVAILABLE = True
except ImportError:
    StreamingRenderer = None
    stream_with_rendering = None
    STREAMING_RENDERER_AVAILABLE = False

# Import approval workflow
try:
    from .approval_workflow import ApprovalManager, ApprovalMode, RiskLevel
    APPROVAL_AVAILABLE = True
except ImportError:
    ApprovalManager = None
    ApprovalMode = None
    RiskLevel = None
    APPROVAL_AVAILABLE = False

# Optional config wizard import
try:
    from .configuration_wizard import ConfigWizard, quick_show_config
    CONFIG_WIZARD_AVAILABLE = True
except ImportError:
    CONFIG_WIZARD_AVAILABLE = False
    ConfigWizard = None
    quick_show_config = None

# Optional subagents import
try:
    from .subagents import (
        SubAgentOrchestrator,
        SubAgentTask,
        SubAgentType,
        create_orchestrator,
    )
    SUBAGENTS_AVAILABLE = True
except ImportError:
    SUBAGENTS_AVAILABLE = False
    SubAgentOrchestrator = None
    SubAgentTask = None
    SubAgentType = None
    create_orchestrator = None


class ConversationHistory:
    """Persistent conversation history management with auto-save."""

    def __init__(
        self,
        storage_path: Optional[str] = None,
        auto_save: bool = True,
        auto_save_interval: int = 30
    ):
        self.storage_path = storage_path or self._default_storage_path()
        self.history: List[Dict[str, str]] = []
        self._available_conversations: List[Dict[str, Any]] = []
        self._load()
        
        # Auto-save configuration
        self.auto_save = auto_save
        self.auto_save_interval = auto_save_interval  # seconds
        self._save_pending = False
        self._auto_save_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Start auto-save thread if enabled
        if self.auto_save:
            self._start_auto_save()
    
    def _start_auto_save(self):
        """Start background auto-save thread."""
        self._running = True
        self._auto_save_thread = threading.Thread(
            target=self._auto_save_loop,
            daemon=True
        )
        self._auto_save_thread.start()
    
    def _auto_save_loop(self):
        """Background loop that saves when dirty."""
        while self._running:
            time.sleep(self.auto_save_interval)
            if self._save_pending:
                self.save()
                self._save_pending = False
    
    def mark_dirty(self):
        """Mark conversation as changed (needs save)."""
        self._save_pending = True
    
    def stop_auto_save(self):
        """Stop auto-save and perform final save."""
        self._running = False
        if self._save_pending and self._auto_save_thread:
            self.save()
            self._save_pending = False
        if self._auto_save_thread:
            self._auto_save_thread.join(timeout=2.0)

    def _default_storage_path(self) -> str:
        storage_dir = Path.home() / '.local' / 'share' / 'rapidwebs-agent' / 'conversations'
        storage_dir.mkdir(parents=True, exist_ok=True)
        return str(storage_dir / f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    def _extract_date(self, filename: str) -> str:
        """Extract date from conversation filename."""
        match = re.search(r'conversation_(\d{8})_(\d{6})', filename)
        if match:
            date_str, time_str = match.groups()
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}"
        return "Unknown"

    def _load(self):
        """Load existing conversations from disk."""
        storage_dir = Path(self.storage_path).parent
        self._available_conversations = []
        
        for conv_file in sorted(storage_dir.glob('conversation_*.json')):
            try:
                with open(conv_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._available_conversations.append({
                        'id': conv_file.stem,
                        'path': str(conv_file),
                        'date': self._extract_date(conv_file.name),
                        'message_count': len(data),
                        'first_message': data[0]['content'][:100] if data else ''
                    })
            except Exception:
                pass  # Skip corrupted files

    def save(self):
        """Save conversation history to disk."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # Silently fail

    def add(self, role: str, content: str, **kwargs):
        """Add message to history."""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        self.history.append(message)
        
        # Mark as dirty for auto-save
        self.mark_dirty()

    def get_recent(self, n: int = 5) -> List[Dict[str, str]]:
        """Get n most recent messages."""
        return self.history[-n:]

    def clear(self):
        """Clear conversation history."""
        self.history.clear()

    def export(self, format: str = 'markdown') -> str:
        """Export conversation in specified format."""
        if format == 'markdown':
            lines = ["# Conversation Log\n"]
            for msg in self.history:
                role = "User" if msg['role'] == 'user' else "Agent"
                lines.append(f"## {role}\n\n{msg['content']}\n")
            return '\n'.join(lines)
        elif format == 'json':
            return json.dumps(self.history, indent=2, ensure_ascii=False)
        return str(self.history)

    def list_conversations(self) -> List[Dict[str, Any]]:
        """List all saved conversations."""
        return self._available_conversations

    def load_conversation(self, conversation_id: str) -> bool:
        """Load a specific conversation by ID."""
        for conv in self._available_conversations:
            if conv['id'] == conversation_id:
                try:
                    with open(conv['path'], 'r', encoding='utf-8') as f:
                        self.history = json.load(f)
                    self.storage_path = conv['path']
                    return True
                except Exception:
                    return False
        return False

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search conversation history for query."""
        results = []
        query_lower = query.lower()
        
        for i, msg in enumerate(self.history):
            content = msg.get('content', '')
            if query_lower in content.lower():
                start = max(0, i - 2)
                end = min(len(self.history), i + 3)
                
                results.append({
                    'index': i,
                    'role': msg['role'],
                    'content': content[:300],
                    'timestamp': msg.get('timestamp', ''),
                    'context': self.history[start:end],
                    'match_position': content.lower().find(query_lower)
                })
        
        results.sort(key=lambda r: r['match_position'] == 0, reverse=True)
        return results[:max_results]

    async def compress(self, llm_callback) -> Tuple[str, Optional[Any]]:
        """Compress conversation using LLM summarization."""
        if len(self.history) < 5:
            return "Conversation too short to compress (need 5+ messages)", None
        
        recent_messages = self.history[-20:]
        
        conversation_text = '\n'.join([
            f"{msg['role']}: {msg['content']}" 
            for msg in recent_messages
            if msg['role'] in ['user', 'agent']
        ])
        
        summary_prompt = f"""You are summarizing a conversation between a user and an AI coding assistant.

Create a dense technical briefing that preserves:
1. **Key decisions made** - What was decided/approved
2. **Code changes** - Files modified, functions changed (include paths)
3. **Action items** - TODOs, pending tasks, follow-ups
4. **Problem context** - What problem was being solved
5. **Solution approach** - How it was solved

Be concise but complete. A developer should be able to resume work from this summary.

Conversation to summarize:
{conversation_text}

Provide the summary in this format:
## Summary
[2-3 sentence overview]

## Key Decisions
- Decision 1
- Decision 2

## Code Changes
- `file/path.py`: Change description
- `another/file.js`: Change description

## Action Items
- [ ] TODO item 1
- [ ] TODO item 2

## Context
[Relevant background for continuing work]
"""
        
        try:
            summary, usage = await llm_callback(summary_prompt)
            
            old_count = len(self.history)
            self.history = [{
                'role': 'system',
                'content': f"## Previous Conversation Summary\n\n{summary}\n\n---\n\n*Conversation compressed from {old_count} messages on {datetime.now().isoformat()}*",
                'timestamp': datetime.now().isoformat(),
                'compressed': True,
                'original_count': old_count
            }]
            
            self.save()
            return summary, usage
        except Exception as e:
            return f"Error compressing conversation: {str(e)}", None


# JSON Schema for tool call validation
TOOL_CALL_SCHEMA = {
    'type': 'object',
    'required': ['tool', 'params'],
    'properties': {
        'tool': {'type': 'string'},
        'params': {'type': 'object'}
    }
}

TOOL_PARAMS_SCHEMA = {
    'fs': {
        'required': ['operation', 'path'],
        'properties': {
            'operation': {'type': 'string', 'enum': ['read', 'list', 'explore', 'write', 'delete']},
            'path': {'type': 'string'},
            'content': {'type': 'string'},
            'max_lines': {'type': 'integer'}
        }
    },
    'terminal': {
        'required': ['command'],
        'properties': {
            'command': {'type': 'string'}
        }
    },
    'web': {
        'required': ['url'],
        'properties': {
            'url': {'type': 'string'},
            'extract_text': {'type': 'boolean'}
        }
    },
    'search': {
        'required': ['action'],
        'properties': {
            'action': {'type': 'string', 'enum': ['grep', 'find_files']},
            'pattern': {'type': 'string'},
            'path': {'type': 'string'},
            'include': {'type': 'string'}
        }
    },
    'code_tools': {
        'required': ['action', 'language'],
        'properties': {
            'action': {'type': 'string', 'enum': ['lint', 'format', 'fix', 'install']},
            'language': {'type': 'string'},
            'file_path': {'type': 'string'},
            'content': {'type': 'string'}
        }
    },
    'subagents': {
        'required': ['type', 'task'],
        'properties': {
            'type': {'type': 'string', 'enum': ['code', 'test', 'docs', 'research', 'security']},
            'task': {'type': 'string'},
            'context': {'type': 'object'}
        }
    }
}


def validate_tool_call(tool_call: Dict) -> tuple[bool, Optional[str]]:
    """Validate tool call against schema - NEW FEATURE"""
    # Basic structure validation
    if not isinstance(tool_call, dict):
        return False, "Tool call must be a JSON object"
    
    if 'tool' not in tool_call:
        return False, "Missing required field: 'tool'"
    
    if 'params' not in tool_call:
        return False, "Missing required field: 'params'"
    
    tool_name = tool_call['tool']
    params = tool_call['params']
    
    # Check if tool exists
    if tool_name not in TOOL_PARAMS_SCHEMA:
        return False, f"Unknown tool: {tool_name}. Available: {', '.join(TOOL_PARAMS_SCHEMA.keys())}"
    
    # Validate params
    schema = TOOL_PARAMS_SCHEMA[tool_name]
    for required_field in schema.get('required', []):
        if required_field not in params:
            return False, f"Missing required parameter for {tool_name}: '{required_field}'"
    
    # Validate enum values
    for prop_name, prop_schema in schema.get('properties', {}).items():
        if prop_name in params and 'enum' in prop_schema:
            if params[prop_name] not in prop_schema['enum']:
                return False, f"Invalid value for '{prop_name}': {params[prop_name]}. Allowed: {prop_schema['enum']}"
    
    return True, None


def clean_response_for_display(response: str) -> str:
    """Remove raw JSON tool calls from LLM response for clean display.
    
    The LLM sometimes includes raw JSON tool calls in its response text.
    This function strips them out so users only see natural language explanations.
    
    Args:
        response: Raw LLM response that may contain JSON tool calls
        
    Returns:
        Cleaned response with JSON tool calls removed
    """
    if not response:
        return response
    
    cleaned = response
    
    # Pattern 1: Remove markdown code blocks with JSON tool calls
    # Matches: ```json {...} ```
    json_block_pattern = r'```json\s*\{"tool":.*?```\s*'
    cleaned = re.sub(json_block_pattern, '\n', cleaned, flags=re.DOTALL | re.IGNORECASE)
    
    # Pattern 2: Remove standalone JSON tool calls (with or without markdown backticks)
    # Matches: {"tool": "...", "params": {...}} with optional trailing fields
    json_tool_pattern = r'`*\s*\{"tool":\s*"[^"]+",\s*"params":\s*\{[^}]*\}(?:[^}]*?)\}\s*`*'
    cleaned = re.sub(json_tool_pattern, '\n', cleaned, flags=re.DOTALL)
    
    # Pattern 3: Remove partial JSON tool calls that start with {"tool":
    # This catches malformed or incomplete JSON
    partial_tool_pattern = r'\{"tool":\s*"[^"]*"(?:[^}]{0,200})?\}'
    cleaned = re.sub(partial_tool_pattern, '\n', cleaned, flags=re.DOTALL)
    
    # Pattern 4: Remove orphaned backticks left behind
    cleaned = re.sub(r'```\s*\n', '', cleaned)
    cleaned = re.sub(r'\n\s*```', '', cleaned)
    
    # Clean up multiple consecutive newlines left behind
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    # Clean up leading/trailing whitespace from the cleanup
    cleaned = cleaned.strip()
    
    return cleaned if cleaned else response  # Return original if cleaning removed everything


def get_error_suggestion(error_type: str, error_message: str) -> str:
    """Generate helpful error suggestions - NEW FEATURE"""
    suggestions = {
        'API key': "Check your config at ~/.config/rapidwebs-agent/config.yaml or set RW_QWEN_API_KEY / RW_GEMINI_API_KEY environment variable",
        'Rate limit': f"Wait a moment before retrying. You can also switch models with 'model switch <name>'",
        'File not found': "Check the file path. Use 'fs list' to see directory contents or 'fs explore' to browse the codebase",
        'Permission': "Check file permissions. The agent can only access files in allowed directories (~ and ./)",
        'Timeout': "The operation took too long. Try breaking it into smaller steps",
        'JSON': "The response format was invalid. This might be a temporary API issue",
        'Network': "Check your internet connection and try again",
        'Command not found': "The command is not in the whitelist. Allowed commands: ls, pwd, cat, grep, find, echo, which, git",
        'Model': "The model may be disabled or misconfigured. Try 'model list' to see available models"
    }
    
    for key, suggestion in suggestions.items():
        if key.lower() in error_message.lower():
            return suggestion
    
    return "If this error persists, try: 1) Check your config file 2) Verify API keys 3) Check network connection"


class Agent:
    """Main agentic engine with conversation persistence and improved error handling"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = Config(config_path)

        # Initialize logging
        log_level = self.config.get('logging.level', 'INFO')
        log_to_file = self.config.get('logging.enabled', 'True')
        log_to_console = self.config.get('logging.console', True)
        self.logger = setup_logging(
            level=log_level,
            log_to_file=log_to_file,
            log_to_console=log_to_console,
            json_format=self.config.get('logging.json_format', False)
        )

        # Budget warning callback - displays warning via UI
        def budget_warning(message: str):
            self.ui.display_message('warning', message)
            self.logger.warning(f'Token budget warning: {message}')

        self.model_manager = ModelManager(self.config, budget_warning_callback=budget_warning)
        self.skill_manager = SkillManager(self.config)
        self.logger.info('Agent initialized with model and skill managers')

        # Initialize approval manager first (needed by UI)
        self.approval_manager: Optional[ApprovalManager] = None
        if APPROVAL_AVAILABLE:
            self.approval_manager = ApprovalManager(self.config)

        # Pass approval manager to UI
        self.ui = AgentUI(self.config, approval_manager=self.approval_manager)

        # Context optimization - use config value
        token_budget = self.config.get('performance.token_budget', 100000)
        self.context_manager = ContextManager(token_budget=token_budget)

        # File tracking for cache invalidation - NEW FEATURE
        self._accessed_files: set[str] = set()

        # Persistent conversation history with auto-save
        auto_save_enabled = self.config.get('conversation.auto_save', True)
        auto_save_interval = self.config.get('conversation.auto_save_interval', 30)
        self.conversation = ConversationHistory(
            auto_save=auto_save_enabled,
            auto_save_interval=auto_save_interval
        )
        self.conversation_history: List[Dict[str, str]] = []  # In-memory for quick access

        # TODO skill for task management
        try:
            from .skills import TodoSkill
            import uuid
            self._session_id = f"session_{uuid.uuid4().hex[:8]}"
            auto_create_todos = self.config.get('todo.auto_create', True)
            self.todo_skill = TodoSkill(config, session_id=self._session_id)
            self.auto_create_todos = auto_create_todos
            self.logger.info(f'TODO skill initialized for session {self._session_id}')
        except ImportError as e:
            self.todo_skill = None
            self.auto_create_todos = False
            self.logger.warning(f'TODO skill not available: {e}')

        self.total_tokens = 0
        self.total_cost = 0.0
        self.running = True

        # SubAgents system (Tier 3)
        self.subagent_orchestrator: Optional[SubAgentOrchestrator] = None
        if SUBAGENTS_AVAILABLE:
            self.subagent_orchestrator = create_orchestrator(
                max_concurrent=self.config.get('subagents.max_concurrent', 3),
                register_defaults=False  # We'll register with model_manager
            )
            # Register default agents with model manager for LLM integration
            self.subagent_orchestrator.register_default_agents(
                model_manager=self.model_manager
            )

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def cleanup(self):
        """Cleanup resources and stop auto-save."""
        self.conversation.stop_auto_save()
        self.conversation.save()
        self.logger.info('Agent cleanup completed')

    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        self.ui.display_message('agent', "🛑 Shutting down gracefully...")
        self.cleanup()
        self.running = False
        sys.exit(0)

    async def _build_context(self, user_input: str) -> str:
        """Build context-aware prompt with conversation history and optimization"""
        # Try to detect current file from conversation
        current_file = self._detect_current_file()

        # Build optimized context if file detected
        if current_file:
            # Async context building
            try:
                context = await self.context_manager.build_optimized_context(
                    query=user_input,
                    current_file=current_file
                )
            except Exception as e:
                # Log the exception for debugging
                self.logger.warning(f"Context optimization failed: {e}")
                # Fallback to standard context if optimization fails
                context = self._build_standard_context(user_input)
        else:
            context = self._build_standard_context(user_input)

        return context
    
    def _detect_current_file(self) -> Optional[Path]:
        """Detect current file from conversation history"""
        import re
        # Check last few messages for file paths
        for msg in reversed(self.conversation_history[-5:]):
            content = msg.get('content', '')
            # Look for .py files
            match = re.search(r'([a-zA-Z0-9_/.\\-]+\.py)', content)
            if match:
                path_str = match.group(1)
                path = Path(path_str)
                if path.exists():
                    return path
            # Look for any file references
            if 'file' in content.lower() and ':' in content:
                parts = content.split(':')
                for part in parts:
                    part = part.strip()
                    if part.endswith('.py') or '/' in part or '\\' in part:
                        path = Path(part)
                        if path.exists():
                            return path
        return None
    
    def _build_standard_context(self, user_input: str) -> str:
        """Build standard context without optimization (fallback)"""
        system_prompt = """You are RapidWebs Agent, a helpful AI assistant for developers.

You have access to these tools. To use a tool, respond with ONLY a JSON object:
{"tool": "tool_name", "params": {"param1": "value1", ...}}

Available tools:
1. "fs" - Filesystem operations
   - operation: "read", "list", "explore", "write", "delete"
   - path: file or directory path
   - content: (for write) content to write
   - max_lines: (optional) limit lines read for large files

   Operations:
   - "read": Read file contents (use for individual files)
   - "list": List directory contents (single level)
   - "explore": Explore directory structure recursively (best for "read the codebase" requests)
   - "write": Write content to a file
   - "delete": Delete a file

   Examples:
   {"tool": "fs", "params": {"operation": "read", "path": "README.md"}}
   {"tool": "fs", "params": {"operation": "list", "path": "./src"}}
   {"tool": "fs", "params": {"operation": "explore", "path": "."}}
   {"tool": "fs", "params": {"operation": "read", "path": "large_file.py", "max_lines": 50}}

2. "terminal" - Execute whitelisted shell commands
   - command: shell command to execute
   Allowed: ls, pwd, cat, grep, find, echo, which, git
   Example: {"tool": "terminal", "params": {"command": "ls -la"}}

3. "web" - Web scraping (with SSRF protection)
   - url: URL to scrape (http/https only, no localhost/private IPs)
   - extract_text: true/false (default: true)
   Example: {"tool": "web", "params": {"url": "https://example.com"}}

4. "search" - Codebase search
   - action: "grep", "find_files"
   - pattern: regex pattern (for grep)
   - path: directory to search
   - include: file pattern (e.g., "*.py")
   Examples:
   {"tool": "search", "params": {"action": "grep", "pattern": "def main", "include": "*.py"}}
   {"tool": "search", "params": {"action": "find_files", "pattern": "*.md"}}

5. "code_tools" - Code linting and formatting
   - action: "lint", "format", "fix", "install"
   - language: "python", "javascript", "go", "rust", "shell", "sql"
   - file_path: path to file (optional if content provided)
   - content: code content (optional if file_path provided)
   Examples:
   {"tool": "code_tools", "params": {"action": "lint", "language": "python", "file_path": "main.py"}}
   {"tool": "code_tools", "params": {"action": "format", "language": "javascript", "content": "function test(){}"}}

6. "subagents" - Parallel task delegation for complex multi-step tasks
   - type: "code", "test", "docs", "research", "security"
   - task: description of task to delegate
   - context: optional context dict (file_path, source_file, etc.)
   Examples:
   {"tool": "subagents", "params": {"type": "code", "task": "Refactor main.py to use async/await", "context": {"file_path": "main.py"}}}
   {"tool": "subagents", "params": {"type": "test", "task": "Write unit tests for utils.py", "context": {"source_file": "utils.py"}}}
   {"tool": "subagents", "params": {"type": "docs", "task": "Generate API documentation", "context": {"source_file": "api.py"}}}

Be concise, helpful, and only use tools when necessary.
For large tasks, break them into multiple tool calls.
After receiving tool results, analyze them and either summarize or make another tool call.

Special Commands (use directly, not as tool calls):
- subagents list    - List available subagent types
- subagents status  - Show subagent orchestrator status
- subagents run <type> <task> - Run a subagent task (e.g., "subagents run code Refactor main.py")
- /stats            - Show token usage statistics
- /model            - Switch LLM model
- /budget           - Show token budget status
- /mode             - Show or change approval mode (plan, default, auto-edit, yolo)
- /configure        - Launch configuration wizard
- /help             - Show available commands
- /clear            - Clear conversation history

Approval Modes (user can switch with /mode command or keyboard shortcuts):
- plan: Read-only mode, no tool execution allowed
- default: Confirm all write/destructive operations (recommended)
- auto-edit: Auto-accept edits, confirm destructive operations
- yolo: No confirmations, full automation

Note: The user can switch approval modes at any time. Respect their current mode choice.
When in "plan" mode, do not attempt write operations. When in "yolo" mode, proceed without asking.
"""

        history_context = ""
        for msg in self.conversation.get_recent(5):
            role = "User" if msg['role'] == 'user' else "Agent"
            history_context += f"{role}: {msg['content']}\n"

        current_query = f"User: {user_input}"

        prompt = f"{system_prompt}\n\nConversation History:\n{history_context}\n{current_query}\n\nAgent:"

        return compress_prompt(prompt, max_tokens=3000)

    async def _parse_and_execute_tool(self, response: str) -> Optional[Dict]:
        """Parse LLM response for tool usage with schema validation and approval workflow.
        
        Implements robust JSON extraction with multiple fallback strategies:
        1. Extract from markdown code blocks (```json or ```)
        2. Find JSON-like content between braces
        3. Clean common artifacts (trailing commas, extra braces)
        4. Validate against schema before execution
        """
        try:
            # Try to extract JSON from response (handle markdown code blocks)
            response_text = response.strip()
            
            # Strategy 1: Extract from markdown code blocks
            json_text = self._extract_json_from_markdown(response_text)
            
            # Strategy 2: If no markdown, try to find JSON between braces
            if json_text is None:
                json_text = self._extract_json_braces(response_text)
            
            # Strategy 3: Clean common artifacts
            if json_text:
                json_text = self._clean_json_artifacts(json_text)
            
            if not json_text:
                self.logger.debug("No JSON found in response")
                return None
            
            # Parse JSON with error recovery
            tool_call = self._parse_json_with_recovery(json_text)
            
            if tool_call is None:
                return None

            if isinstance(tool_call, dict) and 'tool' in tool_call:
                # Validate tool call schema
                valid, error_msg = validate_tool_call(tool_call)
                if not valid:
                    self.logger.warning(f"Invalid tool call: {error_msg}")
                    return {
                        'success': False,
                        'error': f'Invalid tool call: {error_msg}',
                        'suggestion': get_error_suggestion('JSON', error_msg)
                    }

                tool_name = tool_call['tool']
                params = tool_call.get('params', {})

                self.logger.info(f"Tool requested: {tool_name} with params: {params}")

                # Check approval if approval manager is available
                if self.approval_manager and self.approval_manager.requires_approval(tool_name, params):
                    # Get risk level
                    risk_level = self.approval_manager.get_tool_risk(tool_name, params)
                    
                    # Get timeout from config
                    approval_timeout = self.config.get('approval_workflow.timeout_seconds', 300)

                    self.logger.info(f"Requesting approval for {tool_name} (risk: {risk_level}, timeout: {approval_timeout}s)")

                    # Request user approval with timeout
                    try:
                        decision = await self.ui.request_tool_approval(tool_call, risk_level, timeout_seconds=approval_timeout)
                        self.logger.info(f"User decision: {decision}")
                    except Exception as approval_error:
                        self.logger.error(f"Approval workflow failed: {approval_error}")
                        # Explicitly deny on error - no silent auto-approve
                        self.logger.warning("Approval workflow error - denying request")
                        return {
                            'success': False,
                            'error': f'Approval workflow error: {str(approval_error)}',
                            'tool': tool_name
                        }

                    # Handle user decision
                    if decision == 'no':
                        self.logger.warning(f"User denied tool: {tool_name}")
                        return {
                            'success': False,
                            'error': 'User denied tool execution',
                            'tool': tool_name
                        }
                    elif decision == 'timeout':
                        self.logger.warning(f"Approval timeout for tool: {tool_name}")
                        return {
                            'success': False,
                            'error': 'Approval timeout - user did not respond',
                            'tool': tool_name
                        }
                    elif decision == 'always':
                        # Mark for auto-accept in this session
                        self.logger.info(f"Auto-accepting {tool_name} for this session")
                        self.approval_manager.mark_auto_accept(tool_name, params)
                    elif decision == 'never':
                        # Mark for auto-reject in this session
                        self.logger.warning(f"User marked {tool_name} as never allow")
                        self.approval_manager.mark_auto_reject(tool_name, params)
                        return {
                            'success': False,
                            'error': 'User denied tool execution (marked as never allow)',
                            'tool': tool_name
                        }

                # Execute skill
                self.logger.info(f"Executing tool: {tool_name}")
                try:
                    result = await self.skill_manager.execute(tool_name, **params)
                    self.logger.info(f"Tool {tool_name} completed with success: {result.get('success', True)}")
                except Exception as exec_error:
                    self.logger.error(f"Tool execution failed: {exec_error}")
                    return {
                        'success': False,
                        'error': f'Tool execution error: {str(exec_error)}',
                        'tool': tool_name,
                        'suggestion': get_error_suggestion('General', str(exec_error))
                    }

                # Auto-create TODOs for complex multi-step tasks
                if self.auto_create_todos and self.todo_skill:
                    await self._maybe_auto_create_todo(tool_name, params)

                # Track file access for cache invalidation - NEW FEATURE
                self._track_file_access(tool_name, params)

                return result

        except json.JSONDecodeError as e:
            self.logger.debug(f"JSON decode error: {e}")
            pass
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Tool parsing error: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'suggestion': get_error_suggestion('JSON', error_msg)
            }

        return None

    def _track_file_access(self, tool_name: str, params: Dict):
        """Track file access for cache invalidation - NEW FEATURE.
        
        Monitors which files are accessed during tool execution so that
        cache entries can be automatically invalidated when files change.
        
        Args:
            tool_name: Name of the tool executed
            params: Tool parameters
        """
        # Track file reads/writes
        if tool_name == 'fs' and 'path' in params:
            path = params.get('path', '')
            operation = params.get('operation', '')
            
            # Track file operations (not directories)
            if operation in ['read', 'write', 'delete']:
                # Normalize path
                from pathlib import Path
                try:
                    resolved = str(Path(path).resolve())
                    self._accessed_files.add(resolved)
                except Exception:
                    # If path resolution fails, store as-is
                    self._accessed_files.add(path)
        
        # Track search operations that specify files
        elif tool_name == 'search' and 'path' in params:
            path = params.get('path', '')
            if path.endswith('.py') or path.endswith('.js') or path.endswith('.ts'):
                self._accessed_files.add(path)
        
        # Track LSP operations
        elif tool_name == 'lsp' and 'file_path' in params:
            self._accessed_files.add(params.get('file_path', ''))
        
        # Track code tools operations
        elif tool_name == 'code_tools' and 'file_path' in params:
            self._accessed_files.add(params.get('file_path', ''))

        # Track subagents operations with file context
        elif tool_name == 'subagents' and 'context' in params:
            context = params.get('context', {})
            if 'file_path' in context:
                self._accessed_files.add(context['file_path'])
            if 'source_file' in context:
                self._accessed_files.add(context['source_file'])
    
    async def _maybe_auto_create_todo(self, tool_name: str, params: Dict):
        """Auto-create TODOs for complex multi-step tasks.
        
        Monitors tool calls and automatically creates TODO items when
        detecting complex operations that involve multiple steps.
        
        Args:
            tool_name: Name of the tool executed
            params: Tool parameters
        """
        # Track tool calls for auto-TODO generation
        if not hasattr(self, '_recent_tool_calls'):
            self._recent_tool_calls = []
        
        self._recent_tool_calls.append({
            'tool': tool_name,
            'params': params,
            'timestamp': datetime.now()
        })
        
        # Keep only last 10 tool calls
        if len(self._recent_tool_calls) > 10:
            self._recent_tool_calls = self._recent_tool_calls[-10:]
        
        # Auto-create TODOs when detecting 3+ different tool calls in sequence
        # (indicates a complex multi-step task)
        if len(self._recent_tool_calls) >= 3:
            # Check if we have diverse tool usage
            unique_tools = set(tc['tool'] for tc in self._recent_tool_calls[-3:])
            
            if len(unique_tools) >= 2:
                # Create TODOs for the recent tool calls
                tasks = []
                for tc in self._recent_tool_calls[-3:]:
                    task_desc = f"Execute {tc['tool']}"
                    if 'path' in tc['params']:
                        task_desc += f": {tc['params']['path']}"
                    elif 'command' in tc['params']:
                        cmd = tc['params']['command'][:50]
                        task_desc += f": {cmd}..."
                    
                    tasks.append({
                        'description': task_desc,
                        'status': 'completed',  # Already executed
                        'active_form': f'Executed {tc["tool"]}'
                    })
                
                if tasks:
                    await self.todo_skill.execute('create', tasks=tasks)
                    self._recent_tool_calls = []  # Reset to avoid duplicate TODOs

    def _extract_json_from_markdown(self, text: str) -> Optional[str]:
        """Extract JSON content from markdown code blocks.
        
        Args:
            text: Text containing potential markdown code blocks
            
        Returns:
            Extracted JSON string or None if not found
        """
        # Try ```json blocks first
        if '```json' in text:
            start = text.find('```json') + 7
            end = text.find('```', start)
            if end > start:
                return text[start:end].strip()
        
        # Try generic ``` blocks
        if '```' in text:
            start = text.find('```') + 3
            end = text.find('```', start)
            if end > start:
                return text[start:end].strip()
        
        return None
    
    def _extract_json_braces(self, text: str) -> Optional[str]:
        """Extract JSON-like content by finding matching braces.
        
        Args:
            text: Text containing potential JSON
            
        Returns:
            Extracted JSON string or None if not found
        """
        # Find first { and last }
        start = text.find('{')
        end = text.rfind('}')
        
        if start == -1 or end == -1 or end <= start:
            return None
        
        # Extract content between braces
        candidate = text[start:end + 1]
        
        # Basic validation: count braces
        open_count = candidate.count('{')
        close_count = candidate.count('}')
        
        if open_count == close_count:
            return candidate
        
        # Try to balance braces
        if open_count > close_count:
            # Remove extra opening braces from end
            diff = open_count - close_count
            # Find position to cut
            pos = len(candidate)
            removed = 0
            while removed < diff and pos > 0:
                pos = candidate.rfind('{', 0, pos)
                if pos > 0:
                    removed += 1
            if removed == diff:
                return candidate[:pos] + '}' * close_count
        
        return candidate
    
    def _clean_json_artifacts(self, json_text: str) -> str:
        """Clean common JSON artifacts from LLM responses.
        
        Args:
            json_text: Raw JSON text
            
        Returns:
            Cleaned JSON text
        """
        # Remove trailing commas before } or ]
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
        
        # Remove duplicate commas
        json_text = re.sub(r',\s*,', ',', json_text)
        
        # Remove leading/trailing whitespace from keys
        json_text = re.sub(r'"\s+([^"]+)\s+"', r'"\1"', json_text)
        
        # Fix unquoted keys (simple cases)
        # Note: This is a heuristic and may not catch all cases
        # json_text = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_text)
        
        # Remove any stray characters before the first {
        first_brace = json_text.find('{')
        if first_brace > 0:
            json_text = json_text[first_brace:]
        
        # Remove any stray characters after the last }
        last_brace = json_text.rfind('}')
        if last_brace >= 0 and last_brace < len(json_text) - 1:
            json_text = json_text[:last_brace + 1]
        
        return json_text.strip()
    
    def _parse_json_with_recovery(self, json_text: str) -> Optional[Dict]:
        """Parse JSON with error recovery strategies.
        
        Args:
            json_text: JSON text to parse
            
        Returns:
            Parsed dictionary or None if parsing fails
        """
        # First attempt: direct parse
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            self.logger.debug(f"Initial JSON parse failed: {e}")
        
        # Second attempt: fix common issues
        try:
            # Try fixing single quotes
            fixed = json_text.replace("'", '"')
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            self.logger.debug(f"Single-quote fix failed: {e}")
        
        # Third attempt: use eval (safer with ast.literal_eval for simple cases)
        # Only for very simple JSON-like structures
        try:
            import ast
            # This is safe because literal_eval only evaluates literals
            result = ast.literal_eval(json_text)
            if isinstance(result, dict):
                return result
        except (ValueError, SyntaxError) as e:
            self.logger.debug(f"AST literal eval failed: {e}")
        
        # Log the problematic JSON for debugging
        self.logger.warning(f"Failed to parse JSON after recovery attempts: {json_text[:200]}...")
        return None

    def get_accessed_files(self) -> list[str]:
        """Get list of files accessed in current task.
        
        Returns:
            List of file paths that were accessed
        """
        return list(self._accessed_files)

    def reset_accessed_files(self):
        """Reset file tracking for new task."""
        self._accessed_files.clear()

    async def delegate_to_subagents(
        self, tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Delegate tasks to subagents for parallel execution.
        
        Args:
            tasks: List of task dictionaries with 'type', 'description', and 'context'
            
        Returns:
            Dictionary with combined results and statistics
        """
        if not SUBAGENTS_AVAILABLE or not self.subagent_orchestrator:
            return {
                'success': False,
                'error': 'SubAgents not available',
                'results': {}
            }
        
        # Convert task dicts to SubAgentTask objects
        subagent_tasks = []
        for task_dict in tasks:
            task_type_str = task_dict.get('type', 'generic')
            try:
                task_type = SubAgentType(task_type_str)
            except ValueError:
                task_type = SubAgentType.GENERIC
            
            task = SubAgentTask.create(
                type=task_type,
                description=task_dict.get('description', ''),
                context=task_dict.get('context', {}),
                token_budget=task_dict.get('token_budget', 10000),
                timeout=task_dict.get('timeout', 300)
            )
            subagent_tasks.append(task)
        
        # Execute tasks in parallel
        results = await self.subagent_orchestrator.execute_parallel(subagent_tasks)
        
        # Get combined output and stats
        combined_output = self.subagent_orchestrator.get_combined_output()
        conflicts = self.subagent_orchestrator.get_conflicts()
        stats = self.subagent_orchestrator.get_stats()
        
        return {
            'success': True,
            'output': combined_output,
            'results': {k: v.to_dict() for k, v in results.items()},
            'conflicts': conflicts,
            'stats': stats
        }

    async def _handle_subagent_command(self, command: str) -> str:
        """Handle subagent-related commands.
        
        Args:
            command: The full command string
            
        Returns:
            Result message to display
        """
        if not SUBAGENTS_AVAILABLE or not self.subagent_orchestrator:
            return "❌ SubAgents system is not available.\n\n💡 Make sure agent.subagents module is properly installed."
        
        parts = command.split()
        
        if len(parts) < 2:
            return (
                "**SubAgents Commands:**\n\n"
                "- `subagents list` - List available subagent types\n"
                "- `subagents status` - Show orchestrator status\n"
                "- `subagents run <type> <task>` - Run a subagent task\n\n"
                f"**Available Types:** code, test, docs, research, security\n\n"
                f"**Orchestrator Status:** {len(self.subagent_orchestrator.agents)} agents registered"
            )
        
        subcommand = parts[1].lower()
        
        if subcommand == 'list':
            agents_info = []
            for agent_type, agent in self.subagent_orchestrator.agents.items():
                agents_info.append(f"- **{agent_type.value}**: {agent.__class__.__name__}")
            
            return (
                "**Registered SubAgents:**\n\n" + 
                '\n'.join(agents_info) + 
                f"\n\n**Total:** {len(self.subagent_orchestrator.agents)} agents"
            )
        
        elif subcommand == 'status':
            stats = self.subagent_orchestrator.get_stats()
            return (
                f"**SubAgent Orchestrator Status:**\n\n"
                f"- **Registered Agents:** {len(self.subagent_orchestrator.agents)}\n"
                f"- **Max Concurrent:** {self.subagent_orchestrator.max_concurrent}\n"
                f"- **Tasks Completed:** {stats.get('tasks_completed', 0)}\n"
                f"- **Tasks Failed:** {stats.get('tasks_failed', 0)}\n"
                f"- **Total Token Usage:** {stats.get('total_tokens', 0):,}"
            )
        
        elif subcommand == 'run':
            if len(parts) < 4:
                return "❌ Usage: `subagents run <type> <task description>`\n\nExample: `subagents run code Create a Python script to parse CSV files`"
            
            agent_type_str = parts[2].lower()
            task_description = ' '.join(parts[3:])
            
            # Map type string to enum
            type_map = {
                'code': SubAgentType.CODE,
                'test': SubAgentType.TEST,
                'docs': SubAgentType.DOCS,
                'research': SubAgentType.RESEARCH,
                'security': SubAgentType.SECURITY
            }
            
            if agent_type_str not in type_map:
                return f"❌ Unknown subagent type: {agent_type_str}\n\n**Available types:** {', '.join(type_map.keys())}"
            
            agent_type = type_map[agent_type_str]
            
            # Create and execute task
            task = SubAgentTask.create(
                type=agent_type,
                description=task_description,
                context={'query': task_description}
            )
            
            self.ui.display_message('agent', f"🔄 Delegating to {agent_type_str} agent...\n\n**Task:** {task_description}")
            
            try:
                results = await self.subagent_orchestrator.execute_parallel([task])
                combined = self.subagent_orchestrator.get_combined_output()
                stats = self.subagent_orchestrator.get_stats()
                
                return (
                    f"✅ **SubAgent Task Completed**\n\n"
                    f"{combined}\n\n"
                    f"**Stats:**\n"
                    f"- Tokens Used: {stats.get('total_tokens', 0):,}\n"
                    f"- Execution Time: {stats.get('total_time', 0):.2f}s"
                )
            except Exception as e:
                return f"❌ **SubAgent Task Failed:** {str(e)}\n\n💡 Try breaking the task into smaller steps."
        
        else:
            return f"❌ Unknown subagent command: {subcommand}\n\nType `subagents` for available commands."

    async def process_query(self, user_input: str) -> tuple[str, Any]:
        """Process user query with improved error handling and conversation persistence"""
        from .models import TokenUsage
        self.conversation.add('user', user_input)
        self.conversation_history.append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now().isoformat()
        })

        prompt = await self._build_context(user_input)
        usage = TokenUsage()
        model_name = self.config.default_model

        # Check token budget before API call
        daily_limit = self.config.get('performance.token_budget', 100000)
        if not self.model_manager.check_budget(daily_limit):
            error_msg = "Daily token budget exceeded"
            suggestion = "Wait until tomorrow for budget reset, or increase limit in config"
            self.conversation.add('agent', f"⚠️ {error_msg}\n\n💡 Suggestion: {suggestion}")
            return f"⚠️ {error_msg}\n\n💡 Suggestion: {suggestion}", usage

        try:
            with self.ui.show_thinking() as progress:
                task = progress.add_task("Thinking...", total=None)
                response, usage, model_name = await self.model_manager.generate(prompt)
                progress.update(task, completed=True)
        except Exception as e:
            error_msg = str(e)
            suggestion = get_error_suggestion('API', error_msg)
            self.conversation.add('agent', f"Error: {error_msg}\n\n💡 Suggestion: {suggestion}")
            return f"Error: {error_msg}\n\n💡 Suggestion: {suggestion}", usage

        self.total_tokens += usage.total_tokens
        self.total_cost += usage.cost

        max_tool_iterations = self.config.get('agent.max_tool_iterations', 15)
        tool_iterations = 0

        while tool_iterations < max_tool_iterations:
            tool_result = await self._parse_and_execute_tool(response)

            if not tool_result:
                break

            tool_iterations += 1

            if not tool_result.get('success', True):
                error_msg = tool_result.get('error', 'Unknown error')
                tool_summary = json.dumps({
                    'error': error_msg,
                    'suggestion': tool_result.get('suggestion', get_error_suggestion('General', error_msg)),
                    'tool': tool_result.get('tool', 'unknown')
                })
            else:
                tool_summary = json.dumps(tool_result)

            followup_prompt = f"{prompt}\n\nTool Result: {tool_summary}\n\nAnalyze this result and either:\n1. Summarize it clearly for the user, OR\n2. Make another tool call if more information is needed"

            # Check budget before follow-up call
            if not self.model_manager.check_budget(daily_limit):
                response = f"⚠️ Stopping: Approaching token budget limit. Current usage: {self.total_tokens:,} tokens"
                break

            with self.ui.show_thinking() as progress:
                task = progress.add_task("Processing tool result...", total=None)
                response, followup_usage, _ = await self.model_manager.generate(followup_prompt)
                progress.update(task, completed=True)

            self.total_tokens += followup_usage.total_tokens
            self.total_cost += followup_usage.cost

            if tool_result.get('success', True):
                self.ui.display_skill_result(tool_result)

        # Clean response for display (remove raw JSON tool calls)
        display_response = clean_response_for_display(response)

        # Get accessed files for cache invalidation
        accessed_files = self.get_accessed_files()

        self.conversation.add('agent', response, model=model_name, tokens=usage.total_tokens)
        self.conversation_history.append({
            'role': 'agent',
            'content': response,
            'timestamp': datetime.now().isoformat(),
            'model': model_name,
            'tokens': usage.total_tokens
        })

        # Reset file tracking for next task
        self.reset_accessed_files()

        return display_response, usage, accessed_files

    async def process_query_streaming(self, user_input: str):
        """Process query with streaming response and incremental rendering."""
        self.conversation.add('user', user_input)
        self.conversation_history.append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now().isoformat()
        })

        prompt = await self._build_context(user_input)

        try:
            # Show thinking indicator
            self.ui.console.print("[dim]⠋ Thinking...[/dim]", end="\r")
            
            # Start streaming with incremental rendering
            full_response = ""
            usage = None
            
            if STREAMING_RENDERER_AVAILABLE:
                # Use streaming renderer for flicker-free display
                renderer = StreamingRenderer(
                    console=self.ui.console,
                    buffer_size=5,
                    render_interval=0.05,
                    show_thinking=True
                )
                
                async def token_stream():
                    """Generator that yields tokens and tracks usage."""
                    nonlocal usage
                    async for token, current_usage in self.model_manager.generate_stream(prompt):
                        usage = current_usage
                        yield token
                
                full_response = await renderer.render_stream(token_stream())
            else:
                # Fallback to basic streaming
                async for token, current_usage in self.model_manager.generate_stream(prompt):
                    full_response += token
                    usage = current_usage

            usage = usage or TokenUsage()
            self.total_tokens += usage.total_tokens
            self.total_cost += usage.cost
            
            # Clear thinking indicator
            self.ui.console.print(" " * 40, end="\r")

        except Exception as e:
            # Clear thinking indicator
            self.ui.console.print(" " * 40, end="\r")
            error_msg = str(e)
            suggestion = get_error_suggestion('API', error_msg)
            self.conversation.add('agent', f"Error: {error_msg}\n\n💡 Suggestion: {suggestion}")
            return f"Error: {error_msg}\n\n💡 Suggestion: {suggestion}", usage

        # Handle tool calls
        max_tool_iterations = self.config.get('agent.max_tool_iterations', 15)
        tool_iterations = 0

        while tool_iterations < max_tool_iterations:
            tool_result = await self._parse_and_execute_tool(full_response)

            if not tool_result:
                break

            tool_iterations += 1

            if not tool_result.get('success', True):
                error_msg = tool_result.get('error', 'Unknown error')
                tool_summary = json.dumps({
                    'error': error_msg,
                    'suggestion': tool_result.get('suggestion', get_error_suggestion('General', error_msg)),
                    'tool': tool_result.get('tool', 'unknown')
                })
            else:
                tool_summary = json.dumps(tool_result)

            followup_prompt = f"{prompt}\n\nTool Result: {tool_summary}\n\nAnalyze this result and either:\n1. Summarize it clearly for the user, OR\n2. Make another tool call if more information is needed"

            # Stream follow-up response with rendering
            if STREAMING_RENDERER_AVAILABLE:
                renderer = StreamingRenderer(
                    console=self.ui.console,
                    buffer_size=5,
                    render_interval=0.05,
                    show_thinking=False
                )
                
                async def followup_stream():
                    nonlocal usage
                    async for token, current_usage in self.model_manager.generate_stream(followup_prompt):
                        usage = current_usage
                        yield token
                
                full_response = await renderer.render_stream(followup_stream())
            else:
                followup_response = ""
                async for token, current_usage in self.model_manager.generate_stream(followup_prompt):
                    followup_response += token
                    usage = current_usage
                full_response = followup_response

            self.total_tokens += usage.total_tokens
            self.total_cost += usage.cost

            if tool_result.get('success', True):
                self.ui.display_skill_result(tool_result)

        # Clean response for display (remove raw JSON tool calls)
        display_response = clean_response_for_display(full_response)

        # Display final response
        self.conversation.add('agent', full_response, model=self.config.default_model, tokens=usage.total_tokens if usage else 0)
        self.conversation_history.append({
            'role': 'agent',
            'content': full_response,
            'timestamp': datetime.now().isoformat(),
            'model': self.config.default_model,
            'tokens': usage.total_tokens if usage else 0
        })

        usage_dict = {
            'prompt_tokens': usage.prompt_tokens if usage else 0,
            'completion_tokens': usage.completion_tokens if usage else 0,
            'total_tokens': usage.total_tokens if usage else 0,
            'cost': usage.cost if usage else 0
        }
        self.ui.display_message('agent', display_response, usage_dict)

        return display_response, usage

    async def run_interactive(self):
        """Run interactive CLI session"""
        self.ui.display_welcome()

        while self.running:
            try:
                user_input = await self.ui.get_input()
                user_input = user_input.strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ['exit', 'quit']:
                    self.conversation.save()
                    break
                elif user_input.lower() == 'help':
                    self.ui.display_help()
                    continue
                elif user_input.lower() == 'clear':
                    self.ui.clear_screen()
                    continue
                elif user_input.lower() == 'history':
                    for msg in self.conversation.get_recent(10):
                        self.ui.display_message(msg['role'], msg['content'])
                    continue
                
                # Approval mode commands - support both 'mode' and '/mode' syntax
                elif user_input.lower() == 'mode' or user_input.lower() == '/mode':
                    if APPROVAL_AVAILABLE and self.approval_manager:
                        self.ui.display_mode_menu()
                    else:
                        self.ui.display_message('agent', "Approval workflow not available.")
                    continue
                elif user_input.lower().startswith('mode ') or user_input.lower().startswith('/mode '):
                    if APPROVAL_AVAILABLE and self.approval_manager:
                        # Extract mode name (support both 'mode x' and '/mode x')
                        parts = user_input.split()
                        if len(parts) >= 2:
                            mode_str = parts[1].lower()
                            # Use new change_approval_mode method for better feedback
                            success, message = self.ui.change_approval_mode(mode_str)
                            self.ui.display_message('agent', message)
                            if success:
                                # Show inline mode indicator
                                self.ui.display_mode_indicator(self.approval_manager.get_mode(), inline=True)
                    else:
                        self.ui.display_message('agent', "Approval workflow not available.")
                    continue
                
                elif user_input.lower() == 'stats':
                    model_stats = self.model_manager.get_model_stats()
                    token_usage = {'total': self.total_tokens, 'cost': self.total_cost}
                    daily_limit = self.config.get('performance.token_budget', 100000)
                    self.ui.display_stats(model_stats, token_usage, daily_limit)
                    continue
                elif user_input.lower() == 'config':
                    if CONFIG_WIZARD_AVAILABLE:
                        quick_show_config(self.config.config_path)
                    else:
                        self.ui.display_config(self.config._config)
                    continue
                elif user_input.lower() == 'configure':
                    # Launch interactive configuration wizard
                    if CONFIG_WIZARD_AVAILABLE:
                        wizard = ConfigWizard(self.config.config_path)
                        if wizard.run():
                            # Reload config if changes were saved
                            self.config._load_config()
                            self.ui.display_message('agent', "✓ Configuration reloaded")
                    else:
                        self.ui.display_message('agent', "Configuration wizard not available. Edit config file directly.")
                    continue
                elif user_input.lower() == 'budget':
                    # Show token budget dashboard
                    daily_limit = self.config.get('performance.token_budget', 100000)
                    self.ui.display_token_budget(self.total_tokens, daily_limit, self.total_tokens)
                    continue
                elif user_input.lower() == 'cache clear':
                    self.model_manager.clear_cache()
                    self.ui.display_message('agent', "✓ Response cache cleared")
                    continue
                elif user_input.lower() == 'context':
                    # Show context optimization status
                    if self.context_manager.current_context:
                        ctx = self.context_manager.current_context
                        self.ui.display_message('agent', 
                            f"**Context Optimization Status**\n\n"
                            f"- **Symbols**: {len(ctx.symbols)}\n"
                            f"- **Tokens**: {ctx.total_tokens}/{self.context_manager.token_budget}\n"
                            f"- **Budget Used**: {ctx.budget_used*100:.1f}%\n"
                            f"- **Symbols**: {', '.join(ctx.symbols[:10])}{'...' if len(ctx.symbols) > 10 else ''}")
                    else:
                        self.ui.display_message('agent', "No optimized context built yet. Ask a question about a specific file.")
                    continue
                elif user_input.lower() == 'thrashing check':
                    # Check for context thrashing
                    if self.context_manager.thrash_prevention.detect_thrashing():
                        self.ui.display_message('agent', 
                            "⚠️ **Context thrashing detected!**\n\n"
                            "The context is changing too much between turns. "
                            "Automatically stabilizing...\n\n"
                            "💡 Tip: Try to focus on one file or function at a time.")
                        if self.context_manager.current_context:
                            self.context_manager.thrash_prevention.stabilize_context(
                                self.context_manager.current_context
                            )
                    else:
                        self.ui.display_message('agent', "✓ **Context stable** - No thrashing detected")
                    continue
                elif user_input.lower().startswith('export'):
                    parts = user_input.split()
                    format = parts[1] if len(parts) > 1 else 'markdown'
                    exported = self.conversation.export(format)
                    print(exported)
                    continue
                elif user_input.lower().startswith('model list'):
                    models = list(self.model_manager.models.keys())
                    self.ui.display_message('agent', f"Available models: {', '.join(models)}")
                    continue
                elif user_input.lower().startswith('model switch'):
                    parts = user_input.split()
                    if len(parts) >= 3:
                        model_name = parts[2]
                        try:
                            self.model_manager.switch_model(model_name)
                            self.ui.display_message('agent', f"✓ Switched to {model_name}")
                        except ValueError as e:
                            self.ui.display_message('agent', f"✗ {str(e)}")
                    continue
                elif user_input.lower().startswith('model stats'):
                    model_stats = self.model_manager.get_model_stats()
                    self.ui.display_stats(model_stats, {'total': 0, 'cost': 0})
                    continue
                elif user_input.lower().startswith('skills list'):
                    skills = self.skill_manager.list_skills()
                    self.ui.display_message('agent', f"Available skills: {', '.join(skills)}")
                    continue
                elif user_input.lower().startswith('skills info'):
                    parts = user_input.split()
                    if len(parts) >= 3:
                        skill_name = parts[2]
                        info = self.skill_manager.get_skill_info(skill_name)
                        self.ui.display_message('agent', json.dumps(info, indent=2))
                    continue

                # SubAgents commands
                elif user_input.lower().startswith('subagents'):
                    sub_result = await self._handle_subagent_command(user_input)
                    if sub_result:
                        self.ui.display_message('agent', sub_result)
                    continue

                # Process regular query
                self.ui.display_message('user', user_input)

                response, usage = await self.process_query(user_input)

                usage_dict = {
                    'prompt_tokens': usage.prompt_tokens,
                    'completion_tokens': usage.completion_tokens,
                    'total_tokens': usage.total_tokens,
                    'cost': usage.cost
                }
                self.ui.display_message('agent', response, usage_dict)

            except KeyboardInterrupt:
                self.conversation.save()
                break
            except Exception as e:
                self.ui.display_message('agent', f"Error: {str(e)}\n\n💡 {get_error_suggestion('General', str(e))}")

        self.ui.display_message('agent', "👋 Goodbye! Thanks for using RapidWebs Agent.")

    async def run_single_query(self, query: str, model: Optional[str] = None):
        """Run a single query and exit"""
        self.ui.display_message('user', query)

        response, usage = await self.process_query(query)

        usage_dict = {
            'prompt_tokens': usage.prompt_tokens,
            'completion_tokens': usage.completion_tokens,
            'total_tokens': usage.total_tokens,
            'cost': usage.cost
        }
        self.ui.display_message('agent', response, usage_dict)

        model_stats = self.model_manager.get_model_stats()
        token_usage = {'total': self.total_tokens, 'cost': self.total_cost}
        self.ui.display_stats(model_stats, token_usage)
        
        self.conversation.save()

    async def run_single_query_streaming(self, query: str, model: Optional[str] = None):
        """Run a single query with streaming response - NEW FEATURE"""
        self.ui.display_message('user', query)
        await self.process_query_streaming(query)
        model_stats = self.model_manager.get_model_stats()
        token_usage = {'total': self.total_tokens, 'cost': self.total_cost}
        self.ui.display_stats(model_stats, token_usage)
        self.conversation.save()

    async def run(self, query: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Run a single query and return result as dict for CLI integration.

        Args:
            query: User query/task description
            model: Optional model override

        Returns:
            Dict with 'output', 'tokens_used', 'success', 'accessed_files' keys
        """
        try:
            # Override model if specified
            if model:
                self.model_manager.switch_model(model)

            # Process query (now returns accessed files)
            response, usage, accessed_files = await self.process_query(query)

            # Update totals
            if usage:
                self.total_tokens += usage.total_tokens
                self.total_cost += usage.cost

            return {
                'output': response,
                'tokens_used': usage.total_tokens if usage else 0,
                'cost': usage.cost if usage else 0.0,
                'success': True,
                'accessed_files': accessed_files
            }

        except Exception as e:
            return {
                'output': f"Error: {str(e)}",
                'tokens_used': 0,
                'cost': 0.0,
                'success': False,
                'error': str(e)
            }


async def cleanup(agent: Agent):
    """Cleanup resources"""
    agent.cleanup()  # Stop auto-save and save conversation
    await agent.model_manager.close()
    await agent.skill_manager.close()


def main():
    """Main entry point"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="RapidWebs Agentic CLI")
    parser.add_argument('--query', '-q', type=str, help="Single query to execute")
    parser.add_argument('--model', '-m', type=str, help="Model to use (overrides config)")
    parser.add_argument('--config', '-c', type=str, help="Path to config file")
    parser.add_argument('--version', '-v', action='store_true', help="Show version")
    parser.add_argument('--stream', '-s', action='store_true', help="Stream response tokens")
    parser.add_argument('--eval', action='store_true', help="Output executable commands (for shell evaluation)")
    
    args = parser.parse_args()

    if args.version:
        from . import __version__
        print(f"RapidWebs Agent v{__version__}")
        return

    # Handle stdin/pipe input
    stdin_content = ""
    if not sys.stdin.isatty():
        stdin_content = sys.stdin.read().strip()
        if stdin_content and args.query:
            args.query = f"{stdin_content}\n\n{args.query}"
        elif stdin_content:
            args.query = stdin_content

    agent = Agent(config_path=args.config)

    if not agent.config.validate():
        print("❌ Configuration error: Please check your config file and API keys")
        print(f"   Config path: {agent.config.config_path}")
        print(f"\n💡 Tip: Set API keys via environment variables:")
        print(f"   export RW_QWEN_API_KEY=your_key_here")
        print(f"   export RW_GEMINI_API_KEY=your_key_here")
        return

    try:
        if args.query:
            if args.eval:
                # Eval mode - output commands directly
                result = asyncio.run(agent.run_single_query(args.query, args.model))
                return
            
            if args.stream:
                # Streaming mode
                asyncio.run(agent.run_single_query_streaming(args.query, args.model))
            else:
                asyncio.run(agent.run_single_query(args.query, args.model))
        else:
            asyncio.run(agent.run_interactive())
    finally:
        asyncio.run(cleanup(agent))

if __name__ == "__main__":
    main()
