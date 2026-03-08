"""TODO/Task management skill for RapidWebs Agent.

This module provides comprehensive task tracking with:
- Create, update, list, clear, export operations
- Session-based persistence
- Auto-generation for complex multi-step tasks
- Visual status indicators

Example:
    todo_skill = TodoSkill(config, session_id="session_123")
    await todo_skill.execute('create', description='Fix bug in main.py')
    await todo_skill.execute('update', index=0, status='completed')
    todos = await todo_skill.execute('list')
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from ..skills_manager import SkillBase
from ..logging_config import get_logger

logger = get_logger('todo_skill')


class TodoStatus(Enum):
    """TODO item status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class TodoItem:
    """Individual TODO item.
    
    Attributes:
        description: Task description
        status: Current status
        active_form: Present continuous form (e.g., "Fixing bug")
        created_at: Creation timestamp
        completed_at: Completion timestamp (if completed)
        metadata: Additional metadata
    """
    description: str
    status: str = TodoStatus.PENDING.value
    active_form: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set active_form if not provided."""
        if not self.active_form:
            # Simple heuristic: add "ing" to first verb
            self.active_form = self._generate_active_form(self.description)
    
    def _generate_active_form(self, description: str) -> str:
        """Generate present continuous form from description."""
        # Simple heuristic - can be improved with NLP
        words = description.split()
        if words:
            verb = words[0].rstrip('s')
            if verb.endswith('e'):
                return f"{verb}ing..."
            return f"{verb}ing..."
        return "Working..."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TodoItem':
        """Create from dictionary."""
        return cls(**data)


class TodoSkill(SkillBase):
    """TODO/task management skill.
    
    Operations:
    - create: Add new task (single or multiple)
    - update: Change task status or description
    - list: Show all tasks
    - clear: Remove completed/cancelled tasks
    - export: Save to file
    - import: Load from file
    
    Attributes:
        session_id: Unique session identifier
        todos: List of TODO items
        storage_path: Path to persistence file
    """
    
    STATUS_ICONS = {
        TodoStatus.PENDING: '⏸',
        TodoStatus.IN_PROGRESS: '⏳',
        TodoStatus.COMPLETED: '✓',
        TodoStatus.CANCELLED: '✗'
    }
    
    def __init__(self, config: Any, session_id: Optional[str] = None):
        """Initialize TODO skill.
        
        Args:
            config: Configuration object
            session_id: Unique session identifier (auto-generated if None)
        """
        super().__init__(config, 'todo')
        
        import uuid
        self.session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
        self.todos: List[TodoItem] = []
        self.storage_path = self._get_storage_path()
        self._load()
        
        logger.info(f'TodoSkill initialized for session {self.session_id}')
    
    def _get_storage_path(self) -> Path:
        """Get storage path for TODO list."""
        storage_dir = Path.home() / '.local' / 'share' / 'rapidwebs-agent' / 'todos'
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir / f'{self.session_id}.json'
    
    def _load(self):
        """Load TODOs from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.todos = [TodoItem.from_dict(item) for item in data]
                logger.debug(f'Loaded {len(self.todos)} TODOs from {self.storage_path}')
            except Exception as e:
                logger.warning(f'Failed to load TODOs: {e}')
                self.todos = []
    
    def _save(self):
        """Save TODOs to storage."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump([item.to_dict() for item in self.todos], f, indent=2, ensure_ascii=False)
            logger.debug(f'Saved {len(self.todos)} TODOs to {self.storage_path}')
        except Exception as e:
            logger.error(f'Failed to save TODOs: {e}')
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute TODO operation.
        
        Args:
            action: Operation to perform (create, update, list, clear, export, import)
            **kwargs: Operation-specific parameters
            
        Returns:
            Operation result with success status and data
        """
        actions = {
            'create': self._create,
            'update': self._update,
            'list': self._list,
            'clear': self._clear,
            'export': self._export,
            'import': self._import,
            'stats': self._stats
        }
        
        if action not in actions:
            return {
                'success': False,
                'error': f'Unknown action: {action}. Available: {", ".join(actions.keys())}'
            }
        
        try:
            result = await actions[action](**kwargs)
            return result
        except Exception as e:
            logger.exception(f'TODO action {action} failed: {e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _create(
        self,
        description: Optional[str] = None,
        tasks: Optional[List[Dict[str, Any]]] = None,
        status: str = TodoStatus.PENDING.value,
        active_form: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create TODO item(s).
        
        Args:
            description: Single task description
            tasks: List of task dictionaries for bulk creation
            status: Initial status (default: pending)
            active_form: Present continuous form
            
        Returns:
            Created task(s) information
        """
        created = []
        
        # Single task creation
        if description:
            item = TodoItem(
                description=description,
                status=status,
                active_form=active_form
            )
            self.todos.append(item)
            created.append(item.to_dict())
        
        # Bulk creation
        if tasks:
            for task_data in tasks:
                item = TodoItem(
                    description=task_data.get('description', 'Unnamed task'),
                    status=task_data.get('status', status),
                    active_form=task_data.get('active_form'),
                    metadata=task_data.get('metadata', {})
                )
                self.todos.append(item)
                created.append(item.to_dict())
        
        self._save()
        
        return {
            'success': True,
            'created': len(created),
            'tasks': created,
            'total': len(self.todos)
        }
    
    async def _update(
        self,
        index: Optional[int] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        active_form: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update TODO item.
        
        Args:
            index: Task index (0-based)
            description: New description
            status: New status
            active_form: New active form
            
        Returns:
            Updated task information
        """
        if index is None or index < 0 or index >= len(self.todos):
            return {
                'success': False,
                'error': f'Invalid index: {index}. Valid range: 0-{len(self.todos) - 1}'
            }
        
        item = self.todos[index]
        
        if description:
            item.description = description
        if status:
            item.status = status
            if status == TodoStatus.COMPLETED.value and not item.completed_at:
                item.completed_at = datetime.now().isoformat()
        if active_form:
            item.active_form = active_form
        
        self._save()
        
        return {
            'success': True,
            'task': item.to_dict(),
            'total': len(self.todos)
        }
    
    async def _list(self, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """List TODO items.
        
        Args:
            status_filter: Filter by status (optional)
            
        Returns:
            List of TODO items with statistics
        """
        if status_filter:
            filtered = [t for t in self.todos if t.status == status_filter]
        else:
            filtered = self.todos
        
        return {
            'success': True,
            'tasks': [t.to_dict() for t in filtered],
            'total': len(filtered),
            'summary': self._get_summary()
        }
    
    async def _clear(self, keep_incomplete: bool = False) -> Dict[str, Any]:
        """Clear TODO items.
        
        Args:
            keep_incomplete: If True, only clear completed/cancelled
            
        Returns:
            Clearance information
        """
        if keep_incomplete:
            removed = len([t for t in self.todos if t.status in [TodoStatus.COMPLETED.value, TodoStatus.CANCELLED.value]])
            self.todos = [t for t in self.todos if t.status not in [TodoStatus.COMPLETED.value, TodoStatus.CANCELLED.value]]
        else:
            removed = len(self.todos)
            self.todos = []
        
        self._save()
        
        return {
            'success': True,
            'removed': removed,
            'remaining': len(self.todos)
        }
    
    async def _export(self, filepath: Optional[str] = None, format: str = 'json') -> Dict[str, Any]:
        """Export TODOs to file.
        
        Args:
            filepath: Output file path (default: session file with .export suffix)
            format: Export format (json, markdown, text)
            
        Returns:
            Export information
        """
        if not filepath:
            filepath = str(self.storage_path) + f'.export.{format}'
        
        output_path = Path(filepath)
        
        try:
            if format == 'json':
                content = json.dumps([t.to_dict() for t in self.todos], indent=2, ensure_ascii=False)
            elif format == 'markdown':
                content = self._to_markdown()
            elif format == 'text':
                content = self._to_text()
            else:
                return {
                    'success': False,
                    'error': f'Unknown format: {format}. Available: json, markdown, text'
                }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                'success': True,
                'path': str(output_path),
                'tasks': len(self.todos)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _import(self, filepath: str) -> Dict[str, Any]:
        """Import TODOs from file.
        
        Args:
            filepath: Input file path
            
        Returns:
            Import information
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if filepath.endswith('.json'):
                data = json.loads(content)
                imported = [TodoItem.from_dict(item) for item in data]
            else:
                return {
                    'success': False,
                    'error': 'Only JSON format supported for import'
                }
            
            self.todos.extend(imported)
            self._save()
            
            return {
                'success': True,
                'imported': len(imported),
                'total': len(self.todos)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _stats(self) -> Dict[str, Any]:
        """Get TODO statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            'success': True,
            'stats': self._get_summary()
        }
    
    def _get_summary(self) -> Dict[str, Any]:
        """Get TODO summary statistics."""
        total = len(self.todos)
        by_status = {
            'pending': len([t for t in self.todos if t.status == TodoStatus.PENDING.value]),
            'in_progress': len([t for t in self.todos if t.status == TodoStatus.IN_PROGRESS.value]),
            'completed': len([t for t in self.todos if t.status == TodoStatus.COMPLETED.value]),
            'cancelled': len([t for t in self.todos if t.status == TodoStatus.CANCELLED.value])
        }
        
        return {
            'total': total,
            'active': by_status['pending'] + by_status['in_progress'],
            'completed': by_status['completed'],
            'by_status': by_status,
            'completion_rate': round(by_status['completed'] / total * 100, 1) if total > 0 else 0
        }
    
    def _to_markdown(self) -> str:
        """Convert TODOs to Markdown format."""
        lines = ["# TODO List\n"]
        lines.append(f"Session: {self.session_id}\n")
        lines.append(f"Generated: {datetime.now().isoformat()}\n\n")
        
        summary = self._get_summary()
        lines.append(f"**Total:** {summary['total']} | **Active:** {summary['active']} | **Completed:** {summary['completed']}\n\n")
        
        lines.append("## Tasks\n\n")
        
        for i, todo in enumerate(self.todos, 1):
            icon = self.STATUS_ICONS.get(TodoStatus(todo.status), '•')
            lines.append(f"{i}. {icon} **{todo.description}** [{todo.status}]\n")
            if todo.active_form:
                lines.append(f"   _{todo.active_form}_\n")
            if todo.completed_at:
                lines.append(f"   Completed: {todo.completed_at}\n")
        
        return '\n'.join(lines)
    
    def _to_text(self) -> str:
        """Convert TODOs to plain text format."""
        lines = [f"TODO List - Session: {self.session_id}", "=" * 50]
        
        summary = self._get_summary()
        lines.append(f"Total: {summary['total']} | Active: {summary['active']} | Completed: {summary['completed']}")
        lines.append("")
        
        for i, todo in enumerate(self.todos, 1):
            icon = self.STATUS_ICONS.get(TodoStatus(todo.status), '•')
            lines.append(f"{i}. {icon} {todo.description} [{todo.status}]")
        
        return '\n'.join(lines)
    
    def validate(self, **kwargs) -> bool:
        """Validate TODO operation parameters."""
        # Basic validation - can be extended
        return True
