"""Aircraft configuration loader with priority-based loading system."""

import json
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AircraftConfigLoader:
    """Handles loading aircraft configuration with priority-based fallback system."""
    
    def __init__(self, default_config_dir: str = "configs/default", 
                 user_config_dir: str = "configs/user"):
        self.default_config_dir = Path(default_config_dir)
        self.user_config_dir = Path(user_config_dir)
        self.default_config_file = self.default_config_dir / "aircraft_config.json"
        self.user_config_file = self.user_config_dir / "aircraft_config.json"
    
    def load_aircraft_config(self) -> Dict[str, Any]:
        """Load aircraft configuration with priority system.
        
        Priority order:
        1. configs/user/aircraft_config.json (if exists)
        2. Clone configs/default/aircraft_config.json to configs/user/ if user config doesn't exist
        3. Fall back to default config if cloning fails
        
        Returns:
            Dict containing the aircraft configuration
        """
        try:
            # First, try to load from user config
            if self.user_config_file.exists():
                logger.info("Loading aircraft configuration from user config")
                return self._load_config_file(self.user_config_file)
            
            # User config doesn't exist, try to clone from default
            logger.info("User aircraft config not found, attempting to clone from default")
            if self._clone_default_config():
                # Now try to load the cloned user config
                if self.user_config_file.exists():
                    logger.info("Successfully cloned and loaded default aircraft config")
                    return self._load_config_file(self.user_config_file)
            
            # If cloning failed or user config still doesn't exist, load from default
            logger.info("Falling back to default aircraft configuration")
            return self._load_config_file(self.default_config_file)
            
        except Exception as e:
            logger.error(f"Failed to load aircraft configuration: {e}")
            # Return empty config as last resort
            return self._get_empty_config()
    
    def _clone_default_config(self) -> bool:
        """Clone the default aircraft config to the user directory.
        
        Returns:
            bool: True if cloning was successful, False otherwise
        """
        try:
            # Ensure the default config exists
            if not self.default_config_file.exists():
                logger.error(f"Default aircraft config not found: {self.default_config_file}")
                return False
            
            # Ensure user config directory exists
            self.user_config_dir.mkdir(parents=True, exist_ok=True)
            
            # Clone the file
            shutil.copy2(self.default_config_file, self.user_config_file)
            logger.info(f"Successfully cloned default config to: {self.user_config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clone default aircraft config: {e}")
            return False
    
    def _load_config_file(self, config_file: Path) -> Dict[str, Any]:
        """Load configuration from a specific file.
        
        Args:
            config_file: Path to the configuration file to load
            
        Returns:
            Dict containing the configuration data
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded aircraft configuration from: {config_file}")
        return data
    
    def _get_empty_config(self) -> Dict[str, Any]:
        """Get an empty aircraft configuration as a last resort.
        
        Returns:
            Dict containing minimal aircraft configuration
        """
        logger.warning("Using empty aircraft configuration as last resort")
        return {
            "config_version": 1,
            "aircraft_types": {},
            "fleet_presets": {}
        }
    
    def ensure_user_config_exists(self) -> bool:
        """Ensure that a user aircraft config file exists.
        
        This method will clone the default config if the user config doesn't exist.
        
        Returns:
            bool: True if user config exists or was successfully created, False otherwise
        """
        if self.user_config_file.exists():
            logger.info("User aircraft config already exists")
            return True
        
        logger.info("User aircraft config does not exist, creating from default")
        return self._clone_default_config()
    
    def get_config_source_info(self) -> Dict[str, Any]:
        """Get information about the current configuration source.
        
        Returns:
            Dict containing information about the configuration source
        """
        info = {
            "user_config_exists": self.user_config_file.exists(),
            "default_config_exists": self.default_config_file.exists(),
            "user_config_path": str(self.user_config_file),
            "default_config_path": str(self.default_config_file)
        }
        
        if self.user_config_file.exists():
            info["source"] = "user"
            info["source_file"] = str(self.user_config_file)
        elif self.default_config_file.exists():
            info["source"] = "default"
            info["source_file"] = str(self.default_config_file)
        else:
            info["source"] = "none"
            info["source_file"] = None
        
        return info
    
    def reload_config(self) -> Dict[str, Any]:
        """Force reload the configuration from disk.
        
        This is useful when the configuration files may have changed.
        
        Returns:
            Dict containing the reloaded configuration
        """
        logger.info("Reloading aircraft configuration")
        return self.load_aircraft_config()


# Global instance for easy access
_aircraft_config_loader = None

def get_aircraft_config_loader() -> AircraftConfigLoader:
    """Get the global aircraft config loader instance.
    
    Returns:
        AircraftConfigLoader instance
    """
    global _aircraft_config_loader
    if _aircraft_config_loader is None:
        _aircraft_config_loader = AircraftConfigLoader()
    return _aircraft_config_loader

def load_aircraft_config() -> Dict[str, Any]:
    """Load aircraft configuration using the global loader.
    
    Returns:
        Dict containing the aircraft configuration
    """
    return get_aircraft_config_loader().load_aircraft_config()
