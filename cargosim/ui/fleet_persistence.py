"""Fleet persistence and loading utilities for CargoSim."""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class FleetPersistenceManager:
    """Manages persistence and loading of fleet configurations."""
    
    def __init__(self, user_config_dir: str = "configs/user"):
        self.user_config_dir = Path(user_config_dir)
        self.last_fleet_file = self.user_config_dir / "last_fleet.json"
        self.aircraft_config_file = self.user_config_dir / "aircraft_config.json"
        
    def save_last_fleet(self, fleet_composition: Dict[str, Any], spoke_config: Optional[Dict[str, Any]] = None) -> bool:
        """Save the current fleet composition and spoke configuration for future loading.
        
        Args:
            fleet_composition: Dictionary containing fleet information
            spoke_config: Optional spoke configuration to save
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Ensure the user config directory exists
            self.user_config_dir.mkdir(parents=True, exist_ok=True)
            
            # Prepare the fleet data for saving
            fleet_data = {
                "timestamp": self._get_timestamp(),
                "name": fleet_composition.get("name", "Last Used Fleet"),
                "aircraft": fleet_composition.get("aircraft", {}),
                "total_aircraft": fleet_composition.get("total_aircraft", 0),
                "total_capacity": fleet_composition.get("total_capacity", 0)
            }
            
            # Add spoke configuration if provided
            if spoke_config:
                fleet_data["spoke_config"] = spoke_config
            
            # Save to last_fleet.json
            with open(self.last_fleet_file, 'w', encoding='utf-8') as f:
                json.dump(fleet_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Last fleet and configuration saved successfully: {fleet_data['name']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save last fleet: {e}")
            return False
    
    def load_last_fleet(self) -> Optional[Dict[str, Any]]:
        """Load the last-used fleet configuration.
        
        Returns:
            Dict containing fleet information, or None if not found/invalid
        """
        try:
            if not self.last_fleet_file.exists():
                logger.info("No last fleet file found, will use default")
                return None
            
            with open(self.last_fleet_file, 'r', encoding='utf-8') as f:
                fleet_data = json.load(f)
            
            # Validate the loaded data
            if not self._validate_fleet_data(fleet_data):
                logger.warning("Last fleet file is invalid, will use default")
                return None
            
            logger.info(f"Last fleet loaded successfully: {fleet_data.get('name', 'Unknown')}")
            return fleet_data
            
        except Exception as e:
            logger.error(f"Failed to load last fleet: {e}")
            return None
    
    def get_default_fleet(self) -> Dict[str, Any]:
        """Get the default fleet configuration (2 C-130s).
        
        Returns:
            Dict containing default fleet information
        """
        return {
            "name": "Default Fleet",
            "aircraft": {"C-130": 2},
            "total_aircraft": 2,
            "total_capacity": 12,  # 2 * 6 (C-130 base capacity)
            "is_default": True
        }
    
    def load_fleet_on_startup(self) -> Dict[str, Any]:
        """Load the appropriate fleet configuration on startup.
        
        Priority:
        1. Last used fleet (if exists and valid)
        2. Default fleet (2 C-130s)
        
        Returns:
            Dict containing fleet information to load
        """
        # Try to load the last used fleet
        last_fleet = self.load_last_fleet()
        
        if last_fleet and last_fleet.get("aircraft"):
            logger.info("Loading last used fleet on startup")
            return last_fleet
        
        # Fall back to default fleet
        logger.info("No last fleet found, using default fleet (2 C-130s)")
        return self.get_default_fleet()
    
    def _validate_fleet_data(self, fleet_data: Dict[str, Any]) -> bool:
        """Validate that the loaded fleet data has the required structure.
        
        Args:
            fleet_data: Dictionary to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_keys = ["name", "aircraft"]
        
        for key in required_keys:
            if key not in fleet_data:
                logger.warning(f"Missing required key '{key}' in fleet data")
                return False
        
        # Check that aircraft is a dictionary and has content
        if not isinstance(fleet_data["aircraft"], dict):
            logger.warning("Aircraft data is not a dictionary")
            return False
        
        if not fleet_data["aircraft"]:
            logger.warning("Aircraft data is empty")
            return False
        
        return True
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as a string.
        
        Returns:
            String representation of current timestamp
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def clear_last_fleet(self) -> bool:
        """Clear the last fleet file.
        
        Returns:
            bool: True if cleared successfully, False otherwise
        """
        try:
            if self.last_fleet_file.exists():
                self.last_fleet_file.unlink()
                logger.info("Last fleet file cleared successfully")
                return True
            return True  # File didn't exist, so it's already "cleared"
        except Exception as e:
            logger.error(f"Failed to clear last fleet file: {e}")
            return False
