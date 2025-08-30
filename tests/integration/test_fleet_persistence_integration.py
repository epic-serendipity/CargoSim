"""Integration tests for fleet persistence with GUI components."""

import unittest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the modules we want to test
from cargosim.ui.fleet_persistence import FleetPersistenceManager


class TestFleetPersistenceIntegration(unittest.TestCase):
    """Integration tests for fleet persistence with GUI components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "configs" / "user"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a mock aircraft config file
        self.aircraft_config = {
            "config_version": 2,
            "aircraft_types": {
                "C-130": {
                    "name": "C-130 Hercules",
                    "base_capacity": 6,
                    "default_count": 2
                },
                "C-17": {
                    "name": "C-17 Globemaster III",
                    "base_capacity": 15,
                    "default_count": 0
                }
            }
        }
        
        with open(self.config_dir / "aircraft_config.json", 'w') as f:
            json.dump(self.aircraft_config, f)
        
        self.persistence_manager = FleetPersistenceManager(str(self.config_dir))
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_fleet_persistence_workflow(self):
        """Test the complete fleet persistence workflow."""
        # 1. Simulate creating a fleet in the GUI
        test_fleet = {
            "name": "Test Integration Fleet",
            "aircraft": {"C-130": 3, "C-17": 1},
            "total_aircraft": 4,
            "total_capacity": 33
        }
        
        # 2. Save the fleet (simulating what happens when simulation starts)
        save_result = self.persistence_manager.save_last_fleet(test_fleet)
        self.assertTrue(save_result)
        
        # 3. Verify the file was created with correct content
        self.assertTrue(self.persistence_manager.last_fleet_file.exists())
        
        with open(self.persistence_manager.last_fleet_file, 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data["fleet_name"], "Test Integration Fleet")
        self.assertEqual(saved_data["aircraft"], {"C-130": 3, "C-17": 1})
        
        # 4. Simulate application restart - load the saved fleet
        loaded_fleet = self.persistence_manager.load_fleet_on_startup()
        self.assertEqual(loaded_fleet["fleet_name"], "Test Integration Fleet")
        self.assertEqual(loaded_fleet["aircraft"], {"C-130": 3, "C-17": 1})
    
    def test_default_fleet_fallback(self):
        """Test that default fleet is used when no saved fleet exists."""
        # Ensure no saved fleet exists
        if self.persistence_manager.last_fleet_file.exists():
            self.persistence_manager.last_fleet_file.unlink()
        
        # Load fleet on startup - should get default
        startup_fleet = self.persistence_manager.load_fleet_on_startup()
        self.assertEqual(startup_fleet["name"], "Default Fleet")
        self.assertEqual(startup_fleet["aircraft"], {"C-130": 2})
        self.assertTrue(startup_fleet["is_default"])
    
    def test_fleet_persistence_with_empty_fleet(self):
        """Test handling of empty fleet configurations."""
        empty_fleet = {
            "name": "Empty Fleet",
            "aircraft": {},
            "total_aircraft": 0,
            "total_capacity": 0
        }
        
        # Should not save empty fleets
        save_result = self.persistence_manager.save_last_fleet(empty_fleet)
        self.assertTrue(save_result)  # Still saves, but validates on load
        
        # When loading, should fall back to default
        loaded_fleet = self.persistence_manager.load_last_fleet()
        self.assertIsNone(loaded_fleet)  # Empty fleet is invalid
        
        # Startup should use default
        startup_fleet = self.persistence_manager.load_fleet_on_startup()
        self.assertEqual(startup_fleet["name"], "Default Fleet")
    
    def test_fleet_persistence_error_handling(self):
        """Test error handling in fleet persistence."""
        # Test with corrupted fleet file
        corrupted_data = "This is not valid JSON"
        
        with open(self.persistence_manager.last_fleet_file, 'w') as f:
            f.write(corrupted_data)
        
        # Should handle corruption gracefully
        loaded_fleet = self.persistence_manager.load_last_fleet()
        self.assertIsNone(loaded_fleet)
        
        # Startup should still work with default
        startup_fleet = self.persistence_manager.load_fleet_on_startup()
        self.assertEqual(startup_fleet["name"], "Default Fleet")
    
    def test_fleet_persistence_file_permissions(self):
        """Test fleet persistence with different file permission scenarios."""
        # Test with read-only directory (simulate permission issues)
        if os.name == 'nt':  # Windows
            # On Windows, we can't easily make a directory read-only
            # Just test that the system handles errors gracefully
            pass
        else:
            # On Unix-like systems, test read-only directory
            import stat
            os.chmod(self.config_dir, stat.S_IREAD | stat.S_IEXEC)
            
            try:
                # Should handle permission errors gracefully
                test_fleet = {"name": "Test", "aircraft": {"C-130": 2}}
                save_result = self.persistence_manager.save_last_fleet(test_fleet)
                # Should fail gracefully
                self.assertFalse(save_result)
            finally:
                # Restore permissions
                os.chmod(self.config_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    
    def test_fleet_persistence_concurrent_access(self):
        """Test fleet persistence with concurrent access scenarios."""
        import threading
        import time
        
        results = []
        errors = []
        
        def save_fleet(thread_id):
            """Save a fleet from a specific thread."""
            try:
                fleet_data = {
                    "name": f"Thread {thread_id} Fleet",
                    "aircraft": {"C-130": thread_id},
                    "total_aircraft": thread_id,
                    "total_capacity": thread_id * 6
                }
                result = self.persistence_manager.save_last_fleet(fleet_data)
                results.append((thread_id, result))
            except Exception as e:
                errors.append((thread_id, e))
        
        # Create multiple threads to save fleets concurrently
        threads = []
        for i in range(3):
            thread = threading.Thread(target=save_fleet, args=(i + 1,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that all saves completed (though only one will be the final result)
        self.assertEqual(len(results), 3)
        self.assertEqual(len(errors), 0)
        
        # Verify that a fleet file exists (last one written)
        self.assertTrue(self.persistence_manager.last_fleet_file.exists())


if __name__ == "__main__":
    unittest.main()
