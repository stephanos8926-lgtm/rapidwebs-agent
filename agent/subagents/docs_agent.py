"""Docs Agent for documentation generation and explanation.

This subagent specializes in documentation tasks including:
- API documentation generation
- Code explanation and summarization
- README and changelog generation
- Documentation updates
"""

import asyncio
from typing import Dict, Any, List
from pathlib import Path

from .protocol import (
    SubAgentProtocol, SubAgentTask, SubAgentResult, SubAgentStatus,
    SubAgentConfig, SubAgentType
)
from .prompts import (
    API_DOCS_PROMPT, CODE_EXPLAIN_PROMPT, README_GENERATE_PROMPT
)


class DocsAgent(SubAgentProtocol):
    """SubAgent for documentation tasks.
    
    This agent handles:
    - Generating API documentation
    - Writing code explanations
    - Creating README files
    - Updating changelogs
    - Summarizing code functionality
    """
    
    def __init__(self, config: SubAgentConfig = None, model_manager = None):
        """Initialize Docs Agent.
        
        Args:
            config: Agent configuration (uses defaults if None)
            model_manager: ModelManager for LLM integration
        """
        if config is None:
            config = SubAgentConfig(
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
        super().__init__(config, model_manager)
        
        # Documentation formats supported
        self._formats = ['markdown', 'rst', 'docstring', 'json', 'yaml']
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities.
        
        Returns:
            Dictionary describing capabilities
        """
        caps = super().get_capabilities()
        caps['specialties'] = [
            'api_documentation',
            'code_explanation',
            'readme_generation',
            'changelog_updates',
            'code_summarization'
        ]
        caps['supported_formats'] = self._formats
        return caps
    
    async def execute(self, task: SubAgentTask) -> SubAgentResult:
        """Execute a documentation task.
        
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
            
            if task_type == 'api':
                result = await self._execute_api(task)
            elif task_type == 'explain':
                result = await self._execute_explain(task)
            elif task_type == 'readme':
                result = await self._execute_readme(task)
            elif task_type == 'changelog':
                result = await self._execute_changelog(task)
            elif task_type == 'summarize':
                result = await self._execute_summarize(task)
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
        if any(kw in description for kw in ['api doc', 'api reference', 'function signature']):
            return 'api'
        
        if any(kw in description for kw in ['explain', 'describe', 'what does']):
            return 'explain'
        
        if any(kw in description for kw in ['readme', 'project description', 'getting started']):
            return 'readme'
        
        if any(kw in description for kw in ['changelog', 'change log', 'release notes']):
            return 'changelog'
        
        if any(kw in description for kw in ['summarize', 'summary', 'overview']):
            return 'summarize'
        
        return 'generic'
    
    async def _execute_api(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute API documentation task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        source_file = task.context.get('source_file')
        output_format = task.context.get('format', 'markdown')
        
        if not source_file:
            return {
                'status': SubAgentStatus.FAILED,
                'error': 'No source file specified for API documentation',
                'token_usage': 0
            }
        
        # Read source file
        content = await self._read_file(source_file)
        
        # Generate API docs
        docs = await self._generate_api_docs(content, source_file, output_format)

        # Handle error from LLM generation
        if docs.startswith('ERROR:'):
            return {
                'status': SubAgentStatus.FAILED,
                'error': docs,
                'token_usage': 0
            }

        # Write docs file
        output_file = task.context.get('output_file')
        if not output_file:
            ext = {'markdown': 'md', 'rst': 'rst', 'json': 'json'}.get(output_format, 'md')
            output_file = f"{Path(source_file).stem}_api.{ext}"

        await self._write_file(output_file, docs)

        return {
            'status': SubAgentStatus.COMPLETED,
            'output': f'Generated API documentation: {output_file}',
            'token_usage': len(content.split()) + len(docs.split()),
            'metadata': {
                'files_modified': [output_file],
                'operation': 'api_documentation',
                'source_file': source_file,
                'format': output_format
            }
        }
    
    async def _execute_explain(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute code explanation task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        source_file = task.context.get('source_file')
        aspect = task.context.get('aspect', 'functionality')
        
        if not source_file:
            return {
                'status': SubAgentStatus.FAILED,
                'error': 'No source file specified for explanation',
                'token_usage': 0
            }
        
        # Read source file
        content = await self._read_file(source_file)
        
        # Generate explanation
        explanation = await self._generate_explanation(content, source_file, aspect)

        # Handle error from LLM generation
        if explanation.startswith('ERROR:'):
            return {
                'status': SubAgentStatus.FAILED,
                'error': explanation,
                'token_usage': 0
            }

        return {
            'status': SubAgentStatus.COMPLETED,
            'output': explanation,
            'token_usage': len(content.split()) + len(explanation.split()) // 2,
            'metadata': {
                'operation': 'code_explanation',
                'source_file': source_file,
                'aspect': aspect
            }
        }
    
    async def _execute_readme(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute README generation task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        project_root = task.context.get('project_root', '.')
        output_file = task.context.get('output_file', 'README.md')
        
        # Gather project information
        project_info = await self._gather_project_info(project_root)
        
        # Generate README
        readme = await self._generate_readme(project_info)
        
        # Write README
        await self._write_file(output_file, readme)
        
        return {
            'status': SubAgentStatus.COMPLETED,
            'output': f'Generated README: {output_file}',
            'token_usage': len(readme.split()),
            'metadata': {
                'files_modified': [output_file],
                'operation': 'readme_generation',
                'project_root': project_root
            }
        }
    
    async def _execute_changelog(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute changelog update task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        changelog_file = task.context.get('changelog_file', 'CHANGELOG.md')
        version = task.context.get('version', 'unreleased')
        changes = task.context.get('changes', [])
        
        # Read existing changelog
        try:
            existing = await self._read_file(changelog_file)
        except FileNotFoundError:
            existing = '# Changelog\n\n'
        
        # Generate new entry
        new_entry = await self._generate_changelog_entry(version, changes)
        
        # Prepend to existing changelog
        updated = f"{existing}\n{new_entry}"
        
        await self._write_file(changelog_file, updated)
        
        return {
            'status': SubAgentStatus.COMPLETED,
            'output': f'Updated changelog: {changelog_file}',
            'token_usage': len(existing.split()) + len(new_entry.split()),
            'metadata': {
                'files_modified': [changelog_file],
                'operation': 'changelog_update',
                'version': version
            }
        }
    
    async def _execute_summarize(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute code summarization task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        source_files = task.context.get('source_files', [])
        
        if not source_files:
            return {
                'status': SubAgentStatus.FAILED,
                'error': 'No source files specified for summarization',
                'token_usage': 0
            }
        
        # Read and summarize each file
        summaries = []
        total_tokens = 0
        
        for file_path in source_files:
            content = await self._read_file(file_path)
            summary = await self._generate_summary(content, file_path)
            summaries.append(f"## {file_path}\n\n{summary}")
            total_tokens += len(content.split()) + len(summary.split()) // 2
        
        combined = '\n\n'.join(summaries)
        
        return {
            'status': SubAgentStatus.COMPLETED,
            'output': combined,
            'token_usage': total_tokens,
            'metadata': {
                'operation': 'code_summarization',
                'files_summarized': len(source_files)
            }
        }
    
    async def _execute_generic(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute generic documentation task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result dictionary
        """
        return {
            'status': SubAgentStatus.COMPLETED,
            'output': f'Completed documentation task: {task.description}',
            'token_usage': 100,
            'metadata': {'operation': 'generic'}
        }
    
    # Helper methods

    async def _generate_api_docs(self, content: str, source_file: str,
                                 output_format: str) -> str:
        """Generate API documentation using LLM.

        Args:
            content: Source code content
            source_file: Source file path
            output_format: Output format

        Returns:
            Generated API documentation or error message
        """
        from .prompts import get_language_from_file
        
        language = get_language_from_file(source_file) or 'text'
        
        prompt = API_DOCS_PROMPT.format(
            language=language,
            source_code=content,
            format=output_format
        )

        try:
            response, _ = await self._call_llm(prompt)
            return self._extract_code(response) or response
        except RuntimeError as e:
            return f"ERROR: LLM not configured - cannot generate API docs: {e}"
        except Exception as e:
            return f"ERROR: Failed to generate API docs: {e}"

    async def _generate_explanation(self, content: str, source_file: str,
                                    aspect: str) -> str:
        """Generate code explanation using LLM.

        Args:
            content: Source code
            source_file: Source file path
            aspect: Aspect to explain

        Returns:
            Explanation text or error message
        """
        prompt = CODE_EXPLAIN_PROMPT.format(
            source_code=content,
            aspect=aspect
        )

        try:
            response, _ = await self._call_llm(prompt)
            return response
        except RuntimeError as e:
            return f"ERROR: LLM not configured for explanation: {e}"
        except Exception as e:
            return f"ERROR: Failed to generate explanation: {e}"

    async def _gather_project_info(self, project_root: str) -> Dict[str, Any]:
        """Gather project information for README.

        Args:
            project_root: Project root directory

        Returns:
            Project information dictionary
        """
        info = {
            'name': Path(project_root).name,
            'description': '',
            'files': [],
            'has_setup': False,
            'has_requirements': False
        }

        root_path = Path(project_root)

        # Check for common files
        if (root_path / 'pyproject.toml').exists():
            info['has_setup'] = True
        if (root_path / 'requirements.txt').exists():
            info['has_requirements'] = True

        # List main files
        for f in root_path.iterdir():
            if f.is_file() and not f.name.startswith('.'):
                info['files'].append(f.name)

        return info

    async def _generate_readme(self, project_info: Dict[str, Any]) -> str:
        """Generate README content using LLM.

        Args:
            project_info: Project information

        Returns:
            README content
        """
        prompt = README_GENERATE_PROMPT.format(
            project_name=project_info.get('name', 'Project'),
            description=project_info.get('description', ''),
            files=', '.join(project_info.get('files', []))
        )
        
        try:
            response, _ = await self._call_llm(prompt)
            return self._extract_code(response) or response
        except RuntimeError as e:
            # LLM not configured - raise clear error instead of generating broken code
            raise RuntimeError(
                f"LLM not configured. Cannot generate README for '{project_info.get('name', 'Project')}'. "
                f"Set RW_QWEN_API_KEY environment variable or configure model. "
                f"Original error: {e}"
            )

    def _extract_code(self, text: str) -> str:
        """Extract code/documentation from LLM response.
        
        Args:
            text: LLM response text
            
        Returns:
            Extracted content
        """
        import re
        
        # Try to extract from markdown code blocks
        patterns = [
            r'```(?:markdown)?\n(.*?)```',
            r'```\n(.*?)```',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()

        return text.strip()

    def _generate_readme_template(self, name: str) -> str:
        """Generate README template.
        
        Args:
            name: Project name
            
        Returns:
            README template content
        """
        return f"""# {name}

```bash
# Clone the repository
git clone <repository-url>
cd {name}

# Install dependencies
pip install -r requirements.txt
```

## Usage

```python
# Example usage
from {name.replace('-', '_')} import main
main()
```

## Features

- Feature 1
- Feature 2
- Feature 3

## Development

```bash
# Run tests
pytest

# Run linting
ruff check .
```

## License

MIT License

---
*Generated by DocsAgent*
"""
    
    async def _generate_changelog_entry(self, version: str,
                                        changes: List[str]) -> str:
        """Generate changelog entry.
        
        Args:
            version: Version string
            changes: List of changes
            
        Returns:
            Changelog entry
        """
        from datetime import datetime
        
        date = datetime.now().strftime('%Y-%m-%d')
        
        entry = f"""## [{version}] - {date}

"""
        
        if changes:
            for change in changes:
                entry += f"- {change}\n"
        else:
            entry += "- TODO: Add changes here\n"
        
        return entry
    
    async def _generate_summary(self, content: str, file_path: str) -> str:
        """Generate code summary.
        
        Args:
            content: Source code
            file_path: File path
            
        Returns:
            Summary text
        """
        # TODO: Integrate with LLM
        lines = content.splitlines()
        return f"""**File:** {file_path}
**Lines:** {len(lines)}

**Purpose:**
TODO: Add purpose summary

**Key Components:**
- Component 1
- Component 2

**Dependencies:**
- External dependencies used
"""
    
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
