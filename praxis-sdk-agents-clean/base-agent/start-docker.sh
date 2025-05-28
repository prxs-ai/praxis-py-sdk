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

# Show relay node logs to get peer ID
echo -e "\nRelay node peer ID:"
docker-compose logs relay-node | grep "peer_id:" || echo "Relay node not ready yet"

# Check registry
echo -e "\nChecking registry:"
curl -s http://localhost:8082/docs || echo "Registry not accessible yet"

echo -e "\nTo view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
