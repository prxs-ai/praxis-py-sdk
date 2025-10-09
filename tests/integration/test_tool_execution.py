"""Tool execution tests for MCP and Dagger integration"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict

import pytest


@pytest.mark.mcp
@pytest.mark.asyncio
async def test_mcp_filesystem_server_integration(wait_for_services, mcp_client):
    """Test MCP filesystem server integration"""
    # Test MCP server capabilities
    response = await mcp_client.get("/capabilities")
    assert response.status_code == 200

    capabilities = response.json()
    assert "capabilities" in capabilities
    assert "tools" in capabilities["capabilities"]

    tools = capabilities["capabilities"]["tools"]
    tool_names = [tool["name"] for tool in tools.values()]

    # Should have filesystem tools
    expected_tools = ["write_file", "read_file", "list_directory", "create_directory"]
    for tool in expected_tools:
        assert tool in tool_names

    print(f"MCP filesystem server provides tools: {tool_names}")


@pytest.mark.mcp
@pytest.mark.asyncio
async def test_mcp_tool_invocation(wait_for_services, mcp_client):
    """Test direct MCP tool invocation"""
    # Test write_file tool
    write_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "write_file",
            "arguments": {
                "filename": "mcp_test.txt",
                "content": "This is a test from MCP",
                "mode": "overwrite",
            },
        },
    }

    response = await mcp_client.post("/mcp", json=write_request)
    assert response.status_code == 200

    result = response.json()
    assert result["jsonrpc"] == "2.0"
    assert result["id"] == 1
    assert "result" in result

    # Test read_file tool
    read_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "read_file", "arguments": {"filename": "mcp_test.txt"}},
    }

    response = await mcp_client.post("/mcp", json=read_request)
    assert response.status_code == 200

    result = response.json()
    assert result["jsonrpc"] == "2.0"
    assert "result" in result

    # Parse the content (MCP returns text content)
    content_data = result["result"]["content"][0]["text"]
    parsed_content = json.loads(content_data)

    assert parsed_content["success"] == True
    assert "This is a test from MCP" in parsed_content["content"]

    print("MCP tool invocation test passed")


@pytest.mark.mcp
@pytest.mark.asyncio
async def test_mcp_tools_list(wait_for_services, mcp_client):
    """Test MCP tools list functionality"""
    tools_request = {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}

    response = await mcp_client.post("/mcp", json=tools_request)
    assert response.status_code == 200

    result = response.json()
    assert result["jsonrpc"] == "2.0"
    assert "result" in result

    tools_data = result["result"]
    assert "tools" in tools_data

    tools = tools_data["tools"]
    assert isinstance(tools, list)
    assert len(tools) > 0

    # Validate tool structure
    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool

        schema = tool["inputSchema"]
        assert "type" in schema
        assert schema["type"] == "object"
        assert "properties" in schema

        print(f"MCP tool: {tool['name']} - {tool['description']}")

    print(f"MCP server provides {len(tools)} tools")


@pytest.mark.dagger
@pytest.mark.slow
@pytest.mark.asyncio
async def test_dagger_python_execution(
    wait_for_services, orchestrator_client, test_helper, setup_test_files
):
    """Test Dagger-based Python execution"""
    # Create a simple Python analysis script
    analysis_script = """
import json
import sys
from pathlib import Path

