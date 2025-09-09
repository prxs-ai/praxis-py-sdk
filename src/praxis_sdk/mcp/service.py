"""
MCP Service Implementation

Service wrapper around MCP components for HTTP endpoint integration.
Provides tools discovery, statistics, and execution coordination.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from .registry import ToolRegistry
from .server import MCPServer
from .client import MCPClient


class MCPService:
    """
    MCP Service for HTTP endpoint integration.
    
    Provides a high-level interface to MCP functionality including:
    - Tool discovery and listing
    - MCP server management
    - Client connection handling
    - Statistics and monitoring
    """
    
    def __init__(self):
        self.registry = ToolRegistry()
        self.servers: Dict[str, MCPServer] = {}
        self.clients: Dict[str, MCPClient] = {}
        self.started = False
        
        # Service statistics
        self.stats = {
            "service_started": None,
            "total_requests": 0,
            "tools_executed": 0,
            "servers_count": 0,
            "clients_count": 0
        }
    
    async def start(self):
        """Start the MCP service."""
        if self.started:
            return
        
        self.started = True
        self.stats["service_started"] = datetime.now().isoformat()
        logger.info("MCP Service started")
    
    async def stop(self):
        """Stop the MCP service and cleanup resources."""
        if not self.started:
            return
        
        # Stop all servers
        for server in self.servers.values():
            try:
                await server.stop()
            except Exception as e:
                logger.error(f"Error stopping MCP server: {e}")
        
        # Disconnect all clients
        for client in self.clients.values():
            try:
                await client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting MCP client: {e}")
        
        self.servers.clear()
        self.clients.clear()
        self.registry.clear_registry()
        self.started = False
        logger.info("MCP Service stopped")
    
    def get_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all available MCP tools.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of tool information dictionaries
        """
        self.stats["total_requests"] += 1
        
        try:
            tools = self.registry.list_tools(category)
            
            # Convert ToolInfo objects to dictionaries for JSON serialization
            tool_dicts = []
            for tool in tools:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema,
                    "isExternal": tool.is_external,
                    "registeredAt": tool.registered_at,
                    "usageCount": tool.usage_count
                }
                
                if tool.is_external:
                    tool_dict["serverUrl"] = tool.server_url
                    tool_dict["originalName"] = tool.original_name
                
                if tool.last_used:
                    tool_dict["lastUsed"] = tool.last_used
                
                tool_dicts.append(tool_dict)
            
            logger.debug(f"Retrieved {len(tool_dicts)} MCP tools")
            return tool_dicts
            
        except Exception as e:
            logger.error(f"Error getting MCP tools: {e}")
            return []
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get JSON schemas for all registered tools."""
        self.stats["total_requests"] += 1
        
        try:
            schemas = self.registry.get_all_schemas()
            logger.debug(f"Retrieved schemas for {len(schemas)} tools")
            return schemas
        except Exception as e:
            logger.error(f"Error getting tool schemas: {e}")
            return []
    
    def get_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific tool information by name."""
        self.stats["total_requests"] += 1
        
        try:
            tool = self.registry.get_tool(name)
            if not tool:
                return None
            
            return {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
                "isExternal": tool.is_external,
                "registeredAt": tool.registered_at,
                "usageCount": tool.usage_count,
                "lastUsed": tool.last_used,
                "serverUrl": tool.server_url if tool.is_external else None,
                "originalName": tool.original_name if tool.is_external else None
            }
            
        except Exception as e:
            logger.error(f"Error getting tool {name}: {e}")
            return None
    
    def search_tools(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for tools by name or description."""
        self.stats["total_requests"] += 1
        
        try:
            tools = self.registry.search_tools(query, category)
            
            # Convert to dictionaries
            tool_dicts = []
            for tool in tools:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema,
                    "isExternal": tool.is_external,
                    "usageCount": tool.usage_count
                }
                
                if tool.is_external:
                    tool_dict["serverUrl"] = tool.server_url
                    tool_dict["originalName"] = tool.original_name
                
                tool_dicts.append(tool_dict)
            
            logger.debug(f"Found {len(tool_dicts)} tools matching query: {query}")
            return tool_dicts
            
        except Exception as e:
            logger.error(f"Error searching tools: {e}")
            return []
    
    def get_categories(self) -> Dict[str, List[str]]:
        """Get tools organized by category."""
        self.stats["total_requests"] += 1
        
        try:
            categories = self.registry.get_tools_by_category()
            logger.debug(f"Retrieved {len(categories)} tool categories")
            return categories
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive MCP service statistics."""
        self.stats["total_requests"] += 1
        
        try:
            # Get registry statistics
            registry_stats = self.registry.get_tool_statistics()
            
            # Combine with service statistics
            combined_stats = {
                **self.stats,
                "servers_count": len(self.servers),
                "clients_count": len(self.clients),
                "registry": registry_stats,
                "service_status": "running" if self.started else "stopped"
            }
            
            return combined_stats
            
        except Exception as e:
            logger.error(f"Error getting MCP statistics: {e}")
            return {
                **self.stats,
                "error": str(e),
                "service_status": "error"
            }
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP tool."""
        self.stats["total_requests"] += 1
        
        try:
            result = await self.registry.execute_tool(name, arguments)
            self.stats["tools_executed"] += 1
            
            logger.debug(f"Executed MCP tool: {name}")
            return {
                "success": True,
                "result": result,
                "toolName": name
            }
            
        except Exception as e:
            logger.error(f"Error executing MCP tool {name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "toolName": name
            }
    
    def add_server(self, name: str, server: MCPServer):
        """Add an MCP server instance."""
        self.servers[name] = server
        logger.info(f"Added MCP server: {name}")
    
    def remove_server(self, name: str) -> bool:
        """Remove an MCP server instance."""
        if name in self.servers:
            del self.servers[name]
            logger.info(f"Removed MCP server: {name}")
            return True
        return False
    
    def add_client(self, name: str, client: MCPClient):
        """Add an MCP client instance."""
        self.clients[name] = client
        self.registry.set_external_client(name, client)
        logger.info(f"Added MCP client: {name}")
    
    def remove_client(self, name: str) -> bool:
        """Remove an MCP client instance."""
        if name in self.clients:
            del self.clients[name]
            self.registry.remove_external_client(name)
            logger.info(f"Removed MCP client: {name}")
            return True
        return False
    
    def get_registry(self) -> ToolRegistry:
        """Get the underlying tool registry."""
        return self.registry


# Global MCP service instance
mcp_service = MCPService()