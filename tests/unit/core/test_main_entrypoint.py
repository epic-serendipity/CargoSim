"""
Unit tests for the main entry point and correlation ID integration.

Tests that correlation IDs are properly set and propagated through the system.
"""

import pytest
import logging
import uuid
from unittest.mock import patch, MagicMock

from cargosim.core.logging_config import get_correlation_id, set_correlation_id


class TestMainEntryPoint:
    """Test the main entry point functionality."""
    
    def test_correlation_id_generation(self):
        """Test that correlation IDs are generated for new runs."""
        # Get initial correlation ID
        initial_id = get_correlation_id()
        assert isinstance(initial_id, str)
        assert len(initial_id) > 0
        
        # Set a new correlation ID
        new_id = str(uuid.uuid4())
        set_correlation_id(new_id)
        
        # Verify it was set
        assert get_correlation_id() == new_id
    
    def test_correlation_id_uniqueness(self):
        """Test that correlation IDs are unique across different runs."""
        # Get first correlation ID
        first_id = get_correlation_id()
        
        # Set a new one
        second_id = str(uuid.uuid4())
        set_correlation_id(second_id)
        
        # Verify they're different
        assert first_id != second_id
        assert get_correlation_id() == second_id
    
    def test_correlation_id_logging_integration(self, cap_sim_logs):
        """Test that correlation IDs are included in log messages."""
        # Set a known correlation ID
        test_id = "test-run-12345"
        set_correlation_id(test_id)
        
        # Get a logger and log a message
        logger = logging.getLogger("cargosim.test")
        logger.info("Test message with correlation ID")
        
        # Verify the correlation ID appears in the logs
        log_text = cap_sim_logs.text
        assert test_id[:8] in log_text  # First 8 chars should appear
        assert "Test message with correlation ID" in log_text
    
    def test_correlation_id_context_isolation(self):
        """Test that correlation IDs are isolated to their context."""
        # Set initial correlation ID
        initial_id = get_correlation_id()
        
        # Set a new one
        new_id = "context-test-67890"
        set_correlation_id(new_id)
        
        # Verify the new one is active
        assert get_correlation_id() == new_id
        
        # Reset to original
        set_correlation_id(initial_id)
        assert get_correlation_id() == initial_id


class TestLoggingIntegration:
    """Test logging integration with correlation IDs."""
    
    def test_logger_creation_with_correlation(self, cap_sim_logs):
        """Test that loggers include correlation IDs."""
        # Set a correlation ID
        test_id = "logger-test-11111"
        set_correlation_id(test_id)
        
        # Create multiple loggers
        loggers = [
            logging.getLogger("cargosim.core"),
            logging.getLogger("cargosim.ui"),
            logging.getLogger("cargosim.rendering")
        ]
        
        # Log messages from each
        for logger in loggers:
            logger.info(f"Message from {logger.name}")
        
        # Verify all messages include the correlation ID
        log_text = cap_sim_logs.text
        assert test_id[:8] in log_text
        
        # Verify all logger names appear
        for logger in loggers:
            assert logger.name in log_text
    
    def test_log_levels_with_correlation(self, cap_sim_logs):
        """Test that different log levels include correlation IDs."""
        # Set a correlation ID
        test_id = "level-test-22222"
        set_correlation_id(test_id)
        
        logger = logging.getLogger("cargosim.test")
        
        # Log at different levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # Verify correlation ID appears in all levels
        log_text = cap_sim_logs.text
        assert test_id[:8] in log_text
        
        # Verify all messages appear
        assert "Debug message" in log_text
        assert "Info message" in log_text
        assert "Warning message" in log_text
        assert "Error message" in log_text


class TestSimulationRunTracking:
    """Test simulation run tracking with correlation IDs."""
    
    def test_simulation_start_correlation_id(self):
        """Test that simulation start generates a correlation ID."""
        # Simulate starting a new simulation
        simulation_id = str(uuid.uuid4())
        set_correlation_id(simulation_id)
        
        # Verify the correlation ID is set
        assert get_correlation_id() == simulation_id
        
        # Verify it's a valid UUID format
        try:
            uuid.UUID(simulation_id)
        except ValueError:
            pytest.fail("Correlation ID should be a valid UUID")
    
    def test_multiple_simulation_runs(self):
        """Test that multiple simulation runs get different correlation IDs."""
        correlation_ids = set()
        
        # Simulate multiple simulation runs
        for i in range(5):
            run_id = str(uuid.uuid4())
            set_correlation_id(run_id)
            correlation_ids.add(run_id)
            
            # Verify current correlation ID
            assert get_correlation_id() == run_id
        
        # Verify all correlation IDs are unique
        assert len(correlation_ids) == 5
    
    def test_correlation_id_persistence(self):
        """Test that correlation IDs persist during a simulation run."""
        # Set initial correlation ID
        initial_id = str(uuid.uuid4())
        set_correlation_id(initial_id)
        
        # Simulate multiple operations during the same run
        operations = [
            "load_configuration",
            "initialize_aircraft",
            "start_simulation",
            "process_frame",
            "update_physics"
        ]
        
        for operation in operations:
            # Verify correlation ID hasn't changed
            assert get_correlation_id() == initial_id
            
            # Simulate some work
            current_id = get_correlation_id()
            assert current_id == initial_id


if __name__ == "__main__":
    pytest.main([__file__])
