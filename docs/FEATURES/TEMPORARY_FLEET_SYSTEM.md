# Temporary Fleet System Implementation

This document describes the implementation of the temporary fleet system in CargoSim, which allows users to either save custom fleets permanently or use them temporarily for the current session.

## Overview

The temporary fleet system provides two options for users:

1. **Save as Preset**: Saves the fleet permanently to `aircraft_config.json` (existing functionality)
2. **Use Current Fleet**: Uses the fleet temporarily, only saving to `cargo_sim_config.json` for the current session

## Architecture

### **Core Components**

#### **1. FleetBuilder Class** (`cargosim/fleet_builder.py`)
- **New Fields**:
  - `temporary_fleet_label`: Stores the temporary fleet label
  - `temporary_fleet_composition`: Stores the temporary fleet composition

- **New Methods**:
  - `set_temporary_fleet(fleet_label)`: Sets a temporary fleet for the session
  - `get_temporary_fleet_label()`: Returns the current temporary fleet label
  - `is_temporary_fleet_active()`: Checks if a temporary fleet is active
  - `get_temporary_fleet_composition()`: Returns the temporary fleet composition
  - `clear_temporary_fleet()`: Clears the temporary fleet

#### **2. FleetBuilderTab Class** (`cargosim/fleet_builder_gui.py`)
- **New UI Elements**:
  - "Use Current Fleet" button between "Save as Preset" and "Export to Legacy Format"
  - "Clear Temporary Fleet" button in the fleet canvas (only visible when temporary fleet is active)

- **New Methods**:
  - `_use_current_fleet()`: Handles the "Use Current Fleet" button click
  - `_create_temporary_fleet_label()`: Creates a temporary fleet label
  - `load_fleet_from_config(fleet_label)`: Loads a fleet from the main configuration
  - `_clear_temporary_fleet()`: Clears temporary fleet with confirmation
  - `_update_temp_fleet_buttons()`: Updates button states based on temporary fleet status

#### **3. FleetCanvas Class** (`cargosim/fleet_builder_gui.py`)
- **New Methods**:
  - `load_fleet_composition(fleet_composition)`: Loads a fleet composition into the canvas
  - `_update_temp_fleet_buttons()`: Updates temporary fleet button visibility

#### **4. Simulation Integration** (`cargosim/simulation.py`)
- **Enhanced Fleet Building**:
  - Added support for `TEMP_` prefixed fleet labels
  - Temporary fleets are loaded before legacy parsing
  - Fallback to legacy system if temporary fleet is empty

### **Data Flow**

```
User creates fleet in Fleet Builder GUI
           ↓
   [Use Current Fleet] button clicked
           ↓
   Creates TEMP_ label (e.g., "TEMP_2xCustom_Transport_1xC130")
           ↓
   Stores in FleetBuilder.temporary_fleet_composition
           ↓
   Main config uses this label as fleet_label
           ↓
   Simulation loads temporary fleet when building fleet
           ↓
   Custom aircraft are visible and functional
```

## Implementation Details

### **1. Temporary Fleet Labels**

Temporary fleet labels follow the pattern:
```
TEMP_<count>x<aircraft_type>_<count>x<aircraft_type>...
```

Examples:
- `TEMP_2xCustom_Transport` - 2 custom aircraft
- `TEMP_1xC130_2xCustom_Transport` - 1 C-130 + 2 custom aircraft
- `TEMP_3xCustom_Transport_1xC27` - 3 custom aircraft + 1 C-27

### **2. Fleet Loading Priority**

The simulation uses this priority order for fleet loading:

1. **Temporary Fleet** (if `fleet_label` starts with `TEMP_`)
2. **Fleet Preset** (if `fleet_label` matches a preset name)
3. **Legacy Format** (if `fleet_label` contains `_` and `x`)
4. **Hardcoded Fleet** (fallback to known fleet configurations)

### **3. Configuration Integration**

#### **Main Configuration** (`cargo_sim_config.json`)
```json
{
  "fleet_label": "TEMP_2xCustom_Transport_1xC130",
  "periods": 30,
  ...
}
```

#### **Fleet Builder State**
- Temporary fleet composition stored in memory
- Not persisted to `aircraft_config.json`
- Cleared when application restarts

