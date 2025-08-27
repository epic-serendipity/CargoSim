"""
Comprehensive logging configuration for CargoSim.

This module provides advanced logging setup with rotation, filtering,
and multiple output formats for better debugging and monitoring.
"""

import os
import sys
import json
import uuid
import logging
import logging.handlers
import contextvars
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

from .paths import DEBUG_LOG_FILE, RUNTIME_LOG_FILE

# Global correlation ID for tracking simulation runs
_run_id = contextvars.ContextVar("run_id", default=str(uuid.uuid4()))

class CorrelationFilter(logging.Filter):
    """Filter to inject correlation IDs into log records."""
    
    def filter(self, record):
        record.run_id = _run_id.get()
        return True

class JSONFormatter(logging.Formatter):
    """JSON formatter for machine-parsable logs."""
    
    def format(self, record):
        log_dict = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "file": record.filename,
            "line": record.lineno,
            "func": record.funcName,
            "run_id": getattr(record, "run_id", "unknown"),
            "extra": getattr(record, "extra", {})
        }
        
        # Add exception info if present
        if record.exc_info:
            log_dict["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_dict, ensure_ascii=False)

class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output."""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Add color to the log level
        if hasattr(record, 'levelname') and record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        # Add correlation ID if present
        if hasattr(record, 'run_id'):
            record.run_id = f"[{record.run_id[:8]}]"
        else:
            record.run_id = "[unknown]"
        
        return super().format(record)


class TkinterErrorFilter(logging.Filter):
    """Filter to reduce noise from Tkinter font errors."""
    
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.font_error_count = 0
        self.max_font_errors = 5  # Only log first 5 font errors
    
    def filter(self, record):
        # Check if this is a font-related error
        if (hasattr(record, 'msg') and 
            isinstance(record.msg, str) and 
            "font" in record.msg.lower() and
            "unknown option" in record.msg.lower()):
            
            self.font_error_count += 1
            if self.font_error_count > self.max_font_errors:
                return False  # Filter out excessive font errors
        
        return True


class PerformanceFilter(logging.Filter):
    """Filter to reduce performance-related log noise."""
    
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.performance_log_count = 0
        self.max_performance_logs = 10  # Limit performance logs
    
    def filter(self, record):
        # Check if this is a performance-related log
        if (hasattr(record, 'msg') and 
            isinstance(record.msg, str) and 
            any(term in record.msg.lower() for term in ['performance', 'fps', 'memory', 'cpu'])):
            
            self.performance_log_count += 1
            if self.performance_log_count > self.max_performance_logs:
                return False  # Filter out excessive performance logs
        
        return True


class LogManager:
    """Centralized logging management for CargoSim."""
    
    def __init__(self):
        self.loggers = {}
        self.handlers = {}
        self.filters = {}
        self.log_levels = {
            'console': logging.INFO,
            'file': logging.DEBUG,
            'runtime': logging.DEBUG,
            'error': logging.ERROR
        }
        
        # Check for JSON format preference
        self.use_json_format = os.environ.get('CARGOSIM_LOG_FORMAT', 'human').lower() == 'json'
        
        # Initialize filters
        self._init_filters()
        
        # Setup loggers
        self._setup_loggers()
    
    def _init_filters(self):
        """Initialize logging filters."""
        self.filters = {
            'tkinter_error': TkinterErrorFilter(),
            'performance': PerformanceFilter(),
            'correlation': CorrelationFilter()
        }
    
    def _setup_loggers(self):
        """Setup all loggers with appropriate handlers."""
        # Main application logger
        self._setup_main_logger()
        
        # Runtime logger for execution tracking
        self._setup_runtime_logger()
        
        # Error logger for error tracking
        self._setup_error_logger()
        
        # Performance logger
        self._setup_performance_logger()
    
    def _setup_main_logger(self):
        """Setup the main application logger."""
        logger = logging.getLogger("cargosim")
        logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Console handler with color
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_levels['console'])
        
        # Create formatter for console (JSON or colored)
        if self.use_json_format:
            console_formatter = JSONFormatter()
        else:
            console_formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
        console_handler.setFormatter(console_formatter)
        
        # Add filters to reduce noise and correlation
        console_handler.addFilter(self.filters['tkinter_error'])
        console_handler.addFilter(self.filters['performance'])
        console_handler.addFilter(self.filters['correlation'])
        
        # File handler with rotation
        file_handler = self._create_rotating_file_handler(
            DEBUG_LOG_FILE,
            max_bytes=10*1024*1024,  # 10MB
            backup_count=5
        )
        file_handler.setLevel(self.log_levels['file'])
        
        # Create detailed formatter for file (JSON or human)
        if self.use_json_format:
            file_formatter = JSONFormatter()
        else:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            )
        file_handler.setFormatter(file_formatter)
        
        # Add handlers to logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        # Store references
        self.loggers['main'] = logger
        self.handlers['main_console'] = console_handler
        self.handlers['main_file'] = file_handler
    
    def _setup_runtime_logger(self):
        """Setup the runtime logger for execution tracking."""
        logger = logging.getLogger("cargosim.runtime")
        logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Runtime file handler with rotation
        runtime_handler = self._create_rotating_file_handler(
            RUNTIME_LOG_FILE,
            max_bytes=5*1024*1024,  # 5MB
            backup_count=3
        )
        runtime_handler.setLevel(self.log_levels['runtime'])
        
        # Create detailed formatter for runtime
        runtime_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d:%(funcName)s] - %(message)s'
        )
        runtime_handler.setFormatter(runtime_formatter)
        
        # Add handler to logger
        logger.addHandler(runtime_handler)
        
        # Store references
        self.loggers['runtime'] = logger
        self.handlers['runtime_file'] = runtime_handler
    
    def _setup_error_logger(self):
        """Setup the error logger for error tracking."""
        logger = logging.getLogger("cargosim.error")
        logger.setLevel(logging.ERROR)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Error file handler with rotation
        error_log_file = Path(DEBUG_LOG_FILE).parent / "error.log"
        error_handler = self._create_rotating_file_handler(
            error_log_file,
            max_bytes=2*1024*1024,  # 2MB
            backup_count=5
        )
        error_handler.setLevel(self.log_levels['error'])
        
        # Create error formatter
        error_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d:%(funcName)s] - %(message)s\n'
            'Exception: %(exc_info)s\n'
            'Stack Trace: %(stack_info)s\n'
            '---\n'
        )
        error_handler.setFormatter(error_formatter)
        
        # Add handler to logger
        logger.addHandler(error_handler)
        
        # Store references
        self.loggers['error'] = logger
        self.handlers['error_file'] = error_handler
    
    def _setup_performance_logger(self):
        """Setup the performance logger for performance tracking."""
        logger = logging.getLogger("cargosim.performance")
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Performance file handler with rotation
        perf_log_file = Path(DEBUG_LOG_FILE).parent / "performance.log"
        perf_handler = self._create_rotating_file_handler(
            perf_log_file,
            max_bytes=1*1024*1024,  # 1MB
            backup_count=3
        )
        perf_handler.setLevel(logging.INFO)
        
        # Create performance formatter
        perf_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        perf_handler.setFormatter(perf_formatter)
        
        # Add handler to logger
        logger.addHandler(perf_handler)
        
        # Store references
        self.loggers['performance'] = logger
        self.handlers['performance_file'] = perf_handler
    
    def _create_rotating_file_handler(self, log_file: Path, max_bytes: int, backup_count: int):
        """Create a rotating file handler."""
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        return handler
    
    def set_log_level(self, logger_name: str, level: str):
        """Set the log level for a specific logger."""
        if logger_name in self.loggers:
            level_obj = getattr(logging, level.upper(), logging.INFO)
            self.loggers[logger_name].setLevel(level_obj)
            
            # Update stored level
            if logger_name == 'main':
                self.log_levels['console'] = level_obj
                self.log_levels['file'] = level_obj
            elif logger_name == 'runtime':
                self.log_levels['runtime'] = level_obj
            elif logger_name == 'error':
                self.log_levels['error'] = level_obj
    
    def set_correlation_id(self, run_id: str):
        """Set a new correlation ID for the current context."""
        _run_id.set(run_id)
    
    def get_correlation_id(self) -> str:
        """Get the current correlation ID."""
        return _run_id.get()
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger by name."""
        if name in self.loggers:
            return self.loggers[name]
        
        # Create new logger if it doesn't exist
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        # Add to stored loggers
        self.loggers[name] = logger
        
        return logger
    
    def add_custom_filter(self, name: str, filter_obj: logging.Filter):
        """Add a custom filter to all handlers."""
        self.filters[name] = filter_obj
        
        # Apply to all handlers
        for handler in self.handlers.values():
            handler.addFilter(filter_obj)
    
    def remove_filter(self, name: str):
        """Remove a filter from all handlers."""
        if name in self.filters:
            filter_obj = self.filters[name]
            
            # Remove from all handlers
            for handler in self.handlers.values():
                handler.removeFilter(filter_obj)
            
            # Remove from stored filters
            del self.filters[name]
    
    def cleanup(self):
        """Clean up all loggers and handlers."""
        for logger in self.loggers.values():
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        
        self.loggers.clear()
        self.handlers.clear()
        self.filters.clear()
    
    def start_log_retention_cleanup(self, max_age_days: int = 30, cleanup_interval_hours: int = 24):
        """Start background thread for log retention cleanup."""
        def cleanup_old_logs():
            while True:
                try:
                    self._cleanup_old_logs(max_age_days)
                except Exception as e:
                    # Log error but don't crash the cleanup thread
                    print(f"Log cleanup error: {e}")
                
                # Sleep for the specified interval
                time.sleep(cleanup_interval_hours * 3600)
        
        cleanup_thread = threading.Thread(target=cleanup_old_logs, daemon=True)
        cleanup_thread.start()
        return cleanup_thread
    
    def _cleanup_old_logs(self, max_age_days: int):
        """Remove log files older than specified days."""
        log_dir = Path(DEBUG_LOG_FILE).parent
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        
        for log_file in log_dir.glob("*.log*"):
            try:
                if log_file.stat().st_mtime < cutoff_time.timestamp():
                    log_file.unlink()
                    print(f"Removed old log file: {log_file}")
            except Exception as e:
                print(f"Failed to remove old log file {log_file}: {e}")


# Global log manager instance
_log_manager = None


def get_log_manager() -> LogManager:
    """Get the global log manager instance."""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager


def setup_comprehensive_logging(level: str = "INFO", 
                               log_file: Optional[str] = None,
                               console: bool = True,
                               use_json: bool = None) -> LogManager:
    """Setup comprehensive logging for CargoSim."""
    log_manager = get_log_manager()
    
    # Override JSON format if specified
    if use_json is not None:
        log_manager.use_json_format = use_json
    
    # Set log levels
    log_manager.set_log_level('main', level)
    
    return log_manager


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the comprehensive logging setup."""
    log_manager = get_log_manager()
    return log_manager.get_logger(name)


def set_log_level(logger_name: str, level: str):
    """Set the log level for a specific logger."""
    log_manager = get_log_manager()
    log_manager.set_log_level(logger_name, level)

def set_correlation_id(run_id: str):
    """Set a new correlation ID for the current context."""
    log_manager = get_log_manager()
    log_manager.set_correlation_id(run_id)

def get_correlation_id() -> str:
    """Get the current correlation ID."""
    log_manager = get_log_manager()
    return log_manager.get_correlation_id()


def cleanup_logging():
    """Clean up the logging system."""
    global _log_manager
    if _log_manager:
        _log_manager.cleanup()
        _log_manager = None


# Initialize log manager on module import
_log_manager = LogManager()
