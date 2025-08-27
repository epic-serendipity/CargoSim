"""
Unit tests for the enhanced logging configuration system.

Tests JSON formatting, correlation IDs, filters, and log retention.
"""

import os
import sys
import json
import pytest
import logging
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from cargosim.core.logging_config import (
    LogManager, ColoredFormatter, JSONFormatter, CorrelationFilter,
    TkinterErrorFilter, PerformanceFilter, get_log_manager,
    setup_comprehensive_logging, set_correlation_id, get_correlation_id
)


class TestJSONFormatter:
    """Test JSON formatter functionality."""
    
    def test_json_formatter_creates_valid_json(self):
        """Test that JSON formatter creates valid JSON output."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["message"] == "Test message"
        assert parsed["file"] == "test.py"
        assert parsed["line"] == 42
        assert "run_id" in parsed
    
    def test_json_formatter_with_exception(self):
        """Test JSON formatter handles exceptions correctly."""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Test error",
                args=(),
                exc_info=sys.exc_info()
            )
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert parsed["level"] == "ERROR"
        assert "exception" in parsed
        assert "ValueError: Test exception" in parsed["exception"]


class TestCorrelationFilter:
    """Test correlation ID filtering."""
    
    def test_correlation_filter_injects_run_id(self):
        """Test that correlation filter injects run_id into records."""
        filter_obj = CorrelationFilter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Initially no run_id
        assert not hasattr(record, 'run_id')
        
        # Apply filter
        result = filter_obj.filter(record)
        assert result is True
        assert hasattr(record, 'run_id')
        assert isinstance(record.run_id, str)


class TestTkinterErrorFilter:
    """Test Tkinter error filtering."""
    
    def test_tkinter_filter_blocks_excess_font_errors(self):
        """Test that Tkinter filter blocks excessive font errors."""
        filter_obj = TkinterErrorFilter()
        
        # Create multiple font error records
        for i in range(10):
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Unknown option -font in Tk font",
                args=(),
                exc_info=None
            )
            
            # First 5 should pass, rest should be filtered
            expected = i < 5
            assert filter_obj.filter(record) == expected
    
    def test_tkinter_filter_allows_non_font_errors(self):
        """Test that Tkinter filter allows non-font errors."""
        filter_obj = TkinterErrorFilter()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Some other error message",
            args=(),
            exc_info=None
        )
        
        assert filter_obj.filter(record) is True


class TestPerformanceFilter:
    """Test performance log filtering."""
    
    def test_performance_filter_limits_performance_logs(self):
        """Test that performance filter limits performance-related logs."""
        filter_obj = PerformanceFilter()
        
        # Create multiple performance log records
        for i in range(15):
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=42,
                msg=f"Performance metric: {i} FPS",
                args=(),
                exc_info=None
            )
            
            # First 10 should pass, rest should be filtered
            expected = i < 10
            assert filter_obj.filter(record) == expected
    
    def test_performance_filter_allows_non_performance_logs(self):
        """Test that performance filter allows non-performance logs."""
        filter_obj = PerformanceFilter()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Regular log message",
            args=(),
            exc_info=None
        )
        
        assert filter_obj.filter(record) is True


class TestLogManager:
    """Test LogManager functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Clear any existing log manager
        self.cleanup_logging()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        self.cleanup_logging()
    
    def cleanup_logging(self):
        """Helper to cleanup logging state."""
        from cargosim.core.logging_config import cleanup_logging
        cleanup_logging()
    
    def test_log_manager_creates_loggers(self):
        """Test that LogManager creates all required loggers."""
        manager = LogManager()
        
        assert 'main' in manager.loggers
        assert 'runtime' in manager.loggers
        assert 'error' in manager.loggers
        assert 'performance' in manager.loggers
    
    def test_log_manager_json_format_environment(self):
        """Test that LogManager respects CARGOSIM_LOG_FORMAT environment variable."""
        with patch.dict(os.environ, {'CARGOSIM_LOG_FORMAT': 'json'}):
            manager = LogManager()
            assert manager.use_json_format is True
    
    def test_log_manager_human_format_default(self):
        """Test that LogManager defaults to human format."""
        with patch.dict(os.environ, {}, clear=True):
            manager = LogManager()
            assert manager.use_json_format is False
    
    def test_set_correlation_id(self):
        """Test setting correlation ID."""
        manager = LogManager()
        test_id = "test-run-123"
        
        manager.set_correlation_id(test_id)
        assert manager.get_correlation_id() == test_id
    
    def test_get_logger_returns_existing_logger(self):
        """Test that get_logger returns existing loggers."""
        manager = LogManager()
        
        logger1 = manager.get_logger('main')
        logger2 = manager.get_logger('main')
        
        assert logger1 is logger2
    
    def test_get_logger_creates_new_logger(self):
        """Test that get_logger creates new loggers when needed."""
        manager = LogManager()
        
        new_logger = manager.get_logger('custom.module')
        assert new_logger.name == 'custom.module'
        assert new_logger in manager.loggers.values()