### **4. User Experience**

#### **Creating a Temporary Fleet**
1. User opens Fleet Builder tab
2. User adds aircraft to the fleet canvas
3. User clicks "Use Current Fleet" button
4. System creates temporary fleet label
5. Success message shows fleet is active for the session
6. Fleet is immediately available for simulation

#### **Managing Temporary Fleets**
- **Clear Temporary Fleet**: Removes temporary fleet and reverts to default
- **Save as Preset**: Converts temporary fleet to permanent preset
- **Export to Legacy**: Generates legacy format for external use

## Benefits

### **1. User Flexibility**
- **Quick Testing**: Users can test custom fleets without saving them permanently
- **Session-Based**: Temporary fleets are perfect for one-off simulations
- **No Clutter**: Prevents permanent storage of experimental fleet configurations

### **2. Professional Workflow**
- **Iterative Design**: Users can refine fleets before making them permanent
- **Version Control**: Clear distinction between temporary and permanent configurations
- **Clean Organization**: Permanent presets remain organized and purposeful

### **3. System Integration**
- **Seamless Operation**: Temporary fleets work exactly like permanent presets
- **No Breaking Changes**: Existing functionality remains unchanged
- **Performance**: Temporary fleets are stored in memory for fast access

## Testing

The temporary fleet system has been thoroughly tested:

### **Test Results**
```
✓ Fleet builder import and configuration
✓ Aircraft type availability (including Custom_Transport)
✓ Temporary fleet creation and management
✓ Fleet composition storage and retrieval
✓ Simulation integration with temporary fleets
✓ Aircraft creation and visibility
✓ Temporary fleet clearing and cleanup
```

### **Test Scenarios**
1. **Basic Temporary Fleet**: 2 Custom_Transport aircraft
2. **Mixed Fleet**: 1 C-130 + 2 Custom_Transport aircraft
3. **Complex Fleet**: Multiple aircraft types with different counts
4. **Integration**: Simulation loading and aircraft creation
5. **Cleanup**: Temporary fleet clearing and state management

## Usage Examples

### **Example 1: Quick Custom Fleet Test**
```python
# User creates fleet with 3 Custom_Transport aircraft
# Clicks "Use Current Fleet"
# System creates: "TEMP_3xCustom_Transport"
# Fleet is immediately available for simulation
```

### **Example 2: Mixed Fleet Experiment**
```python
# User creates fleet with 2 C-130 + 1 Custom_Transport
# Clicks "Use Current Fleet"
# System creates: "TEMP_2xC130_1xCustom_Transport"
# Fleet works in simulation, custom aircraft are visible
```

### **Example 3: Fleet Evolution**
```python
# User creates experimental fleet
# Clicks "Use Current Fleet" to test
# Runs simulation, sees custom aircraft working
# Decides to keep it, clicks "Save as Preset"
# Fleet becomes permanent preset
```

## Future Enhancements

### **Potential Improvements**
1. **Fleet Templates**: Pre-defined temporary fleet templates
2. **Fleet History**: Track recent temporary fleets
3. **Auto-Save**: Automatically save temporary fleets after successful simulation
4. **Fleet Comparison**: Compare temporary vs. permanent fleet performance
5. **Export Options**: Export temporary fleets to various formats

### **Integration Opportunities**
1. **Scenario Manager**: Temporary fleets for different simulation scenarios
2. **A/B Testing**: Compare different fleet configurations
3. **Performance Analysis**: Track fleet performance metrics
4. **Collaboration**: Share temporary fleet configurations between users

## Conclusion

The temporary fleet system provides a professional, user-friendly way to manage custom fleet configurations in CargoSim. It maintains the existing functionality while adding the flexibility users need for iterative fleet design and testing.

The implementation is:
- **Elegant**: Clean separation of concerns
- **Professional**: Follows software engineering best practices
- **Integrated**: Seamlessly works with existing systems
- **Tested**: Thoroughly validated for reliability
- **Extensible**: Ready for future enhancements

Users can now create custom fleets with confidence, knowing they can either save them permanently or use them temporarily for the current session, all while maintaining the visual visibility and functionality of custom aircraft.
