"""LLM Model management with token counting, cost monitoring, caching, retry logic, and streaming"""
import httpx
from typing import Dict, Any, Optional, Tuple, AsyncGenerator, Callable, List
from dataclasses import dataclass, field
import time
import json
import asyncio
import hashlib
from abc import ABC, abstractmethod

from .config import ModelConfig
from .utilities import get_token_count


# Token budget warning threshold (80% - warn user before exceeding)
TOKEN_BUDGET_WARNING_THRESHOLD = 0.80


@dataclass
class TokenUsage:
    """Track token usage for cost monitoring"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def __add__(self, other: 'TokenUsage') -> 'TokenUsage':
        return TokenUsage(
            self.prompt_tokens + other.prompt_tokens,
            self.completion_tokens + other.completion_tokens,
            self.total_tokens + other.total_tokens,
            self.cost + other.cost,
            self.timestamp
        )


class ResponseCache:
    """Cache LLM responses to avoid redundant API calls"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.cache: Dict[str, Tuple[str, TokenUsage, float]] = {}
        self.max_size = max_size
        self.ttl = ttl
    
    def _get_key(self, prompt: str, model: str) -> str:
        content = f"{model}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, prompt: str, model: str) -> Optional[Tuple[str, TokenUsage]]:
        key = self._get_key(prompt, model)
        if key in self.cache:
            content, usage, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return content, usage
            else:
                del self.cache[key]
        return None
    
    def set(self, prompt: str, model: str, content: str, usage: TokenUsage):
        key = self._get_key(prompt, model)
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][2])
            del self.cache[oldest_key]
        self.cache[key] = (content, usage, time.time())
    
    def clear(self):
        self.cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        now = time.time()
        valid = sum(1 for _, _, ts in self.cache.values() if now - ts < self.ttl)
        return {
            'size': len(self.cache),
            'valid_entries': valid,
            'max_size': self.max_size,
            'ttl': self.ttl
        }