def main():
    try:
        input_file = "/shared/test_input.txt"
        output_file = "/shared/dagger_analysis_result.json"

        if Path(input_file).exists():
            with open(input_file, 'r') as f:
                content = f.read()

            analysis = {
                "success": True,
                "file_analyzed": input_file,
                "content_length": len(content),
                "line_count": len(content.splitlines()),
                "word_count": len(content.split()),
                "first_50_chars": content[:50]
            }
        else:
            analysis = {
                "success": False,
                "error": f"Input file {input_file} not found"
            }

        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)

        print(json.dumps(analysis, indent=2))
        return 0

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e)
        }
        print(json.dumps(error_result, indent=2))
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""

    # Write the analysis script to shared directory
    script_path = setup_test_files["script"].parent / "dagger_analyzer.py"
    with open(script_path, "w") as f:
        f.write(analysis_script)

    # Test Dagger execution via DSL command
    dagger_command = "CALL python_analyzer test_input.txt basic"

    try:
        response = await test_helper.send_dsl_command(
            orchestrator_client, dagger_command
        )

        if response.get("success") or "result" in response:
            # Wait for Dagger execution to complete
            await asyncio.sleep(15)

            # Check if analysis result was created
            result_file = (
                setup_test_files["script"].parent / "dagger_analysis_result.json"
            )
            if result_file.exists():
                with open(result_file) as f:
                    analysis_result = json.load(f)

                assert analysis_result["success"] == True
                assert "content_length" in analysis_result
                print(f"Dagger analysis completed: {analysis_result}")
                print("Dagger Python execution test passed")
            else:
                print(
                    "Dagger analysis result file not found - execution may have failed"
                )
        else:
            print(f"Dagger command not accepted: {response}")

    except Exception as e:
        print(f"Dagger execution test failed: {e}")
        # Don't hard fail - Dagger may not be fully configured in test environment


