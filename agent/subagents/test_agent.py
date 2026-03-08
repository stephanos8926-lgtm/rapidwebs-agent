"""Test Agent for test generation, execution, and fixing.

This subagent specializes in testing tasks including:
- Test file generation
- Test execution and result parsing
- Test fixing based on failures
- Coverage analysis
"""

import asyncio
import re
from typing import Dict, Any, List
from pathlib import Path

from .protocol import (
    SubAgentProtocol, SubAgentTask, SubAgentResult, SubAgentStatus,
    SubAgentConfig, SubAgentType
)
from .prompts import TEST_GENERATE_PROMPT, TEST_FIX_PROMPT, get_language_from_file


class TestAgent(SubAgentProtocol):
    """SubAgent for testing tasks.
    
    This agent handles:
    - Writing new test files
    - Running existing tests
    - Fixing failing tests
    - Analyzing test coverage
    """
    
    def __init__(self, config: SubAgentConfig = None, model_manager = None):
        """Initialize Test Agent.
        
        Args:
            config: Agent configuration (uses defaults if None)
            model_manager: ModelManager for LLM integration
        """
        if config is None:
            config = SubAgentConfig(
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
        super().__init__(config, model_manager)
        
        # Test framework detection
        self._frameworks = {
            'pytest': ['pytest', 'py.test'],
            'unittest': ['unittest', 'python -m unittest'],
            'nose': ['nosetests', 'nose'],
            'jest': ['jest', 'npm test', 'yarn test'],
            'mocha': ['mocha']
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities.
        
        Returns:
            Dictionary describing capabilities
        """
        caps = super().get_capabilities()
        caps['specialties'] = [
            'test_generation',
            'test_execution',
            'test_fixing',
            'coverage_analysis'
        ]
        caps['supported_frameworks'] = list(self._frameworks.keys())
        return caps
    
    async def execute(self, task: SubAgentTask) -> SubAgentResult:
        """Execute a test task.
        
        Args:
            task: Task to execute
            
        Returns:
            Task execution result
        """
        start_time = asyncio.get_event_loop().time()
        files_modified = []
        
        try:
            # Determine task type
            task_type = self._classify_task(task)
            
            if task_type == 'generate':
                result = await self._execute_generate(task)
            elif task_type == 'run':
                result = await self._execute_run(task)
            elif task_type == 'fix':
                result = await self._execute_fix(task)
            elif task_type == 'coverage':
                result = await self._execute_coverage(task)
            else:
                result = await self._execute_generic(task)
            
            # Collect modified files
            if 'files_modified' in result.get('metadata', {}):
                files_modified = result['metadata']['files_modified']
            
            duration = asyncio.get_event_loop().time() - start_time
            
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
            return SubAgentResult(
                task_id=task.id,
                status=SubAgentStatus.FAILED,
                output="",
                error=str(e),
                duration=duration,
                files_modified=files_modified
            )
    
    def _classify_task(self, task: SubAgentTask) -> str:
        """Classify task type.
        
        Args:
            task: Task to classify
            
        Returns:
            Task type string
        """
        description = task.description.lower()
        context = task.context
        
        # Check explicit type
        if 'type' in context:
            return context['type']
        
        # Classify by keywords
        if any(kw in description for kw in ['write test', 'create test', 'generate test']):
            return 'generate'
        
        if any(kw in description for kw in ['run test', 'execute test', 'test run']):
            return 'run'
        
        if any(kw in description for kw in ['fix test', 'repair test', 'test fail']):
            return 'fix'
        
        if any(kw in description for kw in ['coverage', 'cover']):
            return 'coverage'
        
        return 'generic'
    
    async def _execute_generate(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute test generation task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        source_file = task.context.get('source_file')
        test_file = task.context.get('test_file')
        framework = task.context.get('framework', 'pytest')
        
        if not source_file:
            return {
                'status': SubAgentStatus.FAILED,
                'error': 'No source file specified for test generation',
                'token_usage': 0
            }
        
        # Read source file
        try:
            source_content = await self._read_file(source_file)
        except Exception as e:
            return {
                'status': SubAgentStatus.FAILED,
                'error': f'Failed to read source file: {e}',
                'token_usage': 0
            }
        
        # Determine test file path
        if not test_file:
            test_file = self._infer_test_path(source_file, framework)
        
        # Check if test file exists
        try:
            existing_test = await self._read_file(test_file)
        except FileNotFoundError:
            existing_test = ''
        
        # Generate test content
        test_content = await self._generate_tests(
            source_content, source_file, framework, existing_test
        )
        
        # Write test file
        await self._write_file(test_file, test_content)
        
        return {
            'status': SubAgentStatus.COMPLETED,
            'output': f'Generated tests in {test_file}',
            'token_usage': len(source_content.split()) + len(test_content.split()),
            'metadata': {
                'files_modified': [test_file],
                'operation': 'test_generation',
                'framework': framework,
                'source_file': source_file,
                'test_count': self._count_tests(test_content, framework)
            }
        }
    
    async def _execute_run(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute test running task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        test_file = task.context.get('test_file')
        framework = task.context.get('framework', 'pytest')
        test_pattern = task.context.get('pattern', '')

        # Build test command
        cmd = self._build_test_command(framework, test_file, test_pattern)

        # Run tests with timeout from config
        timeout = self.config.max_timeout if self.config else 300
        result = await self._run_command(cmd, timeout=timeout)

        # Parse results
        parsed = self._parse_test_results(result['stdout'], result['stderr'],
                                         result['returncode'], framework)
        
        return {
            'status': SubAgentStatus.COMPLETED if parsed['success'] else SubAgentStatus.FAILED,
            'output': parsed['summary'],
            'token_usage': 100,
            'metadata': {
                'operation': 'test_execution',
                'framework': framework,
                'command': cmd,
                'tests_passed': parsed.get('passed', 0),
                'tests_failed': parsed.get('failed', 0),
                'tests_skipped': parsed.get('skipped', 0),
                'duration': parsed.get('duration', 0),
                'failures': parsed.get('failures', [])
            }
        }
    
    async def _execute_fix(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute test fixing task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        test_file = task.context.get('test_file')
        failure_info = task.context.get('failure', '')
        
        if not test_file:
            return {
                'status': SubAgentStatus.FAILED,
                'error': 'No test file specified for fixing',
                'token_usage': 0
            }
        
        # Read test file
        test_content = await self._read_file(test_file)
        
        # Generate fix
        fixed_content = await self._generate_test_fix(
            test_content, failure_info, test_file
        )
        
        # Apply fix if changed
        if fixed_content != test_content:
            await self._write_file(test_file, fixed_content)
            return {
                'status': SubAgentStatus.COMPLETED,
                'output': f'Fixed test in {test_file}',
                'token_usage': len(test_content.split()) + len(fixed_content.split()),
                'metadata': {
                    'files_modified': [test_file],
                    'operation': 'test_fix',
                    'failure_addressed': failure_info[:200]
                }
            }
        
        return {
            'status': SubAgentStatus.COMPLETED,
            'output': f'No fixes needed for {test_file}',
            'token_usage': len(test_content.split()),
            'metadata': {'files_modified': []}
        }
    
    async def _execute_coverage(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute coverage analysis task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        framework = task.context.get('framework', 'pytest')
        source_dir = task.context.get('source_dir', '.')

        # Build coverage command
        cmd = self._build_coverage_command(framework, source_dir)

        # Run coverage with timeout from config
        timeout = self.config.max_timeout if self.config else 300
        result = await self._run_command(cmd, timeout=timeout)

        # Parse coverage report
        coverage_data = self._parse_coverage_report(result['stdout'], framework)
        
        return {
            'status': SubAgentStatus.COMPLETED,
            'output': coverage_data.get('summary', 'Coverage analysis complete'),
            'token_usage': 100,
            'metadata': {
                'operation': 'coverage_analysis',
                'framework': framework,
                'coverage_percent': coverage_data.get('percent', 0),
                'covered_files': coverage_data.get('covered_files', []),
                'uncovered_files': coverage_data.get('uncovered_files', [])
            }
        }
    
    async def _execute_generic(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute generic test task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        return {
            'status': SubAgentStatus.COMPLETED,
            'output': f'Completed test task: {task.description}',
            'token_usage': 50,
            'metadata': {'operation': 'generic'}
        }
    
    # Helper methods
    
    def _infer_test_path(self, source_file: str, framework: str) -> str:
        """Infer test file path from source file.
        
        Args:
            source_file: Source file path
            framework: Test framework
            
        Returns:
            Inferred test file path
        """
        source_path = Path(source_file)
        
        # Common patterns
        if framework in ['pytest', 'unittest']:
            # test_<name>.py or <name>_test.py
            test_name = f"test_{source_path.stem}.py"
            test_dir = source_path.parent / 'tests'
            return str(test_dir / test_name)
        
        elif framework == 'jest':
            # <name>.test.js or <name>.spec.js
            test_name = f"{source_path.stem}.test.js"
            return str(source_path.parent / test_name)
        
        return str(source_path.parent / f"test_{source_path.name}")
    
    def _build_test_command(self, framework: str, test_file: str = None,
                           pattern: str = '') -> str:
        """Build test execution command.
        
        Args:
            framework: Test framework
            test_file: Specific test file (optional)
            pattern: Test pattern to match
            
        Returns:
            Shell command string
        """
        if framework == 'pytest':
            cmd = 'pytest'
            if test_file:
                cmd += f' {test_file}'
            if pattern:
                cmd += f' -k "{pattern}"'
            cmd += ' -v'
            return cmd
        
        elif framework == 'unittest':
            cmd = 'python -m unittest discover'
            if test_file:
                test_path = test_file.replace('/', '.').replace('.py', '')
                cmd = f'python -m unittest {test_path}'
            return cmd
        
        elif framework == 'jest':
            cmd = 'npx jest'
            if test_file:
                cmd += f' {test_file}'
            if pattern:
                cmd += f' -t "{pattern}"'
            return cmd
        
        # Default to pytest
        return f'pytest {test_file or ""}'
    
    def _build_coverage_command(self, framework: str, source_dir: str) -> str:
        """Build coverage analysis command.
        
        Args:
            framework: Test framework
            source_dir: Source directory to measure
            
        Returns:
            Shell command string
        """
        if framework == 'pytest':
            return f'pytest --cov={source_dir} --cov-report=term-missing'
        elif framework == 'unittest':
            return 'coverage run -m unittest discover && coverage report'
        else:
            return f'pytest --cov={source_dir} --cov-report=term-missing'

    async def _generate_tests(self, source: str, source_file: str,
                             framework: str, existing: str = '') -> str:
        """Generate test content using LLM.

        Args:
            source: Source code to test
            source_file: Source file path
            framework: Test framework
            existing: Existing test content (if any)

        Returns:
            Generated test content
        """
        language = get_language_from_file(source_file)
        
        prompt = TEST_GENERATE_PROMPT.format(
            language=language,
            source_code=source,
            framework=framework
        )
        
        try:
            response, _ = await self._call_llm(prompt)
            return self._extract_code(response) or response
        except RuntimeError as e:
            # LLM not configured - raise clear error instead of generating broken code
            raise RuntimeError(
                f"LLM not configured. Cannot generate tests for {source_file}. "
                f"Set RW_QWEN_API_KEY environment variable or configure model. "
                f"Original error: {e}"
            )

    async def _generate_test_fix(self, content: str, failure: str,
                                 test_file: str) -> str:
        """Generate test fix using LLM.

        Args:
            content: Current test content
            failure: Failure information
            test_file: Test file path

        Returns:
            Fixed test content
        """
        language = get_language_from_file(test_file)
        
        prompt = TEST_FIX_PROMPT.format(
            language=language,
            test_code=content,
            failure_info=failure
        )
        
        try:
            response, _ = await self._call_llm(prompt)
            return self._extract_code(response) or content
        except RuntimeError:
            # Fallback if LLM not configured
            return content

    def _extract_code(self, text: str) -> str:
        """Extract code from LLM response.
        
        Args:
            text: LLM response text
            
        Returns:
            Extracted code content
        """
        import re
        
        # Try to extract from markdown code blocks
        patterns = [
            r'```(?:\w+)?\n(.*?)```',
            r'```\n(.*?)```',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return text.strip()
    
    def _count_tests(self, content: str, framework: str) -> int:
        """Count tests in test content.
        
        Args:
            content: Test file content
            framework: Test framework
            
        Returns:
            Number of tests found
        """
        if framework in ['pytest', 'unittest']:
            return len(re.findall(r'\bdef\s+test_\w+', content))
        elif framework == 'jest':
            return len(re.findall(r'\btest\s*\(', content))
        return 0
    
    def _parse_test_results(self, stdout: str, stderr: str, 
                           returncode: int, framework: str) -> Dict[str, Any]:
        """Parse test execution results.
        
        Args:
            stdout: Standard output
            stderr: Standard error
            returncode: Return code
            framework: Test framework
            
        Returns:
            Parsed results dictionary
        """
        output = stdout + stderr
        
        # Parse pytest/unittest output
        if framework in ['pytest', 'unittest']:
            # Look for summary line
            match = re.search(r'(\d+) passed', output)
            passed = int(match.group(1)) if match else 0
            
            match = re.search(r'(\d+) failed', output)
            failed = int(match.group(1)) if match else 0
            
            match = re.search(r'(\d+) skipped', output)
            skipped = int(match.group(1)) if match else 0
            
            match = re.search(r'in ([\d.]+)s', output)
            duration = float(match.group(1)) if match else 0
            
            return {
                'success': returncode == 0,
                'summary': f"Tests: {passed} passed, {failed} failed, {skipped} skipped",
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'duration': duration,
                'failures': self._extract_failures(output, framework)
            }
        
        # Default parsing
        return {
            'success': returncode == 0,
            'summary': f"Return code: {returncode}",
            'passed': 0,
            'failed': 0 if returncode == 0 else 1,
            'skipped': 0,
            'duration': 0,
            'failures': []
        }
    
    def _extract_failures(self, output: str, framework: str) -> List[Dict[str, Any]]:
        """Extract failure details from test output.
        
        Args:
            output: Test output
            framework: Test framework
            
        Returns:
            List of failure dictionaries
        """
        failures = []
        
        # Simple extraction - would be more sophisticated with LLM
        for match in re.finditer(r'FAILED\s+(\S+)', output):
            failures.append({
                'test': match.group(1),
                'error': 'Test failed'
            })
        
        return failures
    
    def _parse_coverage_report(self, output: str, framework: str) -> Dict[str, Any]:
        """Parse coverage report.
        
        Args:
            output: Coverage report output
            framework: Test framework
            
        Returns:
            Parsed coverage data
        """
        # Look for total coverage percentage
        match = re.search(r'TOTAL\s+(\d+)%', output)
        percent = int(match.group(1)) if match else 0
        
        # Extract file-level coverage
        covered_files = []
        uncovered_files = []
        
        for line in output.splitlines():
            if line.startswith('Total') or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                filename = parts[0]
                try:
                    cov = int(parts[-1].replace('%', ''))
                    if cov > 80:
                        covered_files.append(filename)
                    else:
                        uncovered_files.append(filename)
                except ValueError:
                    pass
        
        return {
            'summary': f"Coverage: {percent}%",
            'percent': percent,
            'covered_files': covered_files[:10],
            'uncovered_files': uncovered_files[:10]
        }
    
    async def _read_file(self, path: str) -> str:
        """Read file content."""
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path
        return file_path.read_text(encoding='utf-8')
    
    async def _write_file(self, path: str, content: str):
        """Write file content."""
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
    
    async def _run_command(self, cmd: str, timeout: int = 300) -> Dict[str, Any]:
        """Run shell command.
        
        Args:
            cmd: Command to run
            timeout: Timeout in seconds (default: 300 = 5 minutes)

        Returns:
            Command result dictionary
        """
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                return {
                    'stdout': stdout.decode('utf-8', errors='replace'),
                    'stderr': stderr.decode('utf-8', errors='replace'),
                    'returncode': process.returncode
                }
            except asyncio.TimeoutError:
                # Kill the process on timeout
                process.kill()
                await process.communicate()  # Clean up zombie process
                return {
                    'stdout': '',
                    'stderr': f'Command timed out after {timeout}s',
                    'returncode': -1
                }
        except Exception as e:
            return {
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }
    
    async def _generate_test_fix(self, content: str, failure: str,
                                 test_file: str) -> str:
        """Generate test fix.
        
        Args:
            content: Current test content
            failure: Failure information
            test_file: Test file path
            
        Returns:
            Fixed test content
        """
        # TODO: Integrate with LLM
        return content
