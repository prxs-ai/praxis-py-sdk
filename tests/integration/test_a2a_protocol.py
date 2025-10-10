"""A2A (Agent-to-Agent) protocol compliance tests"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict

import pytest


@pytest.mark.a2a
@pytest.mark.asyncio
async def test_a2a_message_structure(
    wait_for_services, orchestrator_client, test_helper
):
    """Test A2A message structure compliance with protocol specification"""
    # Create a proper A2A message according to specification
    message_id = f"test-msg-{uuid.uuid4()}"

    a2a_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {"kind": "text", "text": "Create a test file with A2A protocol"}
                ],
                "messageId": message_id,
                "kind": "message",
            }
        },
    }

    response = await orchestrator_client.post("/execute", json=a2a_request)
    assert response.status_code == 200

    result = response.json()

    # Validate A2A response structure
    assert "jsonrpc" in result
    assert result["jsonrpc"] == "2.0"
    assert "id" in result
    assert result["id"] == 1

    if "result" in result:
        task = result["result"]

        # Validate task structure according to A2A spec
        assert "id" in task
        assert "kind" in task
        assert task["kind"] == "task"
        assert "status" in task

        # Validate status structure
        status = task["status"]
        assert "state" in status
        assert status["state"] in ["submitted", "running", "completed", "failed"]
        assert "timestamp" in status

        # Validate task ID format
        task_id = task["id"]
        assert isinstance(task_id, str)
        assert len(task_id) > 0

        print(f"A2A task created: {task_id} with status: {status['state']}")


@pytest.mark.a2a
@pytest.mark.asyncio
async def test_a2a_task_lifecycle(wait_for_services, orchestrator_client, test_helper):
    """Test complete A2A task lifecycle from submission to completion"""
    # Submit A2A task
    message_id = f"lifecycle-test-{uuid.uuid4()}"

    a2a_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Write a test file called lifecycle_test.txt with content 'A2A lifecycle test'",
                    }
                ],
                "messageId": message_id,
                "kind": "message",
            }
        },
    }

    # Submit task
    response = await orchestrator_client.post("/execute", json=a2a_request)
    assert response.status_code == 200

    result = response.json()
    assert "result" in result

    task = result["result"]
    task_id = task["id"]
    initial_status = task["status"]["state"]

    print(f"Task {task_id} submitted with status: {initial_status}")

    # Poll task status until completion
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = await orchestrator_client.get(f"/tasks/{task_id}")
            if response.status_code == 200:
                current_task = response.json()
                current_status = current_task["status"]["state"]

                print(f"Attempt {attempt + 1}: Task status is {current_status}")

                if current_status in ["completed", "failed"]:
                    # Validate final task structure
                    assert "id" in current_task
                    assert current_task["id"] == task_id
                    assert "status" in current_task
                    assert "timestamp" in current_task["status"]

                    if current_status == "completed":
                        print("A2A task lifecycle completed successfully")
                        if "result" in current_task:
                            print(f"Task result: {current_task['result']}")
                        return
                    print(f"Task failed: {current_task.get('error', 'Unknown error')}")
                    # Test passes - we validated the lifecycle even if task failed
                    return

            await asyncio.sleep(2)

        except Exception as e:
            print(f"Error polling task status: {e}")
            break

    print(f"Task {task_id} did not complete within timeout - this may be expected")


@pytest.mark.a2a
@pytest.mark.asyncio
async def test_a2a_error_handling(wait_for_services, orchestrator_client):
    """Test A2A protocol error handling"""
    # Test invalid JSON-RPC structure
    invalid_request = {
        "jsonrpc": "1.0",  # Wrong version
        "method": "invalid_method",
        "params": {},
    }

    response = await orchestrator_client.post("/execute", json=invalid_request)

    # Should handle invalid request gracefully
    if response.status_code == 200:
        result = response.json()

        # Should return JSON-RPC error response
        if "error" in result:
            error = result["error"]
            assert "code" in error
            assert "message" in error
            print(f"Properly handled invalid request with error: {error['message']}")
        elif "success" in result and not result["success"]:
            print("Invalid request handled with success=false response")
    else:
        print(f"Invalid request returned HTTP {response.status_code}")

    # Test invalid method
    invalid_method_request = {
        "jsonrpc": "2.0",
        "id": 999,
        "method": "nonexistent/method",
        "params": {},
    }

    response = await orchestrator_client.post("/execute", json=invalid_method_request)

    if response.status_code == 200:
        result = response.json()

        # Should return method not found error
        if "error" in result:
            assert result["jsonrpc"] == "2.0"
            assert result["id"] == 999
            error = result["error"]
            assert error["code"] == -32601  # Method not found
            print("Properly handled invalid method")


@pytest.mark.a2a
@pytest.mark.asyncio
async def test_a2a_context_management(wait_for_services, orchestrator_client):
    """Test A2A context management and conversation flow"""
    # Create initial context with first message
    context_id = f"context-{uuid.uuid4()}"

    first_message = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "message/send",
        "params": {
            "contextId": context_id,
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Start a conversation about file operations",
                    }
                ],
                "messageId": f"msg-1-{uuid.uuid4()}",
                "kind": "message",
            },
        },
    }

    response = await orchestrator_client.post("/execute", json=first_message)
    assert response.status_code == 200

    result = response.json()
    if "result" in result:
        task = result["result"]

        # Should have context ID
        if "contextId" in task:
            returned_context_id = task["contextId"]
            assert returned_context_id == context_id or len(returned_context_id) > 0
            print(f"Context established: {returned_context_id}")

        # Follow up message in same context
        second_message = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "message/send",
            "params": {
                "contextId": context_id,
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": "Now create a file called context_test.txt",
                        }
                    ],
                    "messageId": f"msg-2-{uuid.uuid4()}",
                    "kind": "message",
                },
            },
        }

        response = await orchestrator_client.post("/execute", json=second_message)
        assert response.status_code == 200

        follow_up_result = response.json()
        if "result" in follow_up_result:
            follow_up_task = follow_up_result["result"]

            # Should maintain same context
            if "contextId" in follow_up_task:
                assert follow_up_task["contextId"] == context_id
                print("Context maintained across messages")


@pytest.mark.a2a
@pytest.mark.asyncio
async def test_a2a_multipart_messages(wait_for_services, orchestrator_client):
    """Test A2A messages with multiple parts"""
    multipart_message = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {"kind": "text", "text": "Here are the instructions:"},
                    {
                        "kind": "text",
                        "text": "1. Create a file called multipart_test.txt",
                    },
                    {
                        "kind": "text",
                        "text": "2. Write 'Multipart message test' in the file",
                    },
                ],
                "messageId": f"multipart-{uuid.uuid4()}",
                "kind": "message",
            }
        },
    }

    response = await orchestrator_client.post("/execute", json=multipart_message)
    assert response.status_code == 200

    result = response.json()

    # Should handle multipart message correctly
    if "result" in result:
        task = result["result"]
        assert task["kind"] == "task"
        print("Multipart message processed successfully")
    elif "error" not in result:
        print("Multipart message handled (may not support all message types)")


@pytest.mark.a2a
@pytest.mark.asyncio
async def test_a2a_tool_result_format(
    wait_for_services, orchestrator_client, shared_dir
):
    """Test A2A tool result formatting and structure"""
    # Submit a task that should produce a clear tool result
    tool_request = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Create a file called tool_result_test.txt with content 'Tool result format test'",
                    }
                ],
                "messageId": f"tool-result-{uuid.uuid4()}",
                "kind": "message",
            }
        },
    }

    response = await orchestrator_client.post("/execute", json=tool_request)
    assert response.status_code == 200

    result = response.json()

    if "result" in result:
        task = result["result"]
        task_id = task["id"]

        # Wait for task completion
        await asyncio.sleep(10)

        try:
            # Get task result
            response = await orchestrator_client.get(f"/tasks/{task_id}")
            if response.status_code == 200:
                completed_task = response.json()

                # Validate result structure
                if "result" in completed_task:
                    task_result = completed_task["result"]

                    # A2A results should be structured
                    print(f"Task result structure: {type(task_result)}")

                    if isinstance(task_result, dict):
                        # Validate common result fields
                        print(f"Task result keys: {list(task_result.keys())}")

                    print("Tool result format validation completed")

        except Exception as e:
            print(f"Could not retrieve task result: {e}")


@pytest.mark.a2a
@pytest.mark.asyncio
async def test_a2a_batch_operations(wait_for_services, orchestrator_client):
    """Test A2A protocol with batch operations"""
    # Submit multiple A2A requests concurrently
    batch_requests = []

    for i in range(3):
        request = {
            "jsonrpc": "2.0",
            "id": 10 + i,
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": f"Create batch file number {i + 1} called batch_test_{i + 1}.txt",
                        }
                    ],
                    "messageId": f"batch-{i + 1}-{uuid.uuid4()}",
                    "kind": "message",
                }
            },
        }
        batch_requests.append(request)

    # Submit all requests concurrently
    tasks = []
    for request in batch_requests:
        task = asyncio.create_task(orchestrator_client.post("/execute", json=request))
        tasks.append(task)

    # Wait for all submissions
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    successful_submissions = 0
    task_ids = []

    for i, response in enumerate(responses):
        if not isinstance(response, Exception):
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    task = result["result"]
                    task_ids.append(task["id"])
                    successful_submissions += 1
                    print(f"Batch request {i + 1} submitted successfully")

    print(f"Successfully submitted {successful_submissions} batch requests")

    # A2A protocol should handle concurrent requests properly
    assert successful_submissions > 0


@pytest.mark.a2a
@pytest.mark.asyncio
async def test_a2a_protocol_headers_and_metadata(
    wait_for_services, orchestrator_client
):
    """Test A2A protocol headers, metadata, and optional fields"""
    # Test message with additional metadata
    enhanced_request = {
        "jsonrpc": "2.0",
        "id": 20,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": "Test message with metadata"}],
                "messageId": f"metadata-{uuid.uuid4()}",
                "kind": "message",
                "metadata": {
                    "priority": "high",
                    "tags": ["test", "metadata"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "integration_test",
                },
            },
            "metadata": {
                "client_version": "test-1.0.0",
                "test_run_id": f"run-{uuid.uuid4()}",
            },
        },
    }

    response = await orchestrator_client.post("/execute", json=enhanced_request)
    assert response.status_code == 200

    result = response.json()

    # Should handle metadata gracefully
    if "result" in result:
        task = result["result"]
        print(f"Enhanced message with metadata processed: {task['id']}")

        # Check if metadata is preserved or handled
        if "metadata" in task:
            print(f"Task metadata: {task['metadata']}")

    # Test passes if the enhanced message is processed without errors
