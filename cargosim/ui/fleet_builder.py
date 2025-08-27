"""Fleet Builder module for CargoSim - manages aircraft configurations and fleet composition."""

import json
import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class AircraftType:
    """Represents an aircraft type with all its properties."""
    id: str
    name: str
    description: str
    base_capacity: int
    rest_periods: int
    range_factor: float
    fuel_efficiency: float
    maintenance_cost: float
    special_capabilities: List[str]
    color: str
    icon: str
    default_count: int
    # Add new fields for custom aircraft
    is_custom: bool = False
    custom_attributes: Dict[str, float] = field(default_factory=dict)
    
    # New time and distance mechanics fields
    cruise_speed_mach: float = 0.45  # Cruise speed in Mach
    turnover_time_base: float = 2.0  # Base turnover time in hours
    fuel_consumption_per_hour: float = 1.0  # Fuel consumption rate per hour
    operational_range_miles: float = 1000.0  # Maximum operational range in miles
    
    def calculate_operational_cost(self) -> float:
        """Calculate operational cost based on aircraft attributes."""
        base_cost = self.maintenance_cost * 1000  # Base cost per period
        
        # Apply special capability modifiers
        capability_multipliers = {
            "tactical": 1.2,      # 20% cost increase
            "short_field": 1.15,  # 15% cost increase
            "fuel_efficient": 0.9, # 10% cost reduction
            "high_capacity": 1.3,  # 30% cost increase
            "long_range": 1.25,    # 25% cost increase
            "all_weather": 1.35,   # 35% cost increase
            "night_ops": 1.2,      # 20% cost increase
            "rough_field": 1.25,   # 25% cost increase
        }
        
        total_multiplier = 1.0
        for capability in self.special_capabilities:
            if capability in capability_multipliers:
                total_multiplier *= capability_multipliers[capability]
        
        return base_cost * total_multiplier
    
    @classmethod
    def from_dict(cls, aircraft_id: str, data: Dict[str, Any]) -> "AircraftType":
        """Create AircraftType from dictionary data."""
        return cls(
            id=aircraft_id,
            name=data.get("name", aircraft_id),
            description=data.get("description", ""),
            base_capacity=data.get("base_capacity", 1),
            rest_periods=data.get("rest_periods", 1),
            range_factor=data.get("range_factor", 1.0),
            fuel_efficiency=data.get("fuel_efficiency", 1.0),
            maintenance_cost=data.get("maintenance_cost", 1.0),
            special_capabilities=data.get("special_capabilities", []),
            color=data.get("color", "#666666"),
            icon=data.get("icon", aircraft_id),
            default_count=data.get("default_count", 0),
            is_custom=data.get("is_custom", False),
            custom_attributes=data.get("custom_attributes", {}),
            cruise_speed_mach=data.get("cruise_speed_mach", 0.45),
            turnover_time_base=data.get("turnover_time_base", 2.0),
            fuel_consumption_per_hour=data.get("fuel_consumption_per_hour", 1.0),
            operational_range_miles=data.get("operational_range_miles", 1000.0)
        )


@dataclass
class FleetPreset:
    """Represents a predefined fleet configuration."""
    name: str
    description: str
    aircraft: Dict[str, int]  # aircraft_id -> count
    
    @classmethod
    def from_dict(cls, preset_name: str, data: Dict[str, Any]) -> "FleetPreset":
        """Create FleetPreset from dictionary data."""
        return cls(
            name=preset_name,
            description=data.get("description", ""),
            aircraft=data.get("aircraft", {})
        )


@dataclass
class FleetComposition:
    """Represents a user-defined fleet composition."""
    name: str
    aircraft: Dict[str, int]  # aircraft_id -> count
    total_capacity: int = 0
    total_cost: float = 0.0
    operational_cost: float = 0.0  # New field
    efficiency_score: float = 0.0
    
    def calculate_metrics(self, aircraft_types: Dict[str, AircraftType]) -> None:
        """Calculate fleet performance metrics including operational costs."""
        self.total_capacity = 0
        self.total_cost = 0.0
        self.operational_cost = 0.0  # Daily operational cost
        efficiency_sum = 0.0
        
        for aircraft_id, count in self.aircraft.items():
            if aircraft_id in aircraft_types:
                aircraft_type = aircraft_types[aircraft_id]
                self.total_capacity += aircraft_type.base_capacity * count
                self.total_cost += aircraft_type.maintenance_cost * count
                
                # Calculate operational cost (per day)
                daily_cost = aircraft_type.calculate_operational_cost()
                self.operational_cost += daily_cost * count
                
                efficiency_sum += aircraft_type.fuel_efficiency * count
        
        if sum(self.aircraft.values()) > 0:
            self.efficiency_score = efficiency_sum / sum(self.aircraft.values())
        else:
            self.efficiency_score = 0.0


