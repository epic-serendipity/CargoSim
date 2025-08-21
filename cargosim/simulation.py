"""Core simulation logic for CargoSim."""

import copy
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import List, Tuple, Optional

from .config import M, PAIR_ORDER_DEFAULT, A_PERIOD_DAYS_DFLT, B_PERIOD_DAYS_DFLT, C_PERIOD_DAYS_DFLT, D_PERIOD_DAYS_DFLT, VIS_CAPS_DFLT
from .config import SimConfig


def _row_to_spoke(row: List[float]) -> SimpleNamespace:
    return SimpleNamespace(A=row[0], B=row[1], C=row[2], D=row[3])


def is_ops_capable(spoke, eps=1e-9) -> bool:
    # Must reflect ONLY inventory available **now**, not in-flight or next-period arrivals.
    return (spoke.A > eps and spoke.B > eps and spoke.C > eps and spoke.D > eps)


@dataclass
class Aircraft:
    typ: str           # "C-130" or "C-27"
    cap: int           # capacity
    name: str
    location: str = "HUB"  # "HUB" or "S{1..10}"
    state: str = "IDLE"    # IDLE, LEG1_ENROUTE, AT_SPOKEA, AT_SPOKEB_ENROUTE, AT_SPOKEB, RETURN_ENROUTE
    plan: Optional[Tuple[int, Optional[int]]] = None  # (i, j|None)
    payload_A: List[int] = field(default_factory=lambda: [0,0,0,0])
    payload_B: List[int] = field(default_factory=lambda: [0,0,0,0])
    active_periods: int = 0
    rest_cooldown: int = 0

    def max_active_before_rest(self, cfg: SimConfig) -> int:
        return cfg.rest_c130 if self.typ == "C-130" else cfg.rest_c27

    def at_hub(self) -> bool:
        return self.location == "HUB"


