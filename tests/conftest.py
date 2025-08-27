"""
Pytest configuration and shared fixtures for CargoSim tests.
"""

import pytest
import logging
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch

from cargosim.core.logging_config import cleanup_logging


@pytest.fixture(scope="function")
def cap_sim_logs(caplog):
    """
    Capture CargoSim logs for testing.
    
    This fixture provides a way to capture and assert on log messages
    from the CargoSim logging system.
    
    Usage:
        def test_something(cap_sim_logs):
            logger = logging.getLogger("cargosim.some.module")
            logger.warning("Test warning")
            
            # Assert on captured logs
            assert "Test warning" in cap_sim_logs.text
            assert len(cap_sim_logs.records) == 1
    """
    # Set the log level for all CargoSim loggers
    caplog.set_level(logging.DEBUG, logger="cargosim")
    
    # Clean up any existing logging state
    cleanup_logging()
    
    yield caplog
    
    # Clean up after test
    cleanup_logging()


@pytest.fixture(scope="function")
def temp_log_dir(tmp_path):
    """
    Create a temporary directory for log files during testing.
    
    This fixture ensures tests don't interfere with actual log files
    and provides a clean environment for each test.
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    
    # Mock the log file paths to use our temp directory
    with patch('cargosim.core.paths.DEBUG_LOG_FILE', log_dir / "debug.log"), \
         patch('cargosim.core.paths.RUNTIME_LOG_FILE', log_dir / "runtime.log"):
        yield log_dir


@pytest.fixture(scope="function")
def mock_config_dir(tmp_path):
    """
    Create a temporary directory for configuration files during testing.
    
    This fixture provides a clean environment for config-related tests.
    """
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    # Create some example config files
    (config_dir / "test_config.json").write_text('{"test": "value"}')
    
    yield config_dir


@pytest.fixture(scope="function")
def isolated_environment():
    """
    Provide an isolated environment for tests.
    
    This fixture clears environment variables and provides a clean slate
    for environment-dependent tests.
    """
    # Store original environment
    original_env = dict(os.environ)
    
    # Clear CargoSim-specific environment variables
    env_vars_to_clear = [
        'CARGOSIM_LOG_FORMAT',
        'CARGOSIM_LOG_LEVEL',
        'CARGOSIM_CONFIG_PATH'
    ]
    
    for var in env_vars_to_clear:
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(scope="session")
def sample_aircraft_config():
    """
    Provide a sample aircraft configuration for testing.
    
    This fixture returns a valid aircraft configuration that can be used
    in tests without needing to load external files.
    """
    return {
        "name": "Test Aircraft",
        "type": "cargo",
        "max_payload": 1000,
        "cruise_speed": 500,
        "fuel_capacity": 2000,
        "range": 3000,
        "crew": 2,
        "dimensions": {
            "length": 20,
            "wingspan": 25,
            "height": 6
        },
        "performance": {
            "takeoff_distance": 800,
            "landing_distance": 600,
            "service_ceiling": 35000
        }
    }


@pytest.fixture(scope="session")
def sample_simulation_config():
    """
    Provide a sample simulation configuration for testing.
    
    This fixture returns a valid simulation configuration that can be used
    in tests without needing to load external files.
    """
    return {
        "simulation": {
            "duration": 3600,
            "time_step": 1.0,
            "max_iterations": 10000
        },
        "rendering": {
            "fps": 60,
            "resolution": [1920, 1080],
            "fullscreen": False
        },
        "logging": {
            "level": "INFO",
            "format": "human",
            "retention_days": 30
        }
    }


# Configure pytest to show more detailed output
def pytest_configure(config):
    """Configure pytest with CargoSim-specific settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add default markers."""
    for item in items:
        # Add unit marker to tests in unit/ directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        # Add integration marker to tests in integration/ directory
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
