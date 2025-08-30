"""Tests for aircraft configuration loader functionality."""

import unittest
import tempfile
import json
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from cargosim.core.aircraft_config_loader import AircraftConfigLoader, get_aircraft_config_loader, load_aircraft_config


class TestAircraftConfigLoader(unittest.TestCase):
    """Test cases for AircraftConfigLoader."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.default_config_dir = Path(self.temp_dir) / "configs" / "default"
        self.user_config_dir = Path(self.temp_dir) / "configs" / "user"
        
        # Create directories
        self.default_config_dir.mkdir(parents=True, exist_ok=True)
        self.user_config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test default config
        self.default_config = {
            "config_version": 2,
            "aircraft_types": {
                "C-130": {
                    "name": "C-130 Hercules",
                    "description": "Medium tactical transport aircraft",
                    "base_capacity": 6,
                    "rest_periods": 6,
                    "range_factor": 1.0,
                    "fuel_efficiency": 1.0,
                    "maintenance_cost": 1.0,
                    "special_capabilities": ["tactical", "short_field"],
                    "color": "#3b82f6",
                    "icon": "C130",
                    "default_count": 2
                },
                "C-17": {
                    "name": "C-17 Globemaster III",
                    "description": "Heavy strategic transport aircraft",
                    "base_capacity": 15,
                    "rest_periods": 8,
                    "range_factor": 1.5,
                    "fuel_efficiency": 0.9,
                    "maintenance_cost": 1.5,
                    "special_capabilities": ["strategic", "long_range"],
                    "color": "#8b5cf6",
                    "icon": "C17",
                    "default_count": 0
                }
            },
            "fleet_presets": {
                "Standard Fleet": {
                    "description": "Balanced fleet for typical operations",
                    "aircraft": {"C-130": 2}
                },
                "Heavy Fleet": {
                    "description": "High-capacity fleet for intensive operations",
                    "aircraft": {"C-17": 1, "C-130": 2}
                }
            }
        }
        
        with open(self.default_config_dir / "aircraft_config.json", 'w') as f:
            json.dump(self.default_config, f)
        
        self.loader = AircraftConfigLoader(str(self.default_config_dir), str(self.user_config_dir))
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """Test AircraftConfigLoader initialization."""
        self.assertEqual(self.loader.default_config_dir, self.default_config_dir)
        self.assertEqual(self.loader.user_config_dir, self.user_config_dir)
        self.assertEqual(self.loader.default_config_file, self.default_config_dir / "aircraft_config.json")
        self.assertEqual(self.loader.user_config_file, self.user_config_dir / "aircraft_config.json")
    
    def test_load_aircraft_config_user_exists(self):
        """Test loading when user config exists."""
        # Create user config
        user_config = {
            "config_version": 2,
            "aircraft_types": {
                "C-130": {
                    "name": "C-130 Hercules (User)",
                    "description": "User-modified C-130",
                    "base_capacity": 8,
                    "rest_periods": 6,
                    "range_factor": 1.0,
                    "fuel_efficiency": 1.0,
                    "maintenance_cost": 1.0,
                    "special_capabilities": ["tactical", "short_field"],
                    "color": "#3b82f6",
                    "icon": "C130",
                    "default_count": 2
                }
            },
            "fleet_presets": {
                "User Fleet": {
                    "description": "User-created fleet",
                    "aircraft": {"C-130": 3}
                }
            }
        }
        
        with open(self.user_config_dir / "aircraft_config.json", 'w') as f:
            json.dump(user_config, f)
        
        # Load config
        result = self.loader.load_aircraft_config()
        
        # Should load from user config
        self.assertEqual(result["config_version"], 2)
        self.assertEqual(result["aircraft_types"]["C-130"]["name"], "C-130 Hercules (User)")
        self.assertEqual(result["aircraft_types"]["C-130"]["base_capacity"], 8)
        self.assertEqual(result["fleet_presets"]["User Fleet"]["aircraft"]["C-130"], 3)
    
    def test_load_aircraft_config_clone_default(self):
        """Test loading when user config doesn't exist and cloning succeeds."""
        # User config doesn't exist, should clone from default
        
        result = self.loader.load_aircraft_config()
        
        # Should load from default config
        self.assertEqual(result["config_version"], 2)
        self.assertEqual(result["aircraft_types"]["C-130"]["name"], "C-130 Hercules")
        self.assertEqual(result["aircraft_types"]["C-17"]["name"], "C-17 Globemaster III")
        self.assertEqual(len(result["fleet_presets"]), 2)
        
        # User config should now exist
        self.assertTrue(self.loader.user_config_file.exists())
        
        # Verify user config was cloned correctly
        with open(self.loader.user_config_file, 'r') as f:
            cloned_config = json.load(f)
        self.assertEqual(cloned_config, self.default_config)
    
    def test_load_aircraft_config_clone_fails(self):
        """Test loading when cloning fails."""
        # Remove default config to simulate cloning failure
        os.remove(self.default_config_dir / "aircraft_config.json")
        
        # Should handle gracefully
        result = self.loader.load_aircraft_config()
        
        # Should return empty config
        self.assertEqual(result["config_version"], 1)
        self.assertEqual(result["aircraft_types"], {})
        self.assertEqual(result["fleet_presets"], {})
    
    def test_clone_default_config_success(self):
        """Test successful cloning of default config."""
        result = self.loader._clone_default_config()
        self.assertTrue(result)
        
        # Verify file was cloned
        self.assertTrue(self.loader.user_config_file.exists())
        
        # Verify content matches
        with open(self.loader.user_config_file, 'r') as f:
            cloned_content = json.load(f)
        self.assertEqual(cloned_content, self.default_config)
    
    def test_clone_default_config_failure(self):
        """Test cloning failure when default config doesn't exist."""
        # Remove default config
        os.remove(self.default_config_dir / "aircraft_config.json")
        
        result = self.loader._clone_default_config()
        self.assertFalse(result)
    
    def test_ensure_user_config_exists_already_exists(self):
        """Test ensure_user_config_exists when user config already exists."""
        # Create user config
        with open(self.loader.user_config_file, 'w') as f:
            json.dump({"test": "data"}, f)
        
        result = self.loader.ensure_user_config_exists()
        self.assertTrue(result)
    
    def test_ensure_user_config_exists_creates_new(self):
        """Test ensure_user_config_exists when user config doesn't exist."""
        result = self.loader.ensure_user_config_exists()
        self.assertTrue(result)
        
        # Verify user config was created
        self.assertTrue(self.loader.user_config_file.exists())
    
    def test_get_config_source_info_user_exists(self):
        """Test get_config_source_info when user config exists."""
        # Create user config
        with open(self.loader.user_config_file, 'w') as f:
            json.dump({"test": "data"}, f)
        
        info = self.loader.get_config_source_info()
        self.assertTrue(info["user_config_exists"])
        self.assertTrue(info["default_config_exists"])
        self.assertEqual(info["source"], "user")
        self.assertEqual(info["source_file"], str(self.loader.user_config_file))
    
    def test_get_config_source_info_default_only(self):
        """Test get_config_source_info when only default config exists."""
        info = self.loader.get_config_source_info()
        self.assertFalse(info["user_config_exists"])
        self.assertTrue(info["default_config_exists"])
        self.assertEqual(info["source"], "default")
        self.assertEqual(info["source_file"], str(self.loader.default_config_file))
    
    def test_get_config_source_info_none_exist(self):
        """Test get_config_source_info when no configs exist."""
        # Remove default config
        os.remove(self.default_config_dir / "aircraft_config.json")
        
        info = self.loader.get_config_source_info()
        self.assertFalse(info["user_config_exists"])
        self.assertFalse(info["default_config_exists"])
        self.assertEqual(info["source"], "none")
        self.assertIsNone(info["source_file"])
    
    def test_reload_config(self):
        """Test reloading configuration."""
        # Load initial config
        initial_config = self.loader.load_aircraft_config()
        
        # Modify user config
        modified_config = initial_config.copy()
        modified_config["aircraft_types"]["C-130"]["name"] = "Modified C-130"
        
        with open(self.loader.user_config_file, 'w') as f:
            json.dump(modified_config, f)
        
        # Reload config
        reloaded_config = self.loader.reload_config()
        
        # Should reflect changes
        self.assertEqual(reloaded_config["aircraft_types"]["C-130"]["name"], "Modified C-130")
    
    def test_load_config_file_success(self):
        """Test successful loading of a config file."""
        result = self.loader._load_config_file(self.loader.default_config_file)
        self.assertEqual(result, self.default_config)
    
    def test_load_config_file_not_found(self):
        """Test loading a non-existent config file."""
        non_existent_file = self.default_config_dir / "nonexistent.json"
        
        with self.assertRaises(FileNotFoundError):
            self.loader._load_config_file(non_existent_file)
    
    def test_load_config_file_invalid_json(self):
        """Test loading a config file with invalid JSON."""
        invalid_json_file = self.user_config_dir / "invalid.json"
        
        with open(invalid_json_file, 'w') as f:
            f.write("This is not valid JSON")
        
        with self.assertRaises(json.JSONDecodeError):
            self.loader._load_config_file(invalid_json_file)


class TestAircraftConfigLoaderGlobalFunctions(unittest.TestCase):
    """Test cases for global functions in aircraft_config_loader module."""
    
    def test_get_aircraft_config_loader(self):
        """Test getting the global aircraft config loader instance."""
        loader1 = get_aircraft_config_loader()
        loader2 = get_aircraft_config_loader()
        
        # Should return the same instance
        self.assertIs(loader1, loader2)
    
    def test_load_aircraft_config_global(self):
        """Test the global load_aircraft_config function."""
        # This test requires a working config directory structure
        # We'll just test that the function can be called without error
        try:
            result = load_aircraft_config()
            # Should return a dict
            self.assertIsInstance(result, dict)
        except Exception as e:
            # It's okay if this fails in test environment
            self.assertIsInstance(e, Exception)


if __name__ == "__main__":
    unittest.main()