class ModelBase(ABC):
    """Base class for all LLM models with retry logic and caching"""

    def __init__(self, config: ModelConfig, name: str,
                 budget_warning_callback: Optional[Callable[[str], None]] = None):
        self.config = config
        self.name = name
        self.client: Optional[httpx.AsyncClient] = None
        self.token_usage: TokenUsage = TokenUsage()
        self.request_count = 0
        self.last_request_time = 0.0
        self.max_retries = 3
        self.base_delay = 1.0
        self.max_delay = 30.0
        self.cache = ResponseCache(max_size=500, ttl=3600)  # 1 hour cache TTL
        self.budget_warning_callback = budget_warning_callback
        self._budget_warned = False  # Track if we already warned this session

    def check_budget_and_warn(self, daily_limit: int, force: bool = False) -> bool:
        """Check if approaching token budget, warn user if so.
        
        Args:
            daily_limit: Daily token budget limit
            force: Force warning even if already warned
            
        Returns:
            True if within budget, False if exceeded
        """
        if daily_limit <= 0:
            return True  # No limit set
            
        usage_pct = self.token_usage.total_tokens / daily_limit
        
        # Check if exceeded
        if self.token_usage.total_tokens >= daily_limit:
            return False
        
        # Check if should warn (only once per session unless force)
        if usage_pct >= TOKEN_BUDGET_WARNING_THRESHOLD and (not self._budget_warned or force):
            remaining = daily_limit - self.token_usage.total_tokens
            if self.budget_warning_callback:
                self.budget_warning_callback(
                    f"⚠️  Token Budget Warning: {usage_pct:.0%} of daily budget used\n"
                    f"   Remaining: {remaining:,} tokens"
                )
            self._budget_warned = True
        
        return True

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                timeout=self.config.timeout,
                follow_redirects=False,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self.client

    async def close(self):
        if self.client and not self.client.is_closed:
            await self.client.aclose()
            self.client = None

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Tuple[str, TokenUsage]:
        cached = self.cache.get(prompt, self.name)
        if cached:
            return cached
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                content, usage = await self._generate_with_retry(prompt, system_prompt)
                self.cache.set(prompt, self.name, content, usage)
                return content, usage
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    await asyncio.sleep(delay)
        
        raise last_error or Exception("Unknown error")

    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream response tokens as they arrive - NEW FEATURE"""
        async for token in self._generate_stream_impl(prompt, system_prompt):
            yield token

    async def _generate_stream_impl(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Streaming implementation - to be overridden by subclasses"""
        # Fallback to non-streaming if not implemented
        content, _ = await self.generate(prompt, system_prompt)
        yield content

    @abstractmethod
    async def _generate_with_retry(self, prompt: str, system_prompt: Optional[str] = None) -> Tuple[str, TokenUsage]:
        """Generate response with retry logic - must be implemented by subclasses"""

    async def generate_no_cache(self, prompt: str, system_prompt: Optional[str] = None) -> Tuple[str, TokenUsage]:
        return await self._generate_with_retry(prompt, system_prompt)

    def count_tokens(self, text: str) -> int:
        try:
            return get_token_count(text)
        except Exception:
            return len(text) // 4

    async def check_rate_limit_async(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < 60 / self.config.rate_limit:
            await asyncio.sleep(60 / self.config.rate_limit - elapsed)

    def update_usage(self, usage: TokenUsage):
        self.token_usage += usage
        self.request_count += 1
        self.last_request_time = time.time()

    def get_daily_usage(self) -> Dict[str, Any]:
        return {
            'requests': self.request_count,
            'tokens': self.token_usage.total_tokens,
            'cost': self.token_usage.cost,
            'cache_stats': self.cache.stats()
        }


class QwenCoderModel(ModelBase):
    """Qwen Coder API implementation with streaming support"""

    async def _generate_with_retry(self, prompt: str, system_prompt: Optional[str] = None) -> Tuple[str, TokenUsage]:
        await self.check_rate_limit_async()
        headers = {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json'
        }
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        payload = {
            'model': self.config.model,
            'input': {'messages': messages},
            'parameters': {
                'temperature': 0.7,
                'top_p': 0.8,
                'result_format': 'message'
            }
        }
        client = await self._get_client()
        try:
            response = await client.post(self.config.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            if 'output' not in data or 'choices' not in data.get('output', {}):
                raise Exception(f"Qwen API returned unexpected response: {data}")
            choices = data['output']['choices']
            if not choices or len(choices) == 0:
                raise Exception("Qwen API returned no choices")
            content = choices[0]['message']['content']
            prompt_tokens = self.count_tokens(prompt)
            completion_tokens = self.count_tokens(content)
            total_tokens = prompt_tokens + completion_tokens
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=0.0
            )
            self.update_usage(usage)
            return content, usage
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait_time = 60 / self.config.rate_limit
                raise Exception(
                    f"Rate limit exceeded. Wait {wait_time:.0f}s. "
                    f"Tip: For web content fetching, use the MCP 'fetch' tool (@fetch <url>) "
                    f"which doesn't count against LLM API rate limits."
                )
            raise Exception(f"Qwen API HTTP error {e.response.status_code}: {str(e)}")
        except httpx.RequestError as e:
            raise Exception(f"Qwen API request failed: {str(e)}")
        except KeyError as e:
            raise Exception(f"Qwen API unexpected response format: {str(e)}")

    async def _generate_stream_impl(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream tokens from Qwen API with timeout and stall detection - NEW FEATURE"""
        await self.check_rate_limit_async()
        headers = {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json'
        }
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        payload = {
            'model': self.config.model,
            'input': {'messages': messages},
            'parameters': {
                'temperature': 0.7,
                'top_p': 0.8,
                'result_format': 'message',
                'incremental_output': True  # Enable streaming
            }
        }
        # Use streaming endpoint
        url = f"{self.config.base_url}/stream"
        client = await self._get_client()

        accumulated_content = ""
        last_token_time = time.time()
        stall_threshold = 30.0  # Consider stream dead if no tokens for 30s
        max_stalls = 3  # Allow 3 stalls before giving up
        stream_timeout = self.config.timeout * 2  # Allow 2x normal timeout for streaming

        try:
            async with client.stream('POST', url, headers=headers, json=payload, timeout=stream_timeout) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    # Check for stall
                    elapsed = time.time() - last_token_time
                    if elapsed > stall_threshold:
                        max_stalls -= 1
                        if max_stalls <= 0:
                            raise Exception(f"Stream stalled: No tokens received for {elapsed:.0f}s")
                    else:
                        max_stalls = 3  # Reset stall counter on activity

                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        if data_str.strip() and data_str.strip() != '[DONE]':
                            try:
                                data = json.loads(data_str)
                                if 'output' in data and 'choices' in data.get('output', {}):
                                    choices = data['output']['choices']
                                    if choices and len(choices) > 0:
                                        delta = choices[0].get('message', {}).get('content', '')
                                        if delta:
                                            accumulated_content += delta
                                            last_token_time = time.time()  # Update activity timestamp
                                            yield delta  # Stream each token
                            except json.JSONDecodeError:
                                # Log but continue - occasional malformed JSON is normal in SSE
                                continue

            # Count tokens for usage tracking
            prompt_tokens = self.count_tokens(prompt)
            completion_tokens = self.count_tokens(accumulated_content)
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost=0.0
            )
            self.update_usage(usage)

        except asyncio.TimeoutError:
            raise Exception(f"Stream timeout after {stream_timeout}s. The API may be overloaded.")
        except httpx.ReadTimeout:
            raise Exception("Read timeout: API stopped sending data. Try again or reduce response length.")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait_time = 60 / self.config.rate_limit
                raise Exception(
                    f"Rate limit exceeded. Wait {wait_time:.0f}s. "
                    f"Tip: For web content fetching, use the MCP 'fetch' tool (@fetch <url>) "
                    f"which doesn't count against LLM API rate limits."
                )
            raise Exception(f"Qwen API HTTP error {e.response.status_code}: {str(e)}")
        except httpx.RequestError as e:
            raise Exception(f"Qwen API request failed: {str(e)}")
        except Exception as e:
            if "stalled" in str(e).lower():
                raise Exception(f"Stream stalled: {str(e)}")
            raise


class GeminiModel(ModelBase):
    """Gemini API implementation with streaming support"""

    async def _generate_with_retry(self, prompt: str, system_prompt: Optional[str] = None) -> Tuple[str, TokenUsage]:
        await self.check_rate_limit_async()
        headers = {'Content-Type': 'application/json'}
        contents = []
        if system_prompt:
            contents.append({'role': 'user', 'parts': [{'text': system_prompt}]})
            contents.append({'role': 'model', 'parts': [{'text': 'Understood.'}]})
        contents.append({'role': 'user', 'parts': [{'text': prompt}]})
        payload = {
            'contents': contents,
            'generationConfig': {
                'temperature': 0.7,
                'topP': 0.8,
                'maxOutputTokens': 8192  # Increased from 2048 to prevent truncation
            }
        }
        url = f"{self.config.base_url}/{self.config.model}:generateContent?key={self.config.api_key}"
        client = await self._get_client()
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            if 'candidates' not in data or not data['candidates']:
                raise Exception(f"Gemini API returned no candidates: {data}")
            content = data['candidates'][0]['content']['parts'][0]['text']
            usage_metadata = data.get('usageMetadata', {})
            prompt_tokens = int(usage_metadata.get('promptTokenCount', self.count_tokens(prompt)))
            completion_tokens = int(usage_metadata.get('candidatesTokenCount', self.count_tokens(content)))
            total_tokens = int(usage_metadata.get('totalTokenCount', prompt_tokens + completion_tokens))
            cost = 0.0
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost
            )
            self.update_usage(usage)
            return content, usage
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait_time = 60 / self.config.rate_limit
                raise Exception(
                    f"Rate limit exceeded. Wait {wait_time:.0f}s. "
                    f"Tip: For web content fetching, use the MCP 'fetch' tool (@fetch <url>) "
                    f"which doesn't count against LLM API rate limits."
                )
            raise Exception(f"API HTTP error {e.response.status_code}: {str(e)}")
        except httpx.RequestError as e:
            raise Exception(f"Gemini API request failed: {str(e)}")
        except KeyError as e:
            raise Exception(f"Gemini API unexpected response format: {str(e)}")

    async def _generate_stream_impl(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream tokens from Gemini API with timeout protection - NEW FEATURE"""
        await self.check_rate_limit_async()
        headers = {'Content-Type': 'application/json'}
        contents = []
        if system_prompt:
            contents.append({'role': 'user', 'parts': [{'text': system_prompt}]})
            contents.append({'role': 'model', 'parts': [{'text': 'Understood.'}]})
        contents.append({'role': 'user', 'parts': [{'text': prompt}]})
        payload = {
            'contents': contents,
            'generationConfig': {
                'temperature': 0.7,
                'topP': 0.8,
                'maxOutputTokens': 8192  # Increased from 2048 to prevent truncation
            }
        }
        # Use streaming endpoint
        url = f"{self.config.base_url}/{self.config.model}:streamGenerateContent?key={self.config.api_key}&alt=sse"
        client = await self._get_client()

        accumulated_content = ""

        # Timeout and stall detection
        stream_timeout = self.config.timeout * 2  # Allow 2x normal timeout for streaming
        last_token_time = time.time()
        stall_threshold = 30.0  # Consider stream dead if no token for 30s
        max_stalls = 3  # Allow 3 stalls before giving up

        try:
            async with client.stream('POST', url, json=payload, headers=headers, timeout=stream_timeout) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    # Check for stall
                    elapsed = time.time() - last_token_time
                    if elapsed > stall_threshold:
                        max_stalls -= 1
                        if max_stalls <= 0:
                            raise Exception(f"Stream stalled: No tokens received for {elapsed:.0f}s")
                        # Continue but warn
                    else:
                        max_stalls = 3  # Reset stall counter on activity
                    
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        if data_str.strip():
                            try:
                                data = json.loads(data_str)
                                if 'candidates' in data and data['candidates']:
                                    candidate = data['candidates'][0]
                                    if 'content' in candidate and 'parts' in candidate['content']:
                                        for part in candidate['content']['parts']:
                                            if 'text' in part:
                                                token = part['text']
                                                accumulated_content += token
                                                last_token_time = time.time()  # Update activity timestamp
                                                yield token  # Stream each token
                            except json.JSONDecodeError:
                                # Log but continue - occasional malformed JSON is normal in SSE
                                continue

            # Count tokens for usage tracking
            prompt_tokens = self.count_tokens(prompt)
            completion_tokens = self.count_tokens(accumulated_content)
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost=0.0
            )
            self.update_usage(usage)

        except asyncio.TimeoutError:
            raise Exception(f"Stream timeout after {stream_timeout}s. The API may be overloaded.")
        except httpx.ReadTimeout:
            raise Exception("Read timeout: API stopped sending data. Try again or reduce response length.")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait_time = 60 / self.config.rate_limit
                raise Exception(
                    f"Rate limit exceeded. Wait {wait_time:.0f}s. "
                    f"Tip: For web content fetching, use the MCP 'fetch' tool (@fetch <url>) "
                    f"which doesn't count against LLM API rate limits."
                )
            raise Exception(f"API HTTP error {e.response.status_code}: {str(e)}")
        except httpx.RequestError as e:
            raise Exception(f"Gemini API request failed: {str(e)}")
        except Exception as e:
            if "stalled" in str(e).lower():
                raise Exception(f"Stream stalled: {str(e)}")
            raise


class OpenAIModel(ModelBase):
    """OpenAI API implementation (GPT-4, GPT-4 Turbo, o1)"""

    async def _generate_with_retry(self, prompt: str, system_prompt: Optional[str] = None) -> Tuple[str, TokenUsage]:
        await self.check_rate_limit_async()
        headers = {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json'
        }
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        payload = {
            'model': self.config.model,
            'messages': messages,
            'temperature': 0.7,
            'max_tokens': 4096
        }
        client = await self._get_client()
        try:
            response = await client.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            if 'choices' not in data or not data['choices']:
                raise Exception(f"OpenAI API returned no choices: {data}")
            content = data['choices'][0]['message']['content']
            usage_data = data.get('usage', {})
            prompt_tokens = int(usage_data.get('prompt_tokens', self.count_tokens(prompt)))
            completion_tokens = int(usage_data.get('completion_tokens', self.count_tokens(content)))
            total_tokens = int(usage_data.get('total_tokens', prompt_tokens + completion_tokens))
            # Cost calculation (approximate, varies by model)
            cost = self._calculate_cost(prompt_tokens, completion_tokens)
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost
            )
            self.update_usage(usage)
            return content, usage
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise Exception(f"Rate limit exceeded. Please wait before retrying.")
            raise Exception(f"OpenAI API HTTP error {e.response.status_code}: {str(e)}")
        except httpx.RequestError as e:
            raise Exception(f"OpenAI API request failed: {str(e)}")
        except KeyError as e:
            raise Exception(f"OpenAI API unexpected response format: {str(e)}")

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate approximate cost based on model."""
        # Approximate costs per 1K tokens (varies by model)
        costs = {
            'gpt-4o': {'prompt': 0.005, 'completion': 0.015},
            'gpt-4-turbo': {'prompt': 0.01, 'completion': 0.03},
            'gpt-4': {'prompt': 0.03, 'completion': 0.06},
            'o1-preview': {'prompt': 0.015, 'completion': 0.06},
            'o1-mini': {'prompt': 0.003, 'completion': 0.012},
        }
        rates = costs.get(self.config.model, {'prompt': 0.03, 'completion': 0.06})
        return (prompt_tokens * rates['prompt'] + completion_tokens * rates['completion']) / 1000

    async def _generate_stream_impl(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream tokens from OpenAI API with SSE"""
        await self.check_rate_limit_async()
        headers = {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json'
        }
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        payload = {
            'model': self.config.model,
            'messages': messages,
            'temperature': 0.7,
            'max_tokens': 4096,
            'stream': True
        }
        client = await self._get_client()
        url = f"{self.config.base_url}/chat/completions"
        
        accumulated_content = ""
        last_token_time = time.time()
        stall_threshold = 30.0
        max_stalls = 3
        stream_timeout = self.config.timeout * 2

        try:
            async with client.stream('POST', url, headers=headers, json=payload, timeout=stream_timeout) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    elapsed = time.time() - last_token_time
                    if elapsed > stall_threshold:
                        max_stalls -= 1
                        if max_stalls <= 0:
                            raise Exception(f"Stream stalled: No tokens for {elapsed:.0f}s")
                    else:
                        max_stalls = 3

                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str.strip() and data_str.strip() != '[DONE]':
                            try:
                                data = json.loads(data_str)
                                choices = data.get('choices', [])
                                if choices and len(choices) > 0:
                                    delta = choices[0].get('delta', {}).get('content', '')
                                    if delta:
                                        accumulated_content += delta
                                        last_token_time = time.time()
                                        yield delta
                            except json.JSONDecodeError:
                                continue

            # Update usage
            prompt_tokens = self.count_tokens(prompt)
            completion_tokens = self.count_tokens(accumulated_content)
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost=self._calculate_cost(prompt_tokens, completion_tokens)
            )
            self.update_usage(usage)

        except asyncio.TimeoutError:
            raise Exception(f"Stream timeout after {stream_timeout}s")
        except httpx.ReadTimeout:
            raise Exception("Read timeout: API stopped sending data")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise Exception(f"Rate limit exceeded. Please wait before retrying.")
            raise Exception(f"OpenAI API HTTP error {e.response.status_code}: {str(e)}")
        except httpx.RequestError as e:
            raise Exception(f"OpenAI API request failed: {str(e)}")
        except Exception as e:
            if "stalled" in str(e).lower():
                raise Exception(f"Stream stalled: {str(e)}")
            raise


