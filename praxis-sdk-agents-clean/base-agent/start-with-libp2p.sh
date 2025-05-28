#!/bin/bash
# Script to start docker-compose with libp2p support

set -e

echo "Starting base-agent with libp2p support..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Start relay node first to get its peer ID
echo "Starting relay node to get peer ID..."
docker-compose -f docker-compose.yaml -f docker-compose.override.yaml up -d relay-node

# Wait for relay node to start
echo "Waiting for relay node to start..."
sleep 5

# Get relay node peer ID from logs
RELAY_PEER_ID=$(docker-compose logs relay-node 2>&1 | grep "Use this peer ID" | awk -F': ' '{print $2}' | tail -1)

if [ -z "$RELAY_PEER_ID" ]; then
    echo "Failed to get relay peer ID from logs. Checking alternative pattern..."
    RELAY_PEER_ID=$(docker-compose logs relay-node 2>&1 | grep "peer_id:" | awk -F': ' '{print $2}' | tail -1)
fi

if [ -z "$RELAY_PEER_ID" ]; then
    echo "ERROR: Could not determine relay node peer ID"
    echo "Relay node logs:"
    docker-compose logs relay-node
    exit 1
fi

echo "Relay node peer ID: $RELAY_PEER_ID"

# Update .env with the relay peer ID
if grep -q "REGISTRY_RELAY_PEER_ID=" .env; then
    # Update existing value
    sed -i.bak "s/REGISTRY_RELAY_PEER_ID=.*/REGISTRY_RELAY_PEER_ID=$RELAY_PEER_ID/" .env
else
    # Add new value
    echo "REGISTRY_RELAY_PEER_ID=$RELAY_PEER_ID" >> .env
fi

# Export for current session
export REGISTRY_RELAY_PEER_ID=$RELAY_PEER_ID

# Start all services
echo "Starting all services..."
docker-compose -f docker-compose.yaml -f docker-compose.override.yaml up

echo "Done!"
