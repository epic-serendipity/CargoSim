"""
Font error limiting and handling system for CargoSim.

This module provides comprehensive font error handling to limit
Tkinter font errors to a reasonable number for debugging while
preventing console flooding.
"""

import sys
import logging
import tkinter as tk
from typing import Optional, Callable, Any
from functools import wraps

# Global error suppressor instance
_font_suppressor = None

class FontErrorLimiter:
    """Limits and handles Tkinter font errors gracefully."""
    
    def __init__(self):
        self.limiting_enabled = True
        self.error_count = 0
        self.max_errors_to_show = 5  # Show first 5 errors, then limit
        self.max_errors_before_disable = 100
        self.error_callbacks = []
        self.logger = logging.getLogger("cargosim.font_limiter")
        self._handling_font_error = False  # Flag to prevent recursion
        
        # Install error handlers
        self._install_error_handlers()
    
    def _install_error_handlers(self):
        """Install error handlers for Tkinter font issues."""
        try:
            # Override tkinter's error handling
            self._override_tkinter_errors()
            
            # Install custom font handling
            self._install_custom_font_handling()
            
            # Install print function override
            self._override_print_function()
            
            self.logger.info("Font error limiting system installed successfully")
        except Exception as e:
            self.logger.warning(f"Could not install font error limiting: {e}")
    
    def _override_tkinter_errors(self):
        """Override Tkinter's default error handling."""
        try:
            # Override the global Tkinter error reporting
            import tkinter.messagebox
            
            # Store original error handling
            original_report_callback = getattr(tk, 'report_callback_exception', None)
            if original_report_callback:
                setattr(tk, '_original_report_callback', original_report_callback)
                setattr(tk, 'report_callback_exception', self._custom_error_handler)
            
            # Also try to override on the default root if it exists
            if hasattr(tk, '_default_root') and tk._default_root:
                original_root_callback = getattr(tk._default_root, 'report_callback_exception', None)
                if original_root_callback:
                    setattr(tk._default_root, '_original_report_callback', original_root_callback)
                    setattr(tk._default_root, 'report_callback_exception', self._custom_error_handler)
                    
        except Exception as e:
            self.logger.debug(f"Could not override Tkinter error handling: {e}")
    
    def _custom_error_handler(self, exc_type, exc_value, exc_traceback):
        """Custom error handler that limits font errors."""
        try:
            # Check if this is a font-related error
            if self._is_font_error(exc_value):
                self._handle_font_error(exc_type, exc_value, exc_traceback)
                return  # Handle the error (don't let Tkinter handle it)
            
            # For non-font errors, call original handler if available
            if hasattr(tk, '_original_report_callback'):
                tk._original_report_callback(exc_type, exc_value, exc_traceback)
            elif hasattr(tk._default_root, '_original_report_callback'):
                tk._default_root._original_report_callback(exc_type, exc_value, exc_traceback)
            else:
                # Fallback to default handling
                import traceback
                traceback.print_exception(exc_type, exc_value, exc_traceback)
                
        except Exception as e:
            self.logger.error(f"Error in custom error handler: {e}")
    
    def _is_font_error(self, exc_value) -> bool:
        """Check if an exception is font-related."""
        if not exc_value:
            return False
        
        error_str = str(exc_value).lower()
        font_indicators = [
            'font',
            'unknown option',
            'recursive font application',
            'tkinter.font',
            'font family',
            'recursive font',
            'unknown option "-font"'
        ]
        
        return any(indicator in error_str for indicator in font_indicators)
    
    def _handle_font_error(self, exc_type, exc_value, exc_traceback):
        """Handle font errors with limiting."""
        self.error_count += 1
        
        if self.error_count <= self.max_errors_to_show:
            # Show the first few errors for debugging
            self.logger.warning(f"Font error {self.error_count}/{self.max_errors_to_show}: {exc_value}")
            
            # Also print to console for visibility
            import traceback
            print(f"Font Error {self.error_count}/{self.max_errors_to_show}: {exc_value}")
            if self.error_count == self.max_errors_to_show:
                print(f"Font errors limited to {self.max_errors_to_show}. Additional errors will be logged only.")
        else:
            # Log additional errors but don't print to console
            self.logger.debug(f"Font error {self.error_count} (limited): {exc_value}")
        
        # Call error callbacks
        for callback in self.error_callbacks:
            try:
                callback(exc_type, exc_value, exc_traceback)
            except Exception as e:
                self.logger.error(f"Error in font error callback: {e}")
        
        # Disable limiting if too many errors
        if self.error_count >= self.max_errors_before_disable:
            self.limiting_enabled = False
            self.logger.warning("Font error limiting disabled due to excessive errors")
    
    def _install_custom_font_handling(self):
        """Install custom font handling for Tkinter widgets."""
        try:
            # Override ttk.Label font handling
            self._override_ttk_label_fonts()
            
            # Override tk.Label font handling
            self._override_tk_label_fonts()
            
        except Exception as e:
            self.logger.debug(f"Could not install custom font handling: {e}")
    
    def _override_ttk_label_fonts(self):
        """Override ttk.Label font handling to prevent errors."""
        try:
            original_ttk_label_init = tk.ttk.Label.__init__
            
            @wraps(original_ttk_label_init)
            def safe_ttk_label_init(self, master=None, **kwargs):
                # Sanitize font specification
                if 'font' in kwargs:
                    kwargs['font'] = _font_suppressor._sanitize_font(kwargs['font'])
                
                # Call original constructor
                return original_ttk_label_init(self, master, **kwargs)
            
            # Replace the constructor
            tk.ttk.Label.__init__ = safe_ttk_label_init
            
        except Exception as e:
            self.logger.debug(f"Could not override ttk.Label: {e}")
    
    def _override_tk_label_fonts(self):
        """Override tk.Label font handling to prevent errors."""
        try:
            original_tk_label_init = tk.Label.__init__
            
            @wraps(original_tk_label_init)
            def safe_tk_label_init(self, master=None, **kwargs):
                # Sanitize font specification
                if 'font' in kwargs:
                    kwargs['font'] = _font_suppressor._sanitize_font(kwargs['font'])
                
                # Call original constructor
                return original_tk_label_init(self, master, **kwargs)
            
            # Replace the constructor
            tk.Label.__init__ = safe_tk_label_init
            
        except Exception as e:
            self.logger.debug(f"Could not override tk.Label: {e}")
    
    def _sanitize_font(self, font_spec):
        """Sanitize font specification to prevent errors."""
        if not font_spec:
            return ("TkDefaultFont",)
        
        try:
            if isinstance(font_spec, str):
                return (font_spec,)
            elif isinstance(font_spec, (tuple, list)):
                if len(font_spec) == 0:
                    return ("TkDefaultFont",)
                elif len(font_spec) == 1:
                    family = font_spec[0] if font_spec[0] else "TkDefaultFont"
                    return (family,)
                elif len(font_spec) == 2:
                    family = font_spec[0] if font_spec[0] else "TkDefaultFont"
                    # Remove size specification to use default tkinter size
                    return (family,)
                elif len(font_spec) == 3:
                    family = font_spec[0] if font_spec[0] else "TkDefaultFont"
                    style = font_spec[2]
                    # Remove size specification to use default tkinter size
                    return (family, style)
                else:
                    return ("TkDefaultFont",)
            else:
                return ("TkDefaultFont",)
        except Exception:
            return ("TkDefaultFont",)
    
    def _override_print_function(self):
        """Override the built-in print function to catch font errors."""
        try:
            import builtins
            
            # Store original print function
            self._original_print = builtins.print
            
            def limited_print(*args, **kwargs):
                """Limited print function that filters font errors."""
                # Prevent recursion - if we're already handling a font error, just print normally
                if self._handling_font_error:
                    return self._original_print(*args, **kwargs)
                
                # Check if any of the arguments contain font error patterns
                text = ' '.join(str(arg) for arg in args)
                if self._is_font_error_text(text):
                    self._handle_font_error_text(text)
                    return  # Don't print font errors
                
                # Call original print for non-font errors
                return self._original_print(*args, **kwargs)
            
            # Replace the built-in print function
            builtins.print = limited_print
            
            # Log successful override
            self.logger.info("Print function override installed successfully")
            
        except Exception as e:
            self.logger.debug(f"Could not override print function: {e}")
    
    def _is_font_error_text(self, text: str) -> bool:
        """Check if text contains font error patterns."""
        if not text:
            return False
        
        text_lower = text.lower().strip()
        
        # More precise font error patterns
        font_indicators = [
            'error in recursive font application: unknown option "-font"',
            'recursive font application: unknown option "-font"',
            'unknown option "-font"',
            'font application: unknown option "-font"'
        ]
        
        # Debug logging
        if any(indicator in text_lower for indicator in font_indicators):
            self.logger.debug(f"Font error pattern detected: '{text_lower}'")
            return True
        
        return False
    
    def _handle_font_error_text(self, text: str):
        """Handle font error text by limiting output."""
        # Set flag to prevent recursion
        self._handling_font_error = True
        
        try:
            self.error_count += 1
            
            if self.error_count <= self.max_errors_to_show:
                # Show the first few errors for debugging
                self.logger.warning(f"Font error {self.error_count}/{self.max_errors_to_show}: {text.strip()}")
                
                # Show limit message when we reach the limit
                if self.error_count == self.max_errors_to_show:
                    self.logger.info(f"Font errors limited to {self.max_errors_to_show}. Additional errors will be logged only.")
            else:
                # Log additional errors but don't print to console
                self.logger.debug(f"Font error {self.error_count} (limited): {text.strip()}")
        finally:
            # Always reset the flag
            self._handling_font_error = False
    
    def add_error_callback(self, callback: Callable):
        """Add a callback for font errors."""
        if callback not in self.error_callbacks:
            self.error_callbacks.append(callback)
    
    def remove_error_callback(self, callback: Callable):
        """Remove a font error callback."""
        if callback in self.error_callbacks:
            self.error_callbacks.remove(callback)
    
    def enable_limiting(self):
        """Enable font error limiting."""
        self.limiting_enabled = True
        self.logger.info("Font error limiting enabled")
    
    def disable_limiting(self):
        """Disable font error limiting."""
        self.limiting_enabled = False
        self.logger.info("Font error limiting disabled")
    
    def set_max_errors_to_show(self, max_errors: int):
        """Set the maximum number of errors to show before limiting."""
        self.max_errors_to_show = max_errors
        self.logger.info(f"Font error limit set to {max_errors}")
    
    def get_error_count(self) -> int:
        """Get the current font error count."""
        return self.error_count
    
    def reset_error_count(self):
        """Reset the font error count."""
        self.error_count = 0
        self.logger.info("Font error count reset")
    
    def get_status(self) -> dict:
        """Get the current status of the font limiter."""
        return {
            'limiting_enabled': self.limiting_enabled,
            'error_count': self.error_count,
            'max_errors_to_show': self.max_errors_to_show,
            'max_errors_before_disable': self.max_errors_before_disable,
            'callback_count': len(self.error_callbacks)
        }


def get_font_limiter() -> FontErrorLimiter:
    """Get the global font error limiter instance."""
    global _font_suppressor
    if _font_suppressor is None:
        _font_suppressor = FontErrorLimiter()
    return _font_suppressor


def limit_font_errors(func: Callable) -> Callable:
    """Decorator to limit font errors in a function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Check if this is a font error
            if _font_suppressor and _font_suppressor._is_font_error(e):
                _font_suppressor._handle_font_error(type(e), e, None)
                return None  # Return None for font errors
            else:
                raise  # Re-raise non-font errors
    return wrapper


def install_font_error_limiting():
    """Install font error limiting system."""
    return get_font_limiter()


# Install limiting system on module import
install_font_error_limiting()
