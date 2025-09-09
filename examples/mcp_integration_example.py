#!/usr/bin/env python3
"""
MCP Integration Example for Praxis SDK

This example demonstrates comprehensive MCP (Model Context Protocol) integration
with the Praxis Python SDK, including:
- Built-in MCP server with filesystem tools
- External MCP server connections
- P2P tool invocation
- Event bus integration
"""

import asyncio
import trio
import json
from pathlib import Path
from loguru import logger

# Import Praxis SDK components
from praxis_sdk.mcp.server import MCPServer
from praxis_sdk.mcp.client import MCPClient, MCPServerConfig
from praxis_sdk.mcp.registry import ToolRegistry
from praxis_sdk.mcp.tools.filesystem import FilesystemTools
from praxis_sdk.mcp.integration import MCPIntegration
from praxis_sdk.bus import event_bus
from praxis_sdk.config import PraxisConfig


async def demonstrate_mcp_server():
    """Demonstrate MCP server functionality"""
    logger.info("=== MCP Server Demonstration ===")
    
    # Create and start MCP server
    mcp_server = MCPServer("example-mcp-server")
    await mcp_server.start()
    
    try:
        # List available tools
        tools = await mcp_server.list_tools()
        logger.info(f"Available tools: {len(tools)}")
        for tool in tools:
            logger.info(f"  - {tool.name}: {tool.description}")
        
        # Test filesystem tools
        shared_dir = Path("./shared")
        shared_dir.mkdir(exist_ok=True)
        
        # Write a test file
        write_result = await mcp_server.call_tool("write_file", {
            "path": "test_file.txt",
            "content": "Hello from MCP!"
        })
        logger.info(f"Write file result: {write_result}")
        
        # Read the file back
        read_result = await mcp_server.call_tool("read_file", {
            "path": "test_file.txt"
        })
        logger.info(f"Read file result: {read_result}")
        
        # List directory contents
        list_result = await mcp_server.call_tool("list_directory", {
            "path": "."
        })
        logger.info(f"Directory listing: {list_result}")
        
        # Get file info
        info_result = await mcp_server.call_tool("get_file_info", {
            "path": "test_file.txt"
        })
        logger.info(f"File info: {info_result}")
        
        # Search for files
        search_result = await mcp_server.call_tool("search_files", {
            "directory": ".",
            "pattern": "*.txt"
        })
        logger.info(f"File search result: {search_result}")
        
        # Clean up
        delete_result = await mcp_server.call_tool("delete_file", {
            "path": "test_file.txt"
        })
        logger.info(f"Delete file result: {delete_result}")
        
    finally:
        await mcp_server.stop()


async def demonstrate_mcp_client():
    """Demonstrate MCP client functionality"""
    logger.info("=== MCP Client Demonstration ===")
    
    # Create MCP client
    mcp_client = MCPClient()
    
    # Add example external MCP servers (these would be real servers in production)
    example_servers = [
        MCPServerConfig(
            name="filesystem-server",
            transport_type="http",
            endpoint="http://localhost:3001"
        ),
        # MCPServerConfig(
        #     name="subprocess-server",
        #     transport_type="subprocess",
        #     endpoint="python -m mcp_server.filesystem"
        # )
    ]
    
    for server_config in example_servers:
        mcp_client.add_server(server_config)
    
    try:
        await mcp_client.start()
        
        # Get server status
        status = mcp_client.get_server_status()
        logger.info(f"Server connection status: {status}")
        
        # Get available tools from all servers
        available_tools = mcp_client.get_available_tools()
        logger.info(f"Available tools from external servers: {available_tools}")
        
        # If servers are connected, demonstrate tool calling
        for server_name, connected in status.items():
            if connected:
                try:
                    # Try to call a tool (this would work with a real server)
                    # result = await mcp_client.call_tool(
                    #     server_name, 
                    #     "list_files", 
                    #     {"directory": "./"}
                    # )
                    # logger.info(f"Tool call result from {server_name}: {result}")
                    logger.info(f"Would call tools on connected server: {server_name}")
                except Exception as e:
                    logger.warning(f"Tool call failed on {server_name}: {e}")
        
    except Exception as e:
        logger.warning(f"MCP client demonstration failed: {e}")
    
    finally:
        await mcp_client.stop()


