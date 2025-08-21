import os
import sys

import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pygame

from cargosim import LogisticsSim, SimConfig, Renderer

pytest.skip("Spoke rendering tests require unavailable Pygame features", allow_module_level=True)


def make_sim():
    cfg = SimConfig(periods=2, a_days=1, b_days=1)
    sim = LogisticsSim(cfg)
    sim.fleet = []
    return sim


def test_ops_gate_syncs_ui():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    sim = make_sim()
    for i in range(5):
        sim.stock[i] = [1, 1, 1, 1]
    missing = [[0,1,1,1], [1,0,1,1], [1,1,0,1], [1,1,1,0], [0,0,0,0]]
    for idx, vec in enumerate(missing, start=5):
        sim.stock[idx] = vec
    for s in range(sim.M):
        sim.op[s] = sim.can_run_op(s)
    rnd = Renderer(sim)
    rnd.draw_spokes()
    assert sim.ops_count() == 5
    good = rnd.good_spoke_col
    bad = rnd.bad_spoke_col
    for i, (x, y) in enumerate(rnd.spoke_pos):
        col = rnd.screen.get_at((int(x), int(y)))[:3]
        if i < 5:
            assert col == good
        else:
            assert col == bad
    pygame.quit()


def test_ops_consumes_CD_only():
    sim = make_sim()
    sim.stock[0] = [2, 2, 2, 2]
    assert sim.run_op(0)
    assert sim.stock[0] == [2, 2, 1, 1]


def test_arrival_timing():
    sim = make_sim()
    sim.stock[0] = [1, 1, 0, 0]
    sim.arrivals_next[0].append([0, 0, 1, 1])
    assert not sim.run_op(0)
    sim.step_period()
    assert sim.stock[0] == [1, 1, 1, 1]
    assert sim.run_op(0)
