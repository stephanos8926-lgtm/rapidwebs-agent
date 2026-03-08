"""SubAgents system for parallel task delegation.

This package provides a subagent architecture for delegating specialized
tasks to isolated agents with parallel execution support.

Example:
    >>> from agent.subagents import SubAgentOrchestrator, SubAgentTask, SubAgentType
    >>> 
    >>> # Create orchestrator
    >>> orchestrator = SubAgentOrchestrator(max_concurrent=3)
    >>> orchestrator.register_default_agents()
    >>> 
    >>> # Create tasks
    >>> tasks = [
    ...     SubAgentTask.create(SubAgentType.CODE, "Refactor main.py"),
    ...     SubAgentTask.create(SubAgentType.TEST, "Write tests for main.py"),
    ...     SubAgentTask.create(SubAgentType.DOCS, "Document main.py API")
    ... ]
    >>> 
    >>> # Execute in parallel
    >>> results = await orchestrator.execute_parallel(tasks)
    >>> 
    >>> # Get combined output
    >>> output = orchestrator.get_combined_output()
    >>> print(output)
"""

from .protocol import (
    SubAgentTask,
    SubAgentResult,
    SubAgentStatus,
    SubAgentType,
    SubAgentProtocol,
    SubAgentConfig,
    SubAgentRegistry,
    DEFAULT_CODE_AGENT_CONFIG,
    DEFAULT_TEST_AGENT_CONFIG,
    DEFAULT_DOCS_AGENT_CONFIG,
    DEFAULT_RESEARCH_AGENT_CONFIG,
    DEFAULT_SECURITY_AGENT_CONFIG,
)

from .orchestrator import (
    SubAgentOrchestrator,
    TaskGraph,
    ResultAggregator,
    ConflictResolver,
)

from .code_agent import CodeAgent
from .test_agent import TestAgent
from .docs_agent import DocsAgent
from .research_agent import ResearchAgent
from .security_agent import SecurityAgent

__all__ = [
    # Protocol
    'SubAgentTask',
    'SubAgentResult',
    'SubAgentStatus',
    'SubAgentType',
    'SubAgentProtocol',
    'SubAgentConfig',
    'SubAgentRegistry',
    # Default configs
    'DEFAULT_CODE_AGENT_CONFIG',
    'DEFAULT_TEST_AGENT_CONFIG',
    'DEFAULT_DOCS_AGENT_CONFIG',
    'DEFAULT_RESEARCH_AGENT_CONFIG',
    'DEFAULT_SECURITY_AGENT_CONFIG',
    # Orchestrator
    'SubAgentOrchestrator',
    'TaskGraph',
    'ResultAggregator',
    'ConflictResolver',
    # Built-in agents
    'CodeAgent',
    'TestAgent',
    'DocsAgent',
    'ResearchAgent',
    'SecurityAgent',
]

# Convenience function for quick setup


def create_orchestrator(max_concurrent: int = 3,
                        register_defaults: bool = True) -> SubAgentOrchestrator:
    """Create and optionally configure a subagent orchestrator.
    
    Args:
        max_concurrent: Maximum concurrent subagent tasks
        register_defaults: Whether to register default agents
        
    Returns:
        Configured SubAgentOrchestrator instance
    """
    orchestrator = SubAgentOrchestrator(max_concurrent=max_concurrent)
    
    if register_defaults:
        orchestrator.register_default_agents()
    
    return orchestrator
