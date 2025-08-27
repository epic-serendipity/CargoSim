#!/usr/bin/env python3
"""
CargoSim - Hub-and-spoke logistics simulator
Entry point script for backward compatibility
"""

import sys
import os

# Add the cargosim package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cargosim'))

from cargosim.main import main
if __name__ == "__main__":
    sys.exit(main())
