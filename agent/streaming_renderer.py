"""Streaming renderer for flicker-free token-by-token display.

This module provides incremental rendering to reduce visual flicker
and improve perceived performance during LLM response streaming.
"""

import asyncio
from typing import AsyncGenerator, Optional, Callable
from rich.console import Console
from rich.text import Text
from rich.live import Live
from rich.panel import Panel


class StreamingRenderer:
    """Incremental token-by-token rendering with flicker reduction.
    
    Features:
    - Token buffering to reduce render frequency
    - Time-based rendering (render every N ms)
    - Clean visual updates without screen flicker
    - Optional thinking indicator during streaming
    
    Example:
        renderer = StreamingRenderer(console)
        async def stream_tokens():
            async for token in model.generate_stream(prompt):
                yield token
        
        full_response = await renderer.render_stream(stream_tokens())
    """
    
    def __init__(
        self,
        console: Console,
        buffer_size: int = 5,
        render_interval: float = 0.05,
        show_thinking: bool = True
    ):
        """Initialize streaming renderer.
        
        Args:
            console: Rich console instance
            buffer_size: Number of tokens to buffer before rendering
            render_interval: Minimum seconds between renders (prevents flicker)
            show_thinking: Show thinking indicator while streaming
        """
        self.console = console
        self.buffer_size = buffer_size
        self.render_interval = render_interval
        self.show_thinking = show_thinking
        
        self._buffer: list[str] = []
        self._last_render_time: float = 0
        self._full_response: str = ""
        self._live_display: Optional[Live] = None
    
    async def render_stream(
        self,
        token_generator: AsyncGenerator[str, None],
        on_token: Optional[Callable[[str], None]] = None
    ) -> str:
        """Render streaming tokens with incremental updates.
        
        Args:
            token_generator: Async generator yielding tokens
            on_token: Optional callback for each token
            
        Returns:
            Complete accumulated response
        """
        import time
        
        self._buffer = []
        self._full_response = ""
        self._last_render_time = time.time()
        
        # Create live display for flicker-free updates
        with Live(
            self._create_initial_display(),
            console=self.console,
            refresh_per_second=20,  # 50ms between refreshes
            transient=False,
            vertical_overflow="visible"
        ) as live:
            self._live_display = live
            
            async for token in token_generator:
                self._buffer.append(token)
                self._full_response += token
                
                # Call token callback if provided
                if on_token:
                    on_token(token)
                
                # Render if buffer full or interval elapsed
                should_render = (
                    len(self._buffer) >= self.buffer_size or
                    (time.time() - self._last_render_time) >= self.render_interval
                )
                
                if should_render:
                    self._update_display(live)
                    self._buffer = []
                    self._last_render_time = time.time()
                
                await asyncio.sleep(0)  # Yield to event loop
            
            # Final render with any remaining tokens
            if self._buffer:
                self._update_display(live)
        
        self._live_display = None
        return self._full_response
    
    def _create_initial_display(self) -> Panel:
        """Create initial display with thinking indicator."""
        if self.show_thinking:
            return Panel(
                "[dim]Thinking...[/dim]",
                title="[bold cyan]Assistant[/bold cyan]",
                border_style="cyan",
                subtitle="[dim]Streaming response[/dim]"
            )
        return Panel(
            "",
            title="[bold cyan]Assistant[/bold cyan]",
            border_style="cyan"
        )
    
    def _update_display(self, live: Live) -> None:
        """Update live display with current content."""
        # Format response with syntax-aware rendering
        content = self._format_response(self._full_response)
        
        panel = Panel(
            content,
            title="[bold cyan]Assistant[/bold cyan]",
            border_style="cyan",
            subtitle=f"[dim]{len(self._full_response)} characters[/dim]"
        )
        
        live.update(panel)
    
    def _format_response(self, text: str) -> Text:
        """Format response text for display.
        
        Handles:
        - Code block detection
        - Basic markdown formatting
        - Proper line wrapping
        """
        # For now, return as Rich Text
        # Could enhance with markdown parsing
        return Text(text)


class ThinkingIndicator:
    """Animated thinking indicator during LLM processing."""
    
    ANIMATIONS = {
        'dots': '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏',
        'spinner': '◐◓◑◒',
        'bounce': '⠁⠂⠃⠄⠅⠆⠇⠈',
        'dots_pulse': '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏',
    }
    
    PHRASES = [
        "Thinking",
        "Processing",
        "Analyzing",
        "Generating response",
        "Working on it",
    ]
    
    def __init__(
        self,
        console: Console,
        animation: str = 'dots',
        show_phrase: bool = True
    ):
        """Initialize thinking indicator.
        
        Args:
            console: Rich console instance
            animation: Animation style name
            show_phrase: Show rotating phrase with animation
        """
        self.console = console
        self.animation = self.ANIMATIONS.get(animation, self.ANIMATIONS['dots'])
        self.show_phrase = show_phrase
        self._frame = 0
        self._phrase_index = 0
    
    def get_frame(self) -> str:
        """Get current animation frame."""
        frame = self.animation[self._frame % len(self.animation)]
        self._frame += 1
        
        if self.show_phrase:
            phrase = self.PHRASES[self._phrase_index % len(self.PHRASES)]
            # Change phrase every 10 frames
            if self._frame % 10 == 0:
                self._phrase_index += 1
            return f"{frame} {phrase}..."
        
        return frame
    
    def reset(self):
        """Reset animation to start."""
        self._frame = 0
        self._phrase_index = 0


async def stream_with_rendering(
    token_generator: AsyncGenerator[str, None],
    console: Optional[Console] = None,
    buffer_size: int = 5,
    show_thinking: bool = True
) -> str:
    """Convenience function for streaming with rendering.
    
    Args:
        token_generator: Async generator yielding tokens
        console: Rich console (creates default if None)
        buffer_size: Token buffer size
        show_thinking: Show thinking indicator
        
    Returns:
        Complete accumulated response
        
    Example:
        async for token in model.generate_stream(prompt):
            yield token
        
        response = await stream_with_rendering(token_generator)
    """
    if console is None:
        console = Console()
    
    renderer = StreamingRenderer(
        console=console,
        buffer_size=buffer_size,
        show_thinking=show_thinking
    )
    
    return await renderer.render_stream(token_generator)