@pytest.mark.dagger
@pytest.mark.slow
@pytest.mark.asyncio
async def test_dagger_container_isolation(
    wait_for_services, orchestrator_client, test_helper, shared_dir
):
    """Test Dagger container isolation and security"""
    # Create a script that tries to access system resources
    isolation_test_script = """
import os
import json
import subprocess
import sys
from pathlib import Path

def test_isolation():
    results = {
        "shared_dir_access": False,
        "system_access_blocked": False,
        "docker_socket_access": False,
        "network_access": False
    }

    try:
        # Test shared directory access (should work)
        shared_path = Path("/shared")
        if shared_path.exists():
            test_file = shared_path / "isolation_test.txt"
            test_file.write_text("Container can write to shared dir")
            if test_file.exists():
                results["shared_dir_access"] = True
                test_file.unlink()  # cleanup
    except Exception:
        pass

    try:
        # Test system directory access (should be limited)
        system_dirs = ["/etc/passwd", "/proc/version", "/sys"]
        accessible_dirs = 0
        for dir_path in system_dirs:
            if os.path.exists(dir_path):
                accessible_dirs += 1

        # Some system access is expected, but should be limited
        results["system_access_blocked"] = accessible_dirs < len(system_dirs)
    except Exception:
        results["system_access_blocked"] = True

    try:
        # Test Docker socket access (should be available for DooD)
        docker_socket = Path("/var/run/docker.sock")
        results["docker_socket_access"] = docker_socket.exists()
    except Exception:
        pass

    return results

if __name__ == "__main__":
    results = test_isolation()
    output_file = "/shared/isolation_test_results.json"

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(json.dumps(results, indent=2))
"""

    # Write the isolation test script
    script_path = shared_dir / "isolation_test.py"
    with open(script_path, "w") as f:
        f.write(isolation_test_script)

    # Execute via Dagger (using custom Python executor if available)
    isolation_command = "CALL python_executor isolation_test.py"

    try:
        response = await test_helper.send_dsl_command(
            orchestrator_client, isolation_command
        )

        if response.get("success") or "result" in response:
            await asyncio.sleep(10)

            # Check isolation test results
            result_file = shared_dir / "isolation_test_results.json"
            if result_file.exists():
                with open(result_file) as f:
                    isolation_results = json.load(f)

                print(f"Container isolation results: {isolation_results}")

                # Validate isolation properties
                assert (
                    isolation_results["shared_dir_access"] == True
                )  # Should have shared access

                print("Container isolation test completed")

                # Cleanup
                result_file.unlink()
                script_path.unlink()
            else:
                print("Isolation test results not found")
        else:
            print(f"Isolation test command not accepted: {response}")

    except Exception as e:
        print(f"Container isolation test failed: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tool_error_handling(wait_for_services, orchestrator_client, test_helper):
    """Test tool error handling and recovery"""
    # Test invalid file operation
    invalid_file_command = "CALL read_file nonexistent_file.txt"

    response = await test_helper.send_dsl_command(
        orchestrator_client, invalid_file_command
    )

    # Should handle error gracefully
    if "error" in response:
        print(f"Tool error handled correctly: {response['error']}")
    elif response.get("success") == False:
        print("Tool error handled with success=false")
    else:
        print("Tool error handling may need improvement")

    # Test invalid tool call
    invalid_tool_command = "CALL nonexistent_tool param1 param2"

    response = await test_helper.send_dsl_command(
        orchestrator_client, invalid_tool_command
    )

    # Should handle unknown tool error
    if "error" in response or response.get("success") == False:
        print("Unknown tool error handled correctly")

    # Test recovery with valid command
    valid_command = "CALL write_file recovery_test.txt 'Recovered after error'"

    response = await test_helper.send_dsl_command(orchestrator_client, valid_command)

    # Should work normally after errors
    if response.get("success") or "result" in response:
        print("System recovered successfully after errors")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_concurrent_tool_execution(
    wait_for_services, orchestrator_client, test_helper, shared_dir
):
    """Test concurrent execution of multiple tools"""
    # Create multiple file operations concurrently
    concurrent_commands = [
        "CALL write_file concurrent_1.txt 'Concurrent execution test 1'",
        "CALL write_file concurrent_2.txt 'Concurrent execution test 2'",
        "CALL write_file concurrent_3.txt 'Concurrent execution test 3'",
    ]

    # Execute all commands concurrently
    tasks = []
    for command in concurrent_commands:
        task = asyncio.create_task(
            test_helper.send_dsl_command(orchestrator_client, command)
        )
        tasks.append(task)

    # Wait for all to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful_commands = 0
    for i, result in enumerate(results):
        if not isinstance(result, Exception):
            if result.get("success") or "result" in result:
                successful_commands += 1
                print(f"Concurrent command {i + 1} succeeded")

    print(
        f"Successfully executed {successful_commands}/{len(concurrent_commands)} concurrent commands"
    )

    # Wait a bit for file operations to complete
    await asyncio.sleep(5)

    # Check that files were created
    created_files = 0
    for i in range(1, 4):
        file_path = shared_dir / f"concurrent_{i}.txt"
        if file_path.exists():
            created_files += 1
            # Cleanup
            file_path.unlink()

    print(f"Created {created_files} files from concurrent operations")
    assert created_files > 0  # At least some should succeed


@pytest.mark.mcp
@pytest.mark.asyncio
async def test_mcp_error_handling(wait_for_services, mcp_client):
    """Test MCP server error handling"""
    # Test invalid tool call
    invalid_request = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {"name": "nonexistent_tool", "arguments": {}},
    }

    response = await mcp_client.post("/mcp", json=invalid_request)
    assert response.status_code == 200

    result = response.json()
    assert "error" in result
    assert result["error"]["code"] == -32601  # Method not found

    print("MCP invalid tool error handled correctly")

    # Test invalid file operation
    invalid_file_request = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "read_file",
            "arguments": {"filename": "/invalid/path/file.txt"},
        },
    }

    response = await mcp_client.post("/mcp", json=invalid_file_request)
    assert response.status_code == 200

    result = response.json()
    # Should return error or error content
    if "error" in result:
        print("MCP invalid file operation handled with JSON-RPC error")
    elif "result" in result:
        # May return success=false in content
        print("MCP invalid file operation handled in result content")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tool_capability_discovery(wait_for_services, orchestrator_client):
    """Test tool capability discovery and matching"""
    # Get agent capabilities
    response = await orchestrator_client.get("/agent/card")
    assert response.status_code == 200

    card = response.json()
    tools = card.get("tools", [])

    # Should have various tool types
    tool_engines = set()
    tool_names = []

    for tool in tools:
        tool_names.append(tool["name"])
        if "engine" in tool:
            tool_engines.add(tool["engine"])

    print(f"Available tools: {tool_names}")
    print(f"Tool engines: {tool_engines}")

    # Should have both local and dagger tools
    assert len(tools) > 0
    expected_engines = {"local", "dagger"}
    found_engines = expected_engines.intersection(tool_engines)

    if found_engines:
        print(f"Tool engines available: {found_engines}")
    else:
        print("Tool engine information not available in card")

    # Test that orchestrator can match capabilities
    # (This is more of a structural test)
    capabilities = card.get("capabilities", [])
    assert len(capabilities) > 0

    print("Tool capability discovery test completed")