class TestLogRetention:
    """Test log retention functionality."""
    
    def test_cleanup_old_logs_removes_old_files(self, tmp_path):
        """Test that cleanup removes old log files."""
        manager = LogManager()
        
        # Create some test log files
        old_file = tmp_path / "old.log"
        new_file = tmp_path / "new.log"
        
        # Create old file (modify time in the past)
        old_file.write_text("old content")
        old_time = time.time() - (31 * 24 * 3600)  # 31 days ago
        os.utime(old_file, (old_time, old_time))
        
        # Create new file
        new_file.write_text("new content")
        
        # Mock the log directory to use our temp directory
        with patch('cargosim.core.logging_config.DEBUG_LOG_FILE', tmp_path / "debug.log"):
            manager._cleanup_old_logs(max_age_days=30)
        
        # Old file should be removed, new file should remain
        assert not old_file.exists()
        assert new_file.exists()
    
    def test_start_log_retention_cleanup_creates_thread(self):
        """Test that log retention cleanup starts a background thread."""
        manager = LogManager()
        
        thread = manager.start_log_retention_cleanup(max_age_days=1, cleanup_interval_hours=1)
        
        assert thread.is_alive()
        assert thread.daemon is True
        
        # Clean up
        thread.join(timeout=0.1)


class TestIntegration:
    """Integration tests for the logging system."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.cleanup_logging()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        self.cleanup_logging()
    
    def cleanup_logging(self):
        """Helper to cleanup logging state."""
        from cargosim.core.logging_config import cleanup_logging
        cleanup_logging()
    
    def test_setup_comprehensive_logging_with_json(self):
        """Test setting up logging with JSON format."""
        manager = setup_comprehensive_logging(level="DEBUG", use_json=True)
        
        # Check that JSON format is enabled
        assert manager.use_json_format is True
        
        # Get a logger and verify it works
        logger = manager.get_logger('test')
        assert logger is not None
    
    def test_correlation_id_propagation(self):
        """Test that correlation IDs propagate through the logging system."""
        manager = setup_comprehensive_logging()
        
        # Set a correlation ID
        test_id = "integration-test-456"
        manager.set_correlation_id(test_id)
        
        # Get a logger and create a record
        logger = manager.get_logger('test.integration')
        
        # Capture the log output
        with patch('sys.stdout', new=MagicMock()) as mock_stdout:
            logger.info("Test message")
            
            # Verify the output contains our correlation ID
            output = mock_stdout.write.call_args[0][0]
            assert test_id[:8] in output
    
    def test_log_level_setting(self):
        """Test that log levels can be set correctly."""
        manager = setup_comprehensive_logging(level="WARNING")
        
        # Set a specific logger to DEBUG
        manager.set_log_level('main', 'DEBUG')
        
        # Verify the level was set
        assert manager.loggers['main'].level == logging.DEBUG


class TestUtilityFunctions:
    """Test utility functions."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.cleanup_logging()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        self.cleanup_logging()
    
    def cleanup_logging(self):
        """Helper to cleanup logging state."""
        from cargosim.core.logging_config import cleanup_logging
        cleanup_logging()
    
    def test_get_log_manager_singleton(self):
        """Test that get_log_manager returns the same instance."""
        manager1 = get_log_manager()
        manager2 = get_log_manager()
        
        assert manager1 is manager2
    
    def test_set_correlation_id_utility(self):
        """Test the set_correlation_id utility function."""
        test_id = "utility-test-789"
        set_correlation_id(test_id)
        
        retrieved_id = get_correlation_id()
        assert retrieved_id == test_id


if __name__ == "__main__":
    pytest.main([__file__])
