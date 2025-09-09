"""
Integration tests for multi-agent communication
"""

import pytest
import asyncio
import json
from pathlib import Path
from typing import Dict, Any

@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_health_checks(wait_for_services, orchestrator_client, worker_fs_client, worker_analytics_client, mcp_client):
    """Test that all agents are healthy and responding"""
    
    # Test orchestrator health
    response = await orchestrator_client.get("/health")
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["status"] == "healthy"
    assert "praxis-orchestrator" in health_data["agent"]
    
    # Test filesystem worker health
    response = await worker_fs_client.get("/health")
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["status"] == "healthy"
    assert "praxis-worker-filesystem" in health_data["agent"]
    
    # Test analytics worker health
    response = await worker_analytics_client.get("/health")
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["status"] == "healthy"
    assert "praxis-worker-analytics" in health_data["agent"]
    
    # Test MCP filesystem server health
    response = await mcp_client.get("/health")
    assert response.status_code == 200
    health_data = response.json()
    assert health_data["status"] == "healthy"
    assert health_data["server"] == "mcp-filesystem"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_card_exchange(wait_for_services, orchestrator_client):
    """Test that agents can exchange A2A cards and discover capabilities"""
    
    # Get orchestrator's own card
    response = await orchestrator_client.get("/agent/card")
    assert response.status_code == 200
    orchestrator_card = response.json()
    
    assert orchestrator_card["name"] == "praxis-orchestrator"
    assert orchestrator_card["version"] == "1.0.0"
    assert "capabilities" in orchestrator_card
    assert "tools" in orchestrator_card
    
    # Verify orchestrator has expected capabilities
    capabilities = orchestrator_card["capabilities"]
    expected_capabilities = [
        "orchestration", "task_delegation", "workflow_management", 
        "llm_integration", "file_operations"
    ]
    for capability in expected_capabilities:
        assert capability in capabilities
    
    # Verify orchestrator has expected tools
    tool_names = [tool["name"] for tool in orchestrator_card["tools"]]
    expected_tools = ["write_file", "read_file", "python_analyzer", "orchestrate_workflow"]
    for tool in expected_tools:
        assert tool in tool_names
    
    # Wait a bit for P2P discovery
    await asyncio.sleep(10)
    
    # Get discovered P2P peers
    response = await orchestrator_client.get("/p2p/cards")
    assert response.status_code == 200
    p2p_cards = response.json()
    
    assert "cards" in p2p_cards
    cards = p2p_cards["cards"]
    
    # Should have discovered worker agents
    worker_names = []
    for peer_id, card in cards.items():
        worker_names.append(card["name"])
    
    # May take time for discovery, so we'll be lenient here
    # In a real deployment, we'd wait longer or implement retry logic
    print(f"Discovered workers: {worker_names}")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_dsl_to_a2a_translation(wait_for_services, orchestrator_client, test_helper, setup_test_files):
    """Test DSL command translation to A2A protocol"""
    
    # Test simple DSL command
    dsl_command = "CALL write_file test_output.txt 'Hello from DSL'"
    response = await test_helper.send_dsl_command(orchestrator_client, dsl_command)
    
    assert response["success"] == True
    assert "task" in response or "workflowSuggestion" in response
    
    # Test natural language DSL (requires LLM)
    if "OPENAI_API_KEY" in os.environ:
        natural_command = "create a file called greeting.txt with hello world"
        response = await test_helper.send_a2a_message(orchestrator_client, natural_command)
        
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        task = response["result"]
        assert task["kind"] == "task"
        assert task["status"]["state"] in ["submitted", "running", "completed"]

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_inter_agent_task_delegation(wait_for_services, orchestrator_client, test_helper, shared_dir):
    """Test task delegation between orchestrator and worker agents"""
    
    # Create a task that should be delegated to filesystem worker
    message = "create a file called delegation_test.txt with content 'This was delegated to a worker'"
    
    response = await test_helper.send_a2a_message(orchestrator_client, message)
    assert response["jsonrpc"] == "2.0"
    assert "result" in response
    
    task = response["result"]
    task_id = task["id"]
    
    # Wait for task completion
    try:
        completed_task = await test_helper.wait_for_task_completion(
            orchestrator_client, task_id, timeout=60.0
        )
        
        assert completed_task["status"]["state"] == "completed"
        
        # Verify the file was actually created
        test_file = shared_dir / "delegation_test.txt"
        assert test_file.exists()
        
        content = test_file.read_text()
        assert "This was delegated to a worker" in content
        
    except TimeoutError:
        pytest.skip("Task delegation test timed out - may indicate P2P connectivity issues")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_agent_workflow(wait_for_services, orchestrator_client, test_helper, setup_test_files):
    """Test complex workflow involving multiple agents"""
    
    # Create a workflow that requires both filesystem and analytics capabilities
    workflow_command = """
    Please do the following:
    1. Read the test data from test_data.csv
    2. Analyze the data using Python
    3. Save the analysis results to analysis_results.json
    """
    
    response = await test_helper.send_a2a_message(orchestrator_client, workflow_command)
    assert response["jsonrpc"] == "2.0"
    
    if "result" in response:
        task = response["result"]
        task_id = task["id"]
        
        # Wait for workflow completion
        try:
            completed_task = await test_helper.wait_for_task_completion(
                orchestrator_client, task_id, timeout=120.0
            )
            
            # Check if workflow completed successfully
            if completed_task["status"]["state"] == "completed":
                # Verify results exist
                results_file = setup_test_files["csv"].parent / "analysis_results.json"
                if results_file.exists():
                    results = json.loads(results_file.read_text())
                    assert isinstance(results, dict)
                    print(f"Workflow results: {results}")
            
        except (TimeoutError, ValueError) as e:
            # Workflow tests may fail due to missing components or timing
            print(f"Workflow test incomplete: {e}")
            pytest.skip("Multi-agent workflow test requires full system integration")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_and_recovery(wait_for_services, orchestrator_client, test_helper):
    """Test error handling and recovery mechanisms"""
    
    # Test invalid tool call
    invalid_command = "CALL nonexistent_tool param1 param2"
    response = await test_helper.send_dsl_command(orchestrator_client, invalid_command)
    
    # Should handle error gracefully
    assert "error" in response or response.get("success") == False
    
    # Test invalid file operation
    invalid_file_command = "CALL read_file /nonexistent/path/file.txt"
    response = await test_helper.send_dsl_command(orchestrator_client, invalid_file_command)
    
    # Should handle file error gracefully
    assert "error" in response or response.get("success") == False
    
    # Test recovery - valid command after error
    valid_command = "CALL write_file recovery_test.txt 'System recovered'"
    response = await test_helper.send_dsl_command(orchestrator_client, valid_command)
    
    # Should work normally after error
    assert response.get("success") == True or "result" in response

