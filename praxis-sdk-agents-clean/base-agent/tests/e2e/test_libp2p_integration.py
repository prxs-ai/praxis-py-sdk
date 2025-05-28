"""
E2E test for libp2p integration with Circuit Relay v2.
This test verifies that the agent can start with libp2p, register with a relay registry,
and be discoverable by other peers.
"""

import asyncio
import os
import sys
import time
from typing import Dict, List

import httpx
from fastapi import FastAPI
from loguru import logger

# Add local py-libp2p to path for mock services
if os.path.exists('/serve_app/py-libp2p'):
    sys.path.insert(0, '/serve_app/py-libp2p')
else:
    sys.path.insert(0, '/Users/hexavor/Desktop/PantheonAI/agents/base-agent/py-libp2p')

# Mock Relay Registry API
app = FastAPI()

# Storage for registered agents
registered_agents: Dict[str, Dict] = {}


@app.post("/register")
async def register_agent(payload: Dict):
    """Register an agent with the relay registry."""
    agent_name = payload.get("agent_name")
    peer_id = payload.get("peer_id")
    addrs = payload.get("addrs", [])
    
    if not all([agent_name, peer_id, addrs]):
        return {"error": "Missing required fields"}, 400
    
    registered_agents[peer_id] = {
        "agent_name": agent_name,
        "peer_id": peer_id,
        "addrs": addrs,
        "registered_at": time.time()
    }
    
    logger.info(f"Registered agent: {agent_name} with peer_id: {peer_id}")
    return {"status": "registered", "peer_id": peer_id}


@app.get("/peers")
async def list_peers():
    """List all registered peers."""
    return {"peers": list(registered_agents.values())}


async def run_mock_registry(port: int = 8081):
    """Run the mock relay registry."""
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def test_agent_registration():
    """Test that an agent can register with the registry."""
    # Import base_agent components
    from base_agent.p2p import setup_libp2p, shutdown_libp2p
    
    try:
        # Start libp2p and register
        await setup_libp2p()
        logger.info("Agent successfully started and registered")
        
        # Wait a bit to ensure registration is processed
        await asyncio.sleep(2)
        
        # Check if agent is registered
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8081/peers")
            data = resp.json()
            
            assert len(data["peers"]) > 0, "No agents registered"
            peer = data["peers"][0]
            assert "peer_id" in peer
            assert "addrs" in peer
            assert len(peer["addrs"]) > 0
            
            logger.info(f"Test passed! Agent registered with peer_id: {peer['peer_id']}")
            
    finally:
        # Cleanup
        await shutdown_libp2p()


async def main():
    """Main test runner."""
    # Start mock registry in background
    registry_task = asyncio.create_task(run_mock_registry())
    
    # Wait for registry to start
    await asyncio.sleep(2)
    
    try:
        # Run test
        await test_agent_registration()
        logger.info("All tests passed!")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        # Cancel registry task
        registry_task.cancel()
        try:
            await registry_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    # Configure logging
    logger.add(sys.stderr, level="INFO")
    
    # Run tests
    asyncio.run(main())