class LogisticsSim:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.M = M
        self.PAIR_ORDER = list(cfg.pair_order)
        self.A_PERIOD_DAYS = cfg.a_days
        self.B_PERIOD_DAYS = cfg.b_days
        self.C_PERIOD_DAYS = cfg.c_days
        self.D_PERIOD_DAYS = cfg.d_days
        self.VIS_CAPS = VIS_CAPS_DFLT

        self.reset_world()

    def reset_world(self):
        self.t = 0  # current period
        self.day = 0
        self.half = "AM"  # AM for even t, PM for odd t
        self.stock = [[self.cfg.init_A, self.cfg.init_B, self.cfg.init_C, self.cfg.init_D] for _ in range(self.M)]
        self.op = [False]*self.M  # operational flags (A+B+C+D gate)
        self.arrivals_next = [[] for _ in range(self.M)]
        self.pair_cursor = 0
        self.fleet = self.build_fleet(self.cfg.fleet_label)
        self.actions_log: List[List[Tuple[str,str]]] = []

        # Stats
        self.ops_by_spoke = [0]*self.M  # counts of OFFLOAD occurrences per spoke
        self.ops_total_history = [0]
        self.integrity_violations: List[str] = []
        self._integrity_logged = False

        # History for rewind
        self.history: List[dict] = []
        self.push_snapshot()  # store initial state (period 0 before any action)

    def can_run_op(self, s: int) -> bool:
        return is_ops_capable(_row_to_spoke(self.stock[s]))

    def run_op(self, s: int, amount: int = 1) -> bool:
        if not is_ops_capable(_row_to_spoke(self.stock[s])):
            return False
        self.stock[s][2] = max(0.0, self.stock[s][2] - amount)
        self.stock[s][3] = max(0, self.stock[s][3] - amount)
        assert self.stock[s][2] >= -1e-9 and self.stock[s][3] >= -1e-9, "C/D negative after op"
        self.ops_by_spoke[s] += 1
        return True

    def build_fleet(self, label: str) -> List[Aircraft]:
        if label == "2xC130":
            return [Aircraft("C-130", self.cfg.cap_c130, "C-130 #1"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #2")]
        if label == "4xC130":
            return [Aircraft("C-130", self.cfg.cap_c130, "C-130 #1"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #2"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #3"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #4")]
        if label == "2xC130_2xC27":
            return [Aircraft("C-130", self.cfg.cap_c130, "C-130 #1"),
                    Aircraft("C-130", self.cfg.cap_c130, "C-130 #2"),
                    Aircraft("C-27", self.cfg.cap_c27, "C-27 #1"),
                    Aircraft("C-27", self.cfg.cap_c27, "C-27 #2")]
        raise ValueError("Unknown fleet label")

    def detect_stage(self) -> str:
        if any(self.stock[i][0] == 0 for i in range(self.M)):
            return "A"
        if any(self.stock[i][1] == 0 for i in range(self.M)):
            return "B"
        return "OPS"

    def plan_for_pair_stage(self, i: int, j: int, cap_left: int, stage: str):
        p_i = [0,0,0,0]; p_j = [0,0,0,0]; rem = cap_left
        def give(target_idx: int, k: int, need: int):
            nonlocal rem
            if rem <= 0 or need <= 0: return
            x = min(rem, need)
            if target_idx == i: p_i[k] += x
            else: p_j[k] += x
            rem -= x

        needA_i = max(0, 1 - self.stock[i][0]); needB_i = max(0, 1 - self.stock[i][1])
        needA_j = max(0, 1 - self.stock[j][0]); needB_j = max(0,  1 - self.stock[j][1])
        needC_i = max(0, 1 - self.stock[i][2]); needD_i = max(0,  1 - self.stock[i][3])
        needC_j = max(0,  1 - self.stock[j][2]); needD_j = max(0,  1 - self.stock[j][3])

        if stage == "A":
            give(i,0,needA_i); give(j,0,needA_j)
            give(i,1,needB_i); give(j,1,needB_j)
            give(i,0, max(0, 2 - (self.stock[i][0] + p_i[0])))
            give(j,0, max(0, 2 - (self.stock[j][0] + p_j[0])))
        elif stage == "B":
            give(i,1,needB_i); give(j,1,needB_j)
            give(i,0, max(0, 2 - self.stock[i][0]))
            give(j,0, max(0, 2 - self.stock[j][0]))
        else:  # "OPS"
            give(i,2,needC_i); give(j,2,needC_j)
            give(i,3,needD_i); give(j,3,needD_j)
            give(i,2, max(0, 2 - (self.stock[i][2] + p_i[2])))
            give(j,2, max(0, 2 - (self.stock[j][2] + p_j[2])))
            give(i,3, max(0, 2 - (self.stock[i][3] + p_i[3])))
            give(j,3, max(0, 2 - (self.stock[j][3] + p_j[3])))

        return p_i, p_j

    def snapshot(self) -> dict:
        return {
            "t": self.t,
            "day": self.day,
            "half": self.half,
            "stock": copy.deepcopy(self.stock),
            "op": self.op.copy(),
            "arrivals_next": copy.deepcopy(self.arrivals_next),
            "pair_cursor": self.pair_cursor,
            "fleet": copy.deepcopy(self.fleet),
            "actions_log": copy.deepcopy(self.actions_log),
            "ops_by_spoke": self.ops_by_spoke[:],
            "ops_total_history": self.ops_total_history[:],
        }

    def restore(self, snap: dict):
        self.t = snap["t"]
        self.day = snap["day"]
        self.half = snap["half"]
        self.stock = copy.deepcopy(snap["stock"])
        self.op = snap["op"].copy()
        self.arrivals_next = copy.deepcopy(snap["arrivals_next"])
        self.pair_cursor = snap["pair_cursor"]
        self.fleet = copy.deepcopy(snap["fleet"])
        self.actions_log = copy.deepcopy(snap["actions_log"])
        self.ops_by_spoke = snap.get("ops_by_spoke", [0]*self.M)[:]
        self.ops_total_history = snap.get("ops_total_history", [0])[:]

    def push_snapshot(self):
        self.history.append(self.snapshot())

    def step_period(self):
        if self.t >= self.cfg.periods:
            return None  # Simulation complete - reached max periods

        pre_stock = [row[:] for row in self.stock]
        ops_before = self.ops_by_spoke[:]
        pre_ops_total = sum(self.ops_by_spoke)

        # 1) APPLY_ARRIVALS_FROM_PREVIOUS_PERIOD
        for s in range(self.M):
            if self.arrivals_next[s]:
                add = [0,0,0,0]
                for vec in self.arrivals_next[s]:
                    for k in range(4): add[k] += vec[k]
                self.arrivals_next[s].clear()
                for k in range(4): self.stock[s][k] += add[k]

        # 2) RECOMPUTE_STATE_SNAPSHOTS (flags derived from stock)
        stage = self.detect_stage()
        actions_this_period: List[Tuple[str,str]] = []
        pairs_used = set()  # ensure unique pair per period across all aircraft

        # 3) Aircraft actions
        for ac in sorted(self.fleet, key=lambda a: (-a.cap, a.name)):
            if ac.rest_cooldown > 0:
                actions_this_period.append((ac.name, "REST at HUB"))
                ac.rest_cooldown -= 1
                continue

            events = 0
            def consume_event():
                nonlocal events, ac
                events += 1
                if events == 1:
                    ac.active_periods += 1

            # rest if due
            if ac.at_hub() and ac.active_periods >= ac.max_active_before_rest(self.cfg) and ac.state in ("IDLE","REST"):
                actions_this_period.append((ac.name, "INITIATE REST at HUB"))
                ac.active_periods = 0
                ac.rest_cooldown = 1
                continue

            # progress in-flight states
            if ac.state == "LEG1_ENROUTE":
                i = ac.plan[0] if ac.plan else 0
                ac.state = "AT_SPOKEA"
                ac.location = f"S{i+1}"
            if ac.state == "AT_SPOKEA":
                i = ac.plan[0]
                self.arrivals_next[i].append(ac.payload_A[:])
                if is_ops_capable(_row_to_spoke(self.stock[i])):
                    self.run_op(i)
                actions_this_period.append((ac.name, f"OFFLOAD@S{i+1}"))
                ac.payload_A = [0,0,0,0]
                consume_event()
                if events < 2:
                    if ac.plan[1] is not None:
                        j = ac.plan[1]
                        ac.state = "AT_SPOKEB_ENROUTE"
                        actions_this_period.append((ac.name, f"MOVE S{i+1}→S{j+1}"))
                        consume_event()
                    else:
                        ac.plan = None
                        ac.state = "RETURN_ENROUTE"
                        actions_this_period.append((ac.name, f"MOVE S{i+1}→HUB"))
                        consume_event()
                continue
            if ac.state == "AT_SPOKEB_ENROUTE":
                j = ac.plan[1] if ac.plan else 0
                ac.state = "AT_SPOKEB"
                ac.location = f"S{j+1}"
            if ac.state == "AT_SPOKEB":
                j = ac.plan[1]
                self.arrivals_next[j].append(ac.payload_B[:])
                if is_ops_capable(_row_to_spoke(self.stock[j])):
                    self.run_op(j)
                actions_this_period.append((ac.name, f"OFFLOAD@S{j+1}"))
                ac.payload_B = [0,0,0,0]
                consume_event()
                if events < 2:
                    ac.plan = None
                    ac.state = "RETURN_ENROUTE"
                    actions_this_period.append((ac.name, f"MOVE S{j+1}→HUB"))
                    consume_event()
                continue
            if ac.state == "RETURN_ENROUTE":
                ac.location = "HUB"
                ac.state = "IDLE"
                continue

            # new sortie
            if ac.at_hub() and ac.state == "IDLE":
                if ac.active_periods >= ac.max_active_before_rest(self.cfg):
                    actions_this_period.append((ac.name, "INITIATE REST at HUB"))
                    ac.active_periods = 0
                    ac.rest_cooldown = 1
                    continue

                tried = 0
                cursor = self.pair_cursor
                chosen_pair = None
                while tried < len(self.PAIR_ORDER):
                    i, j = self.PAIR_ORDER[cursor]
                    p_i, p_j = self.plan_for_pair_stage(i, j, ac.cap, stage)
                    key = (i, j if p_j and sum(p_j)>0 else -1)
                    if (sum(p_i) + sum(p_j)) > 0 and key not in pairs_used:
                        chosen_pair = (i, j)
                        break
                    cursor = (cursor + 1) % len(self.PAIR_ORDER)
                    tried += 1

                if chosen_pair is None:
                    continue

                i, j = chosen_pair
                p_i, p_j = self.plan_for_pair_stage(i, j, ac.cap, stage)
                if sum(p_i) == 0 and sum(p_j) == 0:
                    continue
                leg2_none = False
                if sum(p_j) == 0:
                    chosen_pair = (i, None)
                    leg2_none = True

                key = (i, (j if not leg2_none else -1))
                pairs_used.add(key)
                self.pair_cursor = (cursor + 1) % len(self.PAIR_ORDER)

                ac.plan = chosen_pair
                ac.payload_A = p_i[:]
                ac.payload_B = p_j[:] if not leg2_none else [0,0,0,0]
                actions_this_period.append((ac.name, f"ONLOAD@HUB→S{i+1}"))
                ac.state = "LEG1_ENROUTE"
                actions_this_period.append((ac.name, f"MOVE HUB→S{i+1}"))
                consume_event(); consume_event()

        # 4) PM_CONSUMPTION
        if self.t % 2 == 1:
            self.day = self.t // 2
            if (self.day % self.A_PERIOD_DAYS) == (self.A_PERIOD_DAYS - 1):
                for s in range(self.M):
                    if self.stock[s][0] > 0 and self.stock[s][1] > 0:
                        self.stock[s][0] = max(0, self.stock[s][0] - 1)
            if (self.day % self.B_PERIOD_DAYS) == (self.B_PERIOD_DAYS - 1):
                for s in range(self.M):
                    if self.stock[s][0] > 0 and self.stock[s][1] > 0:
                        self.stock[s][1] = max(0, self.stock[s][1] - 1)

        # recompute operational flags after ops and PM consumption
        for s in range(self.M):
            self.op[s] = is_ops_capable(_row_to_spoke(self.stock[s]))

        self.check_invariants(pre_stock, ops_before)
        self.actions_log.append(actions_this_period)
        self.t += 1
        self.half = "AM" if self.t % 2 == 0 else "PM"
        self.ops_total_history.append(sum(self.ops_by_spoke))
        if len(self.ops_total_history) > 2000:
            self.ops_total_history = self.ops_total_history[-2000:]

        self.push_snapshot()

        if self.cfg.debug_mode:
            from .utils import append_debug
            lines = [f"[t={self.t} {self.half} day={self.t//2}] ops={self.ops_count()}"]
            lines += [f"  {nm}: {act}" for (nm, act) in actions_this_period]
            append_debug(lines)

        # Progress check to prevent infinite loops
        current_ops_total = sum(self.ops_by_spoke)
        if current_ops_total == pre_ops_total and len(actions_this_period) == 0:
            # No progress made this period, check if we need to intervene
            if self.t > 1:  # Skip this check for the first few periods to allow startup
                # Only force action if we've been stuck for multiple periods
                if not hasattr(self, '_stuck_periods'):
                    self._stuck_periods = 0
                self._stuck_periods += 1
                
                if self._stuck_periods >= 3:  # Only force action after 3 stuck periods
                    # Force at least one aircraft to move to prevent deadlock
                    for ac in self.fleet:
                        if ac.at_hub() and ac.state == "IDLE":
                            ac.state = "LEG1_ENROUTE"
                            ac.plan = (0, None)
                            ac.payload_A = [1, 1, 0, 0]
                            actions_this_period.append((ac.name, "FORCED MOVE HUB→S1"))
                            break
            else:
                # Reset stuck counter for early periods
                if hasattr(self, '_stuck_periods'):
                    self._stuck_periods = 0
        else:
            # Reset stuck counter when progress is made
            if hasattr(self, '_stuck_periods'):
                self._stuck_periods = 0

        return actions_this_period

    def ops_count(self) -> int:
        return sum(self.op)

    def check_invariants(self, pre_stock, ops_before):
        violations: List[str] = []
        for s in range(self.M):
            row = self.stock[s]
            assert all(v >= -1e-9 for v in row)
            hud_flag = is_ops_capable(_row_to_spoke(row))
            node_flag = self.op[s]
            if hud_flag != node_flag:
                violations.append(f"ops-cap mismatch at S{s+1}")
            if self.ops_by_spoke[s] > ops_before[s]:
                delta_c = pre_stock[s][2] - row[2]
                delta_d = pre_stock[s][3] - row[3]
                delta_ops = self.ops_by_spoke[s] - ops_before[s]
                if not (delta_c >= delta_ops - 1e-6 and delta_d >= delta_ops - 1e-6):
                    violations.append(f"C/D not consumed for ops at S{s+1}")
        self.integrity_violations = violations
        if violations and not self._integrity_logged:
            from .utils import append_debug
            append_debug(["Integrity violations:"] + violations)
            self._integrity_logged = True
