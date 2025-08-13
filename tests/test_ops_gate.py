import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from cargo_sim import LogisticsSim, SimConfig

def make_sim():
    cfg = SimConfig(periods=2, a_days=1, b_days=1)
    sim = LogisticsSim(cfg)
    sim.fleet = []
    return sim


def test_op_occurs_and_consumes_cd():
    sim = make_sim()
    sim.stock[0] = [1, 1, 1, 1]
    assert sim.run_op(0)
    assert sim.stock[0] == [1, 1, 0, 0]
    assert sim.ops_by_spoke[0] == 1


def test_op_blocked_when_missing():
    sim = make_sim()
    sim.stock[0] = [1, 0, 1, 1]
    assert not sim.run_op(0)
    assert sim.stock[0] == [1, 0, 1, 1]
    assert sim.ops_by_spoke[0] == 0


def test_pm_consumption_requires_a_and_b():
    sim = make_sim()
    sim.stock[0] = [0, 1, 0, 0]
    sim.t = 1
    sim.step_period()
    assert sim.stock[0] == [0, 1, 0, 0]

    sim2 = make_sim()
    sim2.stock[0] = [2, 3, 1, 1]
    sim2.t = 1
    sim2.step_period()
    assert sim2.stock[0][0] == 1 and sim2.stock[0][1] == 2
    assert sim2.stock[0][2] == 1 and sim2.stock[0][3] == 1