class AircraftConfigManager:
    """Manages aircraft type configurations and fleet presets."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize the aircraft configuration manager."""
        from cargosim.core.paths import USER_AIRCRAFT_CONFIG_FILE
        if config_file is None:
            config_file = str(USER_AIRCRAFT_CONFIG_FILE)
        
        self.config_file = config_file
        self.aircraft_types: Dict[str, AircraftType] = {}
        self.fleet_presets: Dict[str, FleetPreset] = {}
        self.config_version = 1
        
        self.load_config()
    
    def load_config(self) -> None:
        """Load aircraft configuration from JSON file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load aircraft types
                aircraft_data = data.get("aircraft_types", {})
                for aircraft_id, aircraft_info in aircraft_data.items():
                    self.aircraft_types[aircraft_id] = AircraftType.from_dict(aircraft_id, aircraft_info)
                
                # Load fleet presets
                presets_data = data.get("fleet_presets", {})
                for preset_name, preset_info in presets_data.items():
                    self.fleet_presets[preset_name] = FleetPreset.from_dict(preset_name, preset_info)
                
                self.config_version = data.get("config_version", 1)
            # ------------------------------------------------------------------
            # After loading (or if file didn't exist) inject mandatory defaults so
            # that essential aircraft such as "C-130" are *always* present.  This
            # guarantees that legacy code paths and tutorials never fail even if
            # the user removed these entries from their personal config file.
            # ------------------------------------------------------------------
            self._inject_required_defaults()
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load aircraft config from {self.config_file}: {e}")
            self._load_default_config()
    
    def _load_default_config(self) -> None:
        """Load default aircraft configuration if file loading fails."""
        # Fallback to hardcoded defaults
        self.aircraft_types = {
            "C-130": AircraftType(
                id="C-130",
                name="C-130 Hercules",
                description="Medium tactical transport aircraft",
                base_capacity=6,
                rest_periods=6,
                range_factor=1.0,
                fuel_efficiency=1.0,
                maintenance_cost=1.0,
                special_capabilities=["tactical", "short_field"],
                color="#3b82f6",
                icon="C130",
                default_count=2
            ),
            "C-27": AircraftType(
                id="C-27",
                name="C-27J Spartan",
                description="Light tactical transport aircraft",
                base_capacity=3,
                rest_periods=12,
                range_factor=0.8,
                fuel_efficiency=1.2,
                maintenance_cost=0.8,
                special_capabilities=["tactical", "fuel_efficient"],
                color="#10b981",
                icon="C27",
                default_count=0
            ),
            "Custom_Transport": AircraftType(
                id="Custom_Transport",
                name="Custom Transport",
                description="User-configurable transport aircraft",
                base_capacity=4,  # Default value
                rest_periods=8,   # Default value
                range_factor=1.0, # Default value
                fuel_efficiency=1.0, # Default value
                maintenance_cost=1.0, # Default value
                special_capabilities=[], # User selects
                color="#8b5cf6",  # Purple to distinguish
                icon="Custom",
                default_count=0,
                is_custom=True,
                custom_attributes={
                    "capacity": 4.0,
                    "rest_periods": 8.0,
                    "range_factor": 1.0,
                    "fuel_efficiency": 1.0,
                    "maintenance_cost": 1.0
                }
            )
        }
        
        self.fleet_presets = {
            "Standard Fleet": FleetPreset(
                name="Standard Fleet",
                description="Balanced fleet for typical operations",
                aircraft={"C-130": 2}
            )
        }
    
    def save_config(self) -> None:
        """Save current aircraft configuration to JSON file."""
        try:
            data = {
                "config_version": self.config_version,
                "aircraft_types": {},
                "fleet_presets": {}
            }
            
            # Save aircraft types
            for aircraft_id, aircraft_type in self.aircraft_types.items():
                data["aircraft_types"][aircraft_id] = {
                    "name": aircraft_type.name,
                    "description": aircraft_type.description,
                    "base_capacity": aircraft_type.base_capacity,
                    "rest_periods": aircraft_type.rest_periods,
                    "range_factor": aircraft_type.range_factor,
                    "fuel_efficiency": aircraft_type.fuel_efficiency,
                    "maintenance_cost": aircraft_type.maintenance_cost,
                    "special_capabilities": aircraft_type.special_capabilities,
                    "color": aircraft_type.color,
                    "icon": aircraft_type.icon,
                    "default_count": aircraft_type.default_count,
                    "is_custom": aircraft_type.is_custom,
                    "custom_attributes": aircraft_type.custom_attributes,
                    "cruise_speed_mach": aircraft_type.cruise_speed_mach,
                    "turnover_time_base": aircraft_type.turnover_time_base,
                    "fuel_consumption_per_hour": aircraft_type.fuel_consumption_per_hour,
                    "operational_range_miles": aircraft_type.operational_range_miles
                }
            
            # Save fleet presets
            for preset_name, preset in self.fleet_presets.items():
                data["fleet_presets"][preset_name] = {
                    "description": preset.description,
                    "aircraft": preset.aircraft
                }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except IOError as e:
            print(f"Warning: Could not save aircraft config to {self.config_file}: {e}")
    
    def add_aircraft_type(self, aircraft_type: AircraftType) -> None:
        """Add a new aircraft type to the configuration."""
        self.aircraft_types[aircraft_type.id] = aircraft_type
        self.save_config()
    
    def update_aircraft_type(self, aircraft_id: str, **kwargs) -> bool:
        """Update an existing aircraft type."""
        if aircraft_id in self.aircraft_types:
            aircraft = self.aircraft_types[aircraft_id]
            for key, value in kwargs.items():
                if hasattr(aircraft, key):
                    setattr(aircraft, key, value)
            self.save_config()
            return True
        return False
    
    def remove_aircraft_type(self, aircraft_id: str) -> bool:
        """Remove an aircraft type from the configuration."""
        if aircraft_id in self.aircraft_types:
            del self.aircraft_types[aircraft_id]
            self.save_config()
            return True
        return False
    
    def get_aircraft_type(self, aircraft_id: str) -> Optional[AircraftType]:
        """Get an aircraft type by ID."""
        return self.aircraft_types.get(aircraft_id)
    
    def get_all_aircraft_types(self) -> List[AircraftType]:
        """Get all available aircraft types."""
        return list(self.aircraft_types.values())
    
    def add_fleet_preset(self, preset: FleetPreset) -> None:
        """Add a new fleet preset."""
        self.fleet_presets[preset.name] = preset
        self.save_config()
    
    def get_fleet_preset(self, preset_name: str) -> Optional[FleetPreset]:
        """Get a fleet preset by name."""
        return self.fleet_presets.get(preset_name)
    
    def get_all_fleet_presets(self) -> List[FleetPreset]:
        """Get all available fleet presets."""
        return list(self.fleet_presets.values())
    
    def save_fleet_preset(self, name: str, fleet_composition: Dict[str, Any]) -> bool:
        """Save a fleet preset."""
        try:
            if not name or not fleet_composition:
                return False
            
            # Extract aircraft composition
            aircraft = fleet_composition.get("aircraft", {})
            if not isinstance(aircraft, dict):
                return False
            
            # Create and add the preset
            preset = FleetPreset(
                name=name,
                description=f"Fleet preset: {name}",
                aircraft=aircraft.copy()
            )
            self.add_fleet_preset(preset)
            return True
            
        except Exception as e:
            print(f"Error saving fleet preset: {e}")
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _inject_required_defaults(self) -> None:
        """Ensure that core built-in aircraft types exist after loading config."""
        REQUIRED_DEFAULTS = {
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
                "default_count": 2,
            }
        }
        for ac_id, ac_info in REQUIRED_DEFAULTS.items():
            if ac_id not in self.aircraft_types:
                logger.warning(f"Injecting missing default aircraft type '{ac_id}' into configuration")
                self.aircraft_types[ac_id] = AircraftType.from_dict(ac_id, ac_info)
        # Do *not* call save_config() automatically to respect read-only setups.


class FleetBuilder:
    """Main fleet builder class for creating and managing fleet compositions."""
    
    def __init__(self, config_manager: AircraftConfigManager):
        """Initialize the fleet builder with a configuration manager."""
        self.config_manager = config_manager
        self.current_fleet = FleetComposition("Empty Fleet", {})
        
        # Load default fleet
        self._load_default_fleet()

    # --- New helper ----------------------------------------------------------
    def get_default_fleet(self) -> Dict[str, int]:
        """Return a sensible default fleet mapping aircraft_id -> count.

        Priority order:
        1. Hard-coded fallback of 2 × C-130.
        2. Last-chance fallback: pick *any* available aircraft type.
        """
        # 1) Hard-coded fallback of 2 × C-130, **but only if it actually exists**
        #    in the current configuration.  User-level config files may not
        #    include the built-in examples (e.g. "C-130"), and trying to use a
        #    missing aircraft ID breaks later validation in the GUI.
        if "C-130" in self.config_manager.aircraft_types:
            return {"C-130": 2}

        # 2) Last-chance fallback: pick *any* available aircraft type so that the
        #    application can still start even if the configuration is highly
        #    customised or minimal.
        if self.config_manager.aircraft_types:
            first_aircraft_id = next(iter(self.config_manager.aircraft_types))
            return {first_aircraft_id: 2}

        # 3) If no aircraft types are available at all, return an empty fleet –
        #    the GUI will display the appropriate empty-state instead of
        #    crashing.
        return {}

    def _load_default_fleet(self) -> None:
        """Load a default fleet composition if no temporary fleet is set."""
        self.current_fleet = FleetComposition(
            name="Default Fleet",
            aircraft=self.get_default_fleet()
        )
        self.current_fleet.calculate_metrics(self.config_manager.aircraft_types)
    
    def create_fleet_from_preset(self, preset_name: str) -> FleetComposition:
        """Create a fleet composition from a preset."""
        preset = self.config_manager.get_fleet_preset(preset_name)
        if preset:
            self.current_fleet = FleetComposition(
                name=preset.name,
                aircraft=preset.aircraft.copy()
            )
            self.current_fleet.calculate_metrics(self.config_manager.aircraft_types)
            return self.current_fleet
        return FleetComposition("Empty Fleet", {})
    
    def create_fleet_from_legacy_label(self, fleet_label: str) -> FleetComposition:
        """Create a fleet composition from legacy fleet labels (for backward compatibility)."""
        aircraft = {}
        
        if fleet_label == "2xC130":
            aircraft = {"C-130": 2}
        elif fleet_label == "4xC130":
            aircraft = {"C-130": 4}
        elif fleet_label == "2xC130_2xC27":
            aircraft = {"C-130": 2, "C-27": 2}
        elif fleet_label == "2xCustom_Transport":
            aircraft = {"Custom_Transport": 2}
        elif fleet_label == "3xCustom_Transport":
            aircraft = {"Custom_Transport": 3}
        elif fleet_label == "1xC130_1xCustom_Transport":
            aircraft = {"C-130": 1, "Custom_Transport": 1}
        else:
            # Try to parse custom format like "3xC130_1xC27"
            try:
                parts = fleet_label.split("_")
                for part in parts:
                    if "x" in part:
                        count_str, aircraft_type = part.split("x", 1)
                        count = int(count_str)
                        if aircraft_type in self.config_manager.aircraft_types:
                            aircraft[aircraft_type] = count
            except (ValueError, KeyError):
                pass
        
        self.current_fleet = FleetComposition(f"Legacy: {fleet_label}", aircraft)
        self.current_fleet.calculate_metrics(self.config_manager.aircraft_types)
        return self.current_fleet
    
    def add_aircraft(self, aircraft_id: str, count: int = 1) -> bool:
        """Add aircraft to the current fleet."""
        if aircraft_id in self.config_manager.aircraft_types:
            current_count = self.current_fleet.aircraft.get(aircraft_id, 0)
            self.current_fleet.aircraft[aircraft_id] = current_count + count
            self.current_fleet.calculate_metrics(self.config_manager.aircraft_types)
            return True
        return False
    
    def remove_aircraft(self, aircraft_id: str, count: int = 1) -> bool:
        """Remove aircraft from the current fleet."""
        if aircraft_id in self.current_fleet.aircraft:
            current_count = self.current_fleet.aircraft[aircraft_id]
            new_count = max(0, current_count - count)
            if new_count == 0:
                del self.current_fleet.aircraft[aircraft_id]
            else:
                self.current_fleet.aircraft[aircraft_id] = new_count
            
            self.current_fleet.calculate_metrics(self.config_manager.aircraft_types)
            return True
        return False
    
    def set_aircraft_count(self, aircraft_id: str, count: int) -> bool:
        """Set the exact count of an aircraft type in the fleet."""
        if aircraft_id in self.config_manager.aircraft_types:
            if count <= 0:
                self.current_fleet.aircraft.pop(aircraft_id, None)
            else:
                self.current_fleet.aircraft[aircraft_id] = count
            
            self.current_fleet.calculate_metrics(self.config_manager.aircraft_types)
            return True
        return False
    
    def clear_fleet(self) -> None:
        """Clear the current fleet."""
        self.current_fleet = FleetComposition("Empty Fleet", {})
        self.current_fleet.calculate_metrics(self.config_manager.aircraft_types)
    
    def get_fleet_summary(self) -> Dict[str, Any]:
        """Get a summary of the current fleet."""
        summary = {
            "name": self.current_fleet.name,
            "total_aircraft": sum(self.current_fleet.aircraft.values()),
            "total_capacity": self.current_fleet.total_capacity,
            "total_cost": self.current_fleet.total_cost,
            "operational_cost": self.current_fleet.operational_cost, # Added operational_cost
            "efficiency_score": self.current_fleet.efficiency_score,
            "aircraft_breakdown": {},
            "capabilities": set()
        }
        
        for aircraft_id, count in self.current_fleet.aircraft.items():
            aircraft_type = self.config_manager.get_aircraft_type(aircraft_id)
            if aircraft_type:
                summary["aircraft_breakdown"][aircraft_id] = {
                    "count": count,
                    "name": aircraft_type.name,
                    "capacity": aircraft_type.base_capacity,
                    "total_capacity": aircraft_type.base_capacity * count,
                    "capabilities": aircraft_type.special_capabilities
                }
                summary["capabilities"].update(aircraft_type.special_capabilities)
        
        summary["capabilities"] = list(summary["capabilities"])
        return summary
    
    def export_fleet_to_legacy_format(self) -> str:
        """Export the current fleet to legacy fleet label format."""
        if not self.current_fleet.aircraft:
            return "2xC130"  # Default fallback
        
        parts = []
        for aircraft_id, count in self.current_fleet.aircraft.items():
            parts.append(f"{count}x{aircraft_id}")
        
        return "_".join(parts)
    
    def save_fleet_preset(self, name: str, description: str = "") -> bool:
        """Save the current fleet as a new preset."""
        preset = FleetPreset(
            name=name,
            description=description,
            aircraft=self.current_fleet.aircraft.copy()
        )
        self.config_manager.add_fleet_preset(preset)
        return True

    def get_current_fleet_name(self) -> str:
        """Get the appropriate name for the current fleet."""
        # Check if current fleet matches any preset
        preset_name = self._find_matching_preset()
        if preset_name:
            return preset_name
        
        # If no preset matches, generate user custom name
        return self._generate_user_custom_name()
    
    def _find_matching_preset(self) -> Optional[str]:
        """Check if the current fleet matches any existing preset."""
        if not self.current_fleet.aircraft:
            return None
            
        # Get all presets
        all_presets = self.config_manager.get_all_fleet_presets()
        
        for preset in all_presets:
            if self._fleets_match(self.current_fleet, preset):
                return preset.name
        
        return None
    
    def _fleets_match(self, fleet1: FleetComposition, fleet2: FleetPreset) -> bool:
        """Check if two fleets have the same aircraft composition."""
        if len(fleet1.aircraft) != len(fleet2.aircraft):
            return False
        
        # Check if all aircraft types and counts match
        for aircraft_id, count in fleet1.aircraft.items():
            if aircraft_id not in fleet2.aircraft or fleet2.aircraft[aircraft_id] != count:
                return False
        
        return True
    
    def get_fleet_composition(self) -> Dict[str, Any]:
        """Get the current fleet composition as a dictionary."""
        return {
            "name": self.current_fleet.name,
            "aircraft": self.current_fleet.aircraft.copy(),
            "total_capacity": self.current_fleet.total_capacity,
            "total_cost": self.current_fleet.total_cost,
            "operational_cost": self.current_fleet.operational_cost,
            "efficiency_score": self.current_fleet.efficiency_score
        }
    
    def get_current_fleet(self) -> Dict[str, int]:
        """Get the current fleet from the Fleet Builder pallet.
        
        Returns:
            Dict[str, int]: Mapping of aircraft_id -> count for the current fleet
        """
        return self.current_fleet.aircraft.copy()
    
    def load_fleet_from_config(self, fleet_config: Dict[str, Any]) -> bool:
        """Load fleet from configuration data."""
        try:
            if not fleet_config or not isinstance(fleet_config, dict):
                return False
            
            # Extract aircraft composition
            aircraft = fleet_config.get("aircraft", {})
            if not isinstance(aircraft, dict):
                return False
            
            # Validate aircraft types exist
            for aircraft_id in aircraft.keys():
                if aircraft_id not in self.config_manager.aircraft_types:
                    logger.warning(f"Aircraft type '{aircraft_id}' not found in configuration")
                    return False
            
            # Create new fleet composition
            fleet_name = fleet_config.get("name", "Loaded Fleet")
            self.current_fleet = FleetComposition(fleet_name, aircraft.copy())
            self.current_fleet.calculate_metrics(self.config_manager.aircraft_types)
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading fleet from config: {e}")
            return False

    def load_fleet_from_preset(self, aircraft_dict: Dict[str, int]) -> bool:
        """Backward-compatibility wrapper used by the GUI.

        Accepts the simple aircraft_id -> count mapping that older GUI code
        expects and adapts it to the full configuration structure required by
        `load_fleet_from_config`.
        """
        if not aircraft_dict or not isinstance(aircraft_dict, dict):
            return False
        return self.load_fleet_from_config({
            "name": "Loaded Fleet",
            "aircraft": aircraft_dict,
        })

    def update_spoke_configuration(self, spoke_config: Dict[str, Any]) -> bool:
        """Update spoke configuration for the fleet."""
        try:
            if not spoke_config or not isinstance(spoke_config, dict):
                return False
            
            # Store spoke configuration for future use
            # This is a placeholder - actual implementation would depend on how
            # spoke configuration affects fleet operations
            if not hasattr(self, '_spoke_config'):
                self._spoke_config = {}
            
            self._spoke_config = spoke_config.copy()
            
            # For now, just log the configuration update
            logger.info(f"Updated spoke configuration: {spoke_config}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating spoke configuration: {e}")
            return False
    
    def _generate_user_custom_name(self) -> str:
        """Generate a user custom fleet name with incrementing number."""
        # Count existing user custom fleets
        user_custom_count = 0
        all_presets = self.config_manager.get_all_fleet_presets()
        
        for preset in all_presets:
            if preset.name.startswith("User Custom"):
                user_custom_count += 1
        
        return f"User Custom {user_custom_count + 1}"


# Global instance for easy access
_aircraft_config_manager = None
_fleet_builder = None


def get_aircraft_config_manager() -> AircraftConfigManager:
    """Get the global aircraft configuration manager instance."""
    global _aircraft_config_manager
    if _aircraft_config_manager is None:
        _aircraft_config_manager = AircraftConfigManager()
    return _aircraft_config_manager


def get_fleet_builder() -> FleetBuilder:
    """Get the global fleet builder instance."""
    global _fleet_builder
    if _fleet_builder is None:
        _fleet_builder = FleetBuilder(get_aircraft_config_manager())
    return _fleet_builder
