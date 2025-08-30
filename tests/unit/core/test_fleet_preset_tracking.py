"""Test fleet preset tracking functionality."""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
import json

from cargosim.core.config import SimConfig, load_config, save_config
from cargosim.ui.fleet_builder import FleetBuilder, FleetComposition, FleetPreset
from cargosim.ui.fleet_builder import AircraftConfigManager


class TestFleetPresetTracking(unittest.TestCase):
    """Test the fleet preset tracking functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test configs
        self.temp_dir = tempfile.mkdtemp()
        self.original_config_file = None
        
        # Mock the config file path
        with patch('cargosim.core.paths.USER_MAIN_CONFIG_FILE') as mock_path:
            mock_path.__str__ = lambda: os.path.join(self.temp_dir, 'test_config.json')
            mock_path.exists = lambda: False
            
            # Create a test config
            self.config = SimConfig()
            self.config.last_fleet_preset_used = None
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_serialization_includes_last_fleet_preset(self):
        """Test that last_fleet_preset_used is included in config serialization."""
        # Set a value
        self.config.last_fleet_preset_used = "Test Fleet"
        
        # Serialize to JSON
        config_dict = self.config.to_json()
        
        # Verify the field is included
        self.assertIn("last_fleet_preset_used", config_dict)
        self.assertEqual(config_dict["last_fleet_preset_used"], "Test Fleet")
    
    def test_config_deserialization_loads_last_fleet_preset(self):
        """Test that last_fleet_preset_used is loaded from config deserialization."""
        # Create a config dictionary
        config_dict = {
            "config_version": 9,
            "last_fleet_preset_used": "Loaded Fleet"
        }
        
        # Deserialize
        config = SimConfig.from_json(config_dict)
        
        # Verify the field is loaded
        self.assertEqual(config.last_fleet_preset_used, "Loaded Fleet")
    
    def test_fleet_builder_tracks_preset_usage(self):
        """Test that FleetBuilder tracks when a preset is loaded."""
        # Create a mock config manager
        mock_config_manager = MagicMock(spec=AircraftConfigManager)
        
        # Mock the aircraft_types attribute
        mock_config_manager.aircraft_types = {"C-130": MagicMock(), "C-27": MagicMock()}
        
        # Create a test preset
        test_preset = FleetPreset(
            name="Test Fleet",
            description="Test description",
            aircraft={"C-130": 2, "C-27": 1}
        )
        
        # Mock the get_fleet_preset method
        mock_config_manager.get_fleet_preset.return_value = test_preset
        
        # Mock the get_all_fleet_presets method to return the test preset
        mock_config_manager.get_all_fleet_presets.return_value = [test_preset]
        
        # Mock the config loading and saving
        with patch('cargosim.core.config.load_config') as mock_load, \
             patch('cargosim.core.config.save_config') as mock_save:
            
            # Mock the config
            mock_config = MagicMock()
            mock_config.last_fleet_preset_used = None
            mock_load.return_value = mock_config
            
            # Create FleetBuilder instance (after mocking config)
            fleet_builder = FleetBuilder(mock_config_manager)
            
            # Load a preset
            result = fleet_builder.create_fleet_from_preset("Test Fleet")
            
            # Verify the preset was loaded
            self.assertIsNotNone(result)
            self.assertEqual(result.name, "Test Fleet")
            self.assertEqual(result.aircraft, {"C-130": 2, "C-27": 1})
            
            # Verify the config was updated
            mock_save.assert_called_once()
            self.assertEqual(mock_config.last_fleet_preset_used, "Test Fleet")
    
    def test_fleet_builder_loads_last_used_preset_on_init(self):
        """Test that FleetBuilder loads the last used preset on initialization."""
        # Create a mock config manager
        mock_config_manager = MagicMock(spec=AircraftConfigManager)
        
        # Mock the aircraft_types attribute
        mock_config_manager.aircraft_types = {"C-130": MagicMock()}
        
        # Create a test preset
        test_preset = FleetPreset(
            name="Last Used Fleet",
            description="Last used description",
            aircraft={"C-130": 3}
        )
        
        # Mock the get_fleet_preset method
        mock_config_manager.get_fleet_preset.return_value = test_preset
        
        # Mock the get_all_fleet_presets method to return the test preset
        mock_config_manager.get_all_fleet_presets.return_value = [test_preset]
        
        # Mock the config loading
        with patch('cargosim.core.config.load_config') as mock_load:
            # Mock the config
            mock_config = MagicMock()
            mock_config.last_fleet_preset_used = "Last Used Fleet"
            mock_load.return_value = mock_config
            
            # Create FleetBuilder instance (this should trigger _load_default_fleet)
            fleet_builder = FleetBuilder(mock_config_manager)
            
            # Verify the last used preset was loaded
            self.assertEqual(fleet_builder.current_fleet.name, "Last Used Fleet")
            self.assertEqual(fleet_builder.current_fleet.aircraft, {"C-130": 3})
    
    def test_fleet_builder_falls_back_to_default_when_last_preset_missing(self):
        """Test that FleetBuilder falls back to default when last preset is missing."""
        # Create a mock config manager
        mock_config_manager = MagicMock(spec=AircraftConfigManager)
        
        # Mock the get_fleet_preset method to return None (preset not found)
        mock_config_manager.get_fleet_preset.return_value = None
        
        # Mock aircraft types
        mock_config_manager.aircraft_types = {"C-130": MagicMock()}
        
        # Mock the config loading
        with patch('cargosim.core.config.load_config') as mock_load, \
             patch('cargosim.core.config.save_config') as mock_save:
            
            # Mock the config
            mock_config = MagicMock()
            mock_config.last_fleet_preset_used = "Missing Fleet"
            mock_load.return_value = mock_config
            
            # Create FleetBuilder instance
            fleet_builder = FleetBuilder(mock_config_manager)
            
            # Verify the default fleet was loaded (2 C-130s)
            self.assertEqual(fleet_builder.current_fleet.name, "Default Fleet")
            self.assertEqual(fleet_builder.current_fleet.aircraft, {"C-130": 2})
            
            # Verify the invalid reference was cleared
            mock_save.assert_called_once()
            self.assertIsNone(mock_config.last_fleet_preset_used)
    
    def test_fleet_builder_clears_invalid_last_preset_reference(self):
        """Test that FleetBuilder clears invalid last preset references."""
        # Create a mock config manager
        mock_config_manager = MagicMock(spec=AircraftConfigManager)
        
        # Mock the get_fleet_preset method to return None (preset not found)
        mock_config_manager.get_fleet_preset.return_value = None
        
        # Mock aircraft types
        mock_config_manager.aircraft_types = {"C-130": MagicMock()}
        
        # Mock the config loading
        with patch('cargosim.core.config.load_config') as mock_load, \
             patch('cargosim.core.config.save_config') as mock_save:
            
            # Mock the config
            mock_config = MagicMock()
            mock_config.last_fleet_preset_used = "Invalid Fleet"
            mock_load.return_value = mock_config
            
            # Create FleetBuilder instance
            fleet_builder = FleetBuilder(mock_config_manager)
            
            # Verify the invalid reference was cleared
            mock_save.assert_called_once()
            self.assertIsNone(mock_config.last_fleet_preset_used)


if __name__ == '__main__':
    unittest.main()
