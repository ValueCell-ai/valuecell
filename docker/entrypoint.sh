#!/bin/bash
# Docker entrypoint script for backend service
# This script ensures the database is initialized before starting the server

set -e

echo "=========================================="
echo "ValueCell Backend Entrypoint"
echo "=========================================="

# Get database path from environment or use default
DB_PATH="${VALUECELL_SQLITE_DB:-sqlite:///app/valuecell.db}"

# Extract file path from SQLite URL (remove sqlite:// prefix, preserve leading slash)
if [[ "$DB_PATH" == sqlite:///* ]]; then
    DB_FILE="${DB_PATH#sqlite://}"
else
    DB_FILE="$DB_PATH"
fi

echo "Database path: $DB_PATH"
echo "Database file: $DB_FILE"

# Check if database file exists and is a regular file
if [ -e "$DB_FILE" ]; then
    if [ -d "$DB_FILE" ]; then
        echo "WARNING: Database path exists but is a directory, not a file!"
        echo "Removing directory and creating database file..."
        rm -rf "$DB_FILE"
    elif [ -f "$DB_FILE" ]; then
        echo "Database file exists: $DB_FILE"
        # Check if database is valid SQLite file
        if command -v sqlite3 &> /dev/null; then
            if sqlite3 "$DB_FILE" "SELECT 1;" &> /dev/null; then
                echo "Database file is valid SQLite database"
            else
                echo "WARNING: Database file exists but is not a valid SQLite database"
                echo "Removing invalid file and will recreate..."
                rm -f "$DB_FILE"
            fi
        fi
    fi
fi

# Create database directory if it doesn't exist
DB_DIR=$(dirname "$DB_FILE")
if [ "$DB_DIR" != "." ] && [ "$DB_DIR" != "/" ]; then
    mkdir -p "$DB_DIR"
    echo "Created database directory: $DB_DIR"
fi

# Initialize database if it doesn't exist
if [ ! -f "$DB_FILE" ]; then
    echo "Database file does not exist, initializing..."
    cd /app/python
    uv run -m valuecell.server.db.init_db || {
        echo "ERROR: Database initialization failed"
        exit 1
    }
    echo "Database initialized successfully"
else
    echo "Database file exists, skipping initialization"
    # Run migration to ensure schema is up to date
fi

echo "=========================================="
echo "Starting ValueCell Backend Server..."
echo "=========================================="

# Execute the main command
exec "$@"
