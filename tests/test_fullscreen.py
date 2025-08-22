import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pygame

from cargosim.simulation import LogisticsSim
from cargosim.config import SimConfig
from cargosim.renderer import Renderer


def test_fullscreen_default():
    """Test that fullscreen mode works correctly."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    cfg = SimConfig()
    sim = LogisticsSim(cfg)
    
    # Test with force_windowed=False to allow fullscreen
    rnd = Renderer(sim, force_windowed=False)
    
    # Force display initialization for testing
    rnd._ensure_display_initialized()
    
    # Test that fullscreen flag is set correctly
    assert rnd.fullscreen == cfg.launch_fullscreen
    
    # Test that pygame screen is created
    assert rnd.screen is not None
    
    pygame.quit()


def test_windowed_mode():
    """Test that windowed mode works correctly."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    cfg = SimConfig()
    sim = LogisticsSim(cfg)
    
    # Test with force_windowed=True to force windowed mode
    rnd = Renderer(sim, force_windowed=True)
    
    # Force display initialization for testing
    rnd._ensure_display_initialized()
    
    # Test that fullscreen flag is False when forced windowed
    assert rnd.fullscreen is False
    
    # Test that pygame screen is created
    assert rnd.screen is not None
    
    pygame.quit()
