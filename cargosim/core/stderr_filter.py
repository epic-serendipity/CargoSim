"""
Standard error stream limiting for CargoSim.

This module limits stderr output to show a reasonable number of font-related 
error messages for debugging while preventing console flooding.
"""

import sys
import logging
from typing import TextIO, Optional

class LimitedStderr:
    """Limits stderr output to show reasonable number of error messages."""
    
    def __init__(self, original_stderr: TextIO):
        self.original_stderr = original_stderr
        self.limited_patterns = [
            'Error in recursive font application: unknown option "-font"',
            'font application: unknown option',
            'recursive font application',
            'unknown option "-font"',
            'Tkinter font error',
            'font family not found'
        ]
        self.limiting_enabled = True
        self.max_errors_to_show = 3  # Show first 3 of each pattern type
        self.error_counts = {}  # Track count for each pattern
        self.logger = logging.getLogger("cargosim.stderr_limiter")
        
    def write(self, text: str):
        """Write text to stderr, limiting unwanted messages."""
        if not self.limiting_enabled:
            self.original_stderr.write(text)
            return
        
        # Check if this text contains any limited patterns
        if self._should_limit(text):
            # Count and limit this type of error
            pattern = self._get_matching_pattern(text)
            if pattern:
                if pattern not in self.error_counts:
                    self.error_counts[pattern] = 0
                
                self.error_counts[pattern] += 1
                
                if self.error_counts[pattern] <= self.max_errors_to_show:
                    # Show the first few errors
                    self.original_stderr.write(text)
                    if self.error_counts[pattern] == self.max_errors_to_show:
                        limit_msg = f"\nFont errors limited to {self.max_errors_to_show}. Additional errors will be logged only.\n"
                        self.original_stderr.write(limit_msg)
                else:
                    # Log additional errors but don't show in console
                    self.logger.debug(f"Limited stderr message: {text.strip()}")
                return
        
        # Write non-limited text to original stderr
        self.original_stderr.write(text)
    
    def _should_limit(self, text: str) -> bool:
        """Check if text should be limited."""
        if not text or not text.strip():
            return False
        
        text_lower = text.lower()
        return any(pattern.lower() in text_lower for pattern in self.limited_patterns)
    
    def _get_matching_pattern(self, text: str) -> Optional[str]:
        """Get the pattern that matches this text."""
        text_lower = text.lower()
        for pattern in self.limited_patterns:
            if pattern.lower() in text_lower:
                return pattern
        return None
    
    def flush(self):
        """Flush the original stderr."""
        self.original_stderr.flush()
    
    def close(self):
        """Close the original stderr."""
        self.original_stderr.close()
    
    def enable_limiting(self):
        """Enable message limiting."""
        self.limiting_enabled = True
        self.logger.info("Stderr limiting enabled")
    
    def disable_limiting(self):
        """Disable message limiting."""
        self.limiting_enabled = False
        self.logger.info("Stderr limiting disabled")
    
    def set_max_errors_to_show(self, max_errors: int):
        """Set the maximum number of errors to show before limiting."""
        self.max_errors_to_show = max_errors
        self.logger.info(f"Stderr error limit set to {max_errors}")
    
    def add_limit_pattern(self, pattern: str):
        """Add a new limit pattern."""
        if pattern not in self.limited_patterns:
            self.limited_patterns.append(pattern)
            self.logger.debug(f"Added limit pattern: {pattern}")
    
    def remove_limit_pattern(self, pattern: str):
        """Remove a limit pattern."""
        if pattern in self.limited_patterns:
            self.limited_patterns.remove(pattern)
            self.logger.debug(f"Removed limit pattern: {pattern}")
    
    def get_limit_patterns(self) -> list:
        """Get current limit patterns."""
        return self.limited_patterns.copy()
    
    def get_error_counts(self) -> dict:
        """Get current error counts for each pattern."""
        return self.error_counts.copy()
    
    def reset_error_counts(self):
        """Reset error counts for all patterns."""
        self.error_counts.clear()
        self.logger.info("Stderr error counts reset")


# Global stderr limiter instance
_stderr_limiter = None


def install_stderr_limiter():
    """Install stderr limiting to limit font errors."""
    global _stderr_limiter
    
    if _stderr_limiter is None:
        # Create and install the limiter
        original_stderr = sys.stderr
        _stderr_limiter = LimitedStderr(original_stderr)
        sys.stderr = _stderr_limiter
        
        # Log the installation
        logger = logging.getLogger("cargosim.stderr_limiter")
        logger.info("Stderr limiting system installed")
    
    return _stderr_limiter


def get_stderr_limiter() -> Optional[LimitedStderr]:
    """Get the current stderr limiter instance."""
    return _stderr_limiter


def restore_original_stderr():
    """Restore the original stderr stream."""
    global _stderr_limiter
    
    if _stderr_limiter and hasattr(_stderr_limiter, 'original_stderr'):
        sys.stderr = _stderr_limiter.original_stderr
        _stderr_limiter = None
        
        logger = logging.getLogger("cargosim.stderr_limiter")
        logger.info("Original stderr restored")


# Install stderr limiter on module import
install_stderr_limiter()
