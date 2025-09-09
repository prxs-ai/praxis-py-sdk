"""
MCP Server implementation using fastmcp library.
Provides built-in tools and connects to external MCP servers.
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
from loguru import logger
from pydantic import BaseModel

from ..bus import EventBus, EventType
from ..config import MCPConfig


# Transport classes for MCP communication
class MCPTransport:
    """Base class for MCP transport mechanisms"""
    
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request and return the response"""
        raise NotImplementedError
    
    async def close(self):
        """Close the transport"""
        pass


class HTTPTransport(MCPTransport):
    """HTTP transport for MCP communication"""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.client = httpx.AsyncClient()
    
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send HTTP request"""
        try:
            response = await self.client.post(
                self.endpoint,
                json=request,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"HTTP transport error: {e}")
            return {"error": {"code": -32603, "message": str(e)}}
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class SSETransport(MCPTransport):
    """Server-Sent Events transport for MCP communication"""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.client = httpx.AsyncClient()
    
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send request via SSE"""
        try:
            # For now, fallback to HTTP POST
            # TODO: Implement proper SSE communication
            response = await self.client.post(
                self.endpoint,
                json=request,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"SSE transport error: {e}")
            return {"error": {"code": -32603, "message": str(e)}}
    
    async def close(self):
        """Close SSE client"""
        await self.client.aclose()


class FileSystemTool(BaseModel):
    """File system tool parameters."""
    operation: str
    path: str
    content: Optional[str] = None
    target: Optional[str] = None


