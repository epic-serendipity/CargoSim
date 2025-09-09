"""Integration tests for Fleet Builder pallet integration with simulation."""

import pytest
from unittest.mock import patch, MagicMock

from cargosim.core.simulation import LogisticsSim
from cargosim.core.config import SimConfig
from cargosim.ui.fleet_builder import FleetBuilder, AircraftType


class TestFleetBuilderSimulationIntegration:
    """Test that simulation launch logic works with Fleet Builder pallet."""
    
    def test_simulation_uses_fleet_builder_pallet(self):
        """Test that simulation uses Fleet Builder pallet contents."""
        cfg = SimConfig()
        cfg.duration_minutes = 300  # Short simulation
        
        # Mock the fleet builder to return a specific fleet
        mock_fleet = {"C-130": 2, "C-27": 1}
        
        with patch('cargosim.ui.fleet_builder.get_fleet_builder') as mock_get_builder:
            mock_builder = MagicMock()
            mock_builder.get_current_fleet.return_value = mock_fleet
            mock_get_builder.return_value = mock_builder
            
            # Create simulation - should use the mocked fleet
            sim = LogisticsSim(cfg)
            
            # Verify that the fleet was built from the pallet
            assert len(sim.fleet) == 3  # 2 C-130 + 1 C-27
            assert any(ac.typ == "C-130" for ac in sim.fleet)
            assert any(ac.typ == "C-27" for ac in sim.fleet)
    
    def test_simulation_auto_adds_default_fleet_when_pallet_empty(self):
        """Test that simulation auto-adds default fleet when pallet is empty."""
        cfg = SimConfig()
        cfg.duration_minutes = 300
        
        # Mock empty fleet
        mock_fleet = {}
        
        with patch('cargosim.ui.fleet_builder.get_fleet_builder') as mock_get_builder:
            mock_builder = MagicMock()
            mock_builder.get_current_fleet.return_value = mock_fleet
            mock_builder.set_aircraft_count.return_value = None
            mock_get_builder.return_value = mock_builder
            
            # Create simulation - should auto-add default fleet
            sim = LogisticsSim(cfg)
            
            # Verify that set_aircraft_count was called to add default fleet
            mock_builder.set_aircraft_count.assert_called_with("C-130", 2)
    
    def test_simulation_validation_catches_empty_fleet(self):
        """Test that config validation catches empty Fleet Builder pallet."""
        cfg = SimConfig()
        
        # Mock empty fleet for validation
        with patch('cargosim.ui.fleet_builder.get_fleet_builder') as mock_get_builder:
            mock_builder = MagicMock()
            mock_builder.get_current_fleet.return_value = {}
            mock_get_builder.return_value = mock_builder
            
            # Import and run validation
            from cargosim.core.config import validate_config
            issues = validate_config(cfg)
            
            # Should have fleet validation issue
            assert any("Fleet Builder pallet is empty" in issue for issue in issues)
    
    def test_simulation_validation_passes_with_fleet(self):
        """Test that config validation passes when Fleet Builder pallet has aircraft."""
        cfg = SimConfig()
        
        # Mock fleet with aircraft
        mock_fleet = {"C-130": 2}
        
        with patch('cargosim.ui.fleet_builder.get_fleet_builder') as mock_get_builder:
            mock_builder = MagicMock()
            mock_builder.get_current_fleet.return_value = mock_fleet
            mock_get_builder.return_value = mock_builder
            
            # Import and run validation
            from cargosim.core.config import validate_config
            issues = validate_config(cfg)
            
            # Should not have fleet validation issues
            fleet_issues = [issue for issue in issues if "Fleet Builder pallet" in issue]
            assert len(fleet_issues) == 0


if __name__ == "__main__":
    pytest.main([__file__])
