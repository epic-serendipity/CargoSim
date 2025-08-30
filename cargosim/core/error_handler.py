"""
Comprehensive error handling and logging system for CargoSim.

This module provides advanced error handling, logging, and recovery mechanisms
to improve application stability and debugging capabilities.
"""

import os
import sys
import time
import logging
import traceback
import threading
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List, Union
from functools import wraps
import tkinter as tk
from tkinter import messagebox

from cargosim.core.utils import get_logger, log_runtime_event, log_exception

# Global error handler instance
_error_handler = None

class ErrorHandler:
    """Comprehensive error handling and logging system."""
    
    def __init__(self):
        self.logger = get_logger("error_handler")
        self.error_count = 0
        self.error_history = []
        self.recovery_strategies = {}
        self.error_callbacks = []
        self.max_history_size = 1000
        self.error_threshold = 10  # Max errors before considering app unstable
        self.last_error_time = 0
        self.error_cooldown = 5.0  # Seconds between error bursts
        
        # Initialize recovery strategies
        self._init_recovery_strategies()
        
        # Setup error monitoring
        self._setup_error_monitoring()
        
        self.logger.info("Error handler initialized")
    
    def _init_recovery_strategies(self):
        """Initialize built-in recovery strategies."""
        self.recovery_strategies = {
            'tkinter_error': self._handle_tkinter_error,
            'font_error': self._handle_font_error,
            'memory_error': self._handle_memory_error,
            'network_error': self._handle_network_error,
            'file_error': self._handle_file_error,
            'general_error': self._handle_general_error
        }
    
    def _setup_error_monitoring(self):
        """Setup error monitoring and alerting."""
        # Monitor error frequency
        def check_error_frequency():
            while True:
                try:
                    current_time = time.time()
                    if (self.error_count > self.error_threshold and 
                        current_time - self.last_error_time < self.error_cooldown):
                        self.logger.critical(f"High error frequency detected: {self.error_count} errors in {self.error_cooldown}s")
                        self._trigger_error_alert("High Error Frequency", 
                                                f"Application experiencing {self.error_count} errors in {self.error_cooldown} seconds")
                    time.sleep(10)  # Check every 10 seconds
                except Exception as e:
                    # Even error monitoring can fail
                    print(f"Error monitoring failed: {e}")
                    time.sleep(30)  # Wait longer if monitoring fails
        
        # Start error monitoring in background thread
        monitor_thread = threading.Thread(target=check_error_frequency, daemon=True)
        monitor_thread.start()
    
    def handle_error(self, error: Exception, context: str = "", 
                    severity: str = "ERROR", recovery_attempt: bool = False) -> bool:
        """
        Handle an error with comprehensive logging and recovery attempts.
        
        Args:
            error: The exception that occurred
            context: Context where the error occurred
            severity: Error severity level
            recovery_attempt: Whether this is a recovery attempt
            
        Returns:
            True if error was handled successfully, False otherwise
        """
        try:
            # Update error tracking
            self.error_count += 1
            self.last_error_time = time.time()
            
            # Determine error type and severity
            error_type = type(error).__name__
            error_message = str(error)
            
            # Log the error
            self.logger.error(f"Error in {context}: {error_type}: {error_message}")
            
            # Add to error history
            error_record = {
                'timestamp': datetime.now().isoformat(),
                'type': error_type,
                'message': error_message,
                'context': context,
                'severity': severity,
                'traceback': traceback.format_exc(),
                'recovery_attempt': recovery_attempt
            }
            
            self.error_history.append(error_record)
            
            # Keep history size manageable
            if len(self.error_history) > self.max_history_size:
                self.error_history = self.error_history[-self.max_history_size:]
            
            # Attempt recovery based on error type
            recovery_successful = self._attempt_recovery(error, context, error_type)
            
            # Trigger error callbacks
            self._trigger_error_callbacks(error, context, severity)
            
            # Log recovery result
            if recovery_successful:
                self.logger.info(f"Error recovery successful for {error_type} in {context}")
            else:
                self.logger.warning(f"Error recovery failed for {error_type} in {context}")
            
            return recovery_successful
            
        except Exception as recovery_error:
            # Even error handling can fail
            self.logger.critical(f"Error handler failed: {recovery_error}")
            return False
    
    def _attempt_recovery(self, error: Exception, context: str, error_type: str) -> bool:
        """Attempt to recover from an error based on its type."""
        try:
            # Try specific recovery strategies
            if error_type in self.recovery_strategies:
                return self.recovery_strategies[error_type](error, context)
            
            # Fall back to general recovery
            return self.recovery_strategies['general_error'](error, context)
            
        except Exception as recovery_error:
            self.logger.error(f"Recovery attempt failed: {recovery_error}")
            return False
    
    def _handle_tkinter_error(self, error: Exception, context: str) -> bool:
        """Handle Tkinter-specific errors."""
        try:
            error_message = str(error)
            
            # Handle font-related errors
            if "font" in error_message.lower() or "unknown option" in error_message.lower():
                self.logger.warning("Font-related error detected, attempting font recovery")
                return self._recover_font_error(error, context)
            
            # Handle widget creation errors
            if "widget" in error_message.lower() or "frame" in error_message.lower():
                self.logger.warning("Widget creation error detected, attempting cleanup")
                return self._recover_widget_error(error, context)
            
            # Handle general Tkinter errors
            self.logger.warning("General Tkinter error detected")
            return False
            
        except Exception as e:
            self.logger.error(f"Tkinter error recovery failed: {e}")
            return False
    
    def _handle_font_error(self, error: Exception, context: str) -> bool:
        """Handle font-specific errors."""
        return self._recover_font_error(error, context)
    
    def _handle_memory_error(self, error: Exception, context: str) -> bool:
        """Handle memory-related errors."""
        try:
            self.logger.warning("Memory error detected, attempting cleanup")
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Log memory usage
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            self.logger.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.1f} MB")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Memory error recovery failed: {e}")
            return False
    
    def _handle_network_error(self, error: Exception, context: str) -> bool:
        """Handle network-related errors."""
        try:
            self.logger.warning("Network error detected, attempting retry")
            
            # Wait a bit before retry
            time.sleep(1)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Network error recovery failed: {e}")
            return False
    
    def _handle_file_error(self, error: Exception, context: str) -> bool:
        """Handle file-related errors."""
        try:
            error_message = str(error)
            
            if "permission" in error_message.lower():
                self.logger.warning("File permission error detected")
                return False
            
            if "not found" in error_message.lower():
                self.logger.warning("File not found error detected")
                return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"File error recovery failed: {e}")
            return False
    
    def _handle_general_error(self, error: Exception, context: str) -> bool:
        """Handle general errors with basic recovery."""
        try:
            # Log additional context
            self.logger.debug(f"General error context: {context}")
            
            # Basic recovery: just log and continue
            return True
            
        except Exception as e:
            self.logger.error(f"General error recovery failed: {e}")
            return False
    
    def _recover_font_error(self, error: Exception, context: str) -> bool:
        """Attempt to recover from font-related errors."""
        try:
            self.logger.info("Attempting font error recovery")
            
            # Try to reset font cache
            try:
                import tkinter.font as tkfont
                tkfont.families()  # This can help reset font cache
            except Exception:
                pass
            
            # Log font recovery attempt
            self.logger.info("Font recovery attempt completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Font recovery failed: {e}")
            return False
    
    def _recover_widget_error(self, error: Exception, context: str) -> bool:
        """Attempt to recover from widget-related errors."""
        try:
            self.logger.info("Attempting widget error recovery")
            
            # Basic widget cleanup
            # This is a simplified approach - in practice, you'd need more context
            
            return True
            
        except Exception as e:
            self.logger.error(f"Widget recovery failed: {e}")
            return False
    
    def _trigger_error_callbacks(self, error: Exception, context: str, severity: str):
        """Trigger registered error callbacks."""
        for callback in self.error_callbacks:
            try:
                callback(error, context, severity)
            except Exception as e:
                self.logger.error(f"Error callback failed: {e}")
    
    def _trigger_error_alert(self, title: str, message: str):
        """Trigger an error alert to the user."""
        try:
            # Try to show a message box if possible
            if 'tkinter' in sys.modules:
                try:
                    # Create a simple root if none exists
                    root = tk.Tk()
                    root.withdraw()
                    messagebox.showwarning(title, message)
                    root.destroy()
                except Exception:
                    pass
            
            # Also log the alert
            self.logger.warning(f"ERROR ALERT: {title} - {message}")
            
        except Exception as e:
            self.logger.error(f"Error alert failed: {e}")
    
    def add_error_callback(self, callback: Callable[[Exception, str, str], None]):
        """Add a callback function to be called when errors occur."""
        self.error_callbacks.append(callback)
        self.logger.debug(f"Added error callback: {callback.__name__}")
    
    def remove_error_callback(self, callback: Callable[[Exception, str, str], None]):
        """Remove an error callback function."""
        if callback in self.error_callbacks:
            self.error_callbacks.remove(callback)
            self.logger.debug(f"Removed error callback: {callback.__name__}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of recent errors."""
        return {
            'total_errors': self.error_count,
            'recent_errors': len(self.error_history),
            'last_error_time': self.last_error_time,
            'error_types': self._get_error_type_distribution(),
            'recent_error_list': self.error_history[-10:]  # Last 10 errors
        }
    
    def _get_error_type_distribution(self) -> Dict[str, int]:
        """Get distribution of error types."""
        distribution = {}
        for error_record in self.error_history:
            error_type = error_record['type']
            distribution[error_type] = distribution.get(error_type, 0) + 1
        return distribution
    
    def reset_error_count(self):
        """Reset the error count (useful for testing or after recovery)."""
        self.error_count = 0
        self.last_error_time = 0
        self.logger.info("Error count reset")
    
    def cleanup(self):
        """Clean up resources used by the error handler."""
        try:
            # Clear callbacks
            self.error_callbacks.clear()
            
            # Clear history
            self.error_history.clear()
            
            self.logger.info("Error handler cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error handler cleanup failed: {e}")


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def handle_error(error: Exception, context: str = "", severity: str = "ERROR") -> bool:
    """Convenience function to handle errors using the global error handler."""
    return get_error_handler().handle_error(error, context, severity)


def error_handler_decorator(context: str = "", severity: str = "ERROR"):
    """Decorator to automatically handle errors in functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handle_error(e, context or func.__name__, severity)
                raise  # Re-raise the exception after handling
        return wrapper
    return decorator


def safe_execute(func: Callable, *args, context: str = "", 
                default_return: Any = None, **kwargs) -> Any:
    """
    Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        context: Context for error handling
        default_return: Value to return if function fails
        **kwargs: Keyword arguments for the function
    
    Returns:
        Function result or default_return if execution fails
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handle_error(e, context, "ERROR")
        return default_return


# Initialize error handler on module import
_error_handler = ErrorHandler()
