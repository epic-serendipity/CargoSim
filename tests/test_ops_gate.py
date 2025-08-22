import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pygame

from cargosim.simulation import LogisticsSim
from cargosim.config import SimConfig
from cargosim.renderer import Renderer


def make_sim():
    cfg = SimConfig(periods=2, a_days=1, b_days=1)
    sim = LogisticsSim(cfg)
    sim.fleet = []
    return sim


def test_ops_gate_syncs_ui():
    """Test that operations gate properly syncs with UI rendering."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    sim = make_sim()
    
    # Set up test data
    for i in range(5):
        sim.stock[i] = [1, 1, 1, 1]
    missing = [[0,1,1,1], [1,0,1,1], [1,1,0,1], [1,1,1,0], [0,0,0,0]]
    for idx, vec in enumerate(missing, start=5):
        sim.stock[idx] = vec
    
    # Update operational flags
    for s in range(sim.M):
        sim.op[s] = sim.can_run_op(s)
    
    # Create renderer with force_windowed to avoid fullscreen issues
    rnd = Renderer(sim, force_windowed=True)
    
    # Force display and graphics pipeline initialization for testing
    rnd._ensure_display_initialized()
    rnd._ensure_gfx_pipeline_initialized()
    
    # Test that operational count is correct
    assert sim.ops_count() == 5
    
    # Test that renderer can access spoke positions (basic functionality)
    assert hasattr(rnd, 'spoke_pos')
    assert rnd.spoke_pos is not None
    assert len(rnd.spoke_pos) == sim.M
    
    pygame.quit()


def test_ops_consumes_CD_only():
    """Test that operations only consume C and D resources."""
    sim = make_sim()
    sim.stock[0] = [2, 2, 2, 2]
    assert sim.run_op(0)
    assert sim.stock[0] == [2, 2, 1, 1]


def test_arrival_timing():
    """Test that arrivals are properly timed and applied."""
    sim = make_sim()
    sim.stock[0] = [1, 1, 0, 0]
    sim.arrivals_next[0].append([0, 0, 1, 1])
    assert not sim.run_op(0)
    sim.step_period()
    assert sim.stock[0] == [1, 1, 1, 1]
    assert sim.run_op(0)