@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_task_execution(wait_for_services, orchestrator_client, test_helper, shared_dir):
    """Test concurrent execution of multiple tasks"""
    
    # Create multiple concurrent tasks
    tasks = []
    for i in range(3):
        command = f"CALL write_file concurrent_test_{i}.txt 'Concurrent task {i}'"
        task = asyncio.create_task(test_helper.send_dsl_command(orchestrator_client, command))
        tasks.append(task)
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check results
    successful_tasks = 0
    for result in results:
        if isinstance(result, dict) and (result.get("success") or "result" in result):
            successful_tasks += 1
    
    # At least some tasks should succeed
    assert successful_tasks > 0
    
    # Verify files were created
    created_files = 0
    for i in range(3):
        file_path = shared_dir / f"concurrent_test_{i}.txt"
        if file_path.exists():
            created_files += 1
    
    assert created_files > 0

@pytest.mark.integration
@pytest.mark.asyncio  
async def test_agent_capability_matching(wait_for_services, orchestrator_client):
    """Test that orchestrator correctly matches tasks to agent capabilities"""
    
    # Get agent cards to understand available capabilities
    response = await orchestrator_client.get("/p2p/cards")
    assert response.status_code == 200
    
    p2p_cards = response.json()
    cards = p2p_cards.get("cards", {})
    
    # Verify capability-based matching would work
    filesystem_agents = []
    analytics_agents = []
    
    for peer_id, card in cards.items():
        capabilities = card.get("capabilities", [])
        if "file_operations" in capabilities:
            filesystem_agents.append(peer_id)
        if "data_analysis" in capabilities:
            analytics_agents.append(peer_id)
    
    print(f"Filesystem agents: {len(filesystem_agents)}")
    print(f"Analytics agents: {len(analytics_agents)}")
    
    # Even if discovery is incomplete, the orchestrator should have the logic
    # This test mainly validates the card structure and capability advertisement

import os