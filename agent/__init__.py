"""RapidWebs Agentic CLI - Cross-platform AI agent for developers

Public API - All exports are stable and backward-compatible.
"""
__version__ = "2.1.0"
__author__ = "Steven @ RapidWebs Enterprise, LLC"

from .agent import Agent
from .config import Config
from .llm_models import ModelManager
from .skills_manager import SkillManager
from .context_manager import (
    ContextManager,
    get_optimized_context,
    get_file_symbols,
    get_symbols_summary,
    suggest_related_files,
)
from .utilities import (
    find_callers,
    find_symbol_definition,
    get_import_graph,
)
from .approval_workflow import (
    ApprovalMode,
    RiskLevel,
    ApprovalManager,
)

# SubAgents system
try:
    from .subagents import (
        SubAgentOrchestrator,
        SubAgentTask,
        SubAgentType,
        SubAgentResult,
        create_orchestrator,
        CodeAgent,
        TestAgent,
        DocsAgent,
        ResearchAgent,
        SecurityAgent,
    )
    SUBAGENTS_AVAILABLE = True
except ImportError:
    SUBAGENTS_AVAILABLE = False
    SubAgentOrchestrator = None
    SubAgentTask = None
    SubAgentType = None
    SubAgentResult = None
    create_orchestrator = None
    CodeAgent = None
    TestAgent = None
    DocsAgent = None
    ResearchAgent = None
    SecurityAgent = None

# Primary public API
__all__ = [
    # Core components
    "Agent",
    "Config",
    "ModelManager",
    "SkillManager",
    "ContextManager",
    # Approval workflow
    "ApprovalMode",
    "RiskLevel",
    "ApprovalManager",
    # Context optimization utilities
    "get_optimized_context",
    "get_file_symbols",
    "get_symbols_summary",
    "suggest_related_files",
    # Code analysis utilities (LSP alternatives)
    "find_callers",
    "find_symbol_definition",
    "get_import_graph",
    # SubAgents system (conditional)
    "SUBAGENTS_AVAILABLE",
]

# Add subagents to __all__ if available
if SUBAGENTS_AVAILABLE:
    __all__.extend([
        "SubAgentOrchestrator",
        "SubAgentTask",
        "SubAgentType",
        "SubAgentResult",
        "create_orchestrator",
        "CodeAgent",
        "TestAgent",
        "DocsAgent",
        "ResearchAgent",
        "SecurityAgent",
    ])

# Backward compatibility aliases (deprecated, use names above)
AgentCore = Agent  # Deprecated: use Agent
__all__.append("AgentCore")