class AnthropicModel(ModelBase):
    """Anthropic API implementation (Claude)"""

    async def _generate_with_retry(self, prompt: str, system_prompt: Optional[str] = None) -> Tuple[str, TokenUsage]:
        await self.check_rate_limit_async()
        headers = {
            'x-api-key': self.config.api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        payload = {
            'model': self.config.model,
            'max_tokens': 4096,
            'messages': [{'role': 'user', 'content': prompt}]
        }
        if system_prompt:
            payload['system'] = system_prompt
        client = await self._get_client()
        try:
            response = await client.post(
                f"{self.config.base_url}/v1/messages",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            if 'content' not in data or not data['content']:
                raise Exception(f"Anthropic API returned no content: {data}")
            content = data['content'][0]['text']
            usage_data = data.get('usage', {})
            prompt_tokens = int(usage_data.get('input_tokens', self.count_tokens(prompt)))
            completion_tokens = int(usage_data.get('output_tokens', self.count_tokens(content)))
            total_tokens = prompt_tokens + completion_tokens
            # Cost calculation
            cost = self._calculate_cost(prompt_tokens, completion_tokens)
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost
            )
            self.update_usage(usage)
            return content, usage
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise Exception(f"Anthropic API rate limit exceeded.")
            raise Exception(f"Anthropic API HTTP error {e.response.status_code}: {str(e)}")
        except httpx.RequestError as e:
            raise Exception(f"Anthropic API request failed: {str(e)}")
        except KeyError as e:
            raise Exception(f"Anthropic API unexpected response format: {str(e)}")

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate approximate cost based on model."""
        costs = {
            'claude-sonnet-4-20250514': {'prompt': 0.003, 'completion': 0.015},
            'claude-opus-20240229': {'prompt': 0.015, 'completion': 0.075},
            'claude-3-5-sonnet': {'prompt': 0.003, 'completion': 0.015},
        }
        rates = costs.get(self.config.model, {'prompt': 0.003, 'completion': 0.015})
        return (prompt_tokens * rates['prompt'] + completion_tokens * rates['completion']) / 1000

    async def _generate_stream_impl(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream tokens from Anthropic API with SSE"""
        await self.check_rate_limit_async()
        headers = {
            'x-api-key': self.config.api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        payload = {
            'model': self.config.model,
            'max_tokens': 4096,
            'messages': [{'role': 'user', 'content': prompt}],
            'stream': True
        }
        if system_prompt:
            payload['system'] = system_prompt
        
        client = await self._get_client()
        url = f"{self.config.base_url}/v1/messages"
        
        accumulated_content = ""
        last_token_time = time.time()
        stall_threshold = 30.0
        max_stalls = 3
        stream_timeout = self.config.timeout * 2

        try:
            async with client.stream('POST', url, headers=headers, json=payload, timeout=stream_timeout) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    elapsed = time.time() - last_token_time
                    if elapsed > stall_threshold:
                        max_stalls -= 1
                        if max_stalls <= 0:
                            raise Exception(f"Stream stalled: No tokens for {elapsed:.0f}s")
                    else:
                        max_stalls = 3

                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str.strip() and data_str.strip() != '[DONE]':
                            try:
                                data = json.loads(data_str)
                                if data.get('type') == 'content_block_delta':
                                    delta = data.get('delta', {}).get('text', '')
                                    if delta:
                                        accumulated_content += delta
                                        last_token_time = time.time()
                                        yield delta
                            except json.JSONDecodeError:
                                continue

            # Update usage
            prompt_tokens = self.count_tokens(prompt)
            completion_tokens = self.count_tokens(accumulated_content)
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost=self._calculate_cost(prompt_tokens, completion_tokens)
            )
            self.update_usage(usage)

        except asyncio.TimeoutError:
            raise Exception(f"Stream timeout after {stream_timeout}s")
        except httpx.ReadTimeout:
            raise Exception("Read timeout: API stopped sending data")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise Exception(f"Anthropic API rate limit exceeded.")
            raise Exception(f"Anthropic API HTTP error {e.response.status_code}: {str(e)}")
        except httpx.RequestError as e:
            raise Exception(f"Anthropic API request failed: {str(e)}")
        except Exception as e:
            if "stalled" in str(e).lower():
                raise Exception(f"Stream stalled: {str(e)}")
            raise


class OpenRouterModel(ModelBase):
    """OpenRouter API implementation (100+ models via single API)"""

    async def _generate_with_retry(self, prompt: str, system_prompt: Optional[str] = None) -> Tuple[str, TokenUsage]:
        await self.check_rate_limit_async()
        headers = {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/stephanos8926-lgtm/rapidwebs-agent',
            'X-Title': 'RapidWebs Agent'
        }
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        payload = {
            'model': self.config.model,
            'messages': messages,
            'temperature': 0.7,
            'max_tokens': 4096
        }
        client = await self._get_client()
        try:
            response = await client.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            if 'choices' not in data or not data['choices']:
                raise Exception(f"OpenRouter API returned no choices: {data}")
            content = data['choices'][0]['message']['content']
            usage_data = data.get('usage', {})
            prompt_tokens = int(usage_data.get('prompt_tokens', self.count_tokens(prompt)))
            completion_tokens = int(usage_data.get('completion_tokens', self.count_tokens(content)))
            total_tokens = int(usage_data.get('total_tokens', prompt_tokens + completion_tokens))
            # OpenRouter provides cost in response
            cost_data = data.get('provider', {}).get('request_cost', 0.0)
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=float(cost_data) if cost_data else 0.0
            )
            self.update_usage(usage)
            return content, usage
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise Exception(f"OpenRouter API rate limit exceeded.")
            raise Exception(f"OpenRouter API HTTP error {e.response.status_code}: {str(e)}")
        except httpx.RequestError as e:
            raise Exception(f"OpenRouter API request failed: {str(e)}")
        except KeyError as e:
            raise Exception(f"OpenRouter API unexpected response format: {str(e)}")

    async def _generate_stream_impl(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream tokens from OpenRouter API with SSE"""
        await self.check_rate_limit_async()
        headers = {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/stephanos8926-lgtm/rapidwebs-agent',
            'X-Title': 'RapidWebs Agent'
        }
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        payload = {
            'model': self.config.model,
            'messages': messages,
            'temperature': 0.7,
            'max_tokens': 4096,
            'stream': True
        }
        client = await self._get_client()
        url = f"{self.config.base_url}/chat/completions"
        
        accumulated_content = ""
        last_token_time = time.time()
        stall_threshold = 30.0
        max_stalls = 3
        stream_timeout = self.config.timeout * 2

        try:
            async with client.stream('POST', url, headers=headers, json=payload, timeout=stream_timeout) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    elapsed = time.time() - last_token_time
                    if elapsed > stall_threshold:
                        max_stalls -= 1
                        if max_stalls <= 0:
                            raise Exception(f"Stream stalled: No tokens for {elapsed:.0f}s")
                    else:
                        max_stalls = 3

                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str.strip() and data_str.strip() != '[DONE]':
                            try:
                                data = json.loads(data_str)
                                choices = data.get('choices', [])
                                if choices and len(choices) > 0:
                                    delta = choices[0].get('delta', {}).get('content', '')
                                    if delta:
                                        accumulated_content += delta
                                        last_token_time = time.time()
                                        yield delta
                            except json.JSONDecodeError:
                                continue

            # Update usage
            prompt_tokens = self.count_tokens(prompt)
            completion_tokens = self.count_tokens(accumulated_content)
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost=0.0  # Cost will be inaccurate for streaming, set to 0
            )
            self.update_usage(usage)

        except asyncio.TimeoutError:
            raise Exception(f"Stream timeout after {stream_timeout}s")
        except httpx.ReadTimeout:
            raise Exception("Read timeout: API stopped sending data")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise Exception(f"OpenRouter API rate limit exceeded.")
            raise Exception(f"OpenRouter API HTTP error {e.response.status_code}: {str(e)}")
        except httpx.RequestError as e:
            raise Exception(f"OpenRouter API request failed: {str(e)}")
        except Exception as e:
            if "stalled" in str(e).lower():
                raise Exception(f"Stream stalled: {str(e)}")
            raise


class ModelManager:
    """Manage multiple LLM models and routing"""

    def __init__(self, config, budget_warning_callback: Optional[Callable[[str], None]] = None):
        self.config = config
        self.models: Dict[str, ModelBase] = {}
        self.budget_warning_callback = budget_warning_callback
        self._initialize_models()

    def _initialize_models(self):
        for name, model_config in self.config.models.items():
            if not model_config.enabled:
                continue
            if name == 'qwen_coder':
                self.models[name] = QwenCoderModel(model_config, name, self.budget_warning_callback)
            elif name == 'gemini':
                self.models[name] = GeminiModel(model_config, name, self.budget_warning_callback)
            elif name.startswith('openai_') or name in ['gpt-4o', 'gpt-4-turbo', 'o1-preview', 'o1-mini']:
                self.models[name] = OpenAIModel(model_config, name, self.budget_warning_callback)
            elif name.startswith('anthropic_') or name in ['claude-sonnet-4-20250514', 'claude-opus-20240229']:
                self.models[name] = AnthropicModel(model_config, name, self.budget_warning_callback)
            elif name.startswith('openrouter_') or '/' in name:
                # OpenRouter models typically have format: provider/model
                self.models[name] = OpenRouterModel(model_config, name, self.budget_warning_callback)

    def check_budget(self, daily_limit: int, force: bool = False) -> bool:
        """Check budget across all models.

        Args:
            daily_limit: Daily token budget limit
            force: Force warning even if already warned

        Returns:
            True if within budget, False if exceeded
        """
        # Check primary model (default)
        primary_model = self.config.default_model
        if primary_model in self.models:
            return self.models[primary_model].check_budget_and_warn(daily_limit, force)
        return True

    async def generate_with_fallback(self, prompt: str, system_prompt: Optional[str] = None,
                                    fallback_order: Optional[List[str]] = None) -> Tuple[str, TokenUsage, str]:
        """Generate with automatic fallback on rate limits.

        Args:
            prompt: Input prompt
            system_prompt: Optional system prompt
            fallback_order: List of model names to try in order (default: all enabled models)

        Returns:
            Tuple of (response, token_usage, model_used)

        Raises:
            Exception: If all models fail
        """
        if fallback_order is None:
            fallback_order = list(self.models.keys())

        last_error = None
        for model_name in fallback_order:
            if model_name not in self.models:
                continue

            model = self.models[model_name]
            try:
                response, usage = await model.generate(prompt, system_prompt)
                return response, usage, model_name
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                # Check if rate limit error - try next model
                if 'rate limit' in error_msg or '429' in error_msg:
                    continue
                # For other errors, raise immediately
                raise

        # All models failed
        raise Exception(f"All models failed. Last error: {last_error}")

    async def generate_stream_with_fallback(self, prompt: str, system_prompt: Optional[str] = None,
                                           fallback_order: Optional[List[str]] = None) -> AsyncGenerator[Tuple[str, TokenUsage], None]:
        """Stream with automatic fallback on rate limits.

        Args:
            prompt: Input prompt
            system_prompt: Optional system prompt
            fallback_order: List of model names to try in order

        Yields:
            Tuple of (token, token_usage)
        """
        if fallback_order is None:
            fallback_order = list(self.models.keys())

        last_error = None
        for model_name in fallback_order:
            if model_name not in self.models:
                continue

            model = self.models[model_name]
            try:
                async for token in model.generate_stream(prompt, system_prompt):
                    yield token, model.token_usage
                return  # Success
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                if 'rate limit' in error_msg or '429' in error_msg:
                    continue
                raise

        raise Exception(f"All models failed streaming. Last error: {last_error}")

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary across all models.

        Returns:
            Dictionary with cost breakdown by model and total
        """
        summary = {
            'models': {},
            'total_cost': 0.0,
            'total_tokens': 0,
            'total_requests': 0
        }

        for name, model in self.models.items():
            usage = model.get_daily_usage()
            model_cost = usage.get('cost', 0.0)
            model_tokens = usage.get('tokens', 0)
            model_requests = usage.get('requests', 0)

            summary['models'][name] = {
                'cost': model_cost,
                'tokens': model_tokens,
                'requests': model_requests
            }
            summary['total_cost'] += model_cost
            summary['total_tokens'] += model_tokens
            summary['total_requests'] += model_requests

        return summary

    async def generate(self, prompt: str, model_name: Optional[str] = None,
                      system_prompt: Optional[str] = None) -> Tuple[str, TokenUsage, str]:
        model_name = model_name or self.config.default_model
        if model_name not in self.models:
            raise ValueError(f"Model '{model_name}' not configured or disabled")
        model = self.models[model_name]
        response, usage = await model.generate(prompt, system_prompt)
        return response, usage, model_name

    async def generate_stream(self, prompt: str, model_name: Optional[str] = None,
                             system_prompt: Optional[str] = None) -> AsyncGenerator[Tuple[str, TokenUsage], None]:
        """Stream response with usage info - NEW FEATURE"""
        model_name = model_name or self.config.default_model
        if model_name not in self.models:
            raise ValueError(f"Model '{model_name}' not configured or disabled")
        model = self.models[model_name]
        async for token in model.generate_stream(prompt, system_prompt):
            yield token, model.token_usage

    async def generate_no_cache(self, prompt: str, model_name: Optional[str] = None,
                                system_prompt: Optional[str] = None) -> Tuple[str, TokenUsage, str]:
        model_name = model_name or self.config.default_model
        if model_name not in self.models:
            raise ValueError(f"Model '{model_name}' not configured or disabled")
        model = self.models[model_name]
        response, usage = await model.generate_no_cache(prompt, system_prompt)
        return response, usage, model_name

    def get_model_stats(self) -> Dict[str, Dict]:
        return {name: model.get_daily_usage() for name, model in self.models.items()}

    @property
    def current_model(self) -> str:
        """Get the current default model name."""
        return self.config.default_model

    def switch_model(self, model_name: str):
        if model_name not in self.models:
            raise ValueError(f"Model '{model_name}' not available")
        self.config.set('default_model', model_name)

    async def close(self):
        for model in self.models.values():
            await model.close()

    def clear_cache(self, model_name: Optional[str] = None):
        if model_name:
            if model_name in self.models:
                self.models[model_name].cache.clear()
        else:
            for model in self.models.values():
                model.cache.clear()
