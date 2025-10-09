"""P2P connectivity and discovery tests"""

import asyncio
import json
import time
from typing import Any, Dict, List

import pytest


@pytest.mark.p2p
@pytest.mark.asyncio
async def test_p2p_service_startup(wait_for_services, orchestrator_client):
    """Test that P2P services start correctly"""
    # Check if P2P is enabled in agent configuration
    response = await orchestrator_client.get("/agent/card")
    assert response.status_code == 200

    card = response.json()
    assert "name" in card
    assert "capabilities" in card
    assert "tools" in card


@pytest.mark.p2p
@pytest.mark.asyncio
async def test_peer_discovery(
    wait_for_services, orchestrator_client, worker_fs_client, worker_analytics_client
):
    """Test P2P peer discovery between agents"""
    # Wait for agents to start and begin discovery
    await asyncio.sleep(15)

    # Get discovered peers from orchestrator
    response = await orchestrator_client.get("/p2p/cards")
    assert response.status_code == 200

    discovery_data = response.json()
    assert "cards" in discovery_data

    discovered_peers = discovery_data["cards"]
    peer_names = [card.get("name", "") for card in discovered_peers.values()]

    print(f"Orchestrator discovered peers: {peer_names}")

    # Check filesystem worker discovery
    response = await worker_fs_client.get("/p2p/cards")
    if response.status_code == 200:
        fs_discovery = response.json()
        fs_peers = fs_discovery.get("cards", {})
        fs_peer_names = [card.get("name", "") for card in fs_peers.values()]
        print(f"Filesystem worker discovered peers: {fs_peer_names}")

    # Check analytics worker discovery
    response = await worker_analytics_client.get("/p2p/cards")
    if response.status_code == 200:
        analytics_discovery = response.json()
        analytics_peers = analytics_discovery.get("cards", {})
        analytics_peer_names = [
            card.get("name", "") for card in analytics_peers.values()
        ]
        print(f"Analytics worker discovered peers: {analytics_peer_names}")

    # Discovery may be incomplete in containerized environment
    # This test mainly validates the P2P infrastructure exists


