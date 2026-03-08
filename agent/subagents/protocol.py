"""SubAgent task delegation protocol.

This module defines the protocol for delegating tasks to specialized subagents
with isolated contexts, parallel execution support, and result aggregation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, TYPE_CHECKING
from pathlib import Path
import time
import uuid
from abc import ABC, abstractmethod

# Conditional import to avoid circular dependency
if TYPE_CHECKING:
    from ..models import ModelManager


class SubAgentStatus(Enum):
    """Status of a subagent task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class SubAgentType(Enum):
    """Type of specialized subagent."""
    CODE = "code"
    TEST = "test"
    DOCS = "docs"
    RESEARCH = "research"
    SECURITY = "security"
    GENERIC = "generic"


@dataclass
class SubAgentTask:
    """Task to be delegated to a subagent.
    
    Attributes:
        id: Unique task identifier
        type: Type of subagent needed
        description: Human-readable task description
        context: Task-specific context and parameters
        token_budget: Maximum tokens allowed for this task
        timeout: Maximum execution time in seconds
        priority: Task priority (1=highest, 5=lowest)
        dependencies: List of task IDs this task depends on
        created_at: Task creation timestamp
    """
    id: str
    type: SubAgentType
    description: str
    context: Dict[str, Any]
    token_budget: int = 10000
    timeout: int = 300
    priority: int = 3
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    
    @classmethod
    def create(cls, type: SubAgentType, description: str, 
               context: Dict[str, Any] = None, **kwargs) -> 'SubAgentTask':
        """Create a new task with auto-generated ID.
        
        Args:
            type: Type of subagent needed
            description: Task description
            context: Task context
            **kwargs: Additional task parameters
            
        Returns:
            New SubAgentTask instance
        """
        return cls(
            id=str(uuid.uuid4())[:8],
            type=type,
            description=description,
            context=context or {},
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            'id': self.id,
            'type': self.type.value,
            'description': self.description,
            'context': self.context,
            'token_budget': self.token_budget,
            'timeout': self.timeout,
            'priority': self.priority,
            'dependencies': self.dependencies,
            'created_at': self.created_at
        }


@dataclass
class SubAgentResult:
    """Result from a subagent task execution.
    
    Attributes:
        task_id: ID of the completed task
        status: Final status of the task
        output: Task output/content
        token_usage: Actual tokens used
        duration: Execution time in seconds
        error: Error message if failed
        metadata: Additional result metadata
        files_modified: List of files modified by the task
    """
    task_id: str
    status: SubAgentStatus
    output: str
    token_usage: int = 0
    duration: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    files_modified: List[str] = field(default_factory=list)
    
    def success(self) -> bool:
        """Check if task completed successfully."""
        return self.status == SubAgentStatus.COMPLETED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'task_id': self.task_id,
            'status': self.status.value,
            'output': self.output,
            'token_usage': self.token_usage,
            'duration': round(self.duration, 2),
            'error': self.error,
            'metadata': self.metadata,
            'files_modified': self.files_modified
        }


@dataclass
class SubAgentConfig:
    """Configuration for a subagent.
    
    Attributes:
        type: Type of subagent
        enabled: Whether this subagent is enabled
        max_token_budget: Maximum tokens per task
        max_timeout: Maximum execution time
        allowed_tools: List of allowed tool names
        parallel_limit: Maximum concurrent tasks of this type
        lsp_integration: Enable LSP integration
    """
    type: SubAgentType
    enabled: bool = True
    max_token_budget: int = 20000
    max_timeout: int = 600
    allowed_tools: List[str] = field(default_factory=list)
    parallel_limit: int = 2
    lsp_integration: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'type': self.type.value,
            'enabled': self.enabled,
            'max_token_budget': self.max_token_budget,
            'max_timeout': self.max_timeout,
            'allowed_tools': self.allowed_tools,
            'parallel_limit': self.parallel_limit,
            'lsp_integration': self.lsp_integration
        }


