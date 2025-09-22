"""
MCP Integration with P2P and Event Bus

This module provides integration between MCP server/client and the P2P protocols
and event bus for seamless tool invocation across the agent network.
"""

import trio
from typing import Dict, Any, List, Optional, Callable, Union
from loguru import logger
import json

from praxis_sdk.bus import event_bus
from praxis_sdk.mcp.server import MCPServer
from praxis_sdk.mcp.client import MCPClient, MCPServerConfig
from praxis_sdk.mcp.registry import ToolRegistry
from praxis_sdk.config import config


class MCPIntegration:
    """
    Integration layer between MCP server/client and P2P protocols
    
    This class coordinates:
    - MCP server for local tool execution
    - MCP client for external tool discovery
    - P2P protocol integration for remote tool invocation
    - Event bus integration for monitoring and coordination
    """
    
    def __init__(self):
        self.mcp_server: Optional[MCPServer] = None
        self.mcp_client: Optional[MCPClient] = None
        self.p2p_service = None
        self.running = False
        
        # Tool routing registry
        self.remote_tools: Dict[str, str] = {}  # tool_name -> peer_id
        self.peer_tools: Dict[str, List[str]] = {}  # peer_id -> [tool_names]
    
    async def initialize(self, p2p_service=None):
        """Initialize MCP integration with P2P service"""
        try:
            logger.info("Initializing MCP integration...")
            
            # Store P2P service reference
            self.p2p_service = p2p_service
            
            # Initialize MCP server
            self.mcp_server = MCPServer("praxis-mcp-server")
            await self.mcp_server.start()
            
            # Initialize MCP client if external servers configured
            if config.agent.external_mcp_endpoints:
                self.mcp_client = MCPClient()
                
                # Add configured servers
                for i, endpoint in enumerate(config.agent.external_mcp_endpoints):
                    server_config = self._create_server_config(endpoint, i)
                    self.mcp_client.add_server(server_config)
                
                await self.mcp_client.start()
                
                # Register external tools with MCP server
                await self._register_external_tools()
            
            # Setup event bus integration
            self._setup_event_handlers()
            
            logger.info("MCP integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP integration: {e}")
            raise
    
    def _create_server_config(self, endpoint: Union[str, Dict[str, Any]], index: int) -> MCPServerConfig:
        """Create MCP server configuration from endpoint"""
        headers: Optional[Dict[str, Any]] = None
        name = f"external_http_{index}"
        transport_type = "http"
        endpoint_value: str

        if isinstance(endpoint, dict):
            endpoint_value = endpoint.get("url") or endpoint.get("endpoint") or endpoint.get("address")
            headers = endpoint.get("headers")
            name = endpoint.get("name", name)
            transport_type = endpoint.get("transport", endpoint.get("type", "http"))
        else:
            endpoint_value = endpoint

        if endpoint_value.startswith("subprocess:"):
            command = endpoint_value[11:]
            return MCPServerConfig(
                name=f"external_subprocess_{index}",
                transport_type="subprocess",
                endpoint=command,
                headers=None
            )

        if endpoint_value.startswith("sse:"):
            endpoint_value = endpoint_value[4:]
            transport_type = "sse"

        return MCPServerConfig(
            name=name,
            transport_type=transport_type,
            endpoint=endpoint_value,
            headers=headers
        )
    
    async def _register_external_tools(self):
        """Register tools from external MCP servers with the main server"""
        if not self.mcp_client:
            return
        
        available_tools = self.mcp_client.get_available_tools()
        
        for server_name, tools in available_tools.items():
            for tool in tools:
                original_name = tool.get("name")
                if not original_name:
                    continue

                tool_key = f"{server_name}:{original_name}"

                async def make_handler(server: str, remote_tool: str):
                    async def handler(**kwargs):
                        return await self.mcp_client.call_tool(server, remote_tool, kwargs)
                    return handler

                handler = await make_handler(server_name, original_name)

                if hasattr(self.mcp_server, 'external_tools'):
                    server_tools = self.mcp_server.external_tools.setdefault(server_name, {})
                    server_tools[original_name] = {
                        "description": tool.get("description", ""),
                        "inputSchema": tool.get("inputSchema", {"type": "object"})
                    }

                await self.mcp_server.register_dynamic_tool(
                    name=tool_key,
                    description=f"External tool from {server_name}: {tool.get('description', '')}",
                    input_schema=tool.get("inputSchema", {"type": "object"}),
                    handler=handler
                )
    
    def _setup_event_handlers(self):
        """Setup event bus handlers for MCP integration"""
        
        # P2P events
        event_bus.subscribe("p2p.peer_discovered", self._on_peer_discovered)
        event_bus.subscribe("p2p.peer_connected", self._on_peer_connected)
        event_bus.subscribe("p2p.peer_disconnected", self._on_peer_disconnected)
        event_bus.subscribe("p2p.tool_request", self._on_p2p_tool_request)
        event_bus.subscribe("p2p.mcp_request", self._on_p2p_mcp_request)
        
        # MCP events
        event_bus.subscribe("mcp.tool_registered", self._on_mcp_tool_registered)
        event_bus.subscribe("mcp.tool_unregistered", self._on_mcp_tool_unregistered)
        event_bus.subscribe("mcp.external_server_connected", self._on_external_server_connected)
        event_bus.subscribe("mcp.external_server_disconnected", self._on_external_server_disconnected)
        
        # Tool execution events
        event_bus.subscribe("tool_execution_start", self._on_tool_execution_start)
        event_bus.subscribe("tool_execution_complete", self._on_tool_execution_complete)
        event_bus.subscribe("tool_execution_error", self._on_tool_execution_error)
    
    async def _on_peer_discovered(self, event_type: str, data: Dict[str, Any]):
        """Handle peer discovered event"""
        peer_id = data.get("peer_id")
        if peer_id:
            logger.info(f"MCP: Peer discovered: {peer_id}")
            
            # Request peer's available tools
            if self.p2p_service:
                try:
                    await self._request_peer_tools(peer_id)
                except Exception as e:
                    logger.error(f"Failed to request tools from peer {peer_id}: {e}")
    
    async def _on_peer_connected(self, event_type: str, data: Dict[str, Any]):
        """Handle peer connected event"""
        peer_id = data.get("peer_id")
        if peer_id:
            logger.info(f"MCP: Peer connected: {peer_id}")
    
    async def _on_peer_disconnected(self, event_type: str, data: Dict[str, Any]):
        """Handle peer disconnected event"""
        peer_id = data.get("peer_id")
        if peer_id:
            logger.info(f"MCP: Peer disconnected: {peer_id}")
            
            # Remove tools from this peer
            if peer_id in self.peer_tools:
                tools = self.peer_tools[peer_id]
                for tool_name in tools:
                    if tool_name in self.remote_tools:
                        del self.remote_tools[tool_name]
                del self.peer_tools[peer_id]
                
                logger.info(f"Removed {len(tools)} tools from disconnected peer {peer_id}")
    
    async def _on_p2p_tool_request(self, event_type: str, data: Dict[str, Any]):
        """Handle P2P tool execution request"""
        tool_name = data.get("tool_name")
        arguments = data.get("arguments", {})
        peer_id = data.get("peer_id")
        
        if not tool_name or not self.mcp_server:
            return
        
        try:
            # Execute tool locally via MCP server
            result = await self.mcp_server.call_tool(tool_name, arguments)
            
            # Send result back via P2P
            if self.p2p_service and peer_id:
                await self.p2p_service.send_tool_response(peer_id, {
                    "tool_name": tool_name,
                    "result": result,
                    "success": True
                })
        
        except Exception as e:
            logger.error(f"P2P tool request failed: {tool_name} - {e}")
            
            if self.p2p_service and peer_id:
                await self.p2p_service.send_tool_response(peer_id, {
                    "tool_name": tool_name,
                    "error": str(e),
                    "success": False
                })
    
    async def _on_p2p_mcp_request(self, event_type: str, data: Dict[str, Any]):
        """Handle P2P MCP protocol request"""
        request = data.get("request")
        peer_id = data.get("peer_id")
        
        if not request or not self.mcp_server:
            return
        
        try:
            # Process MCP request
            response = await self.mcp_server.handle_request(request)
            
            # Send response back via P2P
            if self.p2p_service and peer_id:
                await self.p2p_service.send_mcp_response(peer_id, response)
        
        except Exception as e:
            logger.error(f"P2P MCP request failed: {e}")
            
            if self.p2p_service and peer_id:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
                await self.p2p_service.send_mcp_response(peer_id, error_response)
    
    async def _on_mcp_tool_registered(self, event_type: str, data: Dict[str, Any]):
        """Handle MCP tool registration event"""
        tool_name = data.get("tool_name")
        logger.info(f"MCP tool registered: {tool_name}")
        
        # Broadcast tool availability to P2P peers
        if self.p2p_service:
            await self._broadcast_tool_update()
    
    async def _on_mcp_tool_unregistered(self, event_type: str, data: Dict[str, Any]):
        """Handle MCP tool unregistration event"""
        tool_name = data.get("tool_name")
        logger.info(f"MCP tool unregistered: {tool_name}")
        
        # Broadcast tool availability to P2P peers
        if self.p2p_service:
            await self._broadcast_tool_update()
    
    async def _on_external_server_connected(self, event_type: str, data: Dict[str, Any]):
        """Handle external MCP server connection event"""
        server_name = data.get("server_name")
        logger.info(f"External MCP server connected: {server_name}")
        
        # Re-register external tools
        await self._register_external_tools()
    
    async def _on_external_server_disconnected(self, event_type: str, data: Dict[str, Any]):
        """Handle external MCP server disconnection event"""
        server_name = data.get("server_name")
        logger.info(f"External MCP server disconnected: {server_name}")
        
        # Remove external tools from this server
        if self.mcp_server:
            tools_to_remove = [
                name for name in self.mcp_server.tool_registry.tools.keys()
                if name.startswith("external_") and 
                self.mcp_server.tool_registry.tools[name].server_url == server_name
            ]
            
            for tool_name in tools_to_remove:
                await self.mcp_server.unregister_tool(tool_name)
    
    async def _on_tool_execution_start(self, event_type: str, data: Dict[str, Any]):
        """Handle tool execution start event"""
        tool_name = data.get("tool_name")
        logger.debug(f"Tool execution started: {tool_name}")
    
    async def _on_tool_execution_complete(self, event_type: str, data: Dict[str, Any]):
        """Handle tool execution complete event"""
        tool_name = data.get("tool_name")
        logger.debug(f"Tool execution completed: {tool_name}")
    
    async def _on_tool_execution_error(self, event_type: str, data: Dict[str, Any]):
        """Handle tool execution error event"""
        tool_name = data.get("tool_name")
        error = data.get("error")
        logger.warning(f"Tool execution error: {tool_name} - {error}")
    
    async def _request_peer_tools(self, peer_id: str):
        """Request available tools from a peer"""
        if not self.p2p_service:
            return
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        try:
            response = await self.p2p_service.send_mcp_request(peer_id, request)
            
            if "result" in response and "tools" in response["result"]:
                tools = response["result"]["tools"]
                tool_names = [tool["name"] for tool in tools]
                
                # Store peer tools
                self.peer_tools[peer_id] = tool_names
                
                # Register remote tools
                for tool_name in tool_names:
                    remote_tool_name = f"remote_{peer_id}_{tool_name}"
                    self.remote_tools[remote_tool_name] = peer_id
                
                logger.info(f"Discovered {len(tool_names)} tools from peer {peer_id}")
        
        except Exception as e:
            logger.error(f"Failed to request tools from peer {peer_id}: {e}")
    
    async def _broadcast_tool_update(self):
        """Broadcast tool availability update to all peers"""
        if not self.p2p_service or not self.mcp_server:
            return
        
        tools = await self.mcp_server.list_tools()
        tool_list = [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            }
            for tool in tools
        ]
        
        broadcast_data = {
            "type": "tool_update",
            "tools": tool_list,
            "timestamp": trio.current_time()
        }
        
        try:
            await self.p2p_service.broadcast_to_peers(broadcast_data)
            logger.debug(f"Broadcasted tool update: {len(tool_list)} tools")
        
        except Exception as e:
            logger.error(f"Failed to broadcast tool update: {e}")
    
    async def invoke_remote_tool(self, peer_id: str, tool_name: str, 
                               arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool on a remote peer via P2P"""
        if not self.p2p_service:
            raise RuntimeError("P2P service not available")
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            response = await self.p2p_service.send_mcp_request(peer_id, request)
            
            if "error" in response:
                raise Exception(f"Remote tool error: {response['error']}")
            
            return response.get("result", {})
        
        except Exception as e:
            logger.error(f"Failed to invoke remote tool {tool_name} on {peer_id}: {e}")
            raise
    
    async def get_available_tools(self) -> Dict[str, Any]:
        """Get all available tools (local, external, and remote)"""
        tools = {
            "local": [],
            "external": [],
            "remote": {}
        }
        
        if self.mcp_server:
            server_tools = await self.mcp_server.list_tools()
            
            for tool in server_tools:
                if tool.name.startswith("external_"):
                    tools["external"].append({
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema
                    })
                else:
                    tools["local"].append({
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema
                    })
        
        # Add remote tools
        for peer_id, tool_names in self.peer_tools.items():
            tools["remote"][peer_id] = tool_names
        
        return tools
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool (local, external, or remote)
        
        This method determines the best way to execute the tool:
        - Local tools via MCP server
        - External tools via MCP client
        - Remote tools via P2P
        """
        
        # Check if it's a remote tool
        if tool_name in self.remote_tools:
            peer_id = self.remote_tools[tool_name]
            original_name = tool_name.replace(f"remote_{peer_id}_", "")
            return await self.invoke_remote_tool(peer_id, original_name, arguments)
        
        # Execute via local MCP server
        if self.mcp_server:
            return await self.mcp_server.call_tool(tool_name, arguments)
        
        raise ValueError(f"Tool not found or not available: {tool_name}")
    
    async def start(self):
        """Start the MCP integration"""
        self.running = True
        logger.info("MCP integration started")
    
    async def stop(self):
        """Stop the MCP integration"""
        self.running = False
        
        if self.mcp_client:
            await self.mcp_client.stop()
        
        if self.mcp_server:
            await self.mcp_server.stop()
        
        logger.info("MCP integration stopped")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get MCP integration statistics"""
        stats = {
            "local_tools": 0,
            "external_tools": 0,
            "remote_peers": len(self.peer_tools),
            "remote_tools": len(self.remote_tools),
            "external_servers": 0
        }
        
        if self.mcp_server:
            server_stats = self.mcp_server.tool_registry.get_tool_statistics()
            stats["local_tools"] = server_stats.get("local_tools", 0)
            stats["external_tools"] = server_stats.get("external_tools", 0)
        
        if self.mcp_client:
            server_status = self.mcp_client.get_server_status()
            stats["external_servers"] = len([s for s in server_status.values() if s])
        
        return stats


# Global MCP integration instance
mcp_integration = MCPIntegration()
