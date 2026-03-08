"""Approval workflow management for RapidWebs Agent.

This module provides a comprehensive approval system with multiple modes
(Plan, Default, Auto-Edit, YOLO) and risk-based tool classification.
"""

from enum import Enum
from typing import Dict, Set, Any
from dataclasses import dataclass


class ApprovalMode(Enum):
    """Approval modes for tool execution.
    
    Attributes:
        PLAN: Read-only mode, no tool execution allowed
        DEFAULT: Confirm all write/destructive operations
        AUTO_EDIT: Auto-accept edits, confirm destructive operations
        YOLO: No confirmations, full automation
    """
    PLAN = "plan"
    DEFAULT = "default"
    AUTO_EDIT = "auto_edit"
    YOLO = "yolo"


class RiskLevel(Enum):
    """Risk level classification for tool operations.
    
    Attributes:
        READ: Safe operations (read, list, explore, search)
        WRITE: Medium risk operations (write, edit, create)
        DESTRUCTIVE: High risk operations (delete, execute commands)
    """
    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "danger"


@dataclass
class ToolApproval:
    """Tool approval configuration.
    
    Attributes:
        risk_level: The risk level of the tool operation
        requires_approval: Mapping of approval modes to approval requirements
        description: Human-readable description of the tool operation
    """
    risk_level: RiskLevel
    requires_approval: Dict[ApprovalMode, bool]
    description: str = ""


