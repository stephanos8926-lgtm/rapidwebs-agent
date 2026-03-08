"""Code Agent for code manipulation, refactoring, and debugging.

This subagent specializes in code-related tasks including:
- Code refactoring and improvement
- Bug fixing and debugging
- Code review and analysis
- New code implementation
"""

import asyncio
from typing import Dict, Any
from pathlib import Path

from .protocol import (
    SubAgentProtocol, SubAgentTask, SubAgentResult, SubAgentStatus,
    SubAgentConfig, SubAgentType
)
from .prompts import (
    CODE_REFACTOR_PROMPT, CODE_DEBUG_PROMPT, CODE_REVIEW_PROMPT,
    CODE_IMPLEMENT_PROMPT, CODE_ANALYZE_PROMPT, get_language_from_file
)
from ..logging_config import get_logger


class CodeAgent(SubAgentProtocol):
    """SubAgent for code manipulation tasks.

    This agent handles:
    - Reading and analyzing code files
    - Refactoring and improving code structure
    - Debugging and fixing issues
    - Implementing new features
    - Code review and quality analysis
    """

    def __init__(self, config: SubAgentConfig = None, model_manager = None):
        """Initialize Code Agent.

        Args:
            config: Agent configuration (uses defaults if None)
            model_manager: ModelManager for LLM integration
        """
        if config is None:
            config = SubAgentConfig(
                type=SubAgentType.CODE,
                enabled=True,
                max_token_budget=20000,
                max_timeout=600,
                allowed_tools=[
                    'read_file', 'write_file', 'edit_file',
                    'run_shell_command', 'list_directory', 'search_files'
                ],
                parallel_limit=2
            )
        super().__init__(config, model_manager)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities.

        Returns:
            Dictionary describing capabilities
        """
        caps = super().get_capabilities()
        caps['specialties'] = [
            'code_refactoring',
            'bug_fixing',
            'code_review',
            'feature_implementation',
            'code_analysis'
        ]
        return caps
    
    async def execute(self, task: SubAgentTask) -> SubAgentResult:
        """Execute a code task.

        Args:
            task: Task to execute

        Returns:
            Task execution result
        """
        logger = get_logger('subagents.code')
        start_time = asyncio.get_event_loop().time()
        files_modified = []

        logger.info(f'Starting code task {task.id}: {task.description[:80]}...')
        logger.debug(f'Task context: {task.context}')

        try:
            # Determine task type from description/context
            task_type = self._classify_task(task)
            logger.debug(f'Task classified as: {task_type}')

            if task_type == 'refactor':
                result = await self._execute_refactor(task)
            elif task_type == 'debug':
                result = await self._execute_debug(task)
            elif task_type == 'review':
                result = await self._execute_review(task)
            elif task_type == 'implement':
                result = await self._execute_implement(task)
            elif task_type == 'analyze':
                result = await self._execute_analyze(task)
            else:
                result = await self._execute_generic(task)

            # Collect modified files
            if isinstance(result, dict) and 'files_modified' in result.get('metadata', {}):
                files_modified = result['metadata']['files_modified']
            elif hasattr(result, 'metadata') and 'files_modified' in result.metadata:
                files_modified = result.metadata['files_modified']

            duration = asyncio.get_event_loop().time() - start_time

            if result.get('success', True):
                logger.info(f'Task {task.id} completed in {duration:.2f}s')
            else:
                logger.warning(f'Task {task.id} failed: {result.get("error")}')

            return SubAgentResult(
                task_id=task.id,
                status=result.get('status', SubAgentStatus.COMPLETED),
                output=result.get('output', ''),
                token_usage=result.get('token_usage', 0),
                duration=duration,
                error=result.get('error'),
                metadata=result.get('metadata', {}),
                files_modified=files_modified
            )

        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            logger.error(f'Task {task.id} failed with exception: {e}')
            return SubAgentResult(
                task_id=task.id,
                status=SubAgentStatus.FAILED,
                output="",
                error=str(e),
                duration=duration,
                files_modified=files_modified
            )
    
    def _classify_task(self, task: SubAgentTask) -> str:
        """Classify task type from description and context.
        
        Args:
            task: Task to classify
            
        Returns:
            Task type string
        """
        description = task.description.lower()
        context = task.context
        
        # Check explicit type in context
        if 'type' in context:
            return context['type']
        
        # Classify by keywords
        refactor_keywords = ['refactor', 'restructure', 'reorganize', 'clean up', 
                           'improve structure', 'simplify', 'optimize']
        debug_keywords = ['debug', 'fix bug', 'error', 'issue', 'broken', 
                         'not working', 'crash', 'exception']
        review_keywords = ['review', 'analyze', 'audit', 'check quality',
                          'best practices', 'code quality']
        implement_keywords = ['implement', 'create', 'add feature', 'new',
                            'write code', 'build']
        analyze_keywords = ['analyze', 'explain', 'understand', 'document']
        
        for keyword in refactor_keywords:
            if keyword in description:
                return 'refactor'
        
        for keyword in debug_keywords:
            if keyword in description:
                return 'debug'
        
        for keyword in review_keywords:
            if keyword in description:
                return 'review'
        
        for keyword in implement_keywords:
            if keyword in description:
                return 'implement'
        
        for keyword in analyze_keywords:
            if keyword in description:
                return 'analyze'
        
        return 'generic'
    
    async def _execute_refactor(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute code refactoring task.

        Args:
            task: Task to execute

        Returns:
            Result dictionary
        """
        # Get file to refactor
        file_path = task.context.get('file_path') or task.context.get('path')
        if not file_path:
            return {
                'status': SubAgentStatus.FAILED,
                'error': 'No file path specified for refactoring',
                'token_usage': 0
            }

        # Read the file
        try:
            content = await self._read_file(file_path)
        except Exception as e:
            return {
                'status': SubAgentStatus.FAILED,
                'error': f'Failed to read file: {e}',
                'token_usage': 0
            }

        # Get refactoring instructions
        instructions = task.context.get('instructions', task.description)

        # Generate refactored code
        result = await self._generate_refactoring(content, instructions, file_path)

        # Handle error from LLM generation (check both new 'status' and old 'success' formats)
        if result.get('status') == SubAgentStatus.FAILED or not result.get('success', True):
            return {
                'status': SubAgentStatus.FAILED,
                'error': result.get('error', 'Unknown error'),
                'token_usage': result.get('token_usage', 0)
            }

        # Apply changes if code was modified
        refactored_content = result.get('content', content)
        if result.get('changed', False) and refactored_content != content:
            await self._write_file(file_path, refactored_content)
            return {
                'status': SubAgentStatus.COMPLETED,
                'output': f'Successfully refactored {file_path}',
                'token_usage': result.get('token_usage', 0),
                'metadata': {
                    'files_modified': [file_path],
                    'operation': 'refactor',
                    'original_lines': len(content.splitlines()),
                    'new_lines': len(refactored_content.splitlines())
                }
            }

        return {
            'status': SubAgentStatus.COMPLETED,
            'output': f'No changes needed for {file_path}' + (f": {result.get('message', '')}" if result.get('message') else ''),
            'token_usage': result.get('token_usage', 0),
            'metadata': {'files_modified': []}
        }
    
    async def _execute_debug(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute debugging task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        file_path = task.context.get('file_path')
        error_message = task.context.get('error', '')
        
        if not file_path:
            return {
                'status': SubAgentStatus.FAILED,
                'error': 'No file path specified for debugging',
                'token_usage': 0
            }
        
        # Read the file
        content = await self._read_file(file_path)
        
        # Analyze error and code
        fix = await self._generate_debug_fix(
            content, error_message, file_path
        )

        # Handle both new 'status' and old 'success' formats
        if fix.get('status') == SubAgentStatus.FAILED:
            return {
                'status': SubAgentStatus.FAILED,
                'error': fix.get('error', 'Could not determine fix'),
                'token_usage': fix.get('token_usage', 0)
            }
        
        if fix.get('success', True):
            # Apply fix
            await self._write_file(file_path, fix['content'])
            return {
                'status': SubAgentStatus.COMPLETED,
                'output': f"Fixed bug in {file_path}: {fix.get('explanation', '')}",
                'token_usage': fix.get('token_usage', 0),
                'metadata': {
                    'files_modified': [file_path],
                    'operation': 'debug',
                    'error_fixed': error_message
                }
            }

        return {
            'status': SubAgentStatus.FAILED,
            'error': fix.get('error', 'Could not determine fix'),
            'token_usage': fix.get('token_usage', 0)
        }
    
    async def _execute_review(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute code review task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        file_path = task.context.get('file_path')
        
        if not file_path:
            return {
                'status': SubAgentStatus.FAILED,
                'error': 'No file path specified for review',
                'token_usage': 0
            }
        
        content = await self._read_file(file_path)
        
        # Generate review
        review = await self._generate_review(content, file_path)

        # Handle error from LLM generation
        if review.get('status') == SubAgentStatus.FAILED:
            return {
                'status': SubAgentStatus.FAILED,
                'error': review.get('error', 'Review failed'),
                'token_usage': review.get('token_usage', 0)
            }

        return {
            'status': SubAgentStatus.COMPLETED,
            'output': review.get('report', ''),
            'token_usage': review.get('token_usage', 0),
            'metadata': {
                'files_reviewed': [file_path],
                'operation': 'review',
                'issues_found': review.get('issues_count', 0),
                'severity': review.get('max_severity', 'low')
            }
        }
    
    async def _execute_implement(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute code implementation task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        file_path = task.context.get('file_path')
        requirements = task.context.get('requirements', task.description)
        
        if not file_path:
            return {
                'status': SubAgentStatus.FAILED,
                'error': 'No file path specified for implementation',
                'token_usage': 0
            }
        
        # Check if file exists
        try:
            existing_content = await self._read_file(file_path)
        except FileNotFoundError:
            existing_content = ''
        
        # Generate implementation
        implementation = await self._generate_implementation(
            existing_content, requirements, file_path
        )

        # Handle error from LLM generation
        if implementation.get('status') == SubAgentStatus.FAILED:
            return {
                'status': SubAgentStatus.FAILED,
                'error': implementation.get('error', 'Implementation failed'),
                'token_usage': implementation.get('token_usage', 0)
            }

        await self._write_file(file_path, implementation['content'])

        return {
            'status': SubAgentStatus.COMPLETED,
            'output': f"Implemented feature in {file_path}",
            'token_usage': implementation.get('token_usage', 0),
            'metadata': {
                'files_modified': [file_path],
                'operation': 'implement',
                'lines_added': len(implementation['content'].splitlines())
            }
        }
    
    async def _execute_analyze(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute code analysis task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        file_path = task.context.get('file_path')
        
        if not file_path:
            return {
                'status': SubAgentStatus.FAILED,
                'error': 'No file path specified for analysis',
                'token_usage': 0
            }
        
        content = await self._read_file(file_path)
        
        # Generate analysis
        analysis = await self._generate_analysis(content, file_path)

        # Handle error from LLM generation
        if analysis.get('status') == SubAgentStatus.FAILED:
            return {
                'status': SubAgentStatus.FAILED,
                'error': analysis.get('error', 'Analysis failed'),
                'token_usage': analysis.get('token_usage', 0)
            }

        return {
            'status': SubAgentStatus.COMPLETED,
            'output': analysis.get('report', ''),
            'token_usage': analysis.get('token_usage', 0),
            'metadata': {
                'files_analyzed': [file_path],
                'operation': 'analyze'
            }
        }
    
    async def _execute_generic(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute generic code task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        # Generic implementation - would use LLM
        return {
            'status': SubAgentStatus.COMPLETED,
            'output': f"Completed code task: {task.description}",
            'token_usage': 100,
            'metadata': {'operation': 'generic'}
        }
    
    # Helper methods - these would integrate with actual LLM and tools
    
    async def _read_file(self, path: str) -> str:
        """Read file content with error handling.

        Args:
            path: File path

        Returns:
            File content

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If permission denied
            IOError: If read fails for other reasons
        """
        try:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = Path.cwd() / file_path
            
            # Validate path is within workspace (security)
            workspace_root = Path.cwd().resolve()
            resolved_path = file_path.resolve()
            try:
                resolved_path.relative_to(workspace_root)
            except ValueError:
                # Allow reading outside workspace for absolute paths in config
                pass
            
            return file_path.read_text(encoding='utf-8')
        except FileNotFoundError:
            raise FileNotFoundError(f'File not found: {path}')
        except PermissionError:
            raise PermissionError(f'Permission denied reading file: {path}')
        except UnicodeDecodeError:
            raise IOError(f'Unable to decode file (not UTF-8): {path}')
        except Exception as e:
            raise IOError(f'Failed to read file {path}: {e}')

    async def _write_file(self, path: str, content: str):
        """Write file content with error handling.

        Args:
            path: File path
            content: Content to write

        Raises:
            PermissionError: If permission denied
            IOError: If write fails for other reasons
        """
        try:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = Path.cwd() / file_path
            
            # Validate path is within workspace (security)
            workspace_root = Path.cwd().resolve()
            resolved_path = file_path.resolve()
            try:
                resolved_path.relative_to(workspace_root)
            except ValueError:
                raise IOError(f'Cannot write outside workspace: {path}')
            
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
        except PermissionError:
            raise PermissionError(f'Permission denied writing to file: {path}')
        except OSError as e:
            raise IOError(f'Failed to write file {path}: {e}')
        except Exception as e:
            raise IOError(f'Unexpected error writing file {path}: {e}')
    
    async def _generate_refactoring(
        self, content: str, instructions: str, file_path: str
    ) -> Dict[str, Any]:
        """Generate refactored code using LLM.

        Args:
            content: Original code
            instructions: Refactoring instructions
            file_path: File being refactored

        Returns:
            Dictionary with refactored content or error
        """
        language = get_language_from_file(file_path)

        prompt = CODE_REFACTOR_PROMPT.format(
            language=language,
            code=content,
            instructions=instructions
        )

        try:
            response, tokens = await self._call_llm(prompt)
            # Extract code from response (handle markdown code blocks)
            refactored_code = self._extract_code(response)

            if refactored_code and refactored_code != content:
                return {
                    'success': True,
                    'content': refactored_code,
                    'token_usage': tokens,
                    'changed': True
                }
            else:
                return {
                    'success': True,
                    'content': content,
                    'token_usage': tokens,
                    'changed': False,
                    'message': 'No changes suggested'
                }
        except RuntimeError as e:
            # CRITICAL FIX: Return proper error status for orchestrator
            return {
                'status': SubAgentStatus.FAILED,
                'error': f'LLM not configured - cannot generate refactoring: {e}',
                'token_usage': 0
            }
        except Exception as e:
            # Catch any other unexpected and return as failure
            return {
                'status': SubAgentStatus.FAILED,
                'error': f'Refactoring failed: {e}',
                'token_usage': 0
            }
    
    async def _generate_debug_fix(
        self, content: str, error_message: str, file_path: str
    ) -> Dict[str, Any]:
        """Generate debug fix using LLM.
        
        Args:
            content: Code with bug
            error_message: Error description
            file_path: File being debugged
            
        Returns:
            Fix dictionary with content and explanation
        """
        language = get_language_from_file(file_path)
        
        prompt = CODE_DEBUG_PROMPT.format(
            language=language,
            code=content,
            error_message=error_message or "Code is not working as expected"
        )
        
        try:
            response, tokens = await self._call_llm(prompt)
            
            # Extract code and explanation from response
            code_match = self._extract_code(response, return_all=True)
            explanation = response.replace(code_match, '').strip() if code_match else response
            
            if code_match:
                return {
                    'success': True,
                    'content': self._extract_code(response),
                    'explanation': explanation,
                    'token_usage': tokens
                }
            
            return {
                'success': False,
                'error': 'Could not extract fixed code from response',
                'token_usage': tokens
            }
        except RuntimeError as e:
            return {
                'status': SubAgentStatus.FAILED,
                'error': f'LLM not configured - cannot generate debug fix: {e}',
                'token_usage': 0
            }
        except Exception as e:
            return {
                'status': SubAgentStatus.FAILED,
                'error': f'Debug failed: {e}',
                'token_usage': 0
            }
    
    async def _generate_review(
        self, content: str, file_path: str
    ) -> Dict[str, Any]:
        """Generate code review using LLM.
        
        Args:
            content: Code to review
            file_path: File being reviewed
            
        Returns:
            Review dictionary with report
        """
        language = get_language_from_file(file_path)
        
        prompt = CODE_REVIEW_PROMPT.format(
            language=language,
            code=content
        )
        
        try:
            response, tokens = await self._call_llm(prompt)
            
            # Count issues by severity
            issues_count = {
                'critical': response.lower().count('**severity**: critical'),
                'high': response.lower().count('**severity**: high'),
                'medium': response.lower().count('**severity**: medium'),
                'low': response.lower().count('**severity**: low')
            }
            
            max_severity = 'low'
            if issues_count['critical'] > 0:
                max_severity = 'critical'
            elif issues_count['high'] > 0:
                max_severity = 'high'
            elif issues_count['medium'] > 0:
                max_severity = 'medium'
            
            return {
                'report': response,
                'token_usage': tokens,
                'issues_count': sum(issues_count.values()),
                'max_severity': max_severity,
                'issues_by_severity': issues_count
            }
        except RuntimeError as e:
            return {
                'status': SubAgentStatus.FAILED,
                'error': f'LLM not configured - cannot generate review: {e}',
                'token_usage': 0
            }
        except Exception as e:
            return {
                'status': SubAgentStatus.FAILED,
                'error': f'Review failed: {e}',
                'token_usage': 0
            }
    
    async def _generate_implementation(
        self, existing: str, requirements: str, file_path: str
    ) -> Dict[str, Any]:
        """Generate code implementation using LLM.
        
        Args:
            existing: Existing code (empty for new files)
            requirements: Implementation requirements
            file_path: Target file path
            
        Returns:
            Implementation dictionary with content
        """
        language = get_language_from_file(file_path)
        
        prompt = CODE_IMPLEMENT_PROMPT.format(
            language=language,
            existing_code=existing or "# New file",
            requirements=requirements
        )
        
        try:
            response, tokens = await self._call_llm(prompt)
            return {
                'content': self._extract_code(response),
                'token_usage': tokens
            }
        except RuntimeError as e:
            return {
                'status': SubAgentStatus.FAILED,
                'error': f'LLM not configured - cannot generate implementation: {e}',
                'token_usage': 0
            }
        except Exception as e:
            return {
                'status': SubAgentStatus.FAILED,
                'error': f'Implementation failed: {e}',
                'token_usage': 0
            }
    
    async def _generate_analysis(
        self, content: str, file_path: str
    ) -> Dict[str, Any]:
        """Generate code analysis using LLM.
        
        Args:
            content: Code to analyze
            file_path: File being analyzed
            
        Returns:
            Analysis dictionary with report
        """
        language = get_language_from_file(file_path)
        
        prompt = CODE_ANALYZE_PROMPT.format(
            language=language,
            code=content,
            analysis_type="Provide a comprehensive analysis of this code"
        )
        
        try:
            response, tokens = await self._call_llm(prompt)
            return {
                'report': response,
                'token_usage': tokens
            }
        except RuntimeError as e:
            return {
                'status': SubAgentStatus.FAILED,
                'error': f'LLM not configured - cannot generate analysis: {e}',
                'token_usage': 0
            }
        except Exception as e:
            return {
                'status': SubAgentStatus.FAILED,
                'error': f'Analysis failed: {e}',
                'token_usage': 0
            }
    
    def _extract_code(self, text: str, return_all: bool = False) -> str:
        """Extract code from LLM response.
        
        Args:
            text: LLM response text
            return_all: If True, return full match including backticks
            
        Returns:
            Extracted code content
        """
        import re
        
        # Try to extract from markdown code blocks
        patterns = [
            r'```(?:\w+)?\n(.*?)```',  # fenced code block
            r'```\n(.*?)```',  # unfenced code block
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                if return_all:
                    return match.group(0)
                return match.group(1).strip()
        
        # No code blocks found - return entire response trimmed
        return text.strip()
