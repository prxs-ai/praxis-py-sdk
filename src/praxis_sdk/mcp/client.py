"""
MCP Client Implementation for Praxis SDK

Client for connecting to external MCP servers with tool discovery,
transport management, and error handling with reconnection logic.
"""

import trio
import trio_asyncio
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from loguru import logger
import json
import httpx
import subprocess
import asyncio
from pathlib import Path

from praxis_sdk.mcp.server import HTTPTransport, SSETransport, MCPTransport


@dataclass
class MCPServerConfig:
    """Configuration for MCP server connection"""
    name: str
    transport_type: str  # "http", "sse", "subprocess"
    endpoint: str
    enabled: bool = True
    reconnect_interval: int = 30
    max_retries: int = 3


class SubprocessTransport(MCPTransport):
    """Subprocess transport for MCP communication"""
    
    def __init__(self, command: List[str], cwd: Optional[str] = None):
        self.command = command
        self.cwd = cwd
        self.process = None
        self.stdin_stream = None
        self.stdout_stream = None
    
    async def start(self):
        """Start the subprocess"""
        try:
            self.process = await trio_asyncio.aio_as_trio(
                asyncio.create_subprocess_exec
            )(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd
            )
            
            self.stdin_stream = self.process.stdin
            self.stdout_stream = self.process.stdout
            
            logger.info(f"Started MCP subprocess: {' '.join(self.command)}")
        except Exception as e:
            logger.error(f"Failed to start MCP subprocess: {e}")
            raise
    
    async def send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request via subprocess stdin/stdout"""
        if not self.process or not self.stdin_stream:
            raise RuntimeError("Subprocess not started")
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        try:
            # Send request
            request_line = json.dumps(payload) + "\n"
            self.stdin_stream.write(request_line.encode())
            await trio_asyncio.aio_as_trio(self.stdin_stream.drain)()
            
            # Read response
            response_line = await trio_asyncio.aio_as_trio(
                self.stdout_stream.readline
            )()
            
            if not response_line:
                raise RuntimeError("Subprocess closed unexpectedly")
            
            return json.loads(response_line.decode().strip())
        
        except Exception as e:
            logger.error(f"Subprocess transport error: {e}")
            return {"error": {"code": -32603, "message": str(e)}}
    
    async def close(self):
        """Close the subprocess"""
        if self.process:
            self.process.terminate()
            await trio_asyncio.aio_as_trio(self.process.wait)()
            logger.info("MCP subprocess terminated")


class MCPClient:
    """
    MCP Client for connecting to external servers with tool discovery,
    transport management, and automatic reconnection
    """
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        self.transports: Dict[str, MCPTransport] = {}
        self.discovered_tools: Dict[str, List[Dict[str, Any]]] = {}
        self.connection_status: Dict[str, bool] = {}
        self.reconnect_tasks: Dict[str, bool] = {}
        self.running = False
    
    def add_server(self, config: MCPServerConfig):
        """Add an MCP server configuration"""
        self.servers[config.name] = config
        self.connection_status[config.name] = False
        logger.info(f"Added MCP server config: {config.name} ({config.transport_type})")
    
    def remove_server(self, name: str):
        """Remove an MCP server configuration"""
        if name in self.servers:
            del self.servers[name]
            if name in self.transports:
                del self.transports[name]
            if name in self.connection_status:
                del self.connection_status[name]
            if name in self.discovered_tools:
                del self.discovered_tools[name]
            logger.info(f"Removed MCP server: {name}")
    
    async def start(self):
        """Start the MCP client and connect to all configured servers"""
        self.running = True
        logger.info("Starting MCP Client")
        
        # Connect to all configured servers
        async with trio.open_nursery() as nursery:
            for server_name, server_config in self.servers.items():
                if server_config.enabled:
                    nursery.start_soon(self._connect_server, server_name)
    
    async def stop(self):
        """Stop the MCP client and close all connections"""
        self.running = False
        
        # Stop all reconnect tasks
        for server_name in self.reconnect_tasks:
            self.reconnect_tasks[server_name] = False
        
        # Close all transports
        for server_name, transport in self.transports.items():
            try:
                await transport.close()
                logger.info(f"Closed connection to MCP server: {server_name}")
            except Exception as e:
                logger.error(f"Error closing MCP server {server_name}: {e}")
        
        self.transports.clear()
        self.connection_status.clear()
        logger.info("MCP Client stopped")
    
    async def _connect_server(self, server_name: str):
        """Connect to a specific MCP server"""
        server_config = self.servers[server_name]
        
        try:
            # Create transport based on type
            transport = await self._create_transport(server_config)
            self.transports[server_name] = transport
            
            # Initialize connection
            await self._initialize_server(server_name, transport)
            
            # Discover tools
            await self._discover_tools(server_name, transport)
            
            self.connection_status[server_name] = True
            logger.info(f"Successfully connected to MCP server: {server_name}")
            
            # Start reconnection monitoring if needed
            if server_config.transport_type in ["http", "sse"]:
                await self._monitor_connection(server_name)
        
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server_name}: {e}")
            self.connection_status[server_name] = False
            
            # Schedule reconnection
            await self._schedule_reconnection(server_name)
    
    async def _create_transport(self, config: MCPServerConfig) -> MCPTransport:
        """Create appropriate transport based on configuration"""
        if config.transport_type == "http":
            return HTTPTransport(config.endpoint)
        
        elif config.transport_type == "sse":
            return SSETransport(config.endpoint)
        
        elif config.transport_type == "subprocess":
            # Parse command from endpoint
            command = config.endpoint.split()
            transport = SubprocessTransport(command)
            await transport.start()
            return transport
        
        else:
            raise ValueError(f"Unsupported transport type: {config.transport_type}")
    
    async def _initialize_server(self, server_name: str, transport: MCPTransport):
        """Initialize connection with MCP server"""
        response = await transport.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "clientInfo": {
                "name": "praxis-mcp-client",
                "version": "1.0.0"
            }
        })
        
        if "error" in response:
            raise Exception(f"Server initialization failed: {response['error']}")
        
        logger.debug(f"Initialized MCP server {server_name}: {response.get('result', {})}")
    
    async def _discover_tools(self, server_name: str, transport: MCPTransport):
        """Discover tools from MCP server"""
        response = await transport.send_request("tools/list", {})
        
        if "error" in response:
            logger.error(f"Failed to discover tools from {server_name}: {response['error']}")
            return
        
        tools = response.get("result", {}).get("tools", [])
        self.discovered_tools[server_name] = tools
        
        logger.info(f"Discovered {len(tools)} tools from MCP server {server_name}")
        for tool in tools:
            logger.debug(f"  - {tool.get('name')}: {tool.get('description')}")
    
    async def _monitor_connection(self, server_name: str):
        """Monitor connection health and trigger reconnection if needed"""
        server_config = self.servers[server_name]
        
        while self.running and self.connection_status.get(server_name, False):
            try:
                # Send health check
                transport = self.transports.get(server_name)
                if transport:
                    response = await transport.send_request("ping", {})
                    if "error" in response:
                        raise Exception("Health check failed")
                
                await trio.sleep(server_config.reconnect_interval)
            
            except Exception as e:
                logger.warning(f"Connection lost to MCP server {server_name}: {e}")
                self.connection_status[server_name] = False
                await self._schedule_reconnection(server_name)
                break
    
    async def _schedule_reconnection(self, server_name: str):
        """Schedule reconnection attempts for a failed server"""
        if server_name in self.reconnect_tasks and self.reconnect_tasks[server_name]:
            return  # Already reconnecting
        
        self.reconnect_tasks[server_name] = True
        server_config = self.servers[server_name]
        
        for attempt in range(server_config.max_retries):
            if not self.running or not self.reconnect_tasks.get(server_name, True):
                break
            
            logger.info(f"Reconnection attempt {attempt + 1}/{server_config.max_retries} for {server_name}")
            
            try:
                await self._connect_server(server_name)
                self.reconnect_tasks[server_name] = False
                return
            
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt + 1} failed for {server_name}: {e}")
                
                if attempt < server_config.max_retries - 1:
                    await trio.sleep(server_config.reconnect_interval)
        
        logger.error(f"All reconnection attempts failed for MCP server {server_name}")
        self.reconnect_tasks[server_name] = False
    
    async def call_tool(self, server_name: str, tool_name: str, 
                       arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on a specific MCP server"""
        if server_name not in self.transports:
            raise Exception(f"Not connected to MCP server: {server_name}")
        
        if not self.connection_status.get(server_name, False):
            raise Exception(f"MCP server {server_name} is not connected")
        
        transport = self.transports[server_name]
        
        try:
            response = await transport.send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            
            if "error" in response:
                raise Exception(f"Tool call failed: {response['error']}")
            
            return response.get("result", {})
        
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {server_name}: {e}")
            raise
    
    def get_available_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all discovered tools from all connected servers"""
        return self.discovered_tools.copy()
    
    def get_server_status(self) -> Dict[str, bool]:
        """Get connection status for all servers"""
        return self.connection_status.copy()
    
    async def list_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """List resources from a specific MCP server"""
        if server_name not in self.transports:
            raise Exception(f"Not connected to MCP server: {server_name}")
        
        transport = self.transports[server_name]
        response = await transport.send_request("resources/list", {})
        
        if "error" in response:
            raise Exception(f"Failed to list resources: {response['error']}")
        
        return response.get("result", {}).get("resources", [])
    
    async def read_resource(self, server_name: str, uri: str) -> Dict[str, Any]:
        """Read a resource from a specific MCP server"""
        if server_name not in self.transports:
            raise Exception(f"Not connected to MCP server: {server_name}")
        
        transport = self.transports[server_name]
        response = await transport.send_request("resources/read", {"uri": uri})
        
        if "error" in response:
            raise Exception(f"Failed to read resource: {response['error']}")
        
        return response.get("result", {})
    
    def is_server_connected(self, server_name: str) -> bool:
        """Check if a specific server is connected"""
        return self.connection_status.get(server_name, False)
    
    async def refresh_tools(self, server_name: str):
        """Refresh tool discovery for a specific server"""
        if server_name in self.transports and self.connection_status.get(server_name, False):
            transport = self.transports[server_name]
            await self._discover_tools(server_name, transport)
            logger.info(f"Refreshed tools for MCP server: {server_name}")
        else:
            logger.warning(f"Cannot refresh tools for disconnected server: {server_name}")


def load_mcp_servers_from_config() -> List[MCPServerConfig]:
    """Load MCP server configurations from application config"""
    servers = []
    
    # Load from external MCP endpoints in config
    for endpoint in config.agent.external_mcp_endpoints:
        if endpoint.startswith("http"):
            servers.append(MCPServerConfig(
                name=f"http_server_{len(servers)}",
                transport_type="http",
                endpoint=endpoint
            ))
        elif endpoint.startswith("subprocess:"):
            command = endpoint[11:]  # Remove "subprocess:" prefix
            servers.append(MCPServerConfig(
                name=f"subprocess_server_{len(servers)}",
                transport_type="subprocess",
                endpoint=command
            ))
    
    return servers