class MCPServer:
    """
    MCP Server with fastmcp integration.
    Provides built-in tools and discovers external MCP servers.
    """
    
    def __init__(self, config: MCPConfig, event_bus: EventBus, external_endpoints: Optional[List[Union[str, Dict[str, Any]]]] = None):
        self.config = config
        self.event_bus = event_bus
        self.external_endpoints: List[Union[str, Dict[str, Any]]] = external_endpoints or []
        
        # Built-in tools registry (since fastmcp not available yet)
        self.builtin_tools: Dict[str, Any] = {}
        
        # External MCP clients
        self.external_clients: Dict[str, httpx.AsyncClient] = {}
        self.external_tools: Dict[str, Dict[str, Any]] = {}
        
        # Setup built-in tools
        self._setup_builtin_tools()
        
        # Running state
        self._running = False
    
    def _setup_builtin_tools(self):
        """Setup built-in MCP tools."""
        
        # File system tools if enabled
        if self.config.filesystem_enabled:
            self._setup_filesystem_tools()
        
        # Add other built-in tools here
        self._setup_system_tools()
    
    def _setup_filesystem_tools(self):
        """Setup filesystem tools with security."""
        root_path = Path(self.config.filesystem_root)
        
        async def read_file(path: str) -> str:
            """Read a file from the filesystem."""
            file_path = self._validate_path(root_path, path)
            
            try:
                content = file_path.read_text()
                
                await self.event_bus.publish_data(
                    EventType.LOG_ENTRY,
                    {"tool": "read_file", "path": str(file_path), "status": "success"}
                )
                
                return content
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                raise
        
        async def write_file(path: str, content: str) -> str:
            """Write content to a file."""
            file_path = self._validate_path(root_path, path)
            
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                
                await self.event_bus.publish_data(
                    EventType.LOG_ENTRY,
                    {"tool": "write_file", "path": str(file_path), "status": "success"}
                )
                
                return f"File written: {file_path}"
            except Exception as e:
                logger.error(f"Error writing file {file_path}: {e}")
                raise
        
        async def list_directory(path: str = ".") -> List[str]:
            """List files in a directory."""
            dir_path = self._validate_path(root_path, path)
            
            try:
                if not dir_path.is_dir():
                    raise ValueError(f"{dir_path} is not a directory")
                
                files = [str(f.relative_to(root_path)) for f in dir_path.iterdir()]
                
                await self.event_bus.publish_data(
                    EventType.LOG_ENTRY,
                    {"tool": "list_directory", "path": str(dir_path), "count": len(files)}
                )
                
                return files
            except Exception as e:
                logger.error(f"Error listing directory {dir_path}: {e}")
                raise
        
        async def create_directory(path: str) -> str:
            """Create a directory."""
            dir_path = self._validate_path(root_path, path)
            
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                
                await self.event_bus.publish_data(
                    EventType.LOG_ENTRY,
                    {"tool": "create_directory", "path": str(dir_path), "status": "success"}
                )
                
                return f"Directory created: {dir_path}"
            except Exception as e:
                logger.error(f"Error creating directory {dir_path}: {e}")
                raise
        
        async def delete_file(path: str) -> str:
            """Delete a file or empty directory."""
            file_path = self._validate_path(root_path, path)
            
            try:
                if file_path.is_dir():
                    file_path.rmdir()  # Only removes empty directories
                else:
                    file_path.unlink()
                
                await self.event_bus.publish_data(
                    EventType.LOG_ENTRY,
                    {"tool": "delete_file", "path": str(file_path), "status": "success"}
                )
                
                return f"Deleted: {file_path}"
            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}")
                raise
        
        async def move_file(source: str, target: str) -> str:
            """Move or rename a file."""
            source_path = self._validate_path(root_path, source)
            target_path = self._validate_path(root_path, target)
            
            try:
                source_path.rename(target_path)
                
                await self.event_bus.publish_data(
                    EventType.LOG_ENTRY,
                    {"tool": "move_file", "source": str(source_path), "target": str(target_path)}
                )
                
                return f"Moved {source_path} to {target_path}"
            except Exception as e:
                logger.error(f"Error moving file: {e}")
                raise
        
        # Register filesystem tools with metadata
        self.builtin_tools["read_file"] = read_file
        self.builtin_tools["write_file"] = write_file
        self.builtin_tools["list_directory"] = list_directory
        self.builtin_tools["create_directory"] = create_directory
        self.builtin_tools["delete_file"] = delete_file
        self.builtin_tools["move_file"] = move_file
        
        # Store tool metadata for LLM function calling
        if not hasattr(self, 'tool_metadata'):
            self.tool_metadata = {}
        
        self.tool_metadata.update({
            "read_file": {
                "description": "Read content from a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to read"
                        }
                    },
                    "required": ["path"]
                }
            },
            "write_file": {
                "description": "Write content to a file",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to write"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        }
                    },
                    "required": ["path", "content"]
                }
            },
            "list_directory": {
                "description": "List files in a directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string", 
                            "description": "Directory path to list (default: current directory)",
                            "default": "."
                        }
                    },
                    "required": []
                }
            }
        })
    
    def _setup_system_tools(self):
        """Setup system information tools."""
        
        async def get_system_info() -> Dict[str, Any]:
            """Get system information."""
            import platform
            
            info = {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "processor": platform.processor(),
                "architecture": platform.architecture()[0],
            }
            
            await self.event_bus.publish_data(
                EventType.LOG_ENTRY,
                {"tool": "get_system_info", "info": info}
            )
            
            return info
        
        async def execute_python(code: str) -> Any:
            """Execute Python code in isolated environment."""
            # Security: This should be sandboxed in production
            try:
                # Create isolated namespace
                namespace = {}
                exec(code, namespace)
                
                result = namespace.get("result", "Code executed successfully")
                
                await self.event_bus.publish_data(
                    EventType.LOG_ENTRY,
                    {"tool": "execute_python", "status": "success"}
                )
                
                return str(result)
            except Exception as e:
                logger.error(f"Error executing Python code: {e}")
                raise
        
        # Register system tools
        self.builtin_tools["get_system_info"] = get_system_info
        self.builtin_tools["execute_python"] = execute_python
    
    def _validate_path(self, root: Path, user_path: str) -> Path:
        """Validate and resolve path with security checks."""
        # Resolve the path relative to root
        resolved = (root / user_path).resolve()
        
        # Check if path is within allowed root
        if not str(resolved).startswith(str(root.resolve())):
            raise ValueError(f"Path {user_path} is outside allowed directory")
        
        return resolved
    
    async def start(self):
        """Start MCP server and discover external servers."""
        if self._running:
            logger.warning("MCP server already running")
            return
        
        self._running = True
        logger.info("Starting MCP server...")
        
        # Discover external MCP servers if enabled
        if self.config.auto_discovery:
            await self._discover_external_servers()

        # Connect to configured MCP servers
        for server_config in self.config.servers:
            if server_config.enabled:
                await self._connect_to_mcp_server(server_config)

        # Connect to explicitly configured external endpoints (agent-level and config-level)
        combined_eps: List[Union[str, Dict[str, Any]]] = []
        combined_eps.extend(self.external_endpoints)
        # Also accept endpoints from config.mcp.external_endpoints
        try:
            if isinstance(self.config.external_endpoints, list):
                combined_eps.extend(self.config.external_endpoints)
        except Exception:
            pass
        
        for endpoint in combined_eps:
            await self._connect_to_external_endpoint(endpoint)
        
        logger.success("MCP server started")
    
    async def stop(self):
        """Stop MCP server and cleanup."""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping MCP server...")
        
        # Close external clients
        for client in self.external_clients.values():
            await client.aclose()
        
        self.external_clients.clear()
        self.external_tools.clear()
        
        logger.info("MCP server stopped")
    
    async def _discover_external_servers(self):
        """Discover external MCP servers on configured ports."""
        logger.info(f"Discovering MCP servers on ports: {self.config.discovery_ports}")
        
        for port in self.config.discovery_ports:
            # Try multiple hosts from inside Docker network and host
            for host in ["localhost", "host.docker.internal", "mcp-filesystem"]:
                base = f"http://{host}:{port}"
                sse_url = f"{base}/sse"
                try:
                    async with httpx.AsyncClient() as client:
                        # Try to connect to SSE endpoint
                        response = await client.get(
                            sse_url,
                            timeout=2.0,
                            headers={"Accept": "text/event-stream"}
                        )
                        
                        if response.status_code == 200:
                            logger.info(f"Found MCP server at {sse_url}")
                            
                            # Initialize
                            info_response = await client.post(
                                f"{base}/",
                                json={
                                    "jsonrpc": "2.0",
                                    "method": "initialize",
                                    "params": {
                                        "protocolVersion": "2024-11-05",
                                        "capabilities": {},
                                        "clientInfo": {
                                            "name": "Praxis Agent",
                                            "version": "0.1.0"
                                        }
                                    },
                                    "id": 1
                                }
                            )
                            
                            if info_response.status_code == 200:
                                server_info = info_response.json()
                                logger.info(f"MCP server info: {server_info}")
                                
                                server_id = f"discovered_{host}_{port}"
                                self.external_clients[server_id] = httpx.AsyncClient(base_url=base)
                                await self._fetch_server_tools(server_id)
                                # Proceed to next port after first success
                                break
                except Exception as e:
                    logger.debug(f"No MCP server at {sse_url}: {e}")

    async def _connect_to_external_endpoint(self, endpoint: Union[str, Dict[str, Any]]):
        """Connect to a user-specified external MCP endpoint.

        Accepts URLs like:
        - http://host:3002
        - http://host:3002/mcp
        - http://host:3002/sse (SSE endpoint)
        """
        try:
            # Parse endpoint into url + headers
            if isinstance(endpoint, dict):
                base_url = endpoint.get("url") or endpoint.get("endpoint") or endpoint.get("address")
                headers = endpoint.get("headers", {})
                name = endpoint.get("name") or base_url
            else:
                base_url = str(endpoint)
                headers = {}
                name = base_url
            # Normalize base URL
            base = base_url.rstrip('/')
            if base.endswith('/mcp') or base.endswith('/sse'):
                base = base.rsplit('/', 1)[0]

            sse_url = f"{base}/sse"
            async with httpx.AsyncClient() as client:
                # Probe SSE
                try:
                    resp = await client.get(sse_url, timeout=2.0, headers={"Accept": "text/event-stream"})
                    if resp.status_code != 200:
                        logger.debug(f"Endpoint {name} SSE probe returned {resp.status_code}")
                except Exception as e:
                    logger.debug(f"Endpoint {name} SSE probe failed: {e}")

                # Initialize JSON-RPC
                init = await client.post(
                    f"{base}/",
                    json={
                        "jsonrpc": "2.0",
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "Praxis Agent", "version": "0.1.0"}
                        },
                        "id": 1
                    }
                )

                if init.status_code == 200:
                    server_id = f"external_{name}"
                    # Create persistent client with default headers if provided
                    self.external_clients[server_id] = httpx.AsyncClient(base_url=base, headers=headers)
                    await self._fetch_server_tools(server_id)
                    logger.success(f"Connected to external MCP: {base}")
                else:
                    logger.warning(f"Failed to initialize external MCP at {base}: HTTP {init.status_code}")
        except Exception as e:
            logger.warning(f"Error connecting to external endpoint {endpoint}: {e}")
    
    async def _connect_to_mcp_server(self, server_config):
        """Connect to a configured MCP server."""
        server_name = server_config.name
        
        try:
            # Parse command to get connection details
            # For now, assume it's a local server with SSE
            if server_config.command and len(server_config.command) > 0:
                # Extract port from command if available
                # Example: ["npx", "@modelcontextprotocol/server-filesystem", "--port", "3001"]
                port = 3001  # Default
                for i, arg in enumerate(server_config.command):
                    if arg == "--port" and i + 1 < len(server_config.command):
                        port = int(server_config.command[i + 1])
                        break
                
                base_url = f"http://localhost:{port}"
                
                # Create client
                client = httpx.AsyncClient(base_url=base_url)
                self.external_clients[server_name] = client
                
                # Initialize connection
                init_response = await client.post(
                    "/",
                    json={
                        "jsonrpc": "2.0",
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {
                                "name": "Praxis Agent",
                                "version": "0.1.0"
                            }
                        },
                        "id": 1
                    }
                )
                
                if init_response.status_code == 200:
                    logger.success(f"Connected to MCP server: {server_name}")
                    
                    # Fetch available tools
                    await self._fetch_server_tools(server_name)
                else:
                    logger.error(f"Failed to initialize MCP server {server_name}")
                    
        except Exception as e:
            logger.error(f"Error connecting to MCP server {server_name}: {e}")
    
    async def _fetch_server_tools(self, server_id: str):
        """Fetch available tools from an MCP server."""
        client = self.external_clients.get(server_id)
        if not client:
            return
        
        try:
            # List available tools
            response = await client.post(
                "/",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": 2
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                tools = result.get("result", {}).get("tools", [])
                
                # Store tools for this server
                self.external_tools[server_id] = {
                    tool["name"]: tool for tool in tools
                }
                
                logger.info(f"Found {len(tools)} tools on {server_id}: {[t['name'] for t in tools]}")
                
        except Exception as e:
            logger.error(f"Error fetching tools from {server_id}: {e}")
    
    async def invoke_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool (built-in or external)."""
        
        logger.info(f"🛠️  MCP TOOL INVOCATION: '{tool_name}'")
        logger.info(f"   📋 Arguments: {arguments}")
        
        # Check if it's a built-in tool
        if tool_name in self.builtin_tools:
            # Invoke built-in tool
            logger.info(f"   🏠 BUILT-IN TOOL: Executing locally")
            tool_func = self.builtin_tools[tool_name]
            try:
                result = await tool_func(**arguments)
                logger.info(f"   ✅ TOOL SUCCESS: {tool_name}")
                logger.info(f"   📤 Result: {str(result)[:200]}...")
                return {"success": True, "result": result}
            except Exception as e:
                logger.error(f"   ❌ TOOL FAILED: {tool_name} - {e}")
                return {"success": False, "error": str(e)}
        
        # Check external tools
        logger.info(f"   🔍 SEARCHING EXTERNAL TOOLS...")
        for server_id, tools in self.external_tools.items():
            if tool_name in tools:
                logger.info(f"   🌐 EXTERNAL TOOL FOUND: {server_id}")
                return await self._invoke_external_tool(server_id, tool_name, arguments)
        
        logger.error(f"   ❌ TOOL NOT FOUND: {tool_name}")
        return {"success": False, "error": f"Tool {tool_name} not found"}
    
    async def _invoke_external_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool on an external MCP server."""
        logger.info(f"   🌐 EXTERNAL TOOL INVOCATION:")
        logger.info(f"      🎯 Server: {server_id}")
        logger.info(f"      🛠️  Tool: {tool_name}")
        logger.info(f"      📋 Args: {arguments}")
        
        client = self.external_clients.get(server_id)
        if not client:
            logger.error(f"   ❌ SERVER NOT CONNECTED: {server_id}")
            return {"success": False, "error": f"Server {server_id} not connected"}
        
        try:
            request_payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                },
                "id": 3
            }
            
            logger.info(f"   📤 SENDING MCP REQUEST:")
            logger.info(f"      🔗 Endpoint: POST /")
            logger.info(f"      📦 Payload: {request_payload}")
            
            response = await client.post("/", json=request_payload)
            
            logger.info(f"   📥 MCP RESPONSE:")
            logger.info(f"      🌟 Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"      📄 Response Body: {result}")
                
                if "error" in result:
                    error_msg = result["error"]["message"]
                    logger.error(f"   ❌ MCP TOOL ERROR: {error_msg}")
                    return {"success": False, "error": error_msg}
                
                logger.info(f"   ✅ EXTERNAL TOOL SUCCESS: {tool_name}")
                return {"success": True, "result": result.get("result")}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error invoking external tool {tool_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available tools."""
        tools = []
        
        # Get built-in tools with proper metadata
        for tool_name in self.builtin_tools.keys():
            tool_metadata = getattr(self, 'tool_metadata', {}).get(tool_name, {})
            tools.append({
                "name": tool_name,
                "description": tool_metadata.get("description", f"Built-in tool: {tool_name}"),
                "source": "built-in",
                "parameters": tool_metadata.get("parameters", {}),
                "agent_id": "local",
                "agent_name": "praxis-agent-1",
                "agent_type": "local"
            })
        
        # Get external tools
        for server_id, server_tools in self.external_tools.items():
            for tool_name, tool_info in server_tools.items():
                tools.append({
                    "name": tool_name,
                    "description": tool_info.get("description", ""),
                    "source": server_id,
                    "parameters": tool_info.get("inputSchema", {}),
                    "agent_id": server_id,
                    "agent_name": f"external-{server_id}",
                    "agent_type": "external"
                })
        
        return tools
    
    async def register_dagger_tool(
        self,
        name: str,
        image: str,
        command: List[str],
        mounts: Dict[str, str] = None,
        env: Dict[str, str] = None,
        description: str = None,
        agent=None
    ):
        """Register a Dagger-based tool for execution via MCP.
        
        Args:
            name: Tool name
            image: Docker image
            command: Command to execute
            mounts: Host to container path mappings
            env: Environment variables
            description: Tool description
            agent: Reference to PraxisAgent for tool execution
        """
        from ..execution.contracts import ToolContract, EngineType
        
        # Create tool contract
        contract = ToolContract.create_dagger_tool(
            name=name,
            image=image,
            command=command,
            mounts=mounts or {},
            env=env or {},
            env_passthrough=["PATH", "HOME", "USER", "OPENAI_API_KEY"],
            description=description
        )
        
        # Create tool handler that uses execution engine
        async def dagger_tool_handler(**args) -> str:
            if not agent:
                raise ValueError("Agent not available for tool execution")
            
            logger.info(f"🐳 DAGGER TOOL EXECUTION STARTED: {name}")
            logger.info(f"   📊 Docker Image: {image}")
            logger.info(f"   🔧 Command: {command}")
            logger.info(f"   📂 Working Dir: {contract.engine_spec.get('working_dir', '/workspace')}")
            logger.info(f"   💾 Input Arguments: {args}")
            logger.info(f"   🔄 DELEGATING TO EXECUTION ENGINE...")
            
            # Execute tool using agent's execution engines
            result = await agent.execute_tool(contract, args)
            
            logger.info(f"   📋 EXECUTION RESULT RECEIVED:")
            logger.info(f"      🎯 Success: {result.success}")
            logger.info(f"      ⏱️  Duration: {getattr(result, 'duration', 'unknown')}s")
            
            if result.success:
                logger.info(f"   ✅ DAGGER TOOL SUCCESS: {name}")
                output_preview = (result.output or 'Tool executed successfully')[:200]
                logger.info(f"   📤 Output Preview: {output_preview}...")
                logger.info(f"   🎉 DAGGER TOOL COMPLETED SUCCESSFULLY")
                return result.output or "Tool executed successfully"
            else:
                logger.error(f"   ❌ DAGGER TOOL FAILED: {name}")
                logger.error(f"      💥 Error: {result.error}")
                logger.error(f"      📄 Output: {result.output or 'No output'}")
                raise ValueError(f"Tool execution failed: {result.error}")
        
        # Register as built-in tool
        self.builtin_tools[name] = dagger_tool_handler
        
        # Store tool metadata for LLM function calling
        if not hasattr(self, 'tool_metadata'):
            self.tool_metadata = {}
            
        self.tool_metadata[name] = {
            "description": description or f"Dagger containerized tool: {name}",
            "parameters": {
                "type": "object",
                "properties": self._infer_dagger_parameters(name, command, description),
                "required": list(self._infer_dagger_parameters(name, command, description).keys())
            }
        }
        
        logger.info(f"Registered Dagger tool: {name}")
        
        return contract
    
    async def register_local_tool(
        self,
        name: str,
        command: List[str],
        working_dir: str = None,
        env: Dict[str, str] = None,
        description: str = None,
        agent=None
    ):
        """Register a local subprocess tool for execution via MCP.
        
        Args:
            name: Tool name
            command: Command to execute
            working_dir: Working directory
            env: Environment variables
            description: Tool description
            agent: Reference to PraxisAgent for tool execution
        """
        from ..execution.contracts import ToolContract, EngineType
        
        # Create tool contract
        contract = ToolContract.create_local_tool(
            name=name,
            command=command,
            working_dir=working_dir,
            env=env or {},
            env_passthrough=["PATH", "HOME", "USER"],
            description=description
        )
        
        # Create tool handler that uses execution engine
        async def local_tool_handler(**args) -> str:
            if not agent:
                raise ValueError("Agent not available for tool execution")
            
            logger.info(f"💻 LOCAL TOOL EXECUTION: {name}")
            logger.info(f"   🔧 Command: {command}")
            logger.info(f"   💾 Arguments: {args}")
            
            # Execute tool using agent's execution engines
            result = await agent.execute_tool(contract, args)
            
            if result.success:
                logger.info(f"   ✅ LOCAL SUCCESS: {name}")
                logger.info(f"   📤 Output: {(result.output or 'Tool executed successfully')[:200]}...")
                return result.output or "Tool executed successfully"
            else:
                logger.error(f"   ❌ LOCAL FAILED: {name} - {result.error}")
                raise ValueError(f"Tool execution failed: {result.error}")
        
        # Register as built-in tool
        self.builtin_tools[name] = local_tool_handler
        logger.info(f"Registered local tool: {name}")
        
        return contract
    
    async def setup_default_dagger_tools(self, agent=None, shared_path: str = "/app/shared"):
        """Setup default Dagger tools similar to Go implementation.
        
        Args:
            agent: Reference to PraxisAgent for tool execution
            shared_path: Path to shared directory for file operations
        """
        if not agent:
            logger.warning("No agent provided - Dagger tools not registered")
            return
        
        # Text analyzer tool using Dagger (containerized execution)
        await self.register_dagger_tool(
            name="analyze_text",
            image="python:3.11-slim",
            command=["python", "/app/tools/text_analyzer/main.py"],
            mounts={
                # Only mount tools directory - remove problematic shared path
                "/app/tools": "/app/tools"
            },
            env={
                "PYTHONPATH": "/app",
                "PYTHONIOENCODING": "utf-8"
            },
            description="Analyze text file using Dagger container: count letters, words, lines. Args: filename='test_text.txt'",
            agent=agent
        )
        
        # Python analyzer tool (equivalent to Go implementation) - FIXED MOUNTS
        await self.register_dagger_tool(
            name="python_analyzer",
            image="python:3.11-slim",
            command=["python", "/app/tools/analyzer.py"],
            mounts={
                "/app/tools": "/app/tools",
                "/app/data": "/app/data"  # Use data directory instead of shared
            },
            env={
                "PYTHONPATH": "/app",
                "LOG_LEVEL": "INFO",
                "ANALYSIS_MODE": "full"
            },
            description="Analyze Python code and generate reports",
            agent=agent
        )
        
        # Simple Dagger demo tool - NO MOUNTS (works everywhere)
        await self.register_dagger_tool(
            name="hello_dagger",
            image="python:3.11-slim",
            command=["python", "-c", """
import time
import os
print("🔍 HELLO FROM DAGGER CONTAINER!")
print("=" * 60)
print(f"📦 Container hostname: {os.uname().nodename}")
print(f"🐍 Python version: {os.sys.version}")
print(f"📁 Current working directory: {os.getcwd()}")
print(f"🌍 Environment ARG_MESSAGE: {os.getenv('ARG_MESSAGE', 'No message')}")
print("⏰ Processing for 2 seconds...")
for i in range(1, 6):
    print(f"   📊 Step {i}/5: Processing...")
    time.sleep(0.4)
print("✅ DAGGER PROCESSING COMPLETED!")
print("📤 Returning result to Praxis system...")
"""],
            mounts={},  # NO EXTERNAL MOUNTS - will always work
            env={},
            description="Simple Dagger demo tool that shows container execution logs - no external files required",
            agent=agent
        )
        
        # Text processor tool
        await self.register_dagger_tool(
            name="text_processor",
            image="busybox:latest", 
            command=["sh", "-c", "echo \"$text\" | wc -w > \"/shared/word_count.txt\""],
            mounts={shared_path: "/shared"},
            env={},
            description="Process text and count words",
            agent=agent
        )
        
        logger.info("Default Dagger tools registered including text analysis")
    
    def _infer_dagger_parameters(self, name: str, command: List[str], description: str = None) -> Dict[str, Any]:
        """Infer parameters for Dagger tools based on name and description."""
        
        # Specific parameter schemas for known tools
        if name == "analyze_text":
            return {
                "filename": {
                    "type": "string",
                    "description": "Name of the text file to analyze (e.g., 'test_text.txt')"
                }
            }
        elif name == "python_analyzer":
            return {
                "input_file": {
                    "type": "string", 
                    "description": "Path to the Python file to analyze"
                }
            }
        elif name == "write_file_docker":
            return {
                "filename": {
                    "type": "string",
                    "description": "Name of the file to create"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            }
        elif name == "text_processor":
            return {
                "text": {
                    "type": "string",
                    "description": "Text to process"
                }
            }
        
        # Default parameters for unknown tools
        return {
            "input": {
                "type": "string",
                "description": f"Input for {name}"
            }
        }
