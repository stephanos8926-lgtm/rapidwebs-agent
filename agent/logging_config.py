"""Logging configuration for RapidWebs Agent.

This module provides structured logging with file rotation,
session-based log files, and optional JSON formatting.
"""

import logging
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any
import json


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'pathname', 'process', 'processName', 'relativeCreated',
                          'stack_info', 'exc_info', 'thread', 'threadName'):
                log_data[key] = value

        return json.dumps(log_data)


class SessionLogFilter(logging.Filter):
    """Filter to add session ID to log records."""

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id

    def filter(self, record: logging.LogRecord) -> bool:
        """Add session ID to log record."""
        record.session_id = self.session_id
        return True


def get_log_directory() -> Path:
    """Get the log directory path.

    Returns:
        Path to the log directory
    """
    import os

    # Try multiple locations in order of preference
    candidates = []

    if sys.platform == 'win32':
        # Windows: Try LOCALAPPDATA first, then project dir, then temp
        local_appdata = os.environ.get('LOCALAPPDATA')
        if local_appdata:
            candidates.append(Path(local_appdata) / 'rapidwebs-agent' / 'logs')
        candidates.append(Path.home() / 'AppData' / 'Local' / 'rapidwebs-agent' / 'logs')
    elif sys.platform == 'darwin':
        # macOS: ~/Library/Logs/rapidwebs-agent
        candidates.append(Path.home() / 'Library' / 'Logs' / 'rapidwebs-agent' / 'logs')
    else:
        # Linux/Unix: ~/.local/share/rapidwebs-agent/logs
        candidates.append(Path.home() / '.local' / 'share' / 'rapidwebs-agent' / 'logs')

    # Always add project-based and temp fallbacks
    # Project-based: works well for development
    try:
        import agent
        project_dir = Path(agent.__file__).parent.parent
        candidates.append(project_dir / '.logs')
    except (ImportError, AttributeError):
        pass

    # Temp directory: always writable
    candidates.append(Path(tempfile.gettempdir()) / 'rapidwebs-agent' / 'logs')

    # Try each location until one works
    last_error = None
    for log_dir in candidates:
        try:
            # Create directory with parents
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Verify it actually exists
            if not log_dir.exists():
                continue
                
            # Test write access by creating a test file
            test_file = log_dir / f'.write_test_{os.getpid()}'
            try:
                test_file.write_text('test')
                test_file.unlink(missing_ok=True)
                # Successfully created and wrote to directory
                return log_dir
            except (PermissionError, OSError) as write_error:
                last_error = write_error
                continue
        except (PermissionError, OSError) as dir_error:
            last_error = dir_error
            continue

    # If all candidates failed, force use temp directory
    try:
        fallback_dir = Path(tempfile.gettempdir()) / 'rapidwebs-agent' / 'logs'
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir
    except Exception as final_error:
        # Ultimate fallback - should never reach here
        raise RuntimeError(
            f"Unable to create log directory. Tried: {candidates}. "
            f"Last error: {last_error or final_error}"
        )


def setup_logging(
    level: str = 'INFO',
    log_to_file: bool = True,
    log_to_console: bool = True,
    json_format: bool = False,
    session_id: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """Set up logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Enable file logging
        log_to_console: Enable console logging
        json_format: Use JSON format for logs
        session_id: Session identifier (auto-generated if not provided)
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup log files to keep

    Returns:
        Configured logger instance
    """
    # Generate session ID if not provided
    if session_id is None:
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Create logger
    logger = logging.getLogger('rapidwebs_agent')
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler with rotation
    if log_to_file:
        try:
            log_dir = get_log_directory()
            log_file = log_dir / f'session_{session_id}.log'

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
            file_handler.setFormatter(formatter)

            # Add session filter
            session_filter = SessionLogFilter(session_id)
            file_handler.addFilter(session_filter)

            logger.addHandler(file_handler)
            
            # Log the log file location for debugging
            logger.debug(f'Log file created at: {log_file}')
        except Exception as file_error:
            # Log to console that file logging failed
            print(f"Warning: File logging failed to initialize: {file_error}")
            print("Logs will only appear in console. Check permissions and disk space.")
            # Still continue with console logging

    # Log startup message
    logger.info(f'RapidWebs Agent logging initialized (session: {session_id})')
    
    # Log the log directory location at INFO level so users know where to find logs
    if log_to_file:
        try:
            log_dir = get_log_directory()
            logger.info(f'Log files location: {log_dir}')
        except Exception:
            pass

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (uses 'rapidwebs_agent' if not provided)

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f'rapidwebs_agent.{name}')
    return logging.getLogger('rapidwebs_agent')


class LogContext:
    """Context manager for adding extra context to logs."""

    def __init__(self, logger: logging.Logger, **kwargs):
        """Initialize log context.

        Args:
            logger: Logger instance
            **kwargs: Extra context to add to logs
        """
        self.logger = logger
        self.context = kwargs
        self.handler: Optional[logging.Handler] = None

    def __enter__(self):
        """Add context filter to logger."""
        class ContextFilter(logging.Filter):
            def __init__(self, context: Dict[str, Any]):
                self.context = context

            def filter(self, record: logging.LogRecord) -> bool:
                for key, value in self.context.items():
                    setattr(record, key, value)
                return True

        self.handler = logging.Filter()
        self.handler.filter = ContextFilter(self.context).filter
        self.logger.addFilter(self.handler)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Remove context filter from logger."""
        if self.handler:
            self.logger.removeFilter(self.handler)


def log_function_call(logger: logging.Logger):
    """Decorator to log function calls.

    Args:
        logger: Logger instance

    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f'Calling {func.__name__} with args={args}, kwargs={kwargs}')
            try:
                result = func(*args, **kwargs)
                logger.debug(f'{func.__name__} returned {result}')
                return result
            except Exception as e:
                logger.error(f'{func.__name__} raised {type(e).__name__}: {e}')
                raise
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator
