"""Pytest configuration and common fixtures for CargoSim tests."""

import os
import sys
import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables for testing
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


@pytest.fixture(scope="session")
def test_config():
    """Provide a basic test configuration."""
    from cargosim.config import SimConfig
    
    cfg = SimConfig()
    cfg.periods = 10
    cfg.fleet_label = "2xC130"
    cfg.debug_mode = False
    cfg.launch_fullscreen = False
    return cfg


@pytest.fixture(scope="function")
def test_simulation(test_config):
    """Provide a test simulation instance."""
    from cargosim.simulation import LogisticsSim
    
    sim = LogisticsSim(test_config)
    yield sim
    
    # Cleanup if needed
    if hasattr(sim, 'cleanup'):
        sim.cleanup()


@pytest.fixture(scope="function")
def test_renderer(test_simulation):
    """Provide a test renderer instance."""
    from cargosim.renderer import Renderer
    
    renderer = Renderer(test_simulation, force_windowed=True)
    
    # Force initialization for testing
    renderer._ensure_display_initialized()
    renderer._ensure_gfx_pipeline_initialized()
    
    yield renderer
    
    # Cleanup pygame
    try:
        pygame.quit()
    except:
        pass


def pytest_configure(config):
    """Configure pytest for CargoSim testing."""
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
        # Mark tests based on their location
        if "test_simulation.py" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "test_enhanced_features.py" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "test_ops_gate.py" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "test_fullscreen.py" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