async def demonstrate_tool_registry():
    """Demonstrate tool registry functionality"""
    logger.info("=== Tool Registry Demonstration ===")
    
    registry = ToolRegistry()
    
    # Define a custom tool
    async def custom_tool(message: str, count: int = 1) -> dict:
        """A custom tool that repeats a message"""
        return {
            "success": True,
            "result": message * count,
            "message_length": len(message),
            "repeat_count": count
        }
    
    # Register the custom tool
    success = registry.register_tool(
        name="repeat_message",
        description="Repeat a message a specified number of times",
        input_schema={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to repeat"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of times to repeat",
                    "default": 1
                }
            },
            "required": ["message"]
        },
        handler=custom_tool,
        category="custom"
    )
    
    logger.info(f"Tool registration success: {success}")
    
    # List tools
    tools = registry.list_tools()
    logger.info(f"Registered tools: {len(tools)}")
    for tool in tools:
        logger.info(f"  - {tool.name}: {tool.description} (external: {tool.is_external})")
    
    # Get tool statistics
    stats = registry.get_tool_statistics()
    logger.info(f"Registry statistics: {stats}")
    
    # Execute the custom tool
    result = await registry.execute_tool("repeat_message", {
        "message": "Hello MCP! ",
        "count": 3
    })
    logger.info(f"Custom tool execution result: {result}")
    
    # Search tools
    search_results = registry.search_tools("repeat")
    logger.info(f"Search results for 'repeat': {len(search_results)} tools found")
    
    # Get tool schema
    schema = registry.get_tool_schema("repeat_message")
    logger.info(f"Tool schema: {schema}")


async def demonstrate_event_integration():
    """Demonstrate event bus integration"""
    logger.info("=== Event Integration Demonstration ===")
    
    # Event handlers
    async def on_tool_execution(event_type: str, payload: dict):
        logger.info(f"Event: {event_type} - Tool: {payload.get('tool_name')}")
    
    async def on_mcp_event(event_type: str, payload: dict):
        logger.info(f"MCP Event: {event_type} - {payload}")
    
    # Subscribe to events
    event_bus.subscribe("tool_execution_start", on_tool_execution)
    event_bus.subscribe("tool_execution_complete", on_tool_execution)
    event_bus.subscribe("tool_execution_error", on_tool_execution)
    event_bus.subscribe("mcp.tool_registered", on_mcp_event)
    
    # Create MCP server and trigger some events
    mcp_server = MCPServer("event-demo-server")
    await mcp_server.start()
    
    try:
        # Register a dynamic tool (this will trigger events)
        async def demo_tool(value: str) -> dict:
            return {"processed_value": value.upper()}
        
        await mcp_server.register_dynamic_tool(
            name="demo_uppercase",
            description="Convert text to uppercase",
            input_schema={
                "type": "object",
                "properties": {
                    "value": {"type": "string", "description": "Text to convert"}
                },
                "required": ["value"]
            },
            handler=demo_tool
        )
        
        # Execute the tool (this will trigger execution events)
        result = await mcp_server.call_tool("demo_uppercase", {"value": "hello world"})
        logger.info(f"Demo tool result: {result}")
        
        # Unregister the tool
        await mcp_server.unregister_tool("demo_uppercase")
        
    finally:
        await mcp_server.stop()


async def demonstrate_mcp_integration():
    """Demonstrate full MCP integration with P2P (simulated)"""
    logger.info("=== MCP Integration Demonstration ===")
    
    # Create MCP integration instance
    integration = MCPIntegration()
    
    # Initialize without P2P service for this demo
    await integration.initialize(p2p_service=None)
    
    try:
        # Get available tools
        available_tools = await integration.get_available_tools()
        logger.info(f"Integration available tools: {available_tools}")
        
        # Execute a local tool
        result = await integration.execute_tool("write_file", {
            "path": "integration_test.txt",
            "content": "MCP Integration Test"
        })
        logger.info(f"Integration tool execution result: {result}")
        
        # Get statistics
        stats = integration.get_statistics()
        logger.info(f"Integration statistics: {stats}")
        
        # Clean up
        await integration.execute_tool("delete_file", {
            "path": "integration_test.txt"
        })
        
    finally:
        await integration.stop()


async def run_example():
    """Run all MCP examples"""
    logger.info("Starting Praxis MCP Integration Examples")
    
    try:
        # Run demonstrations
        await demonstrate_mcp_server()
        await trio.sleep(1)
        
        await demonstrate_mcp_client()
        await trio.sleep(1)
        
        await demonstrate_tool_registry()
        await trio.sleep(1)
        
        await demonstrate_event_integration()
        await trio.sleep(1)
        
        await demonstrate_mcp_integration()
        
        logger.info("All MCP examples completed successfully!")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise


def main():
    """Main entry point"""
    import sys
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    logger.info("Praxis MCP Integration Example")
    
    try:
        trio.run(run_example)
    except KeyboardInterrupt:
        logger.info("Example interrupted by user")
    except Exception as e:
        logger.error(f"Example failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()