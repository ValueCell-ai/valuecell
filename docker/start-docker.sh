#!/bin/bash
# Docker Quick Start Script

set -e

echo "=========================================="
echo "ValueCell Docker Startup Script"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Using default configuration."
    echo "It is recommended to create a .env file and configure necessary environment variables."
fi

# Build and start services
echo ""
echo "Building Docker images..."
docker-compose build

echo ""
echo "Starting services..."
docker-compose up -d

echo ""
echo "Waiting for services to start..."
sleep 5

# Check service status
echo ""
echo "Service status:"
docker-compose ps

echo ""
echo "=========================================="
echo "Services started!"
echo "Frontend: http://localhost:1420"
echo "Backend API: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "=========================================="
echo ""
echo "View logs: docker-compose logs -f"
echo "Stop services: docker-compose down"
echo ""
