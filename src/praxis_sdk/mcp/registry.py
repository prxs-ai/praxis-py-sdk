"""
MCP Tool Registry Implementation

Central tool registry for all MCP tools with dynamic registration,
schema management, validation, and routing coordination.
"""

import trio
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from loguru import logger
import json
import inspect
from datetime import datetime

from praxis_sdk.bus import event_bus


@dataclass
class ToolInfo:
    """Information about a registered tool"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Optional[Callable] = None
    is_external: bool = False
    server_url: Optional[str] = None
    original_name: Optional[str] = None
    registered_at: str = ""
    last_used: Optional[str] = None
    usage_count: int = 0
    
    def __post_init__(self):
        if not self.registered_at:
            self.registered_at = datetime.now().isoformat()


class ToolRegistry:
    """
    Central registry for all MCP tools with dynamic registration,
    schema validation, and execution coordination
    """
    
    def __init__(self):
        self.tools: Dict[str, ToolInfo] = {}
        self.external_clients: Dict[str, Any] = {}  # MCP clients for external servers
        self.tool_categories: Dict[str, List[str]] = {}
        self._lock = trio.Lock()
    
    def register_tool(self, name: str, description: str, 
                     input_schema: Dict[str, Any], handler: Callable,
                     category: str = "general") -> bool:
        """
        Register a new tool with the registry
        
        Args:
            name: Unique tool name
            description: Tool description
            input_schema: JSON schema for tool input validation
            handler: Async function to handle tool execution
            category: Tool category for organization
            
        Returns:
            True if registered successfully, False if name conflicts
        """
        if name in self.tools:
            logger.warning(f"Tool '{name}' already registered, skipping")
            return False
        
        # Validate handler is callable
        if not callable(handler):
            raise ValueError(f"Tool handler for '{name}' must be callable")
        
        # Validate input schema has required structure
        if not isinstance(input_schema, dict) or "type" not in input_schema:
            raise ValueError(f"Invalid input schema for tool '{name}'")
        
        tool_info = ToolInfo(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler,
            is_external=False
        )
        
        self.tools[name] = tool_info
        
        # Add to category
        if category not in self.tool_categories:
            self.tool_categories[category] = []
        self.tool_categories[category].append(name)
        
        logger.info(f"Registered tool: {name} (category: {category})")
        return True
    
    def register_external_tool(self, name: str, description: str,
                             input_schema: Dict[str, Any], server_url: str,
                             original_name: str, category: str = "external") -> bool:
        """
        Register an external tool from an MCP server
        
        Args:
            name: Unique tool name (usually prefixed)
            description: Tool description
            input_schema: JSON schema for tool input validation
            server_url: URL of the external MCP server
            original_name: Original tool name on the external server
            category: Tool category
            
        Returns:
            True if registered successfully, False if name conflicts
        """
        if name in self.tools:
            logger.warning(f"External tool '{name}' already registered, skipping")
            return False
        
        tool_info = ToolInfo(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=None,  # External tools don't have local handlers
            is_external=True,
            server_url=server_url,
            original_name=original_name
        )
        
        self.tools[name] = tool_info
        
        # Add to category
        if category not in self.tool_categories:
            self.tool_categories[category] = []
        self.tool_categories[category].append(name)
        
        logger.info(f"Registered external tool: {name} -> {server_url}")
        return True
    
    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool from the registry
        
        Args:
            name: Tool name to unregister
            
        Returns:
            True if unregistered successfully, False if not found
        """
        if name not in self.tools:
            return False
        
        tool_info = self.tools[name]
        
        # Remove from categories
        for category, tool_list in self.tool_categories.items():
            if name in tool_list:
                tool_list.remove(name)
                if not tool_list:  # Remove empty categories
                    del self.tool_categories[category]
                break
        
        del self.tools[name]
        
        logger.info(f"Unregistered tool: {name}")
        return True
    
    def get_tool(self, name: str) -> Optional[ToolInfo]:
        """Get tool information by name"""
        return self.tools.get(name)
    
    def list_tools(self, category: Optional[str] = None) -> List[ToolInfo]:
        """
        List all registered tools, optionally filtered by category
        
        Args:
            category: Optional category filter
            
        Returns:
            List of ToolInfo objects
        """
        if category:
            if category in self.tool_categories:
                tool_names = self.tool_categories[category]
                return [self.tools[name] for name in tool_names]
            return []
        
        return list(self.tools.values())
    
    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get JSON schema for a specific tool"""
        tool_info = self.get_tool(name)
        if tool_info:
            return {
                "name": name,
                "description": tool_info.description,
                "inputSchema": tool_info.input_schema
            }
        return None
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get JSON schemas for all registered tools"""
        schemas = []
        for tool_info in self.tools.values():
            schemas.append({
                "name": tool_info.name,
                "description": tool_info.description,
                "inputSchema": tool_info.input_schema
            })
        return schemas
    
    def validate_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """
        Validate arguments against tool's input schema
        
        Args:
            tool_name: Name of the tool
            arguments: Arguments to validate
            
        Returns:
            True if valid, False otherwise
        """
        tool_info = self.get_tool(tool_name)
        if not tool_info:
            return False
        
        # Basic validation - check required properties
        schema = tool_info.input_schema
        if "properties" in schema and "required" in schema:
            required_props = schema["required"]
            for prop in required_props:
                if prop not in arguments:
                    logger.warning(f"Missing required argument '{prop}' for tool '{tool_name}'")
                    return False
        
        return True
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with given arguments
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found or arguments invalid
            Exception: If tool execution fails
        """
        async with self._lock:
            tool_info = self.get_tool(name)
            if not tool_info:
                raise ValueError(f"Tool not found: {name}")
            
            # Validate arguments
            if not self.validate_arguments(name, arguments):
                raise ValueError(f"Invalid arguments for tool: {name}")
            
            # Update usage statistics
            tool_info.last_used = datetime.now().isoformat()
            tool_info.usage_count += 1
            
            try:
                if tool_info.is_external:
                    # Execute external tool via MCP client
                    result = await self._execute_external_tool(tool_info, arguments)
                else:
                    # Execute local tool
                    if inspect.iscoroutinefunction(tool_info.handler):
                        result = await tool_info.handler(**arguments)
                    else:
                        result = tool_info.handler(**arguments)
                
                logger.debug(f"Tool execution successful: {name}")
                return result
            
            except Exception as e:
                logger.error(f"Tool execution failed: {name} - {str(e)}")
                raise
    
    async def _execute_external_tool(self, tool_info: ToolInfo, 
                                   arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an external tool via MCP client
        
        Args:
            tool_info: External tool information
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        server_url = tool_info.server_url
        original_name = tool_info.original_name
        
        if server_url not in self.external_clients:
            raise RuntimeError(f"No MCP client available for server: {server_url}")
        
        client = self.external_clients[server_url]
        
        try:
            result = await client.call_tool(server_url, original_name, arguments)
            return result
        
        except Exception as e:
            logger.error(f"External tool execution failed: {original_name} on {server_url} - {str(e)}")
            raise
    
    def set_external_client(self, server_url: str, client: Any):
        """
        Set MCP client for external server
        
        Args:
            server_url: Server URL
            client: MCP client instance
        """
        self.external_clients[server_url] = client
        logger.info(f"Set MCP client for server: {server_url}")
    
    def remove_external_client(self, server_url: str):
        """Remove MCP client for external server"""
        if server_url in self.external_clients:
            del self.external_clients[server_url]
            logger.info(f"Removed MCP client for server: {server_url}")
    
    def get_tools_by_category(self) -> Dict[str, List[str]]:
        """Get tools organized by category"""
        return self.tool_categories.copy()
    
    def get_tool_statistics(self) -> Dict[str, Any]:
        """Get usage statistics for all tools"""
        stats = {
            "total_tools": len(self.tools),
            "external_tools": len([t for t in self.tools.values() if t.is_external]),
            "local_tools": len([t for t in self.tools.values() if not t.is_external]),
            "categories": len(self.tool_categories),
            "tools_by_category": {cat: len(tools) for cat, tools in self.tool_categories.items()},
            "most_used": [],
            "recently_used": []
        }
        
        # Get most used tools
        used_tools = [(name, info.usage_count) for name, info in self.tools.items() 
                      if info.usage_count > 0]
        used_tools.sort(key=lambda x: x[1], reverse=True)
        stats["most_used"] = used_tools[:10]
        
        # Get recently used tools
        recent_tools = [(name, info.last_used) for name, info in self.tools.items() 
                       if info.last_used]
        recent_tools.sort(key=lambda x: x[1], reverse=True)
        stats["recently_used"] = [name for name, _ in recent_tools[:10]]
        
        return stats
    
    def search_tools(self, query: str, category: Optional[str] = None) -> List[ToolInfo]:
        """
        Search for tools by name or description
        
        Args:
            query: Search query
            category: Optional category filter
            
        Returns:
            List of matching ToolInfo objects
        """
        query_lower = query.lower()
        matches = []
        
        tools_to_search = self.list_tools(category)
        
        for tool_info in tools_to_search:
            if (query_lower in tool_info.name.lower() or 
                query_lower in tool_info.description.lower()):
                matches.append(tool_info)
        
        return matches
    
    async def batch_register_tools(self, tools_config: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Register multiple tools at once
        
        Args:
            tools_config: List of tool configuration dictionaries
            
        Returns:
            Dictionary mapping tool names to registration success status
        """
        results = {}
        
        for tool_config in tools_config:
            try:
                name = tool_config["name"]
                description = tool_config["description"]
                input_schema = tool_config["input_schema"]
                handler = tool_config.get("handler")
                category = tool_config.get("category", "general")
                
                if tool_config.get("is_external", False):
                    success = self.register_external_tool(
                        name=name,
                        description=description,
                        input_schema=input_schema,
                        server_url=tool_config["server_url"],
                        original_name=tool_config["original_name"],
                        category=category
                    )
                else:
                    success = self.register_tool(
                        name=name,
                        description=description,
                        input_schema=input_schema,
                        handler=handler,
                        category=category
                    )
                
                results[name] = success
            
            except Exception as e:
                logger.error(f"Failed to register tool from config: {e}")
                results[tool_config.get("name", "unknown")] = False
        
        return results
    
    def export_tools_config(self) -> List[Dict[str, Any]]:
        """
        Export tool configurations for backup or transfer
        
        Returns:
            List of tool configuration dictionaries
        """
        configs = []
        
        for tool_info in self.tools.values():
            config = {
                "name": tool_info.name,
                "description": tool_info.description,
                "input_schema": tool_info.input_schema,
                "is_external": tool_info.is_external,
                "registered_at": tool_info.registered_at,
                "usage_count": tool_info.usage_count
            }
            
            if tool_info.is_external:
                config["server_url"] = tool_info.server_url
                config["original_name"] = tool_info.original_name
            
            # Find category
            for category, tool_names in self.tool_categories.items():
                if tool_info.name in tool_names:
                    config["category"] = category
                    break
            
            configs.append(config)
        
        return configs
    
    def clear_registry(self):
        """Clear all registered tools"""
        self.tools.clear()
        self.tool_categories.clear()
        self.external_clients.clear()
        logger.info("Cleared tool registry")