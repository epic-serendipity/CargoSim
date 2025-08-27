#!/usr/bin/env python3
"""
Demonstration of enhanced logging capabilities in CargoSim.

This script shows:
- JSON vs Human logging formats
- Correlation ID tracking
- Log filtering and noise reduction
- Log retention management
"""

import os
import sys
import time
import uuid
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from cargosim.core.logging_config import (
    setup_comprehensive_logging,
    set_correlation_id,
    get_correlation_id,
    get_log_manager
)


def demonstrate_human_logging():
    """Demonstrate human-readable logging format."""
    print("\n" + "="*60)
    print("DEMONSTRATING HUMAN-READABLE LOGGING")
    print("="*60)
    
    # Setup human-readable logging
    log_manager = setup_comprehensive_logging(
        level="DEBUG",
        use_json=False
    )
    
    # Set a correlation ID for this demo
    demo_id = f"demo-human-{uuid.uuid4().hex[:8]}"
    set_correlation_id(demo_id)
    
    # Get loggers for different components
    main_logger = log_manager.get_logger("cargosim.main")
    ui_logger = log_manager.get_logger("cargosim.ui")
    sim_logger = log_manager.get_logger("cargosim.simulation")
    
    # Demonstrate different log levels
    main_logger.info("Starting CargoSim application")
    main_logger.debug("Loading configuration files")
    
    ui_logger.info("Initializing user interface")
    ui_logger.warning("Font 'Arial' not found, using fallback")
    
    sim_logger.info("Starting simulation engine")
    sim_logger.debug("Physics engine initialized")
    
    # Demonstrate correlation ID in logs
    print(f"\nCorrelation ID for this demo: {get_correlation_id()}")
    print("Notice how the correlation ID appears in the log messages above")


def demonstrate_json_logging():
    """Demonstrate JSON logging format."""
    print("\n" + "="*60)
    print("DEMONSTRATING JSON LOGGING FORMAT")
    print("="*60)
    
    # Setup JSON logging
    log_manager = setup_comprehensive_logging(
        level="DEBUG",
        use_json=True
    )
    
    # Set a new correlation ID for this demo
    demo_id = f"demo-json-{uuid.uuid4().hex[:8]}"
    set_correlation_id(demo_id)
    
    # Get loggers
    main_logger = log_manager.get_logger("cargosim.main")
    perf_logger = log_manager.get_logger("cargosim.performance")
    
    # Log some messages in JSON format
    main_logger.info("JSON logging enabled")
    main_logger.debug("Configuration loaded successfully")
    
    # Log performance metrics
    perf_logger.info("Frame rate: 60 FPS")
    perf_logger.info("Memory usage: 128 MB")
    perf_logger.info("CPU usage: 15%")
    
    print(f"\nCorrelation ID for this demo: {get_correlation_id()}")
    print("Notice how the logs above are in JSON format")
    print("This makes them machine-parsable for log aggregation systems")


def demonstrate_log_filtering():
    """Demonstrate log filtering capabilities."""
    print("\n" + "="*60)
    print("DEMONSTRATING LOG FILTERING")
    print("="*60)
    
    # Setup logging
    log_manager = setup_comprehensive_logging(level="DEBUG")
    
    # Set correlation ID
    demo_id = f"demo-filter-{uuid.uuid4().hex[:8]}"
    set_correlation_id(demo_id)
    
    # Get logger
    logger = log_manager.get_logger("cargosim.test")
    
    # Demonstrate Tkinter error filtering
    print("Generating multiple Tkinter font errors...")
    for i in range(10):
        logger.error("Unknown option -font in Tk font")
    
    print("Notice how only the first 5 font errors are logged")
    print("The rest are filtered out to reduce noise")
    
    # Demonstrate performance log filtering
    print("\nGenerating multiple performance logs...")
    for i in range(15):
        logger.info(f"Performance metric: {i} FPS")
    
    print("Notice how only the first 10 performance logs are shown")
    print("The rest are filtered out to prevent spam")


