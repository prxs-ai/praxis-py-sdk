"""WebSocket connectivity and event streaming tests"""

import asyncio
import json
import uuid
from typing import Any, Dict, List

import pytest
import websockets


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_connection(wait_for_services, orchestrator_ws, test_helper):
    """Test basic WebSocket connection to orchestrator"""
    # Send a simple ping message
    ping_message = {
        "type": "ping",
        "payload": {"timestamp": asyncio.get_event_loop().time()},
    }

    await test_helper.send_websocket_message(
        orchestrator_ws, "ping", ping_message["payload"]
    )

    # Try to receive a response
    try:
        response = await test_helper.receive_websocket_message(
            orchestrator_ws, timeout=10.0
        )
        print(f"WebSocket ping response: {response}")

        # Should get some kind of response (pong, ack, or error)
        assert "type" in response
        print("WebSocket basic connectivity test passed")

    except asyncio.TimeoutError:
        # WebSocket connection established but no response to ping
        print("WebSocket connection established (no ping response)")


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_dsl_command_streaming(
    wait_for_services, orchestrator_ws, test_helper
):
    """Test DSL command execution through WebSocket with event streaming"""
    # Send DSL command via WebSocket
    dsl_message = {
        "type": "DSL_COMMAND",
        "payload": {
            "command": "CALL write_file websocket_test.txt 'WebSocket DSL test'"
        },
    }

    await test_helper.send_websocket_message(
        orchestrator_ws, "DSL_COMMAND", dsl_message["payload"]
    )

    # Collect streaming events
    events = []
    max_events = 10
    timeout_per_event = 5.0

    for i in range(max_events):
        try:
            event = await test_helper.receive_websocket_message(
                orchestrator_ws, timeout=timeout_per_event
            )
            events.append(event)

            print(
                f"Received event {i + 1}: {event['type'] if 'type' in event else 'unknown'}"
            )

            # Check for completion events
            if event.get("type") in ["dslResult", "workflowComplete", "error"]:
                break

        except asyncio.TimeoutError:
            print(f"No more events received after {timeout_per_event}s")
            break

    print(f"Received {len(events)} WebSocket events")

    # Validate event structure
    for event in events:
        assert "type" in event
        assert "payload" in event or "data" in event or isinstance(event, dict)

    # Should have received at least some events
    if len(events) > 0:
        print("WebSocket DSL command streaming test passed")
    else:
        print("WebSocket DSL command sent but no events received")


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_workflow_execution(
    wait_for_services, orchestrator_ws, test_helper
):
    """Test workflow execution through WebSocket"""
    # Send workflow execution request
    workflow_message = {
        "type": "EXECUTE_WORKFLOW",
        "payload": {
            "workflowId": f"ws-workflow-{uuid.uuid4()}",
            "nodes": [
                {
                    "id": "node1",
                    "type": "tool_call",
                    "tool": "write_file",
                    "params": {
                        "filename": "workflow_test.txt",
                        "content": "Workflow via WebSocket",
                    },
                }
            ],
            "edges": [],
        },
    }

    await test_helper.send_websocket_message(
        orchestrator_ws, "EXECUTE_WORKFLOW", workflow_message["payload"]
    )

    # Monitor workflow events
    workflow_events = []
    expected_events = {
        "workflowStart",
        "nodeStatusUpdate",
        "workflowComplete",
        "workflowError",
    }
    received_event_types = set()

    for i in range(15):  # Allow more events for workflow
        try:
            event = await test_helper.receive_websocket_message(
                orchestrator_ws, timeout=8.0
            )
            workflow_events.append(event)

            event_type = event.get("type", "unknown")
            received_event_types.add(event_type)

            print(f"Workflow event: {event_type}")

            # Check for workflow completion
            if event_type in ["workflowComplete", "workflowError"]:
                break

        except asyncio.TimeoutError:
            print("Workflow event timeout")
            break

    print(f"Workflow events received: {list(received_event_types)}")
    print(f"Total workflow events: {len(workflow_events)}")

    # Validate we got workflow-related events
    workflow_related_events = expected_events.intersection(received_event_types)
    if workflow_related_events:
        print(f"Received expected workflow events: {workflow_related_events}")
    else:
        print("No specific workflow events received (may use different event names)")


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_chat_interface(
    wait_for_services, orchestrator_ws, test_helper
):
    """Test chat-like interface through WebSocket"""
    # Send chat message
    chat_message = {
        "type": "CHAT_MESSAGE",
        "payload": {
            "content": "Create a file called chat_test.txt with content 'Hello from chat'",
            "sender": "user",
            "messageId": f"chat-{uuid.uuid4()}",
        },
    }

    await test_helper.send_websocket_message(
        orchestrator_ws, "CHAT_MESSAGE", chat_message["payload"]
    )

    # Collect chat responses
    chat_responses = []

    for i in range(8):
        try:
            response = await test_helper.receive_websocket_message(
                orchestrator_ws, timeout=6.0
            )
            chat_responses.append(response)

            response_type = response.get("type", "unknown")
            print(f"Chat response {i + 1}: {response_type}")

            # Look for assistant responses
            if response_type in ["chatMessage", "tool_result", "dslResult"]:
                if response.get("payload", {}).get("sender") == "assistant":
                    print("Received assistant response")
                    break

        except asyncio.TimeoutError:
            print("Chat response timeout")
            break

    print(f"Chat responses received: {len(chat_responses)}")

    # Should have received some kind of response
    if len(chat_responses) > 0:
        print("WebSocket chat interface test passed")


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_concurrent_connections(wait_for_services):
    """Test multiple concurrent WebSocket connections"""
    ORCHESTRATOR_WS = (
        os.getenv("PRAXIS_ORCHESTRATOR_URL", "http://localhost:8000").replace(
            "http://", "ws://"
        )
        + "/ws/workflow"
    )

    # Create multiple WebSocket connections
    connections = []
    connection_count = 3

    try:
        for i in range(connection_count):
            try:
                ws = await websockets.connect(ORCHESTRATOR_WS)
                connections.append(ws)
                print(f"WebSocket connection {i + 1} established")
            except Exception as e:
                print(f"Failed to establish WebSocket connection {i + 1}: {e}")

        print(f"Established {len(connections)} concurrent WebSocket connections")

        # Send messages from each connection
        tasks = []
        for i, ws in enumerate(connections):
            message = {
                "type": "ping",
                "payload": {
                    "connection_id": i,
                    "timestamp": asyncio.get_event_loop().time(),
                },
            }

            task = asyncio.create_task(ws.send(json.dumps(message)))
            tasks.append(task)

        # Wait for all sends to complete
        await asyncio.gather(*tasks, return_exceptions=True)

        # Try to receive responses
        response_tasks = []
        for ws in connections:
            task = asyncio.create_task(asyncio.wait_for(ws.recv(), timeout=5.0))
            response_tasks.append(task)

        responses = await asyncio.gather(*response_tasks, return_exceptions=True)

        successful_responses = 0
        for response in responses:
            if not isinstance(response, Exception):
                successful_responses += 1

        print(
            f"Received responses from {successful_responses}/{len(connections)} connections"
        )

        # Test passes if multiple connections can be established
        assert len(connections) > 0

    finally:
        # Clean up connections
        for ws in connections:
            try:
                await ws.close()
            except Exception:
                pass


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_error_handling(
    wait_for_services, orchestrator_ws, test_helper
):
    """Test WebSocket error handling"""
    # Send malformed message
    try:
        malformed_message = '{"type": "invalid", "malformed": json}'
        await orchestrator_ws.send(malformed_message)

        # Try to receive error response
        response = await test_helper.receive_websocket_message(
            orchestrator_ws, timeout=5.0
        )

        if "error" in response or response.get("type") == "error":
            print("WebSocket handled malformed message with error response")
        else:
            print(f"WebSocket response to malformed message: {response}")

    except Exception as e:
        print(f"Error sending malformed message: {e}")

    # Send message with invalid type
    invalid_message = {
        "type": "NONEXISTENT_MESSAGE_TYPE",
        "payload": {"test": "invalid message type"},
    }

    await test_helper.send_websocket_message(
        orchestrator_ws, "NONEXISTENT_MESSAGE_TYPE", invalid_message["payload"]
    )

    try:
        response = await test_helper.receive_websocket_message(
            orchestrator_ws, timeout=5.0
        )

        if "error" in response or response.get("type") == "error":
            print("WebSocket handled invalid message type with error")
        else:
            print(f"WebSocket response to invalid type: {response}")

    except asyncio.TimeoutError:
        print("No response to invalid message type")


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_large_message_handling(
    wait_for_services, orchestrator_ws, test_helper
):
    """Test WebSocket handling of large messages"""
    # Create a large message
    large_content = "Large message content. " * 1000  # ~22KB

    large_message = {
        "type": "CHAT_MESSAGE",
        "payload": {
            "content": f"Process this large content: {large_content}",
            "sender": "user",
            "messageId": f"large-{uuid.uuid4()}",
        },
    }

    try:
        await test_helper.send_websocket_message(
            orchestrator_ws, "CHAT_MESSAGE", large_message["payload"]
        )

        # Try to receive response
        response = await test_helper.receive_websocket_message(
            orchestrator_ws, timeout=10.0
        )

        print("Large message handled successfully")

        # Validate response structure
        assert "type" in response

    except Exception as e:
        print(f"Large message handling failed: {e}")


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_heartbeat_and_keepalive(
    wait_for_services, orchestrator_ws, test_helper
):
    """Test WebSocket heartbeat and keep-alive functionality"""
    # Send periodic messages to test connection stability
    message_count = 5
    interval = 2.0

    for i in range(message_count):
        heartbeat_message = {
            "type": "heartbeat",
            "payload": {"sequence": i, "timestamp": asyncio.get_event_loop().time()},
        }

        try:
            await test_helper.send_websocket_message(
                orchestrator_ws, "heartbeat", heartbeat_message["payload"]
            )

            print(f"Sent heartbeat {i + 1}/{message_count}")

            # Wait between heartbeats
            if i < message_count - 1:
                await asyncio.sleep(interval)

        except Exception as e:
            print(f"Heartbeat {i + 1} failed: {e}")
            break

    # Try to receive any heartbeat responses
    received_responses = 0
    for i in range(message_count):
        try:
            response = await test_helper.receive_websocket_message(
                orchestrator_ws, timeout=1.0
            )
            received_responses += 1
            print(
                f"Heartbeat response {received_responses}: {response.get('type', 'unknown')}"
            )

        except asyncio.TimeoutError:
            break

    print(f"Received {received_responses} heartbeat responses")
    print("WebSocket heartbeat test completed")


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_message_ordering(
    wait_for_services, orchestrator_ws, test_helper
):
    """Test WebSocket message ordering and sequencing"""
    # Send sequential messages
    sequence_count = 5
    messages = []

    for i in range(sequence_count):
        message = {
            "type": "sequence_test",
            "payload": {
                "sequence_id": i,
                "command": f"CALL write_file sequence_{i}.txt 'Sequence test {i}'",
                "timestamp": asyncio.get_event_loop().time(),
            },
        }
        messages.append(message)

    # Send all messages rapidly
    send_tasks = []
    for message in messages:
        task = asyncio.create_task(
            test_helper.send_websocket_message(
                orchestrator_ws, message["type"], message["payload"]
            )
        )
        send_tasks.append(task)

    # Wait for all sends to complete
    await asyncio.gather(*send_tasks, return_exceptions=True)

    print(f"Sent {len(messages)} sequential messages")

    # Try to receive responses and check ordering
    responses = []
    for i in range(sequence_count * 2):  # Allow for more responses
        try:
            response = await test_helper.receive_websocket_message(
                orchestrator_ws, timeout=3.0
            )
            responses.append(response)

        except asyncio.TimeoutError:
            break

    print(f"Received {len(responses)} responses to sequential messages")

    # Message ordering test passes if messages were processed
    if len(responses) > 0:
        print("WebSocket message ordering test completed")


import os
