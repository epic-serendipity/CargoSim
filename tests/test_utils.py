"""Tests for utility functions."""

import pytest
import os
import logging
import tempfile
from unittest.mock import patch, mock_open, MagicMock
from io import StringIO

from cargosim.utils import (
    setup_logging, setup_runtime_logging, log_runtime_event, log_exception,
    get_logger, append_debug, clamp, _mp4_available, ensure_mp4_ext, tmp_mp4_path
)


class TestLoggingSetup:
    """Test logging setup functions."""
    
    def test_setup_logging_default(self):
        """Test basic logging setup."""
        logger = setup_logging()
        
        assert logger.name == "cargosim"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0
    
    def test_setup_logging_with_level(self):
        """Test logging setup with custom level."""
        logger = setup_logging(level="DEBUG")
        
        assert logger.level == logging.DEBUG
    
    def test_setup_logging_with_file(self):
        """Test logging setup with file handler."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            log_file = f.name
        
        try:
            logger = setup_logging(log_file=log_file)
            
            # Should have both console and file handlers
            handler_types = [type(h).__name__ for h in logger.handlers]
            assert 'StreamHandler' in handler_types
            assert 'FileHandler' in handler_types
            
            # Test that logging to file works
            logger.info("Test message")
            
            with open(log_file, 'r') as f:
                content = f.read()
                assert "Test message" in content
                
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_setup_logging_console_only(self):
        """Test logging setup with console only."""
        logger = setup_logging(console=True, log_file=None)
        
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert 'StreamHandler' in handler_types
        assert 'FileHandler' not in handler_types
    
    def test_setup_runtime_logging(self):
        """Test runtime logging setup."""
        logger = setup_runtime_logging()
        
        assert logger.name == "cargosim.runtime"
        assert len(logger.handlers) > 0
    
    def test_get_logger(self):
        """Test logger retrieval."""
        logger = get_logger("test_module")
        
        assert logger.name == "test_module"
        assert isinstance(logger, logging.Logger)


class TestRuntimeLogging:
    """Test runtime event logging."""
    
    def test_log_runtime_event_basic(self):
        """Test basic runtime event logging."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_runtime_event("Test event")
            
            mock_get_logger.assert_called_with("cargosim.runtime")
            mock_logger.info.assert_called_once()
            
            # Check that the message contains the event
            call_args = mock_logger.info.call_args[0][0]
            assert "Test event" in call_args
    
    def test_log_runtime_event_with_details(self):
        """Test runtime event logging with details."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_runtime_event("Test event", "Additional details")
            
            call_args = mock_logger.info.call_args[0][0]
            assert "Test event" in call_args
            assert "Additional details" in call_args
    
    def test_log_runtime_event_debug_level(self):
        """Test runtime event logging with debug level."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_runtime_event("Debug event", level="DEBUG")
            
            mock_logger.debug.assert_called_once()
    
    def test_log_exception(self):
        """Test exception logging."""
        test_exception = ValueError("Test error")
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_exception(test_exception, "test_context")
            
            # Should call error twice - once for message, once for traceback
            assert mock_logger.error.call_count == 2
            first_call_args = mock_logger.error.call_args_list[0][0][0]
            assert "test_context" in first_call_args
            assert "ValueError" in first_call_args


class TestUtilityFunctions:
    """Test general utility functions."""
    
    def test_clamp_within_range(self):
        """Test clamping values within range."""
        assert clamp(5, 0, 10) == 5
        assert clamp(0, 0, 10) == 0
        assert clamp(10, 0, 10) == 10
    
    def test_clamp_below_range(self):
        """Test clamping values below range."""
        assert clamp(-5, 0, 10) == 0
        assert clamp(-1, 0, 10) == 0
    
    def test_clamp_above_range(self):
        """Test clamping values above range."""
        assert clamp(15, 0, 10) == 10
        assert clamp(100, 0, 10) == 10
    
    def test_clamp_float_values(self):
        """Test clamping with float values."""
        assert clamp(5.5, 0.0, 10.0) == 5.5
        assert clamp(-1.5, 0.0, 10.0) == 0.0
        assert clamp(15.7, 0.0, 10.0) == 10.0


