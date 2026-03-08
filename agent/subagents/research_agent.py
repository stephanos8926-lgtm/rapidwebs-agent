"""Research Agent for information gathering and web research.

This subagent specializes in research tasks including:
- Web search and information retrieval
- Documentation lookup
- Codebase search and analysis
- Information synthesis and summarization
"""

import asyncio
import re
from typing import Dict, Any, List
from pathlib import Path

from .protocol import (
    SubAgentProtocol, SubAgentTask, SubAgentResult, SubAgentStatus,
    SubAgentConfig, SubAgentType
)

# Fallback prompts if prompts.py module not available
try:
    from .prompts import (
        RESEARCH_SEARCH_PROMPT, RESEARCH_SUMMARIZE_PROMPT,
        RESEARCH_DOCUMENTATION_PROMPT, RESEARCH_CODEBASE_PROMPT
    )
except ImportError:
    # Inline fallback prompts
    RESEARCH_SEARCH_PROMPT = """You are an expert researcher. Query: {query}. Tools: {tools_available}."""
    RESEARCH_SUMMARIZE_PROMPT = "Summarize the following content clearly and concisely."
    RESEARCH_DOCUMENTATION_PROMPT = "Provide documentation for: {topic}"
    RESEARCH_CODEBASE_PROMPT = "Analyze this codebase query: {query}"