class SubAgentProtocol(ABC):
    """Protocol for subagent communication and task execution.

    This class defines the interface that all subagents must implement.
    """

    def __init__(self, config: SubAgentConfig, model_manager: Any = None):
        """Initialize subagent protocol.

        Args:
            config: Subagent configuration
            model_manager: Optional ModelManager for LLM integration
        """
        self.config = config
        self.type = config.type
        self.enabled = config.enabled
        self.model_manager = model_manager
        self._token_usage = 0
    
    def set_model_manager(self, model_manager: Any):
        """Set model manager for LLM integration.
        
        Args:
            model_manager: ModelManager instance from agent.core
        """
        self.model_manager = model_manager
    
    async def _call_llm(self, prompt: str, system_prompt: str = None) -> tuple[str, int]:
        """Call LLM with prompt and return response with token usage.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            Tuple of (response_text, token_usage)
            
        Raises:
            RuntimeError: If model_manager not configured
        """
        if not self.model_manager:
            raise RuntimeError("ModelManager not configured. Call set_model_manager() first.")
        
        # Build full prompt with system message
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt
        
        # Generate response
        response, usage, _ = await self.model_manager.generate(full_prompt)
        
        # Track token usage
        tokens_used = usage.total_tokens if hasattr(usage, 'total_tokens') else 0
        self._token_usage += tokens_used
        
        return response, tokens_used
    
    def reset_token_usage(self):
        """Reset token usage counter for this agent."""
        self._token_usage = 0
    
    def get_token_usage(self) -> int:
        """Get total token usage for this agent.
        
        Returns:
            Total tokens used
        """
        return self._token_usage

    @abstractmethod
    async def execute(self, task: SubAgentTask) -> SubAgentResult:
        """Execute a task.

        Args:
            task: Task to execute

        Returns:
            Task execution result
        """

    def validate_task(self, task: SubAgentTask) -> tuple[bool, Optional[str]]:
        """Validate a task before execution.
        
        Args:
            task: Task to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.enabled:
            return False, f"SubAgent type {self.type.value} is disabled"
        
        if task.token_budget > self.config.max_token_budget:
            return False, f"Token budget exceeds limit ({task.token_budget} > {self.config.max_token_budget})"
        
        if task.timeout > self.config.max_timeout:
            return False, f"Timeout exceeds limit ({task.timeout} > {self.config.max_timeout})"
        
        return True, None
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get subagent capabilities.
        
        Returns:
            Dictionary describing capabilities
        """
        return {
            'type': self.type.value,
            'enabled': self.enabled,
            'max_token_budget': self.config.max_token_budget,
            'max_timeout': self.config.max_timeout,
            'allowed_tools': self.config.allowed_tools,
            'parallel_limit': self.config.parallel_limit
        }


class SubAgentRegistry:
    """Registry for subagent types and instances.
    
    This class manages subagent registration and lookup.
    """
    
    def __init__(self):
        """Initialize subagent registry."""
        self._protocols: Dict[SubAgentType, SubAgentProtocol] = {}
        self._configs: Dict[SubAgentType, SubAgentConfig] = {}
    
    def register(self, protocol: SubAgentProtocol, config: SubAgentConfig = None):
        """Register a subagent protocol.
        
        Args:
            protocol: SubAgentProtocol instance
            config: Optional config (uses protocol.config if not provided)
        """
        config = config or protocol.config
        self._protocols[config.type] = protocol
        self._configs[config.type] = config
    
    def get_protocol(self, type: SubAgentType) -> Optional[SubAgentProtocol]:
        """Get protocol for subagent type.
        
        Args:
            type: SubAgentType to look up
            
        Returns:
            SubAgentProtocol or None if not registered
        """
        return self._protocols.get(type)
    
    def get_config(self, type: SubAgentType) -> Optional[SubAgentConfig]:
        """Get config for subagent type.
        
        Args:
            type: SubAgentType to look up
            
        Returns:
            SubAgentConfig or None if not registered
        """
        return self._configs.get(type)
    
    def list_available(self) -> List[Dict[str, Any]]:
        """List all available subagents.
        
        Returns:
            List of subagent capability dictionaries
        """
        return [
            protocol.get_capabilities()
            for protocol in self._protocols.values()
        ]
    
    def is_available(self, type: SubAgentType) -> bool:
        """Check if subagent type is available.
        
        Args:
            type: SubAgentType to check
            
        Returns:
            True if available and enabled
        """
        protocol = self._protocols.get(type)
        return protocol is not None and protocol.enabled


# Default subagent configurations

DEFAULT_CODE_AGENT_CONFIG = SubAgentConfig(
    type=SubAgentType.CODE,
    enabled=True,
    max_token_budget=20000,
    max_timeout=600,
    allowed_tools=[
        'read_file', 'write_file', 'edit_file', 'run_shell_command',
        'list_directory', 'search_files'
    ],
    parallel_limit=2,
    lsp_integration=True
)

DEFAULT_TEST_AGENT_CONFIG = SubAgentConfig(
    type=SubAgentType.TEST,
    enabled=True,
    max_token_budget=15000,
    max_timeout=300,
    allowed_tools=[
        'read_file', 'write_file', 'run_shell_command',
        'list_directory'
    ],
    parallel_limit=2,
    lsp_integration=False
)

DEFAULT_DOCS_AGENT_CONFIG = SubAgentConfig(
    type=SubAgentType.DOCS,
    enabled=True,
    max_token_budget=10000,
    max_timeout=300,
    allowed_tools=[
        'read_file', 'write_file', 'list_directory'
    ],
    parallel_limit=3,
    lsp_integration=False
)

DEFAULT_RESEARCH_AGENT_CONFIG = SubAgentConfig(
    type=SubAgentType.RESEARCH,
    enabled=True,
    max_token_budget=15000,
    max_timeout=300,
    allowed_tools=[
        'read_file', 'web_search', 'fetch_url'
    ],
    parallel_limit=2,
    lsp_integration=False
)

DEFAULT_SECURITY_AGENT_CONFIG = SubAgentConfig(
    type=SubAgentType.SECURITY,
    enabled=True,
    max_token_budget=15000,
    max_timeout=300,
    allowed_tools=[
        'read_file', 'search_files', 'run_shell_command'
    ],
    parallel_limit=1,
    lsp_integration=True
)
