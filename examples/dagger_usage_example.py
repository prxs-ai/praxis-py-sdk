"""
Example of using Dagger Execution Engine

This example demonstrates how to use the DaggerExecutionEngine to execute
tools in Docker containers, similar to the Go implementation.
"""

import asyncio
import tempfile
import json
from pathlib import Path

from praxis_sdk.execution import (
    DaggerExecutionEngine,
    LocalExecutionEngine,
    ToolContract,
    EngineType,
    test_docker_availability
)


async def example_simple_docker_execution():
    """
    Example 1: Simple Docker execution
    Execute a basic command in a busybox container
    """
    print("=== Example 1: Simple Docker Execution ===")
    
    if not await test_docker_availability():
        print("❌ Docker not available, skipping Docker examples")
        return
    
    engine = DaggerExecutionEngine()
    
    # Create a simple tool contract
    contract = ToolContract(
        engine=EngineType.DAGGER,
        name="hello_world",
        description="Simple hello world tool",
        engine_spec={
            "image": "busybox:latest",
            "command": ["echo", "Hello from Dagger!"],
            "timeout": 60
        }
    )
    
    try:
        print("📦 Executing tool in Docker container...")
        result = await engine.execute(contract, {})
        print(f"✅ Result: {result.strip()}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await engine.cleanup()


async def example_docker_with_arguments():
    """
    Example 2: Docker execution with arguments
    Pass arguments to the container via environment variables
    """
    print("\n=== Example 2: Docker Execution with Arguments ===")
    
    if not await test_docker_availability():
        print("❌ Docker not available, skipping Docker examples")
        return
    
    engine = DaggerExecutionEngine()
    
    # Tool contract that uses arguments
    contract = ToolContract(
        engine=EngineType.DAGGER,
        name="env_echo",
        description="Echo environment variables",
        engine_spec={
            "image": "busybox:latest",
            "command": ["sh", "-c", "echo 'Name: '$ARG_NAME'; Message: '$ARG_MESSAGE"],
            "timeout": 60
        }
    )
    
    try:
        print("📦 Executing tool with arguments...")
        result = await engine.execute(
            contract, 
            args={
                "name": "Alice",
                "message": "Hello from Python Dagger!"
            }
        )
        print(f"✅ Result:\n{result}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await engine.cleanup()


async def example_docker_with_mounts():
    """
    Example 3: Docker execution with volume mounts
    Mount host directories into container
    """
    print("\n=== Example 3: Docker Execution with Volume Mounts ===")
    
    if not await test_docker_availability():
        print("❌ Docker not available, skipping Docker examples")
        return
    
    engine = DaggerExecutionEngine()
    
    # Create temporary directory with test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        (temp_path / "input.txt").write_text("Hello from host filesystem!")
        (temp_path / "data.json").write_text(json.dumps({"key": "value", "number": 42}))
        
        print(f"📁 Created test files in: {temp_dir}")
        
        # Tool contract with mounts
        contract = ToolContract(
            engine=EngineType.DAGGER,
            name="file_processor",
            description="Process files from mounted directory",
            engine_spec={
                "image": "busybox:latest",
                "command": [
                    "sh", "-c", 
                    "echo '=== Directory listing ==='; "
                    "ls -la /workspace; "
                    "echo '=== File contents ==='; "
                    "cat /workspace/input.txt; "
                    "echo; "
                    "cat /workspace/data.json; "
                    "echo '=== Creating output ==='; "
                    "echo 'Processed by Docker!' > /workspace/output.txt"
                ],
                "mounts": {
                    temp_dir: "/workspace"
                },
                "timeout": 60
            }
        )
        
        try:
            print("📦 Executing tool with volume mounts...")
            result = await engine.execute(contract, {})
            print(f"✅ Container output:\n{result}")
            
            # Check if output file was created
            output_file = temp_path / "output.txt"
            if output_file.exists():
                print(f"📄 Output file created: {output_file.read_text()}")
            else:
                print("❌ Output file was not created")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await engine.cleanup()


async def example_docker_with_environment():
    """
    Example 4: Docker execution with custom environment
    Set environment variables and pass through host variables
    """
    print("\n=== Example 4: Docker Execution with Environment Variables ===")
    
    if not await test_docker_availability():
        print("❌ Docker not available, skipping Docker examples")
        return
    
    engine = DaggerExecutionEngine()
    
    # Tool contract with environment configuration
    contract = ToolContract(
        engine=EngineType.DAGGER,
        name="env_info",
        description="Display environment information",
        engine_spec={
            "image": "busybox:latest",
            "command": [
                "sh", "-c",
                "echo 'Custom variables:'; "
                "echo 'APP_NAME: '$APP_NAME; "
                "echo 'DEBUG_MODE: '$DEBUG_MODE; "
                "echo 'Arguments:'; "
                "echo 'User: '$ARG_USER; "
                "echo 'Action: '$ARG_ACTION; "
                "echo 'Host PATH: '$PATH"
            ],
            "env": {
                "APP_NAME": "Praxis Dagger Engine",
                "DEBUG_MODE": "true"
            },
            "env_passthrough": ["PATH"],
            "timeout": 60
        }
    )
    
    try:
        print("📦 Executing tool with environment variables...")
        result = await engine.execute(
            contract,
            args={
                "user": "developer",
                "action": "testing"
            }
        )
        print(f"✅ Result:\n{result}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await engine.cleanup()


async def example_python_execution():
    """
    Example 5: Python code execution
    Run Python code in a container with libraries
    """
    print("\n=== Example 5: Python Code Execution ===")
    
    if not await test_docker_availability():
        print("❌ Docker not available, skipping Docker examples")
        return
    
    engine = DaggerExecutionEngine()
    
    # Python script to execute
    python_code = '''
import json
import math
from datetime import datetime

data = {
    "timestamp": datetime.now().isoformat(),
    "calculation": math.sqrt(42),
    "message": "Hello from Python in Docker!"
}

print("Python execution results:")
print(json.dumps(data, indent=2))

# Also create a file
with open("/workspace/python_output.json", "w") as f:
    json.dump(data, f, indent=2)

print("File created: python_output.json")
    '''
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write Python script to file
        script_file = Path(temp_dir) / "script.py"
        script_file.write_text(python_code)
        
        contract = ToolContract(
            engine=EngineType.DAGGER,
            name="python_runner",
            description="Execute Python code in container",
            engine_spec={
                "image": "python:3.11-slim",
                "command": ["python", "/workspace/script.py"],
                "mounts": {
                    temp_dir: "/workspace"
                },
                "timeout": 120
            }
        )
        
        try:
            print("🐍 Executing Python code in container...")
            result = await engine.execute(contract, {})
            print(f"✅ Python output:\n{result}")
            
            # Check output file
            output_file = Path(temp_dir) / "python_output.json"
            if output_file.exists():
                output_data = json.loads(output_file.read_text())
                print(f"📄 Created file contents:")
                print(json.dumps(output_data, indent=2))
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await engine.cleanup()


async def example_local_execution():
    """
    Example 6: Local execution (without Docker)
    Execute commands directly on the host system
    """
    print("\n=== Example 6: Local Execution ===")
    
    engine = LocalExecutionEngine()
    
    # Simple local command
    contract = ToolContract(
        engine=EngineType.LOCAL,
        name="system_info",
        description="Get system information",
        engine_spec={
            "command": ["uname", "-a"],
            "timeout": 30
        }
    )
    
    try:
        print("💻 Executing command locally...")
        result = await engine.execute(contract, {})
        print(f"✅ System info: {result.strip()}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Local command with shell
    contract2 = ToolContract(
        engine=EngineType.LOCAL,
        name="shell_command",
        description="Execute shell command with pipes",
        engine_spec={
            "command": ["echo 'Current date:'; date; echo 'User: '$ARG_USERNAME"],
            "shell": True,
            "timeout": 30
        }
    )
    
    try:
        print("🐚 Executing shell command locally...")
        result = await engine.execute(
            contract2, 
            args={"username": "developer"}
        )
        print(f"✅ Shell output:\n{result}")
    except Exception as e:
        print(f"❌ Error: {e}")


async def example_error_handling():
    """
    Example 7: Error handling
    Demonstrate how errors are handled in execution engines
    """
    print("\n=== Example 7: Error Handling ===")
    
    # Test with local engine first
    local_engine = LocalExecutionEngine()
    
    # Command that will fail
    failing_contract = ToolContract(
        engine=EngineType.LOCAL,
        name="failing_tool",
        description="A tool that fails",
        engine_spec={
            "command": ["false"],  # Command that always returns 1
            "timeout": 30
        }
    )
    
    try:
        print("💻 Testing error handling with failing command...")
        result = await local_engine.execute(failing_contract, {})
        print(f"Unexpected success: {result}")
    except Exception as e:
        print(f"✅ Expected error caught: {e}")
    
    # Test timeout
    timeout_contract = ToolContract(
        engine=EngineType.LOCAL,
        name="timeout_tool",
        description="A tool that times out",
        engine_spec={
            "command": ["sleep", "60"],
            "timeout": 2  # Short timeout
        }
    )
    
    try:
        print("⏰ Testing timeout handling...")
        result = await local_engine.execute(timeout_contract, {})
        print(f"Unexpected success: {result}")
    except Exception as e:
        print(f"✅ Expected timeout error: {e}")


async def main():
    """
    Run all examples
    """
    print("🚀 Praxis SDK Dagger Engine Examples")
    print("=" * 50)
    
    # Check Docker availability
    docker_available = await test_docker_availability()
    print(f"🐳 Docker availability: {'✅ Available' if docker_available else '❌ Not available'}")
    
    # Run all examples
    await example_simple_docker_execution()
    await example_docker_with_arguments()
    await example_docker_with_mounts()
    await example_docker_with_environment()
    await example_python_execution()
    await example_local_execution()
    await example_error_handling()
    
    print("\n🎉 All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())