#!/usr/bin/env python3
"""Standalone database initialization script for ValueCell."""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now import from valuecell
from valuecell.server.db.init_db import main

if __name__ == "__main__":
    main()
