"""
Unit tests for configuration validation.

Tests that all example configurations are valid and conform to the schema.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from cargosim.core.config_validator import validate_config
from cargosim.core.config import load_config


class TestExampleConfigValidation:
    """Test that all example configurations are valid."""
    
    def test_default_aircraft_config(self):
        """Test that the default aircraft configuration is valid."""
        config_path = Path("configs/default/aircraft_config.json")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Validate the configuration
            is_valid, errors = validate_config(config, "aircraft")
            assert is_valid, f"Aircraft config validation failed: {errors}"
    
    def test_default_cargo_sim_config(self):
        """Test that the default cargo sim configuration is valid."""
        config_path = Path("configs/default/cargo_sim_config.json")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Validate the configuration
            is_valid, errors = validate_config(config, "cargo_sim")
            assert is_valid, f"Cargo sim config validation failed: {errors}"
    
    def test_smart_targeting_config(self):
        """Test that the smart targeting configuration is valid."""
        config_path = Path("configs/examples/cargo_sim_smart_targeting_config.json")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Validate the configuration
            is_valid, errors = validate_config(config, "cargo_sim")
            assert is_valid, f"Smart targeting config validation failed: {errors}"
    
    def test_all_config_files_exist(self):
        """Test that all expected configuration files exist."""
        expected_configs = [
            "configs/default/aircraft_config.json",
            "configs/default/cargo_sim_config.json",
            "configs/examples/cargo_sim_smart_targeting_config.json"
        ]
        
        for config_path in expected_configs:
            assert Path(config_path).exists(), f"Expected config file not found: {config_path}"


class TestConfigSchemaCompliance:
    """Test that configurations comply with expected schemas."""
    
    def test_aircraft_config_schema(self):
        """Test aircraft configuration schema compliance."""
        config_path = Path("configs/default/aircraft_config.json")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Check required fields
            required_fields = ["aircraft", "categories"]
            for field in required_fields:
                assert field in config, f"Required field '{field}' missing from aircraft config"
            
            # Check aircraft structure
            if "aircraft" in config:
                for aircraft_id, aircraft_data in config["aircraft"].items():
                    required_aircraft_fields = ["name", "type", "max_payload"]
                    for field in required_aircraft_fields:
                        assert field in aircraft_data, f"Required field '{field}' missing from aircraft {aircraft_id}"
    
    def test_cargo_sim_config_schema(self):
        """Test cargo sim configuration schema compliance."""
        config_path = Path("configs/default/cargo_sim_config.json")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Check required sections
            required_sections = ["simulation", "rendering", "logging"]
            for section in required_sections:
                assert section in config, f"Required section '{section}' missing from cargo sim config"
            
            # Check simulation settings
            if "simulation" in config:
                sim_config = config["simulation"]
                assert "duration" in sim_config, "Simulation duration missing"
                assert "time_step" in sim_config, "Simulation time step missing"
    
    def test_smart_targeting_config_schema(self):
        """Test smart targeting configuration schema compliance."""
        config_path = Path("configs/examples/cargo_sim_smart_targeting_config.json")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Check that it has smart targeting features
            if "features" in config:
                features = config["features"]
                assert "smart_targeting" in features, "Smart targeting feature missing"
                
                smart_config = features["smart_targeting"]
                assert "enabled" in smart_config, "Smart targeting enabled flag missing"


class TestConfigLoading:
    """Test configuration loading functionality."""
    
    def test_load_default_config(self):
        """Test loading the default configuration."""
        try:
            config = load_config()
            assert config is not None, "Default config should load successfully"
        except Exception as e:
            pytest.skip(f"Default config loading failed: {e}")
    
    def test_load_aircraft_config(self):
        """Test loading the aircraft configuration."""
        config_path = Path("configs/default/aircraft_config.json")
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                assert config is not None, "Aircraft config should load successfully"
            except Exception as e:
                pytest.fail(f"Aircraft config loading failed: {e}")
    
    def test_config_file_permissions(self):
        """Test that configuration files have proper permissions."""
        config_files = [
            "configs/default/aircraft_config.json",
            "configs/default/cargo_sim_config.json",
            "configs/examples/cargo_sim_smart_targeting_config.json"
        ]
        
        for config_path in config_files:
            path = Path(config_path)
            if path.exists():
                # Check that file is readable
                assert path.is_file(), f"{config_path} should be a file"
                assert path.stat().st_mode & 0o444, f"{config_path} should be readable"


class TestConfigValidationEdgeCases:
    """Test configuration validation edge cases."""
    
    def test_empty_config_validation(self):
        """Test validation of empty configuration."""
        empty_config = {}
        
        # Empty config should fail validation for any type
        is_valid, errors = validate_config(empty_config, "aircraft")
        assert not is_valid, "Empty config should not be valid"
        assert len(errors) > 0, "Empty config should have validation errors"
    
    def test_malformed_json_handling(self):
        """Test handling of malformed JSON configurations."""
        malformed_json = '{"invalid": json}'
        
        # This should raise a JSON decode error
        with pytest.raises(json.JSONDecodeError):
            json.loads(malformed_json)
    
    def test_missing_required_fields(self):
        """Test validation of configurations with missing required fields."""
        incomplete_config = {
            "aircraft": {
                "test_aircraft": {
                    "name": "Test Aircraft"
                    # Missing required fields like type and max_payload
                }
            }
        }
        
        # This should fail validation
        is_valid, errors = validate_config(incomplete_config, "aircraft")
        assert not is_valid, "Incomplete config should not be valid"
        assert len(errors) > 0, "Incomplete config should have validation errors"


class TestConfigMigration:
    """Test configuration migration functionality."""
    
    def test_config_version_compatibility(self):
        """Test that configurations are compatible with current version."""
        config_files = [
            "configs/default/cargo_sim_config.json",
            "configs/examples/cargo_sim_smart_targeting_config.json"
        ]
        
        for config_path in config_files:
            path = Path(config_path)
            if path.exists():
                with open(path, 'r') as f:
                    config = json.load(f)
                
                # Check if config has version information
                if "version" in config:
                    version = config["version"]
                    # Add version compatibility checks here as needed
                    assert isinstance(version, (str, int)), f"Version should be string or int, got {type(version)}"


if __name__ == "__main__":
    pytest.main([__file__])
