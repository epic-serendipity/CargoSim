"""Tests for fleet persistence functionality."""

import unittest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from cargosim.ui.fleet_persistence import FleetPersistenceManager


class TestFleetPersistenceManager(unittest.TestCase):
    """Test cases for FleetPersistenceManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "configs" / "user"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.persistence_manager = FleetPersistenceManager(str(self.config_dir))
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """Test FleetPersistenceManager initialization."""
        self.assertEqual(self.persistence_manager.user_config_dir, self.config_dir)
        self.assertEqual(self.persistence_manager.last_fleet_file, self.config_dir / "last_fleet.json")
        self.assertEqual(self.persistence_manager.aircraft_config_file, self.config_dir / "aircraft_config.json")
    
    def test_save_last_fleet(self):
        """Test saving a fleet configuration."""
        fleet_data = {
            "name": "Test Fleet",
            "aircraft": {"C-130": 2, "C-17": 1},
            "total_aircraft": 3,
            "total_capacity": 27
        }
        
        result = self.persistence_manager.save_last_fleet(fleet_data)
        self.assertTrue(result)
        
        # Check that file was created
        self.assertTrue(self.persistence_manager.last_fleet_file.exists())
        
        # Check file contents
        with open(self.persistence_manager.last_fleet_file, 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data["fleet_name"], "Test Fleet")
        self.assertEqual(saved_data["aircraft"], {"C-130": 2, "C-17": 1})
        self.assertEqual(saved_data["total_aircraft"], 3)
        self.assertEqual(saved_data["total_capacity"], 27)
        self.assertIn("timestamp", saved_data)
    
    def test_load_last_fleet_success(self):
        """Test successfully loading a saved fleet."""
        # Create a test fleet file
        test_fleet_data = {
            "timestamp": "2024-01-01T00:00:00",
            "fleet_name": "Test Fleet",
            "aircraft": {"C-130": 2, "C-17": 1},
            "total_aircraft": 3,
            "total_capacity": 27
        }
        
        with open(self.persistence_manager.last_fleet_file, 'w') as f:
            json.dump(test_fleet_data, f)
        
        loaded_fleet = self.persistence_manager.load_last_fleet()
        self.assertIsNotNone(loaded_fleet)
        self.assertEqual(loaded_fleet["fleet_name"], "Test Fleet")
        self.assertEqual(loaded_fleet["aircraft"], {"C-130": 2, "C-17": 1})
    
    def test_load_last_fleet_not_found(self):
        """Test loading when no fleet file exists."""
        loaded_fleet = self.persistence_manager.load_last_fleet()
        self.assertIsNone(loaded_fleet)
    
    def test_load_last_fleet_invalid_data(self):
        """Test loading with invalid fleet data."""
        # Create an invalid fleet file
        invalid_fleet_data = {
            "timestamp": "2024-01-01T00:00:00"
            # Missing required fields
        }
        
        with open(self.persistence_manager.last_fleet_file, 'w') as f:
            json.dump(invalid_fleet_data, f)
        
        loaded_fleet = self.persistence_manager.load_last_fleet()
        self.assertIsNone(loaded_fleet)
    
    def test_get_default_fleet(self):
        """Test getting the default fleet configuration."""
        default_fleet = self.persistence_manager.get_default_fleet()
        
        self.assertEqual(default_fleet["name"], "Default Fleet")
        self.assertEqual(default_fleet["aircraft"], {"C-130": 2})
        self.assertEqual(default_fleet["total_aircraft"], 2)
        self.assertEqual(default_fleet["total_capacity"], 12)
        self.assertTrue(default_fleet["is_default"])
    
    def test_load_fleet_on_startup_with_last_fleet(self):
        """Test loading fleet on startup when last fleet exists."""
        # Create a test fleet file
        test_fleet_data = {
            "timestamp": "2024-01-01T00:00:00",
            "fleet_name": "Test Fleet",
            "aircraft": {"C-130": 3, "C-17": 1},
            "total_aircraft": 4,
            "total_capacity": 33
        }
        
        with open(self.persistence_manager.last_fleet_file, 'w') as f:
            json.dump(test_fleet_data, f)
        
        startup_fleet = self.persistence_manager.load_fleet_on_startup()
        self.assertEqual(startup_fleet["fleet_name"], "Test Fleet")
        self.assertEqual(startup_fleet["aircraft"], {"C-130": 3, "C-17": 1})
    
    def test_load_fleet_on_startup_no_last_fleet(self):
        """Test loading fleet on startup when no last fleet exists."""
        startup_fleet = self.persistence_manager.load_fleet_on_startup()
        self.assertEqual(startup_fleet["name"], "Default Fleet")
        self.assertEqual(startup_fleet["aircraft"], {"C-130": 2})
        self.assertTrue(startup_fleet["is_default"])
    
    def test_clear_last_fleet(self):
        """Test clearing the last fleet file."""
        # Create a test fleet file
        test_fleet_data = {"fleet_name": "Test Fleet", "aircraft": {"C-130": 2}}
        with open(self.persistence_manager.last_fleet_file, 'w') as f:
            json.dump(test_fleet_data, f)
        
        # Verify file exists
        self.assertTrue(self.persistence_manager.last_fleet_file.exists())
        
        # Clear the file
        result = self.persistence_manager.clear_last_fleet()
        self.assertTrue(result)
        
        # Verify file was removed
        self.assertFalse(self.persistence_manager.last_fleet_file.exists())
    
    def test_clear_last_fleet_not_exists(self):
        """Test clearing when no fleet file exists."""
        result = self.persistence_manager.clear_last_fleet()
        self.assertTrue(result)  # Should return True even if file doesn't exist
    
    def test_validate_fleet_data_valid(self):
        """Test validation of valid fleet data."""
        valid_fleet_data = {
            "fleet_name": "Test Fleet",
            "aircraft": {"C-130": 2}
        }
        
        # Use reflection to access private method
        result = self.persistence_manager._validate_fleet_data(valid_fleet_data)
        self.assertTrue(result)
    
    def test_validate_fleet_data_missing_key(self):
        """Test validation of fleet data with missing required key."""
        invalid_fleet_data = {
            "fleet_name": "Test Fleet"
            # Missing "aircraft" key
        }
        
        result = self.persistence_manager._validate_fleet_data(invalid_fleet_data)
        self.assertFalse(result)
    
    def test_validate_fleet_data_empty_aircraft(self):
        """Test validation of fleet data with empty aircraft."""
        invalid_fleet_data = {
            "fleet_name": "Test Fleet",
            "aircraft": {}
        }
        
        result = self.persistence_manager._validate_fleet_data(invalid_fleet_data)
        self.assertFalse(result)
    
    def test_validate_fleet_data_invalid_aircraft_type(self):
        """Test validation of fleet data with invalid aircraft type."""
        invalid_fleet_data = {
            "fleet_name": "Test Fleet",
            "aircraft": "not a dict"
        }
        
        result = self.persistence_manager._validate_fleet_data(invalid_fleet_data)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