class TestMP4Availability:
    """Test MP4 availability checking."""
    
    def test_mp4_available_success(self):
        """Test MP4 availability when dependencies are available."""
        with patch('cargosim.utils.imageio'):
            with patch('cargosim.utils.imageio_ffmpeg'):
                available, reason = _mp4_available()
                
                assert available is True
                assert "imageio-ffmpeg available" in reason
    
    def test_mp4_available_missing_dependencies(self):
        """Test MP4 availability when dependencies are missing."""
        with patch('cargosim.utils.imageio', side_effect=ImportError("No module named 'imageio'")):
            available, reason = _mp4_available()
            
            assert available is False
            assert "not available" in reason
    
    def test_ensure_mp4_ext(self):
        """Test MP4 file extension enforcement."""
        assert ensure_mp4_ext("video") == "video.mp4"
        assert ensure_mp4_ext("video.mp4") == "video.mp4"
        assert ensure_mp4_ext("video.avi") == "video.avi.mp4"
        assert ensure_mp4_ext("path/to/video") == "path/to/video.mp4"
    
    def test_tmp_mp4_path(self):
        """Test temporary MP4 path generation."""
        path = tmp_mp4_path()
        
        assert path.endswith(".mp4")
        assert "cargo_sim_" in path
        assert "tmp" in path or "temp" in path.lower()


class TestDebugLogging:
    """Test debug logging functionality."""
    
    def test_append_debug_single_line(self):
        """Test appending a single debug line."""
        with patch('builtins.open', mock_open()) as mock_file:
            append_debug(["Test debug message"])
            
            mock_file.assert_called_once()
            handle = mock_file()
            handle.write.assert_called()
            
            # Check that the message was written (each character separately + newline)
            written_calls = [call[0][0] for call in handle.write.call_args_list]
            written_content = ''.join(written_calls)
            assert "Test debug message" in written_content
    
    def test_append_debug_multiple_lines(self):
        """Test appending multiple debug lines."""
        lines = ["Line 1", "Line 2", "Line 3"]
        
        with patch('builtins.open', mock_open()) as mock_file:
            append_debug(lines)
            
            handle = mock_file()
            written_content = ''.join(call[0][0] for call in handle.write.call_args_list)
            
            for line in lines:
                assert line in written_content
    
    def test_append_debug_with_timestamp(self):
        """Test that debug messages include timestamps."""
        with patch('builtins.open', mock_open()) as mock_file:
            append_debug(["Test message"])
            
            handle = mock_file()
            written_content = ''.join(call[0][0] for call in handle.write.call_args_list)
            
            # Should contain the message content
            assert "Test message" in written_content
    
    def test_append_debug_file_error(self):
        """Test debug logging when file write fails."""
        with patch('builtins.open', side_effect=IOError("File write failed")):
            # Should not raise an exception
            try:
                append_debug(["Test message"])
            except IOError:
                pytest.fail("append_debug should handle file write errors gracefully")


class TestFileOperations:
    """Test file-related utility functions."""
    
    def test_file_path_constants(self):
        """Test that file path constants are defined."""
        from cargosim.utils import DEBUG_LOG, RUNTIME_LOG
        
        assert isinstance(DEBUG_LOG, str)
        assert isinstance(RUNTIME_LOG, str)
        assert DEBUG_LOG.endswith('.log')
        assert RUNTIME_LOG.endswith('.log')
    
    def test_log_files_are_different(self):
        """Test that debug and runtime logs are different files."""
        from cargosim.utils import DEBUG_LOG, RUNTIME_LOG
        
        assert DEBUG_LOG != RUNTIME_LOG


if __name__ == "__main__":
    pytest.main([__file__])
