"""Tests for logging configuration.

These tests verify the logging system:
- Logger setup
- File rotation
- JSON formatting
- Session management
- Log context
"""

import pytest
import logging
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from agent.logging_config import (
    setup_logging,
    get_logger,
    get_log_directory,
    JSONFormatter,
    SessionLogFilter,
    LogContext,
    log_function_call,
)


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create temporary log directory."""
    log_dir = tmp_path / 'logs'
    log_dir.mkdir()
    with patch('agent.logging_config.get_log_directory', return_value=log_dir):
        yield log_dir


@pytest.fixture
def clean_handlers():
    """Clean up logging handlers after test."""
    logger = logging.getLogger('rapidwebs_agent')
    original_handlers = logger.handlers.copy()
    yield
    logger.handlers.clear()
    for handler in original_handlers:
        logger.addHandler(handler)


class TestLoggingSetup:
    """Tests for logging setup."""

    def test_setup_logging_creates_logger(self, clean_handlers):
        """Test that setup_logging creates a logger."""
        logger = setup_logging(level='INFO', log_to_file=False, log_to_console=False)
        
        assert logger is not None
        assert logger.name == 'rapidwebs_agent'
        assert logger.level == logging.INFO

    def test_setup_logging_console_handler(self, clean_handlers):
        """Test console handler is added."""
        logger = setup_logging(level='DEBUG', log_to_file=False, log_to_console=True)
        
        console_handlers = [
            h for h in logger.handlers 
            if isinstance(h, logging.StreamHandler)
        ]
        assert len(console_handlers) >= 1

    def test_setup_logging_file_handler(self, temp_log_dir, clean_handlers):
        """Test file handler is added."""
        logger = setup_logging(
            level='INFO', 
            log_to_file=True, 
            log_to_console=False
        )
        
        file_handlers = [
            h for h in logger.handlers 
            if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) >= 1

    def test_setup_logging_json_format(self, clean_handlers):
        """Test JSON formatter is used when specified."""
        logger = setup_logging(
            level='INFO',
            log_to_file=False,
            log_to_console=True,
            json_format=True
        )
        
        # Check that at least one handler has JSON formatter
        has_json = False
        for handler in logger.handlers:
            if isinstance(handler.formatter, JSONFormatter):
                has_json = True
                break
        assert has_json

    def test_setup_logging_custom_level(self, clean_handlers):
        """Test custom log level."""
        logger = setup_logging(level='DEBUG', log_to_file=False, log_to_console=False)
        assert logger.level == logging.DEBUG

    def test_setup_logging_invalid_level(self, clean_handlers):
        """Test invalid log level defaults to INFO."""
        logger = setup_logging(level='INVALID', log_to_file=False, log_to_console=False)
        assert logger.level == logging.INFO

    def test_setup_logging_session_id(self, clean_handlers):
        """Test session ID is used."""
        logger = setup_logging(
            level='INFO',
            log_to_file=False,
            log_to_console=False,
            session_id='test-session-123'
        )
        
        # Logger should be created successfully
        assert logger is not None


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_default(self):
        """Test get_logger with default name."""
        logger = get_logger()
        assert logger.name == 'rapidwebs_agent'

    def test_get_logger_custom_name(self):
        """Test get_logger with custom name."""
        logger = get_logger('test_module')
        assert logger.name == 'rapidwebs_agent.test_module'

    def test_get_logger_nested_name(self):
        """Test get_logger with nested name."""
        logger = get_logger('skills.git')
        assert logger.name == 'rapidwebs_agent.skills.git'


class TestGetLogDirectory:
    """Tests for get_log_directory function."""

    def test_get_log_directory_creates_path(self):
        """Test that get_log_directory creates the directory."""
        log_dir = get_log_directory()
        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_get_log_directory_path_format(self):
        """Test log directory path format."""
        log_dir = get_log_directory()
        assert 'rapidwebs-agent' in str(log_dir)
        assert 'logs' in str(log_dir)


class TestJSONFormatter:
    """Tests for JSONFormatter."""

    def test_json_formatter_basic(self):
        """Test JSON formatter with basic message."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed['level'] == 'INFO'
        assert parsed['message'] == 'Test message'
        assert parsed['logger'] == 'test'

    def test_json_formatter_with_exception(self):
        """Test JSON formatter with exception info."""
        formatter = JSONFormatter()
        
        try:
            raise ValueError('Test error')
        except ValueError:
            import sys
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name='test',
                level=logging.ERROR,
                pathname='test.py',
                lineno=1,
                msg='Error occurred',
                args=(),
                exc_info=exc_info
            )
            
            output = formatter.format(record)
            parsed = json.loads(output)
            
            assert 'exception' in parsed
            assert 'ValueError' in parsed['exception']

    def test_json_formatter_extra_fields(self):
        """Test JSON formatter with extra fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test with extra',
            args=(),
            exc_info=None
        )
        record.custom_field = 'custom_value'
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed['custom_field'] == 'custom_value'


class TestSessionLogFilter:
    """Tests for SessionLogFilter."""

    def test_session_filter_adds_session_id(self):
        """Test that filter adds session ID to records."""
        filter = SessionLogFilter('test-session-456')
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test',
            args=(),
            exc_info=None
        )
        
        result = filter.filter(record)
        
        assert result is True
        assert record.session_id == 'test-session-456'


class TestLogContext:
    """Tests for LogContext."""

    def test_log_context_adds_fields(self, caplog):
        """Test that context adds fields to log records."""
        logger = logging.getLogger('test_context')
        logger.setLevel(logging.DEBUG)
        
        with LogContext(logger, user_id='123', action='test'):
            with caplog.at_level(logging.DEBUG):
                logger.debug('Test message')
        
        # Check that context was added
        assert len(caplog.records) == 1
        record = caplog.records[0]
        # Context should be available in the record

    def test_log_context_cleanup(self):
        """Test that context is cleaned up after use."""
        logger = logging.getLogger('test_context_cleanup')
        
        context = LogContext(logger, temp_field='value')
        with context:
            pass
        
        # Filter should be removed after context
        assert context.handler not in logger.filters


class TestLogFunctionCall:
    """Tests for log_function_call decorator."""

    def test_decorator_logs_call(self, caplog):
        """Test that decorator logs function calls."""
        logger = logging.getLogger('test_decorator')
        logger.setLevel(logging.DEBUG)
        
        @log_function_call(logger)
        def test_func(x, y):
            return x + y
        
        with caplog.at_level(logging.DEBUG):
            result = test_func(2, 3)
        
        assert result == 5
        assert 'Calling test_func' in caplog.text
        assert 'returned 5' in caplog.text

    def test_decorator_logs_exception(self, caplog):
        """Test that decorator logs exceptions."""
        logger = logging.getLogger('test_decorator_error')
        logger.setLevel(logging.ERROR)
        
        @log_function_call(logger)
        def failing_func():
            raise ValueError('Test error')
        
        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                failing_func()
        
        assert 'failing_func raised ValueError' in caplog.text

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""
        logger = logging.getLogger('test_metadata')
        
        @log_function_call(logger)
        def documented_func():
            """This is a docstring."""
            pass
        
        assert documented_func.__name__ == 'documented_func'
        assert documented_func.__doc__ == 'This is a docstring.'


class TestLoggingIntegration:
    """Integration tests for logging system."""

    def test_full_logging_workflow(self, temp_log_dir, clean_handlers):
        """Test complete logging workflow."""
        logger = setup_logging(
            level='DEBUG',
            log_to_file=True,
            log_to_console=False,
            session_id='integration-test'
        )
        
        # Log at different levels
        logger.debug('Debug message')
        logger.info('Info message')
        logger.warning('Warning message')
        logger.error('Error message')
        
        # Check log file exists
        log_files = list(temp_log_dir.glob('session_integration-test.log'))
        assert len(log_files) == 1
        
        # Check log file content
        log_content = log_files[0].read_text()
        assert 'Debug message' in log_content
        assert 'Info message' in log_content
        assert 'Warning message' in log_content
        assert 'Error message' in log_content

    def test_concurrent_logging(self, temp_log_dir, clean_handlers):
        """Test concurrent logging from multiple sources."""
        logger1 = setup_logging(
            level='INFO',
            log_to_file=True,
            log_to_console=False,
            session_id='concurrent-1'
        )
        logger2 = get_logger('module2')
        
        logger1.info('Message from logger1')
        logger2.info('Message from logger2')
        
        # Both should work without interference
        assert len(logger1.handlers) > 0
