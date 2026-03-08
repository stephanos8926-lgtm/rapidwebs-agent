"""SubAgent orchestrator for task coordination and result aggregation.

This module provides the main orchestration layer for delegating tasks
to specialized subagents, managing parallel execution, and aggregating results.
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple, Set
from pathlib import Path
import time
from collections import defaultdict

from .protocol import (
    SubAgentTask, SubAgentResult, SubAgentStatus, SubAgentType,
    SubAgentProtocol, SubAgentConfig, SubAgentRegistry,
    DEFAULT_CODE_AGENT_CONFIG, DEFAULT_TEST_AGENT_CONFIG,
    DEFAULT_DOCS_AGENT_CONFIG, DEFAULT_RESEARCH_AGENT_CONFIG,
    DEFAULT_SECURITY_AGENT_CONFIG
)

from ..logging_config import get_logger


class TaskGraph:
    """Directed acyclic graph for task dependencies.
    
    This class manages task dependencies and determines execution order.
    """
    
    def __init__(self):
        """Initialize task graph."""
        self._tasks: Dict[str, SubAgentTask] = {}
        self._dependencies: Dict[str, Set[str]] = defaultdict(set)
        self._dependents: Dict[str, Set[str]] = defaultdict(set)
    
    def add_task(self, task: SubAgentTask):
        """Add task to graph.
        
        Args:
            task: Task to add
        """
        self._tasks[task.id] = task
        for dep_id in task.dependencies:
            self._dependencies[task.id].add(dep_id)
            self._dependents[dep_id].add(task.id)
    
    def get_ready_tasks(self, completed: Set[str]) -> List[SubAgentTask]:
        """Get tasks that are ready to execute.
        
        Args:
            completed: Set of completed task IDs
            
        Returns:
            List of tasks with all dependencies satisfied
        """
        ready = []
        for task_id, task in self._tasks.items():
            if task_id in completed:
                continue
            if self._dependencies[task_id].issubset(completed):
                ready.append(task)
        
        # Sort by priority (lower number = higher priority)
        ready.sort(key=lambda t: (t.priority, t.created_at))
        return ready
    
    def get_task(self, task_id: str) -> Optional[SubAgentTask]:
        """Get task by ID."""
        return self._tasks.get(task_id)
    
    def all_tasks(self) -> List[SubAgentTask]:
        """Get all tasks."""
        return list(self._tasks.values())
    
    def is_complete(self, completed: Set[str]) -> bool:
        """Check if all tasks are completed.
        
        Args:
            completed: Set of completed task IDs
            
        Returns:
            True if all tasks completed
        """
        return completed >= set(self._tasks.keys())


class ResultAggregator:
    """Aggregates results from multiple subagent tasks.
    
    This class collects results, detects conflicts, and merges outputs.
    """
    
    def __init__(self):
        """Initialize result aggregator."""
        self._results: Dict[str, SubAgentResult] = {}
        self._conflicts: List[Dict[str, Any]] = []
    
    def add_result(self, result: SubAgentResult):
        """Add a task result.
        
        Args:
            result: Task result to add
        """
        self._results[result.task_id] = result
        
        # Check for file conflicts
        self._detect_conflicts(result)
    
    def _detect_conflicts(self, new_result: SubAgentResult):
        """Detect conflicts with existing results.
        
        Args:
            new_result: New result to check
        """
        if not new_result.files_modified:
            return
        
        for task_id, existing in self._results.items():
            if task_id == new_result.task_id:
                continue
            
            if not existing.files_modified:
                continue
            
            # Check for overlapping file modifications
            overlap = set(new_result.files_modified) & set(existing.files_modified)
            if overlap:
                self._conflicts.append({
                    'task1': task_id,
                    'task2': new_result.task_id,
                    'files': list(overlap),
                    'result1': existing,
                    'result2': new_result
                })
    
    def get_result(self, task_id: str) -> Optional[SubAgentResult]:
        """Get result for a task."""
        return self._results.get(task_id)
    
    def get_all_results(self) -> Dict[str, SubAgentResult]:
        """Get all results."""
        return self._results.copy()
    
    def get_conflicts(self) -> List[Dict[str, Any]]:
        """Get detected conflicts."""
        return self._conflicts.copy()
    
    def has_conflicts(self) -> bool:
        """Check if there are any conflicts."""
        return len(self._conflicts) > 0
    
    def get_combined_output(self) -> str:
        """Get combined output from all results.
        
        Returns:
            Combined output string
        """
        outputs = []
        for result in self._results.values():
            if result.success() and result.output:
                outputs.append(f"=== Task {result.task_id} ===\n{result.output}")
        return '\n\n'.join(outputs)
    
    def get_total_token_usage(self) -> int:
        """Get total token usage from all results.
        
        Returns:
            Total tokens used
        """
        return sum(r.token_usage for r in self._results.values())
    
    def get_total_duration(self) -> float:
        """Get total duration from all results.
        
        Returns:
            Total duration in seconds
        """
        return sum(r.duration for r in self._results.values())
    
    def clear(self):
        """Clear all results and conflicts."""
        self._results.clear()
        self._conflicts.clear()


class SubAgentOrchestrator:
    """Main orchestrator for subagent task execution.
    
    This class coordinates task decomposition, assignment, parallel
    execution, and result aggregation.
    
    Example:
        >>> orchestrator = SubAgentOrchestrator()
        >>> orchestrator.register_agent(CodeAgent())
        >>> orchestrator.register_agent(TestAgent())
        >>> 
        >>> # Execute tasks
        >>> tasks = [
        ...     SubAgentTask.create(SubAgentType.CODE, "Refactor main.py"),
        ...     SubAgentTask.create(SubAgentType.TEST, "Write tests for main.py")
        ... ]
        >>> results = await orchestrator.execute_parallel(tasks)
    """
    
    def __init__(self, max_concurrent: int = 3):
        """Initialize orchestrator.

        Args:
            max_concurrent: Maximum concurrent subagent tasks
        """
        self.max_concurrent = max_concurrent
        self._registry = SubAgentRegistry()
        self._task_graph = TaskGraph()
        self._aggregator = ResultAggregator()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._stats = {
            'tasks_executed': 0,
            'tasks_failed': 0,
            'total_tokens': 0,
            'total_duration': 0.0
        }
        # Thread-safe locks for concurrent operations
        self._completed_lock = asyncio.Lock()
        self._running_lock = asyncio.Lock()

    @property
    def agents(self) -> dict:
        """Get dictionary of registered agents by type.
        
        Returns:
            Dict mapping SubAgentType to SubAgentProtocol instances
        """
        agents_dict = {}
        for agent_type in SubAgentType:
            protocol = self._registry.get_protocol(agent_type)
            if protocol:
                agents_dict[agent_type] = protocol
        return agents_dict

    def register_agent(self, protocol: SubAgentProtocol,
                       config: SubAgentConfig = None):
        """Register a subagent.
        
        Args:
            protocol: SubAgentProtocol instance
            config: Optional configuration
        """
        self._registry.register(protocol, config)
    
    def register_default_agents(self, model_manager):
        """Register default subagent implementations.

        This method registers Code, Test, Docs, Research, and Security agents with
        default configurations.

        Args:
            model_manager: Required ModelManager for LLM integration
            
        Raises:
            ValueError: If model_manager is None
        """
        if model_manager is None:
            raise ValueError("model_manager is required for SubAgent registration. "
                           "Call orchestrator.register_default_agents(agent.model_manager)")
        
        # Import here to avoid circular dependency
        from .code_agent import CodeAgent
        from .test_agent import TestAgent
        from .docs_agent import DocsAgent
        from .research_agent import ResearchAgent
        from .security_agent import SecurityAgent

        # Register with model_manager explicitly set
        code_agent = CodeAgent(model_manager=model_manager)
        code_agent.set_model_manager(model_manager)  # Ensure it's set
        self.register_agent(code_agent, DEFAULT_CODE_AGENT_CONFIG)
        
        test_agent = TestAgent(model_manager=model_manager)
        test_agent.set_model_manager(model_manager)
        self.register_agent(test_agent, DEFAULT_TEST_AGENT_CONFIG)
        
        docs_agent = DocsAgent(model_manager=model_manager)
        docs_agent.set_model_manager(model_manager)
        self.register_agent(docs_agent, DEFAULT_DOCS_AGENT_CONFIG)
        
        research_agent = ResearchAgent(model_manager=model_manager)
        research_agent.set_model_manager(model_manager)
        self.register_agent(research_agent, DEFAULT_RESEARCH_AGENT_CONFIG)
        
        security_agent = SecurityAgent(model_manager=model_manager)
        security_agent.set_model_manager(model_manager)
        self.register_agent(security_agent, DEFAULT_SECURITY_AGENT_CONFIG)
    
    async def execute_task(self, task: SubAgentTask) -> SubAgentResult:
        """Execute a single task.

        Args:
            task: Task to execute

        Returns:
            Task execution result
        """
        logger = get_logger('subagents_orchestrator')
        protocol = self._registry.get_protocol(task.type)

        if not protocol:
            error_msg = f"No subagent registered for type {task.type.value}"
            logger.error(error_msg)
            return SubAgentResult(
                task_id=task.id,
                status=SubAgentStatus.FAILED,
                output="",
                error=error_msg
            )

        # Validate task
        is_valid, error = protocol.validate_task(task)
        if not is_valid:
            logger.error(f'Task {task.id} validation failed: {error}')
            return SubAgentResult(
                task_id=task.id,
                status=SubAgentStatus.FAILED,
                output="",
                error=error
            )

        logger.info(f'Executing task {task.id}: {task.description[:80]}')

        # Execute with semaphore for concurrency control
        async with self._semaphore:
            start_time = time.time()
            try:
                result = await asyncio.wait_for(
                    protocol.execute(task),
                    timeout=task.timeout
                )
                duration = time.time() - start_time

                # Update stats
                if result.success():
                    logger.info(f'Task {task.id} completed successfully in {duration:.2f}s')
                    self._stats['tasks_executed'] += 1
                else:
                    logger.warning(f'Task {task.id} failed: {result.error}')
                    self._stats['tasks_failed'] += 1
                self._stats['total_tokens'] += result.token_usage
                self._stats['total_duration'] += duration

                return result

            except asyncio.TimeoutError:
                error_msg = f"Task timed out after {task.timeout}s"
                logger.error(f'Task {task.id} timeout: {error_msg}')
                return SubAgentResult(
                    task_id=task.id,
                    status=SubAgentStatus.TIMEOUT,
                    output="",
                    error=error_msg,
                    duration=task.timeout
                )
            except Exception as e:
                error_msg = f"Task failed with exception: {type(e).__name__}: {str(e)}"
                logger.error(f'Task {task.id} failed: {error_msg}')
                import traceback
                logger.debug(f'Traceback: {traceback.format_exc()}')
                return SubAgentResult(
                    task_id=task.id,
                    status=SubAgentStatus.FAILED,
                    output="",
                    error=error_msg
                )
    
    async def execute_parallel(self, tasks: List[SubAgentTask]) -> Dict[str, SubAgentResult]:
        """Execute multiple tasks in parallel.

        Args:
            tasks: List of tasks to execute

        Returns:
            Dictionary mapping task IDs to results
        """
        if not tasks:
            return {}

        # Build task graph
        self._task_graph = TaskGraph()
        for task in tasks:
            self._task_graph.add_task(task)

        self._aggregator.clear()
        completed: Set[str] = set()
        running: Dict[str, asyncio.Task] = {}

        # Log execution start
        logger = get_logger('subagents_orchestrator')
        logger.info(f'Starting parallel execution: {len(tasks)} tasks, max_concurrent={self.max_concurrent}')

        try:
            while not self._task_graph.is_complete(completed):
                # Get ready tasks
                ready = self._task_graph.get_ready_tasks(completed)

                # Start new tasks (respecting concurrency limit)
                for task in ready:
                    if task.id not in running and task.id not in completed:
                        # Check if we have capacity
                        if len(running) >= self.max_concurrent:
                            break

                        # Start task
                        logger.debug(f'Starting task {task.id}: {task.description[:50]}')
                        running[task.id] = asyncio.create_task(
                            self.execute_task(task),
                            name=f"subagent-{task.id}"
                        )

                if not running:
                    # No tasks running and none ready - might have circular deps
                    if completed < set(self._task_graph.all_tasks()):
                        # Mark remaining tasks as failed
                        for task in self._task_graph.all_tasks():
                            if task.id not in completed:
                                error_msg = "Task could not be scheduled (possible circular dependency)"
                                logger.error(f'Task {task.id} failed: {error_msg}')
                                self._aggregator.add_result(SubAgentResult(
                                    task_id=task.id,
                                    status=SubAgentStatus.FAILED,
                                    output="",
                                    error=error_msg
                                ))
                                completed.add(task.id)
                    break

                # Wait for at least one task to complete
                done, pending = await asyncio.wait(
                    running.values(),
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Process completed tasks with proper locking
                for asyncio_task in done:
                    # Find which task ID this was
                    task_id = None
                    for tid, t in list(running.items()):
                        if t == asyncio_task:
                            task_id = tid
                            break

                    if task_id:
                        async with self._running_lock:
                            del running[task_id]
                        
                        try:
                            result = asyncio_task.result()
                            self._aggregator.add_result(result)
                            async with self._completed_lock:
                                completed.add(task_id)
                        except Exception as e:
                            # Task raised exception
                            async with self._completed_lock:
                                self._aggregator.add_result(SubAgentResult(
                                    task_id=task_id,
                                    status=SubAgentStatus.FAILED,
                                    output="",
                                    error=str(e)
                                ))
                                completed.add(task_id)

            return self._aggregator.get_all_results()
            
        except asyncio.CancelledError:
            # Cancel all running tasks on cancellation
            for task in running.values():
                task.cancel()
            # Wait for all tasks to complete cancellation
            if running:
                await asyncio.gather(*running.values(), return_exceptions=True)
            raise
    
    async def execute_sequential(self, tasks: List[SubAgentTask]) -> Dict[str, SubAgentResult]:
        """Execute tasks sequentially (one at a time).
        
        Args:
            tasks: List of tasks to execute
            
        Returns:
            Dictionary mapping task IDs to results
        """
        results = {}
        for task in tasks:
            result = await self.execute_task(task)
            self._aggregator.add_result(result)
            results[task.id] = result
            
            # Stop on first failure if it's critical
            if not result.success():
                break
        
        return results
    
    async def execute_with_dependencies(
        self, tasks: List[SubAgentTask]
    ) -> Dict[str, SubAgentResult]:
        """Execute tasks respecting dependencies.
        
        This is the main execution method that handles complex
        dependency graphs.
        
        Args:
            tasks: List of tasks with dependencies
            
        Returns:
            Dictionary mapping task IDs to results
        """
        return await self.execute_parallel(tasks)
    
    def get_results(self) -> Dict[str, SubAgentResult]:
        """Get all results from last execution."""
        return self._aggregator.get_all_results()
    
    def get_combined_output(self) -> str:
        """Get combined output from all results."""
        return self._aggregator.get_combined_output()
    
    def get_conflicts(self) -> List[Dict[str, Any]]:
        """Get detected conflicts between results."""
        return self._aggregator.get_conflicts()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            **self._stats,
            'max_concurrent': self.max_concurrent,
            'registered_agents': len(self._registry.list_available()),
            'available_agents': [
                a['type'] for a in self._registry.list_available() if a['enabled']
            ]
        }
    
    def get_available_agents(self) -> List[Dict[str, Any]]:
        """Get list of available subagents.
        
        Returns:
            List of agent capability dictionaries
        """
        return self._registry.list_available()
    
    def clear_stats(self):
        """Clear execution statistics."""
        self._stats = {
            'tasks_executed': 0,
            'tasks_failed': 0,
            'total_tokens': 0,
            'total_duration': 0.0
        }


class ConflictResolver:
    """Resolves conflicts between subagent results.
    
    This class provides strategies for resolving file modification
    conflicts and output inconsistencies.
    """
    
    def __init__(self, orchestrator: SubAgentOrchestrator):
        """Initialize conflict resolver.
        
        Args:
            orchestrator: Orchestrator instance
        """
        self.orchestrator = orchestrator
    
    def detect_conflicts(self) -> List[Dict[str, Any]]:
        """Detect conflicts in current results.
        
        Returns:
            List of conflict dictionaries
        """
        return self.orchestrator.get_conflicts()
    
    async def resolve_with_main_agent(
        self, conflict: Dict[str, Any], main_agent_callback: callable
    ) -> Dict[str, Any]:
        """Resolve conflict using main agent.
        
        Args:
            conflict: Conflict dictionary
            main_agent_callback: Callback to main agent for resolution
            
        Returns:
            Resolution dictionary
        """
        # Prepare conflict context for main agent
        context = {
            'conflict_type': 'file_modification',
            'task1': conflict['task1'],
            'task2': conflict['task2'],
            'conflicting_files': conflict['files'],
            'result1_output': conflict['result1'].output,
            'result2_output': conflict['result2'].output
        }
        
        # Ask main agent to resolve
        resolution = await main_agent_callback(context)
        
        return {
            'resolved': True,
            'resolution': resolution,
            'conflict': conflict
        }
    
    def auto_resolve_priority(self, conflict: Dict[str, Any]) -> Optional[str]:
        """Attempt automatic resolution based on priority.
        
        Args:
            conflict: Conflict dictionary
            
        Returns:
            Winning task ID, or None if can't auto-resolve
        """
        result1 = conflict['result1']
        result2 = conflict['result2']
        
        # Prefer successful results
        if result1.success() and not result2.success():
            return result1.task_id
        if result2.success() and not result1.success():
            return result2.task_id
        
        # Prefer result with more token usage (more thorough)
        if result1.token_usage > result2.token_usage * 1.5:
            return result1.task_id
        if result2.token_usage > result1.token_usage * 1.5:
            return result2.task_id
        
        # Can't auto-resolve
        return None