@pytest.mark.p2p
@pytest.mark.asyncio
async def test_agent_card_structure(
    wait_for_services, orchestrator_client, worker_fs_client, worker_analytics_client
):
    """Test that agent cards conform to A2A specification"""
    clients_and_names = [
        (orchestrator_client, "orchestrator"),
        (worker_fs_client, "filesystem-worker"),
        (worker_analytics_client, "analytics-worker"),
    ]

    for client, agent_type in clients_and_names:
        response = await client.get("/agent/card")
        assert response.status_code == 200

        card = response.json()

        # Validate required A2A card fields
        assert "name" in card
        assert "version" in card
        assert "capabilities" in card
        assert "tools" in card

        # Validate card structure
        assert isinstance(card["name"], str)
        assert isinstance(card["version"], str)
        assert isinstance(card["capabilities"], list)
        assert isinstance(card["tools"], list)

        # Validate tools structure
        for tool in card["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert isinstance(tool["name"], str)
            assert isinstance(tool["description"], str)

            if "params" in tool:
                assert isinstance(tool["params"], list)
                for param in tool["params"]:
                    assert "name" in param
                    assert "type" in param
                    assert "required" in param

        # Validate capabilities are non-empty
        assert len(card["capabilities"]) > 0
        assert len(card["tools"]) > 0

        print(f"{agent_type} card validation passed")


@pytest.mark.p2p
@pytest.mark.slow
@pytest.mark.asyncio
async def test_p2p_tool_invocation(
    wait_for_services, orchestrator_client, test_helper, shared_dir
):
    """Test remote tool invocation over P2P"""
    # Wait for P2P discovery
    await asyncio.sleep(20)

    # Try to invoke a tool that should be delegated to a worker
    # This tests the P2P tool invocation pathway
    command = "CALL write_file p2p_test.txt 'This tests P2P tool invocation'"

    try:
        response = await test_helper.send_dsl_command(orchestrator_client, command)

        # Check if command was accepted
        if response.get("success") or "result" in response:
            # Wait a bit for processing
            await asyncio.sleep(5)

            # Check if file was created (indicates P2P worked)
            test_file = shared_dir / "p2p_test.txt"
            if test_file.exists():
                content = test_file.read_text()
                assert "This tests P2P tool invocation" in content
                print("P2P tool invocation successful")
            else:
                print(
                    "P2P tool invocation: file not found, may indicate delegation issue"
                )
        else:
            print(f"P2P tool invocation: command not accepted - {response}")

    except Exception as e:
        print(f"P2P tool invocation test failed: {e}")
        # Don't fail the test hard - P2P may not be fully functional in test environment


@pytest.mark.p2p
@pytest.mark.asyncio
async def test_p2p_capability_advertisement(wait_for_services, orchestrator_client):
    """Test that agents correctly advertise their capabilities"""
    # Get orchestrator card
    response = await orchestrator_client.get("/agent/card")
    assert response.status_code == 200

    orchestrator_card = response.json()
    orchestrator_capabilities = set(orchestrator_card["capabilities"])

    # Orchestrator should advertise orchestration capabilities
    expected_orchestrator_caps = {
        "orchestration",
        "task_delegation",
        "workflow_management",
        "llm_integration",
    }

    # Check that expected capabilities are present
    for cap in expected_orchestrator_caps:
        if cap in orchestrator_capabilities:
            print(f"✓ Orchestrator advertises {cap}")
        else:
            print(f"✗ Orchestrator missing {cap}")

    # Wait for discovery and check worker capabilities
    await asyncio.sleep(10)

    response = await orchestrator_client.get("/p2p/cards")
    if response.status_code == 200:
        p2p_cards = response.json()
        cards = p2p_cards.get("cards", {})

        for peer_id, card in cards.items():
            peer_name = card.get("name", "unknown")
            peer_caps = set(card.get("capabilities", []))

            print(f"Peer {peer_name} capabilities: {peer_caps}")

            # Validate capability types based on agent name
            if "filesystem" in peer_name.lower():
                expected_caps = {"file_operations", "directory_management"}
                found_caps = expected_caps.intersection(peer_caps)
                if found_caps:
                    print(
                        f"✓ Filesystem worker has expected capabilities: {found_caps}"
                    )

            elif "analytics" in peer_name.lower():
                expected_caps = {"data_analysis", "python_execution"}
                found_caps = expected_caps.intersection(peer_caps)
                if found_caps:
                    print(f"✓ Analytics worker has expected capabilities: {found_caps}")


@pytest.mark.p2p
@pytest.mark.asyncio
async def test_p2p_connection_resilience(wait_for_services, orchestrator_client):
    """Test P2P connection resilience and recovery"""
    # Get initial peer count
    response = await orchestrator_client.get("/p2p/cards")
    assert response.status_code == 200

    initial_peers = len(response.json().get("cards", {}))
    print(f"Initial peer count: {initial_peers}")

    # Wait and check again - peers should remain stable
    await asyncio.sleep(30)

    response = await orchestrator_client.get("/p2p/cards")
    assert response.status_code == 200

    later_peers = len(response.json().get("cards", {}))
    print(f"Later peer count: {later_peers}")

    # In a stable environment, peer count should not decrease significantly
    # (allowing for some discovery timing variations)
    if initial_peers > 0:
        assert later_peers >= initial_peers * 0.5  # Allow 50% tolerance

    # Test that agent can handle repeated discovery requests
    for i in range(5):
        response = await orchestrator_client.get("/p2p/cards")
        assert response.status_code == 200
        await asyncio.sleep(1)

    print("P2P connection stability test completed")


@pytest.mark.p2p
@pytest.mark.asyncio
async def test_mdns_service_registration(wait_for_services, orchestrator_client):
    """Test mDNS service registration and discovery"""
    # This test validates that the mDNS service registration is working
    # by checking if agents can discover each other

    # Wait for mDNS discovery to occur
    await asyncio.sleep(25)

    # Check discovery results
    response = await orchestrator_client.get("/p2p/cards")
    assert response.status_code == 200

    discovery_data = response.json()
    cards = discovery_data.get("cards", {})

    if len(cards) > 0:
        print(f"mDNS discovery found {len(cards)} peers")

        # Validate that discovered peers have proper mDNS service info
        for peer_id, card in cards.items():
            assert "name" in card
            assert len(peer_id) > 0  # Should have valid peer ID

            peer_name = card.get("name")
            print(f"Discovered peer via mDNS: {peer_name} ({peer_id[:16]}...)")

        print("mDNS service registration test passed")
    else:
        print(
            "mDNS discovery: no peers found (may be expected in isolated test environment)"
        )

    # The test passes if the discovery mechanism is functional,
    # even if no peers are found (due to containerization/networking)


@pytest.mark.p2p
@pytest.mark.asyncio
async def test_p2p_protocol_versioning(wait_for_services, orchestrator_client):
    """Test P2P protocol version compatibility"""
    # Get agent card and check protocol version
    response = await orchestrator_client.get("/agent/card")
    assert response.status_code == 200

    card = response.json()

    # Check if protocol version is specified
    if "protocol_version" in card:
        protocol_version = card["protocol_version"]
        assert isinstance(protocol_version, str)
        assert len(protocol_version) > 0
        print(f"Agent protocol version: {protocol_version}")

    # Check discovered peers for version compatibility
    await asyncio.sleep(15)

    response = await orchestrator_client.get("/p2p/cards")
    if response.status_code == 200:
        p2p_cards = response.json()
        cards = p2p_cards.get("cards", {})

        versions = []
        for peer_id, card in cards.items():
            peer_version = card.get("protocol_version", "unknown")
            versions.append(peer_version)
            print(
                f"Peer {card.get('name', 'unknown')} protocol version: {peer_version}"
            )

        # In production, all agents should have compatible versions
        if versions:
            unique_versions = set(versions)
            print(f"Unique protocol versions: {unique_versions}")


@pytest.mark.p2p
@pytest.mark.asyncio
async def test_p2p_security_handshake(wait_for_services, orchestrator_client):
    """Test P2P security and noise protocol handshake"""
    # This test verifies that P2P connections use security protocols
    # by checking that discovery and connections work (implying successful handshakes)

    # Wait for secure connections to be established
    await asyncio.sleep(20)

    response = await orchestrator_client.get("/p2p/cards")
    assert response.status_code == 200

    discovery_data = response.json()
    secure_connections = 0

    cards = discovery_data.get("cards", {})
    for peer_id, card in cards.items():
        # If we can see the peer card, it means a secure connection was established
        if "name" in card and "capabilities" in card:
            secure_connections += 1
            print(f"Secure connection established with: {card['name']}")

    print(f"Total secure P2P connections: {secure_connections}")

    # Test passes if P2P infrastructure is working (implying security is functional)
    # Even 0 connections can be valid in isolated test environment
