#!/usr/bin/env python3
"""
CargoSim - Hub-and-spoke logistics simulator
Entry point script for backward compatibility
"""

import sys
from cargosim.main import main
if __name__ == "__main__":
    sys.exit(main())
