#!/usr/bin/env python3
"""Standalone database initialization script for ValueCell."""

import sys
from pathlib import Path


def setup_path_and_run():
    """Setup Python path and run the database initialization."""
    # Add the project root to Python path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    # Import after path setup to avoid import errors
    import valuecell.server.db.init_db as init_db_module

    # Run the main function
    init_db_module.main()


if __name__ == "__main__":
    setup_path_and_run()