class ApprovalManager:
    """Manage tool approval workflow.
    
    The ApprovalManager handles:
    - Tool risk level classification
    - Approval mode management
    - Session-level auto-accept/reject tracking
    - Approval requirement determination
    
    Attributes:
        mode: Current approval mode
        auto_accept_tools: Set of tool keys user said "always" for
        auto_reject_tools: Set of tool keys user said "never" for
    """
    
    def __init__(self, config: Any):
        """Initialize approval manager.
        
        Args:
            config: Configuration object with approval settings
        """
        self.config = config
        self.mode = self._load_initial_mode()
        self.auto_accept_tools: Set[str] = set()
        self.auto_reject_tools: Set[str] = set()
        
        # Tool risk mapping
        self.tool_risk_map = self._build_tool_risk_map()
    
    def _load_initial_mode(self) -> ApprovalMode:
        """Load initial approval mode from config.
        
        Returns:
            ApprovalMode from config or DEFAULT if not specified
        """
        mode_str = self.config.get('agent.default_approval_mode', 'default')
        try:
            return ApprovalMode(mode_str)
        except ValueError:
            return ApprovalMode.DEFAULT
    
    def _build_tool_risk_map(self) -> Dict[str, ToolApproval]:
        """Build tool risk level mapping.
        
        Returns:
            Dictionary mapping tool keys to ToolApproval configurations
        """
        # Define approval requirements for each mode
        # Format: {ApprovalMode: requires_approval}
        
        read_approval = {
            ApprovalMode.PLAN: False,
            ApprovalMode.DEFAULT: False,
            ApprovalMode.AUTO_EDIT: False,
            ApprovalMode.YOLO: False
        }
        
        write_approval = {
            ApprovalMode.PLAN: True,
            ApprovalMode.DEFAULT: True,
            ApprovalMode.AUTO_EDIT: False,
            ApprovalMode.YOLO: False
        }
        
        destructive_approval = {
            ApprovalMode.PLAN: True,
            ApprovalMode.DEFAULT: True,
            ApprovalMode.AUTO_EDIT: True,
            ApprovalMode.YOLO: False
        }
        
        return {
            # Filesystem operations
            'fs_read': ToolApproval(
                risk_level=RiskLevel.READ,
                requires_approval=read_approval,
                description="Read file contents"
            ),
            'fs_list': ToolApproval(
                risk_level=RiskLevel.READ,
                requires_approval=read_approval,
                description="List directory contents"
            ),
            'fs_explore': ToolApproval(
                risk_level=RiskLevel.READ,
                requires_approval=read_approval,
                description="Explore directory structure"
            ),
            'fs_write': ToolApproval(
                risk_level=RiskLevel.WRITE,
                requires_approval=write_approval,
                description="Write content to file"
            ),
            'fs_delete': ToolApproval(
                risk_level=RiskLevel.DESTRUCTIVE,
                requires_approval=destructive_approval,
                description="Delete file"
            ),
            
            # Terminal operations
            'terminal': ToolApproval(
                risk_level=RiskLevel.DESTRUCTIVE,
                requires_approval=destructive_approval,
                description="Execute terminal command"
            ),
            
            # Web operations
            'web': ToolApproval(
                risk_level=RiskLevel.READ,
                requires_approval=read_approval,
                description="Scrape web content"
            ),
            
            # LSP operations
            'lsp_check': ToolApproval(
                risk_level=RiskLevel.READ,
                requires_approval=read_approval,
                description="Check code with linter"
            ),
            'lsp_format': ToolApproval(
                risk_level=RiskLevel.WRITE,
                requires_approval=write_approval,
                description="Format code"
            ),
            'lsp_fix': ToolApproval(
                risk_level=RiskLevel.WRITE,
                requires_approval=write_approval,
                description="Fix code issues"
            ),
            
            # Search operations
            'search': ToolApproval(
                risk_level=RiskLevel.READ,
                requires_approval=read_approval,
                description="Search codebase"
            ),
            
            # Code tools operations
            'code_tools_lint': ToolApproval(
                risk_level=RiskLevel.READ,
                requires_approval=read_approval,
                description="Lint code"
            ),
            'code_tools_format': ToolApproval(
                risk_level=RiskLevel.WRITE,
                requires_approval=write_approval,
                description="Format code with code tools"
            ),
        }
    
    def _get_tool_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Generate a tool key for approval tracking.
        
        Args:
            tool_name: Name of the tool
            params: Tool parameters
            
        Returns:
            Tool key string in format "tool_operation" or "tool_risk"
        """
        # Special handling for fs tool based on operation
        if tool_name == 'fs':
            operation = params.get('operation', 'read')
            return f"fs_{operation}"
        
        # Special handling for lsp tool based on action
        if tool_name == 'lsp':
            action = params.get('action', 'check')
            return f"lsp_{action}"
        
        # Special handling for search tool
        if tool_name == 'search':
            return 'search'
        
        # Special handling for code_tools
        if tool_name == 'code_tools':
            action = params.get('action', 'lint')
            return f"code_tools_{action}"
        
        # Default: use tool name
        return tool_name
    
    def get_tool_risk(self, tool_name: str, params: Dict[str, Any]) -> RiskLevel:
        """Determine risk level for a tool call.
        
        Args:
            tool_name: Name of the tool
            params: Tool parameters
            
        Returns:
            RiskLevel for the tool operation
        """
        tool_key = self._get_tool_key(tool_name, params)
        
        # Check if we have a specific mapping
        if tool_key in self.tool_risk_map:
            return self.tool_risk_map[tool_key].risk_level
        
        # Default risk levels for unknown tools
        if tool_name in ['fs', 'lsp', 'code_tools']:
            # These have operation-based risk
            operation = params.get('operation', params.get('action', 'read'))
            if operation in ['delete', 'remove']:
                return RiskLevel.DESTRUCTIVE
            elif operation in ['write', 'edit', 'create', 'format', 'fix']:
                return RiskLevel.WRITE
            else:
                return RiskLevel.READ
        
        if tool_name == 'terminal':
            return RiskLevel.DESTRUCTIVE
        
        # Default to READ for unknown tools
        return RiskLevel.READ
    
    def requires_approval(self, tool_name: str, params: Dict[str, Any]) -> bool:
        """Check if tool execution requires user approval.
        
        Args:
            tool_name: Name of the tool
            params: Tool parameters
            
        Returns:
            True if approval is required, False otherwise
        """
        # YOLO mode never requires approval
        if self.mode == ApprovalMode.YOLO:
            return False
        
        # PLAN mode requires approval for all non-read operations
        if self.mode == ApprovalMode.PLAN:
            risk = self.get_tool_risk(tool_name, params)
            # Allow read operations in PLAN mode
            if risk == RiskLevel.READ:
                return False
            # Block all write/destructive operations in PLAN mode
            return True
        
        tool_key = self._get_tool_key(tool_name, params)
        
        # Check auto-accept list first
        if tool_key in self.auto_accept_tools:
            return False
        
        # Check auto-reject list
        if tool_key in self.auto_reject_tools:
            return True
        
        # Check mode requirements from tool risk map
        approval = self.tool_risk_map.get(tool_key)
        if approval:
            return approval.requires_approval[self.mode]
        
        # Default behavior for unknown tools
        risk = self.get_tool_risk(tool_name, params)
        if risk == RiskLevel.READ:
            return False
        elif risk == RiskLevel.WRITE:
            return self.mode == ApprovalMode.DEFAULT
        else:  # DESTRUCTIVE
            return self.mode in [ApprovalMode.DEFAULT, ApprovalMode.AUTO_EDIT]
    
    def mark_auto_accept(self, tool_name: str, params: Dict[str, Any]):
        """Add tool to auto-accept list.
        
        Args:
            tool_name: Name of the tool
            params: Tool parameters
        """
        tool_key = self._get_tool_key(tool_name, params)
        self.auto_accept_tools.add(tool_key)
    
    def mark_auto_reject(self, tool_name: str, params: Dict[str, Any]):
        """Add tool to auto-reject list.
        
        Args:
            tool_name: Name of the tool
            params: Tool parameters
        """
        tool_key = self._get_tool_key(tool_name, params)
        self.auto_reject_tools.add(tool_key)
    
    def set_mode(self, mode_str: str) -> bool:
        """Set approval mode.
        
        Args:
            mode_str: Mode string to set
            
        Returns:
            True if mode was set successfully, False if invalid mode
        """
        try:
            self.mode = ApprovalMode(mode_str.lower().replace('-', '_'))
            return True
        except ValueError:
            return False
    
    def get_mode(self) -> ApprovalMode:
        """Get current approval mode.
        
        Returns:
            Current ApprovalMode
        """
        return self.mode
    
    def get_mode_description(self) -> str:
        """Get human-readable description of current mode.
        
        Returns:
            Description string
        """
        descriptions = {
            ApprovalMode.PLAN: "Read-only mode - Tool execution disabled for write/destructive operations",
            ApprovalMode.DEFAULT: "Default mode - Confirm all write/destructive operations",
            ApprovalMode.AUTO_EDIT: "Auto-edit mode - Auto-accept edits, confirm destructive operations",
            ApprovalMode.YOLO: "YOLO mode - Full automation, no confirmations"
        }
        return descriptions.get(self.mode, "Unknown mode")
    
    def get_auto_accept_count(self) -> int:
        """Get number of tools in auto-accept list.
        
        Returns:
            Count of auto-accepted tools
        """
        return len(self.auto_accept_tools)
    
    def get_auto_reject_count(self) -> int:
        """Get number of tools in auto-reject list.
        
        Returns:
            Count of auto-rejected tools
        """
        return len(self.auto_reject_tools)
    
    def clear_session_state(self):
        """Clear session-level auto-accept/reject lists.

        This should be called when the agent session ends.
        """
        self.auto_accept_tools.clear()
        self.auto_reject_tools.clear()

    def log_mode_change(self, new_mode: str):
        """Log approval mode change for audit trail.
        
        Args:
            new_mode: New mode name string
        """
        from datetime import datetime, timezone
        
        timestamp = datetime.now(timezone.utc).isoformat()
        mode_info = {
            'timestamp': timestamp,
            'mode': new_mode,
            'auto_accept_count': len(self.auto_accept_tools),
            'auto_reject_count': len(self.auto_reject_tools)
        }
        
        # Log to logger if available
        try:
            from .logging_config import get_logger
            logger = get_logger('approval_workflow')
            logger.info(f'Mode changed to {new_mode}: {mode_info}')
        except Exception:
            pass  # Logging not available
