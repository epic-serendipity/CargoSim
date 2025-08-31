"""
Centralized path configuration for CargoSim.

This module provides a single source of truth for all file paths,
making it easier to manage folder reorganization and prevent path-related issues.
"""

import os
from pathlib import Path

# Base project directory (3 levels up from core/)
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()

# Configuration directories
CONFIGS_DIR = PROJECT_ROOT / "configs"
DEFAULT_CONFIGS_DIR = CONFIGS_DIR / "default"
USER_CONFIGS_DIR = CONFIGS_DIR / "user"

# Log directories
LOGS_DIR = PROJECT_ROOT / "logs"
DEBUG_LOGS_DIR = LOGS_DIR / "debug"
RUNTIME_LOGS_DIR = LOGS_DIR / "runtime"

# Ensure log directories exist
DEBUG_LOGS_DIR.mkdir(parents=True, exist_ok=True)
RUNTIME_LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# User configuration auto-cloning helpers
# ------------------------------------------------------------------
import shutil


def _ensure_user_aircraft_config() -> None:
    """Clone the default aircraft config to the user directory if absent.

    The application always reads/writes the *user* version of the file.  On the
    first run a user may not have this file yet, so copy the pristine default
    as a starting point.  Any subsequent modifications affect only the user-
    level configuration.
    """
    try:
        if not USER_AIRCRAFT_CONFIG_FILE.exists():
            USER_AIRCRAFT_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            if AIRCRAFT_CONFIG_FILE.exists():
                shutil.copyfile(AIRCRAFT_CONFIG_FILE, USER_AIRCRAFT_CONFIG_FILE)
    except OSError as exc:
        # If cloning fails we silently continue; downstream code will fallback
        # to built-in defaults so the application can still function.
        import logging
        logging.getLogger(__name__).warning(
            "Could not clone default aircraft configuration: %s", exc
        )


# Configuration files
AIRCRAFT_CONFIG_FILE = DEFAULT_CONFIGS_DIR / "aircraft_config.json"
MAIN_CONFIG_FILE = DEFAULT_CONFIGS_DIR / "cargo_sim_config.json"

# User-level configuration files
USER_AIRCRAFT_CONFIG_FILE = USER_CONFIGS_DIR / "aircraft_config.json"
USER_MAIN_CONFIG_FILE = USER_CONFIGS_DIR / "cargo_sim_config.json"

# Log files
DEBUG_LOG_FILE = DEBUG_LOGS_DIR / "cargo_sim_debug.log"
RUNTIME_LOG_FILE = RUNTIME_LOGS_DIR / "cargo_sim_runtime.log"

# Example and test directories
EXAMPLES_DIR = PROJECT_ROOT / "examples"
TESTS_DIR = PROJECT_ROOT / "tests"

def get_config_path(filename: str) -> Path:
    """Get path to a configuration file."""
    return DEFAULT_CONFIGS_DIR / filename

def get_user_config_path(filename: str) -> Path:
    """Get path to a user configuration file."""
    return USER_CONFIGS_DIR / filename

def get_config_dir() -> Path:
    """Get the default configuration directory."""
    return DEFAULT_CONFIGS_DIR

def get_user_config_dir() -> Path:
    """Get the user configuration directory."""
    return USER_CONFIGS_DIR

def get_log_path(filename: str, log_type: str = "runtime") -> Path:
    """Get path to a log file."""
    if log_type == "debug":
        return DEBUG_LOGS_DIR / filename
    else:
        return RUNTIME_LOGS_DIR / filename

def ensure_directories():
    """Ensure all required directories exist."""
    directories = [
        CONFIGS_DIR,
        DEFAULT_CONFIGS_DIR,
        USER_CONFIGS_DIR,
        LOGS_DIR,
        DEBUG_LOGS_DIR,
        RUNTIME_LOGS_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

def get_config_dir() -> Path:
    """Get the default configuration directory."""
    return DEFAULT_CONFIGS_DIR

def get_user_config_dir() -> Path:
    """Get the user configuration directory."""
    return USER_CONFIGS_DIR

# Ensure directories exist when module is imported
ensure_directories()
_ensure_user_aircraft_config()