class ResearchAgent(SubAgentProtocol):
    """SubAgent for research and information gathering tasks.

    This agent handles:
    - Web searches using Brave Search or fetch MCP
    - Documentation lookup using Context7 or web fetch
    - Codebase search and analysis
    - Information synthesis and summarization
    - Competitive research and market analysis
    """

    def __init__(self, config: SubAgentConfig = None, model_manager=None):
        """Initialize Research Agent.

        Args:
            config: Agent configuration (uses defaults if None)
            model_manager: ModelManager for LLM integration
        """
        if config is None:
            config = SubAgentConfig(
                type=SubAgentType.RESEARCH,
                enabled=True,
                max_token_budget=15000,
                max_timeout=600,
                allowed_tools=[
                    'brave_web_search', 'fetch', 'read_file',
                    'search_files', 'sequential_thinking', 'write_file'
                ],
                parallel_limit=3
            )
        super().__init__(config, model_manager)

    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities.

        Returns:
            Dictionary describing capabilities
        """
        caps = super().get_capabilities()
        caps['specialties'] = [
            'web_search',
            'documentation_lookup',
            'codebase_research',
            'information_synthesis',
            'summarization'
        ]
        caps['tools'] = {
            'brave_search': 'Web search via Brave Search API',
            'fetch': 'Web content fetching via MCP',
            'sequential_thinking': 'Complex reasoning and analysis',
            'file_search': 'Codebase pattern matching',
        }
        return caps

    async def execute(self, task: SubAgentTask) -> SubAgentResult:
        """Execute a research task.

        Args:
            task: Task to execute

        Returns:
            Task execution result
        """
        start_time = asyncio.get_event_loop().time()
        files_modified = []

        try:
            # Classify task type
            task_type = self._classify_task(task)

            if task_type == 'web_search':
                result = await self._execute_web_search(task)
            elif task_type == 'documentation':
                result = await self._execute_documentation(task)
            elif task_type == 'codebase':
                result = await self._execute_codebase_research(task)
            elif task_type == 'summarize':
                result = await self._execute_summarize(task)
            else:
                result = await self._execute_general_research(task)

            # Collect modified files
            if 'files_modified' in result:
                files_modified = result['files_modified']

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
        web_search_keywords = [
            'search', 'find information', 'look up', 'google',
            'latest', 'news', 'trending', 'current',
            'who is', 'what is', 'when did', 'where can'
        ]

        doc_keywords = [
            'documentation', 'docs', 'api reference', 'manual',
            'how to use', 'tutorial', 'guide', 'example code'
        ]

        codebase_keywords = [
            'in this codebase', 'in this project', 'search code',
            'find function', 'find class', 'where is', 'locate'
        ]

        summarize_keywords = [
            'summarize', 'summary', 'overview', 'brief',
            'key points', 'main ideas', 'tl;dr'
        ]

        for keyword in web_search_keywords:
            if keyword in description:
                return 'web_search'

        for keyword in doc_keywords:
            if keyword in description:
                return 'documentation'

        for keyword in codebase_keywords:
            if keyword in description:
                return 'codebase'

        for keyword in summarize_keywords:
            if keyword in description:
                return 'summarize'

        return 'general'

    def _contains_url(self, text: str) -> bool:
        """Check if text contains a URL.

        Args:
            text: Text to check

        Returns:
            True if URL found
        """
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return bool(re.search(url_pattern, text))

    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text.

        Args:
            text: Text to extract from

        Returns:
            List of URLs
        """
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, text)

    async def _execute_web_search(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute web search task.

        Args:
            task: Task to execute

        Returns:
            Result dictionary
        """
        query = task.description
        if 'query' in task.context:
            query = task.context['query']

        # Check if query contains URLs
        if self._contains_url(query):
            return await self._fetch_urls(query)

        # Use LLM to perform search via sequential thinking or direct response
        system_prompt = RESEARCH_SEARCH_PROMPT.format(
            query=query,
            tools_available="brave_search, fetch, sequential_thinking"
        )

        try:
            # Add timeout protection for LLM call (60s)
            response, tokens = await asyncio.wait_for(
                self._call_llm(query, system_prompt),
                timeout=60.0
            )

            return {
                'status': SubAgentStatus.COMPLETED,
                'output': response,
                'token_usage': tokens,
                'metadata': {
                    'search_query': query,
                    'sources': self._extract_urls(response)
                },
                'files_modified': []
            }
        except asyncio.TimeoutError:
            return {
                'status': SubAgentStatus.FAILED,
                'output': "",
                'error': "Web search timed out after 60s",
                'token_usage': 0,
                'metadata': {},
                'files_modified': []
            }
        except Exception as e:
            return {
                'status': SubAgentStatus.FAILED,
                'output': "",
                'error': f"Web search failed: {str(e)}",
                'token_usage': 0,
                'metadata': {},
                'files_modified': []
            }

    async def _fetch_urls(self, text: str) -> Dict[str, Any]:
        """Fetch content from URLs in text with parallel fetching and timeout.

        Args:
            text: Text containing URLs

        Returns:
            Result dictionary
        """
        urls = self._extract_urls(text)
        if not urls:
            return {
                'status': SubAgentStatus.FAILED,
                'output': "No URLs found in query",
                'token_usage': 0,
                'metadata': {},
                'files_modified': []
            }

        # Limit URLs and add timeout protection
        urls = urls[:5]
        MAX_CONTENT_PER_URL = 2000
        FETCH_TIMEOUT = 60.0

        async def fetch_one(url: str) -> Dict[str, Any]:
            """Fetch single URL with timeout."""
            try:
                fetch_prompt = f"Fetch and summarize the content from this URL: {url}"
                response, tokens = await asyncio.wait_for(
                    self._call_llm(fetch_prompt),
                    timeout=FETCH_TIMEOUT
                )
                return {
                    'url': url,
                    'content': response[:MAX_CONTENT_PER_URL],  # Truncate for token efficiency
                    'tokens': tokens,
                    'truncated': len(response) > MAX_CONTENT_PER_URL
                }
            except asyncio.TimeoutError:
                return {
                    'url': url,
                    'error': f"Timeout after {FETCH_TIMEOUT}s"
                }
            except Exception as e:
                return {
                    'url': url,
                    'error': str(e)
                }

        # Fetch URLs in parallel
        fetched_content = await asyncio.gather(*[fetch_one(url) for url in urls])

        # Synthesize results with token-efficient prompt
        synthesize_prompt = "Synthesize the following fetched content into a coherent summary:\n\n"
        for item in fetched_content:
            if 'content' in item:
                synthesize_prompt += f"From {item['url']}:\n{item['content']}\n\n"
            else:
                synthesize_prompt += f"From {item['url']}: Failed to fetch ({item.get('error', 'unknown')})\n\n"

        response, tokens = await self._call_llm(synthesize_prompt)

        return {
            'status': SubAgentStatus.COMPLETED,
            'output': response,
            'token_usage': sum(item.get('tokens', 0) for item in fetched_content if 'tokens' in item) + tokens,
            'metadata': {
                'urls_fetched': [item.get('url') for item in fetched_content],
                'fetch_results': fetched_content,
                'urls_truncated': sum(1 for item in fetched_content if item.get('truncated'))
            },
            'files_modified': []
        }

    async def _execute_documentation(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute documentation lookup task.

        Args:
            task: Task to execute

        Returns:
            Result dictionary
        """
        topic = task.description
        if 'topic' in task.context:
            topic = task.context['topic']

        # Validate file paths if provided
        if 'file_path' in task.context:
            file_path = Path(task.context['file_path'])
            if not file_path.exists():
                return {
                    'status': SubAgentStatus.FAILED,
                    'output': f"File not found: {file_path}",
                    'token_usage': 0,
                    'metadata': {},
                    'files_modified': []
                }

        system_prompt = RESEARCH_DOCUMENTATION_PROMPT.format(topic=topic)

        try:
            # Add timeout protection for LLM call (60s)
            response, tokens = await asyncio.wait_for(
                self._call_llm(topic, system_prompt),
                timeout=60.0
            )

            return {
                'status': SubAgentStatus.COMPLETED,
                'output': response,
                'token_usage': tokens,
                'metadata': {
                    'topic': topic,
                    'documentation_type': 'generated'
                },
                'files_modified': []
            }
        except asyncio.TimeoutError:
            return {
                'status': SubAgentStatus.FAILED,
                'output': "",
                'error': "Documentation lookup timed out after 60s",
                'token_usage': 0,
                'metadata': {},
                'files_modified': []
            }
        except Exception as e:
            return {
                'status': SubAgentStatus.FAILED,
                'output': "",
                'error': f"Documentation lookup failed: {str(e)}",
                'token_usage': 0,
                'metadata': {},
                'files_modified': []
            }

    async def _execute_codebase_research(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute codebase research task.

        Args:
            task: Task to execute

        Returns:
            Result dictionary
        """
        search_query = task.description
        if 'query' in task.context:
            search_query = task.context['query']

        # Use LLM to guide codebase search
        system_prompt = RESEARCH_CODEBASE_PROMPT.format(query=search_query)

        try:
            # Add timeout protection for LLM call (60s)
            response, tokens = await asyncio.wait_for(
                self._call_llm(search_query, system_prompt),
                timeout=60.0
            )

            return {
                'status': SubAgentStatus.COMPLETED,
                'output': response,
                'token_usage': tokens,
                'metadata': {
                    'search_query': search_query,
                    'research_type': 'codebase'
                },
                'files_modified': []
            }
        except asyncio.TimeoutError:
            return {
                'status': SubAgentStatus.FAILED,
                'output': "",
                'error': "Codebase research timed out after 60s",
                'token_usage': 0,
                'metadata': {},
                'files_modified': []
            }
        except Exception as e:
            return {
                'status': SubAgentStatus.FAILED,
                'output': "",
                'error': f"Codebase research failed: {str(e)}",
                'token_usage': 0,
                'metadata': {},
                'files_modified': []
            }

    async def _execute_summarize(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute summarization task.

        Args:
            task: Task to execute

        Returns:
            Result dictionary
        """
        content = task.description
        if 'content' in task.context:
            content = task.context['content']

        system_prompt = RESEARCH_SUMMARIZE_PROMPT

        try:
            # Add timeout protection for LLM call (60s)
            response, tokens = await asyncio.wait_for(
                self._call_llm(
                    f"Summarize the following:\n\n{content}",
                    system_prompt
                ),
                timeout=60.0
            )

            return {
                'status': SubAgentStatus.COMPLETED,
                'output': response,
                'token_usage': tokens,
                'metadata': {
                    'summarization_type': 'text',
                    'original_length': len(content),
                    'summary_length': len(response)
                },
                'files_modified': []
            }
        except asyncio.TimeoutError:
            return {
                'status': SubAgentStatus.FAILED,
                'output': "",
                'error': "Summarization timed out after 60s",
                'token_usage': 0,
                'metadata': {},
                'files_modified': []
            }
        except Exception as e:
            return {
                'status': SubAgentStatus.FAILED,
                'output': "",
                'error': f"Summarization failed: {str(e)}",
                'token_usage': 0,
                'metadata': {},
                'files_modified': []
            }

    async def _execute_general_research(self, task: SubAgentTask) -> Dict[str, Any]:
        """Execute general research task.

        Args:
            task: Task to execute

        Returns:
            Result dictionary
        """
        # Use sequential thinking for complex research
        research_prompt = f"""Conduct comprehensive research on: {task.description}

Use sequential thinking to:
1. Break down the research question
2. Identify information sources needed
3. Gather and analyze information
4. Synthesize findings
5. Present conclusions

Provide a well-structured research report with sources."""

        try:
            # Add timeout protection for LLM call (60s)
            response, tokens = await asyncio.wait_for(
                self._call_llm(research_prompt),
                timeout=60.0
            )

            return {
                'status': SubAgentStatus.COMPLETED,
                'output': response,
                'token_usage': tokens,
                'metadata': {
                    'research_type': 'general',
                    'topic': task.description
                },
                'files_modified': []
            }
        except asyncio.TimeoutError:
            return {
                'status': SubAgentStatus.FAILED,
                'output': "",
                'error': "General research timed out after 60s",
                'token_usage': 0,
                'metadata': {},
                'files_modified': []
            }
        except Exception as e:
            return {
                'status': SubAgentStatus.FAILED,
                'output': "",
                'error': f"General research failed: {str(e)}",
                'token_usage': 0,
                'metadata': {},
                'files_modified': []
            }
