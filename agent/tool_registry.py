"""Tool registry with conflict resolution and status tracking.

This module provides centralized tool registration with:
- Automatic name conflict detection and resolution
- Server prefixing for MCP tools
- Include/exclude filtering
- Status tracking (registered, connected, disconnected, error)
"""

from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

from .logging_config import get_logger

logger = get_logger('tool_registry')


class ToolStatus(Enum):
    """Tool status enumeration."""
    REGISTERED = "registered"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class ToolInfo:
    """Information about a registered tool.
    
    Attributes:
        name: Final registered name (may be prefixed for conflicts)
        original_name: Original name before conflict resolution
        server: MCP server name (None for builtin tools)
        status: Current tool status
        schema: Tool schema dictionary
        risk_level: Risk classification (read, write, danger)
        enabled: Whether tool is enabled
    """
    name: str
    original_name: str
    server: Optional[str] = None
    status: ToolStatus = ToolStatus.REGISTERED
    schema: Dict = field(default_factory=dict)
    risk_level: str = "read"
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'original_name': self.original_name,
            'server': self.server,
            'status': self.status.value,
            'schema': self.schema,
            'risk_level': self.risk_level,
            'enabled': self.enabled
        }


class ToolRegistry:
    """Centralized tool registry with conflict resolution.
    
    Features:
    - Automatic name conflict detection
    - Server prefixing for external tools
    - Include/exclude filtering
    - Status tracking
    
    Example:
        registry = ToolRegistry()
        registry.register('fs', FileSystemSkill(config), risk_level='read')
        registry.register('read_file', mcp_tool, server='filesystem_mcp')
        # If conflict, mcp_tool becomes 'filesystem_mcp__read_file'
    """
    
    def __init__(self):
        """Initialize tool registry."""
        self.tools: Dict[str, ToolInfo] = {}
        self.skill_instances: Dict[str, Any] = {}
        self._name_history: Set[str] = set()
        self.logger = get_logger('tool_registry')
    
    def register(
        self,
        name: str,
        skill: Any,
        server: Optional[str] = None,
        schema: Optional[Dict] = None,
        risk_level: str = "read",
        include_tools: Optional[List[str]] = None,
        exclude_tools: Optional[List[str]] = None
    ) -> Optional[str]:
        """Register a tool with automatic conflict resolution.
        
        Args:
            name: Tool name
            skill: Skill instance
            server: MCP server name (None for builtin)
            schema: Tool schema
            risk_level: Risk classification
            include_tools: Allowlist (only for MCP)
            exclude_tools: Denylist (takes precedence)
            
        Returns:
            Final registered name, or None if excluded
        """
        # Check exclusions first
        if exclude_tools and name in exclude_tools:
            self.logger.debug(f"Tool {name} excluded by configuration")
            return None
        
        # Check inclusions
        if include_tools and name not in include_tools:
            self.logger.debug(f"Tool {name} not in include list")
            return None
        
        # Handle conflicts
        final_name = self._resolve_conflict(name, server)
        
        # Register tool
        self.tools[final_name] = ToolInfo(
            name=final_name,
            original_name=name,
            server=server,
            schema=schema or {},
            risk_level=risk_level
        )
        self.skill_instances[final_name] = skill
        self._name_history.add(final_name)
        
        self.logger.info(
            f"Registered tool: {final_name}" +
            (f" (from server {server})" if server else "")
        )
        
        return final_name
    
    def _resolve_conflict(self, name: str, server: Optional[str]) -> str:
        """Resolve name conflicts with automatic prefixing.
        
        Strategy:
        1. If no conflict, use original name
        2. If conflict and has server, prefix with server__name
        3. If conflict and no server, add numeric suffix name__2
        
        Args:
            name: Original tool name
            server: MCP server name (if applicable)
            
        Returns:
            Resolved name (may be prefixed)
        """
        if name not in self._name_history:
            return name
        
        # Has server - prefix with server name
        if server:
            prefixed = f"{server}__{name}"
            if prefixed not in self._name_history:
                return prefixed
            
            # Still conflicts - add counter
            counter = 2
            while f"{server}__{name}__{counter}" in self._name_history:
                counter += 1
            return f"{server}__{name}__{counter}"
        
        # No server - add numeric suffix
        counter = 2
        while f"{name}__{counter}" in self._name_history:
            counter += 1
        return f"{name}__{counter}"
    
    def get(self, name: str) -> Optional[Any]:
        """Get skill instance by name.
        
        Args:
            name: Tool name
            
        Returns:
            Skill instance or None
        """
        return self.skill_instances.get(name)
    
    def get_tool_info(self, name: str) -> Optional[ToolInfo]:
        """Get tool metadata.
        
        Args:
            name: Tool name
            
        Returns:
            Tool info or None
        """
        return self.tools.get(name)
    
    def list_tools(self, server: Optional[str] = None) -> List[ToolInfo]:
        """List all registered tools, optionally filtered by server.
        
        Args:
            server: Filter by server name (None for all)
            
        Returns:
            List of tool info
        """
        if server:
            return [t for t in self.tools.values() if t.server == server]
        return list(self.tools.values())
    
    def update_status(self, name: str, status: ToolStatus):
        """Update tool status.
        
        Args:
            name: Tool name
            status: New status
        """
        if name in self.tools:
            self.tools[name].status = status
            self.logger.debug(f"Updated status for {name}: {status.value}")
    
    def unregister(self, name: str) -> bool:
        """Unregister a tool.
        
        Args:
            name: Tool name
            
        Returns:
            True if unregistered, False if not found
        """
        if name in self.tools:
            del self.tools[name]
            del self.skill_instances[name]
            self._name_history.discard(name)
            self.logger.info(f"Unregistered tool: {name}")
            return True
        return False
    
    def enable_tool(self, name: str) -> bool:
        """Enable a tool.
        
        Args:
            name: Tool name
            
        Returns:
            True if enabled, False if not found
        """
        if name in self.tools:
            self.tools[name].enabled = True
            return True
        return False
    
    def disable_tool(self, name: str) -> bool:
        """Disable a tool.
        
        Args:
            name: Tool name
            
        Returns:
            True if disabled, False if not found
        """
        if name in self.tools:
            self.tools[name].enabled = False
            return True
        return False
    
    def has_tool(self, name: str) -> bool:
        """Check if tool is registered.
        
        Args:
            name: Tool name
            
        Returns:
            True if registered
        """
        return name in self.tools
    
    def get_all_tools(self) -> Dict[str, ToolInfo]:
        """Get all registered tools.
        
        Returns:
            Dictionary of tool name to info
        """
        return self.tools.copy()
    
    def clear(self):
        """Clear all registered tools."""
        self.tools.clear()
        self.skill_instances.clear()
        self._name_history.clear()
        self.logger.info("Cleared all registered tools")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics.
        
        Returns:
            Statistics dictionary
        """
        by_server: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        by_risk: Dict[str, int] = {}
        
        for tool in self.tools.values():
            # By server
            server = tool.server or 'builtin'
            by_server[server] = by_server.get(server, 0) + 1
            
            # By status
            status = tool.status.value
            by_status[status] = by_status.get(status, 0) + 1
            
            # By risk
            risk = tool.risk_level
            by_risk[risk] = by_risk.get(risk, 0) + 1
        
        return {
            'total': len(self.tools),
            'by_server': by_server,
            'by_status': by_status,
            'by_risk': by_risk,
            'enabled': sum(1 for t in self.tools.values() if t.enabled),
            'disabled': sum(1 for t in self.tools.values() if not t.enabled)
        }
