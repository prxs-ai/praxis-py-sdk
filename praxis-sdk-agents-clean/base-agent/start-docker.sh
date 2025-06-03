#!/bin/bash
# Start services with libp2p support

set -e

echo "Building and starting services..."

# Build images
docker-compose build

# Start services with override
docker-compose -f docker-compose.yaml -f docker-compose.override.yaml up -d

echo "Waiting for services to start..."
sleep 10

# Check services
echo "Checking services status:"
docker-compose ps

echo -e "\nTo view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
