"""Tests for the simulation module."""

import pytest
from cargosim.simulation import LogisticsSim, Aircraft, is_ops_capable, _row_to_spoke
from cargosim.config import SimConfig


class TestAircraft:
    """Test Aircraft class functionality."""
    
    def test_aircraft_creation(self):
        """Test aircraft creation with basic parameters."""
        ac = Aircraft("C-130", 6, "Test Aircraft")
        assert ac.typ == "C-130"
        assert ac.cap == 6
        assert ac.name == "Test Aircraft"
        assert ac.location == "HUB"
        assert ac.state == "IDLE"
    
    def test_aircraft_max_active_before_rest(self):
        """Test max active periods calculation."""
        cfg = SimConfig()
        ac_c130 = Aircraft("C-130", 6, "C-130")
        ac_c27 = Aircraft("C-27", 4, "C-27")
        
        assert ac_c130.max_active_before_rest(cfg) == cfg.rest_c130
        assert ac_c27.max_active_before_rest(cfg) == cfg.rest_c27
    
    def test_aircraft_at_hub(self):
        """Test hub location detection."""
        ac = Aircraft("C-130", 6, "Test")
        assert ac.at_hub() is True
        
        ac.location = "S1"
        assert ac.at_hub() is False


class TestLogisticsSim:
    """Test LogisticsSim class functionality."""
    
    @pytest.fixture
    def sim(self):
        """Create a basic simulation instance."""
        cfg = SimConfig()
        cfg.periods = 10
        cfg.fleet_label = "2xC130"
        return LogisticsSim(cfg)
    
    def test_simulation_initialization(self, sim):
        """Test simulation initialization."""
        assert sim.t == 0
        assert sim.half == "AM"
        assert sim.M == 10
        assert len(sim.fleet) == 2
        assert sim.fleet[0].typ == "C-130"
        assert sim.fleet[1].typ == "C-130"
    
    def test_reset_world(self, sim):
        """Test world reset functionality."""
        sim.t = 5
        sim.half = "PM"
        sim.reset_world()
        
        assert sim.t == 0
        assert sim.half == "AM"
        assert len(sim.history) > 0
    
    def test_build_fleet(self, sim):
        """Test fleet building with different configurations."""
        cfg = sim.cfg
        
        # Test 2xC130
        fleet = sim.build_fleet("2xC130")
        assert len(fleet) == 2
        assert all(ac.typ == "C-130" for ac in fleet)
        
        # Test 4xC130
        fleet = sim.build_fleet("4xC130")
        assert len(fleet) == 4
        assert all(ac.typ == "C-130" for ac in fleet)
        
        # Test 2xC130_2xC27
        fleet = sim.build_fleet("2xC130_2xC27")
        assert len(fleet) == 4
        assert fleet[0].typ == "C-130"
        assert fleet[1].typ == "C-130"
        assert fleet[2].typ == "C-27"
        assert fleet[3].typ == "C-27"
    
    def test_can_run_op(self, sim):
        """Test operational capability detection."""
        # Initially all spokes should be operational
        for i in range(sim.M):
            assert sim.can_run_op(i) is True
        
        # Make a spoke non-operational
        sim.stock[0] = [0, 1, 1, 1]  # No A resource
        assert sim.can_run_op(0) is False
        
        # Make it operational again
        sim.stock[0] = [1, 1, 1, 1]
        assert sim.can_run_op(0) is True
    
    def test_run_op(self, sim):
        """Test operation execution."""
        initial_c = sim.stock[0][2]
        initial_d = sim.stock[0][3]
        
        # Run an operation
        success = sim.run_op(0, 1)
        assert success is True
        assert sim.stock[0][2] == initial_c - 1
        assert sim.stock[0][3] == initial_d - 1
        assert sim.ops_by_spoke[0] == 1
        
        # Try to run operation on non-operational spoke
        sim.stock[0] = [0, 1, 1, 1]  # No A resource
        success = sim.run_op(0, 1)
        assert success is False


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_row_to_spoke(self):
        """Test row to spoke conversion."""
        row = [1.0, 2.0, 3.0, 4.0]
        spoke = _row_to_spoke(row)
        
        assert spoke.A == 1.0
        assert spoke.B == 2.0
        assert spoke.C == 3.0
        assert spoke.D == 4.0
    
    def test_is_ops_capable(self):
        """Test operational capability detection."""
        from types import SimpleNamespace
        
        # Operational spoke
        spoke = SimpleNamespace(A=1.0, B=1.0, C=1.0, D=1.0)
        assert is_ops_capable(spoke) is True
        
        # Non-operational spoke (missing A)
        spoke = SimpleNamespace(A=0.0, B=1.0, C=1.0, D=1.0)
        assert is_ops_capable(spoke) is False
        
        # Non-operational spoke (missing B)
        spoke = SimpleNamespace(A=1.0, B=0.0, C=1.0, D=1.0)
        assert is_ops_capable(spoke) is False
        
        # Non-operational spoke (missing C)
        spoke = SimpleNamespace(A=1.0, B=1.0, C=0.0, D=1.0)
        assert is_ops_capable(spoke) is False
        
        # Non-operational spoke (missing D)
        spoke = SimpleNamespace(A=1.0, B=1.0, C=1.0, D=0.0)
        assert is_ops_capable(spoke) is False
        
        # Edge case: very small values
        spoke = SimpleNamespace(A=1e-10, B=1e-10, C=1e-10, D=1e-10)
        assert is_ops_capable(spoke) is False
        
        # Edge case: exactly zero
        spoke = SimpleNamespace(A=0.0, B=0.0, C=0.0, D=0.0)
        assert is_ops_capable(spoke) is False


if __name__ == "__main__":
    pytest.main([__file__])