def demonstrate_correlation_tracking():
    """Demonstrate correlation ID tracking across operations."""
    print("\n" + "="*60)
    print("DEMONSTRATING CORRELATION ID TRACKING")
    print("="*60)
    
    # Setup logging
    log_manager = setup_comprehensive_logging(level="INFO")
    
    # Simulate a simulation run
    simulation_id = f"sim-{uuid.uuid4().hex[:8]}"
    set_correlation_id(simulation_id)
    
    print(f"Starting simulation with ID: {simulation_id}")
    
    # Simulate different phases of simulation
    phases = [
        ("Configuration", "Loading aircraft configurations"),
        ("Initialization", "Initializing physics engine"),
        ("Execution", "Running simulation loop"),
        ("Cleanup", "Cleaning up resources")
    ]
    
    for phase_name, message in phases:
        logger = log_manager.get_logger(f"cargosim.simulation.{phase_name.lower()}")
        logger.info(f"Phase: {phase_name} - {message}")
        
        # Verify correlation ID is maintained
        current_id = get_correlation_id()
        assert current_id == simulation_id, f"Correlation ID changed unexpectedly: {current_id}"
        
        time.sleep(0.1)  # Small delay to simulate work
    
    print(f"\nSimulation completed. All logs used correlation ID: {simulation_id}")


def demonstrate_log_retention():
    """Demonstrate log retention management."""
    print("\n" + "="*60)
    print("DEMONSTRATING LOG RETENTION MANAGEMENT")
    print("="*60)
    
    # Setup logging
    log_manager = setup_comprehensive_logging(level="INFO")
    
    # Set correlation ID
    demo_id = f"demo-retention-{uuid.uuid4().hex[:8]}"
    set_correlation_id(demo_id)
    
    # Get logger
    logger = log_manager.get_logger("cargosim.retention")
    
    # Log some messages
    logger.info("Testing log retention functionality")
    logger.info("This log will be managed by the retention system")
    
    # Demonstrate retention cleanup (in a real scenario, this would run in background)
    print("\nLog retention system would automatically clean up old logs")
    print("Default retention: 30 days")
    print("Log rotation: 10MB max file size, 5 backup files")
    
    # Show how to start retention cleanup manually
    print("\nTo start log retention cleanup manually:")
    print("log_manager.start_log_retention_cleanup(max_age_days=30, cleanup_interval_hours=24)")


def demonstrate_environment_variables():
    """Demonstrate environment variable configuration."""
    print("\n" + "="*60)
    print("DEMONSTRATING ENVIRONMENT VARIABLE CONFIGURATION")
    print("="*60)
    
    print("You can control logging behavior using environment variables:")
    print()
    print("CARGOSIM_LOG_FORMAT=json    # Enable JSON logging")
    print("CARGOSIM_LOG_FORMAT=human   # Enable human-readable logging (default)")
    print()
    print("Example usage:")
    print("export CARGOSIM_LOG_FORMAT=json")
    print("python demo_enhanced_logging.py")
    print()
    print("Or inline:")
    print("CARGOSIM_LOG_FORMAT=json python demo_enhanced_logging.py")


def main():
    """Main demonstration function."""
    print("CargoSim Enhanced Logging Demonstration")
    print("="*60)
    
    # Check if JSON logging is requested via environment
    use_json = os.environ.get('CARGOSIM_LOG_FORMAT', 'human').lower() == 'json'
    
    if use_json:
        print("JSON logging enabled via environment variable")
    else:
        print("Human-readable logging enabled (default)")
    
    try:
        # Run demonstrations
        demonstrate_human_logging()
        demonstrate_json_logging()
        demonstrate_log_filtering()
        demonstrate_correlation_tracking()
        demonstrate_log_retention()
        demonstrate_environment_variables()
        
        print("\n" + "="*60)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("="*60)
        
        print("\nKey features demonstrated:")
        print("✅ Dual logging formats (Human/JSON)")
        print("✅ Correlation ID tracking")
        print("✅ Intelligent log filtering")
        print("✅ Log retention management")
        print("✅ Environment variable configuration")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
