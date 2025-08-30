"""
Configuration Health Management for CargoSim.

This module provides classes and enums for tracking configuration health status,
validation errors, and recovery information.
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

class ConfigurationStatus(Enum):
    """Configuration status enumeration."""
    VALID = "valid"
    INVALID = "invalid"
    CORRUPTED = "corrupted"
    RECOVERING = "recovering"
    BACKUP_NEEDED = "backup_needed"

@dataclass
class ConfigurationHealth:
    """Represents configuration health status."""
    status: ConfigurationStatus
    last_validated: datetime
    validation_errors: List[str]
    backup_count: int
    last_backup: Optional[datetime]
    corruption_detected: bool
    recovery_attempts: int
    # Add missing attributes that are referenced in configuration_manager.py
    last_check: Optional[datetime] = None
    checksum: str = ""
    file_size: int = 0
    issues: List[str] = None  # Alias for validation_errors for backward compatibility
    
    def __post_init__(self):
        """Initialize default values for optional fields."""
        if self.issues is None:
            self.issues = self.validation_errors

class ConfigurationError(Exception):
    """Base exception for configuration-related errors."""
    pass

class ValidationError(ConfigurationError):
    """Exception raised when configuration validation fails."""
    pass

class RecoveryError(ConfigurationError):
    """Exception raised when configuration recovery fails."""
    pass
