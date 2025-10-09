"""P2P Protocol Handlers for Praxis SDK

This module implements protocol handlers for different P2P communication protocols:
- Card exchange protocol for agent capabilities
- Tool execution protocol for remote tool calls
- MCP bridge protocol
- A2A task management protocol
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional

import trio
import trio_asyncio
from libp2p import IHost
from libp2p.network.stream.net_stream import INetStream
from libp2p.peer.id import ID as PeerID

from ..a2a.models import JSONRPCRequest, JSONRPCResponse, TaskStatus
from ..bus import EventBus

logger = logging.getLogger(__name__)

# Protocol IDs
PROTOCOL_MCP = "/praxis/mcp/1.0.0"
PROTOCOL_CARD = "/praxis/card/1.0.0"
PROTOCOL_TOOL = "/praxis/tool/1.0.0"
PROTOCOL_A2A = "/praxis/a2a/1.0.0"


@dataclass
class ToolParameter:
    """Tool parameter specification"""

    name: str
    type: str  # "string", "boolean", "number", "object", "array"
    description: str
    required: bool = False


@dataclass
class ToolSpec:
    """Complete tool specification"""

    name: str
    description: str
    parameters: list[ToolParameter]


@dataclass
class AgentCard:
    """Agent capability card"""

    name: str
    version: str
    peer_id: str
    capabilities: list[str]
    tools: list[ToolSpec]
    timestamp: int

    def model_dump(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> "AgentCard":
        """Create from dictionary"""
        # Handle tools conversion
        tools = []
        for tool_data in data.get("tools", []):
            if isinstance(tool_data, dict):
                params = []
                for param_data in tool_data.get("parameters", []):
                    if isinstance(param_data, dict):
                        params.append(ToolParameter(**param_data))
                tools.append(
                    ToolSpec(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        parameters=params,
                    )
                )

        return cls(
            name=data["name"],
            version=data["version"],
            peer_id=data["peer_id"],
            capabilities=data["capabilities"],
            tools=tools,
            timestamp=data["timestamp"],
        )


@dataclass
class ToolRequest:
    """Tool invocation request"""

    id: str
    name: str
    arguments: dict[str, Any]
    timestamp: int


@dataclass
class ToolResponse:
    """Tool invocation response"""

    id: str
    result: Any = None
    error: str | None = None


@dataclass
class P2PMessage:
    """Generic P2P message"""

    type: str
    id: str
    method: str
    params: Any = None
    result: Any = None
    error: dict[str, Any] | None = None


class ProtocolRegistry:
    """Registry for protocol handlers"""

    def __init__(self):
        self.handlers: dict[str, Callable] = {}

    def register(self, protocol_id: str, handler: Callable):
        """Register a protocol handler"""
        self.handlers[protocol_id] = handler
        logger.debug(f"Registered protocol handler: {protocol_id}")

    def get_handler(self, protocol_id: str) -> Callable | None:
        """Get protocol handler by ID"""
        return self.handlers.get(protocol_id)

    def list_protocols(self) -> list[str]:
        """List all registered protocol IDs"""
        return list(self.handlers.keys())


class P2PProtocolHandler:
    """Main P2P protocol handler managing all communication protocols.

    Handles:
    - Agent card exchange
    - Remote tool execution
    - MCP bridge communication
    - A2A task management
    """

    def __init__(self, host: IHost, event_bus: EventBus, config: Any):
        self.host = host
        self.event_bus = event_bus
        self.config = config

        # State management
        self.peer_cards: dict[str, AgentCard] = {}
        self.our_card: AgentCard | None = None
        self.pending_requests: dict[str, asyncio.Future] = {}

        # Initialize our agent card
        self._initialize_agent_card()

    def _initialize_agent_card(self):
        """Initialize our agent card with default values"""
        self.our_card = AgentCard(
            name=getattr(self.config, "agent_name", "praxis-agent"),
            version=getattr(self.config, "agent_version", "1.0.0"),
            peer_id=str(self.host.get_id()),
            capabilities=["mcp", "dsl", "workflow", "p2p", "a2a"],
            tools=[],  # Will be populated by MCP server
            timestamp=int(time.time()),
        )

    async def handle_card_stream(self, stream: INetStream):
        """Handle agent card exchange protocol"""
        peer_id = str(stream.muxed_conn.peer_id)
        logger.info(f"🎴 Card exchange with peer: {peer_id}")

        try:
            # Send our card first
            our_card_json = json.dumps(self.our_card.model_dump())
            await stream.write(our_card_json.encode())

            # Receive peer's card
            data = await stream.read(4096)
            if data:
                peer_card_data = json.loads(data.decode())
                peer_card = AgentCard.model_validate(peer_card_data)

                # Store peer card
                self.peer_cards[peer_id] = peer_card

                # Publish event
                await self.event_bus.publish(
                    "p2p.card_exchanged",
                    {"peer_id": peer_id, "card": peer_card.model_dump()},
                )

                logger.info(
                    f"✅ Card exchange complete: {peer_card.name} v{peer_card.version}"
                )

        except Exception as e:
            logger.error(f"Error in card exchange with {peer_id}: {e}")
        finally:
            await stream.close()

    async def handle_tool_stream(self, stream: INetStream):
        """Handle tool execution protocol"""
        peer_id = str(stream.muxed_conn.peer_id)
        logger.info(f"🔧 Tool request from peer: {peer_id}")

        try:
            # Receive tool request
            data = await stream.read(4096)
            if not data:
                return

            request_data = json.loads(data.decode())
            request = ToolRequest(**request_data)

            logger.info(
                f"📥 Tool request: {request.name} with args: {request.arguments}"
            )

            # Process tool request through event bus
            response = await self._execute_tool_request(request, peer_id)

            # Send response
            response_json = json.dumps(asdict(response))
            await stream.write(response_json.encode())

            logger.info(f"📤 Tool response sent for: {request.name}")

        except Exception as e:
            logger.error(f"Error handling tool request from {peer_id}: {e}")
            # Send error response
            error_response = ToolResponse(
                id=request.id if "request" in locals() else "unknown", error=str(e)
            )
            try:
                response_json = json.dumps(asdict(error_response))
                await stream.write(response_json.encode())
            except:
                pass
        finally:
            await stream.close()

    async def handle_mcp_stream(self, stream: INetStream):
        """Handle MCP bridge protocol"""
        peer_id = str(stream.muxed_conn.peer_id)
        logger.info(f"📡 MCP stream from peer: {peer_id}")

        try:
            while True:
                # Read message
                data = await stream.read(4096)
                if not data:
                    break

                try:
                    message_data = json.loads(data.decode())
                    message = P2PMessage(**message_data)

                    logger.debug(f"MCP message: {message.method}")

                    # Process MCP message
                    response = await self._process_mcp_message(message, peer_id)

                    # Send response
                    response_json = json.dumps(asdict(response))
                    await stream.write(response_json.encode())

                except json.JSONDecodeError:
                    logger.error("Invalid JSON in MCP stream")
                    break
                except Exception as e:
                    logger.error(f"Error processing MCP message: {e}")
                    break

        except Exception as e:
            logger.error(f"Error in MCP stream with {peer_id}: {e}")
        finally:
            await stream.close()

    async def handle_a2a_stream(self, stream: INetStream):
        """Handle A2A protocol streams with JSON-RPC 2.0"""
        peer_id = str(stream.muxed_conn.peer_id)
        logger.info(f"🔗 A2A stream from peer: {peer_id}")

        try:
            while True:
                # Read JSON-RPC request
                data = await stream.read(4096)
                if not data:
                    break

                try:
                    request_data = json.loads(data.decode())
                    rpc_request = JSONRPCRequest(**request_data)

                    logger.debug(
                        f"A2A request: {rpc_request.method} ID: {rpc_request.id}"
                    )

                    # Process A2A request
                    response = await self._process_a2a_request(rpc_request, peer_id)

                    # Send response
                    response_json = response.model_dump_json()
                    await stream.write(response_json.encode())

                except json.JSONDecodeError:
                    logger.error("Invalid JSON in A2A stream")
                    break
                except Exception as e:
                    logger.error(f"Error processing A2A request: {e}")
                    # Send error response
                    from ..a2a.models import RPCError

                    error_response = JSONRPCResponse(
                        id=request_data.get("id", None),
                        error=RPCError(
                            code=-32603, message="Internal error", data=str(e)
                        ),
                    )
                    error_json = error_response.model_dump_json()
                    await stream.write(error_json.encode())
                    break

        except Exception as e:
            logger.error(f"Error in A2A stream with {peer_id}: {e}")
        finally:
            await stream.close()

    async def _execute_tool_request(
        self, request: ToolRequest, peer_id: str
    ) -> ToolResponse:
        """Execute a tool request locally"""
        try:
            # Publish tool execution event
            execution_result = await self.event_bus.publish_and_wait(
                "tool.execute_remote",
                {
                    "tool_name": request.name,
                    "arguments": request.arguments,
                    "peer_id": peer_id,
                    "request_id": request.id,
                },
                timeout=30.0,
            )

            if execution_result and "result" in execution_result:
                return ToolResponse(id=request.id, result=execution_result["result"])
            return ToolResponse(
                id=request.id, error="Tool execution failed or timed out"
            )

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return ToolResponse(id=request.id, error=str(e))

    async def _process_mcp_message(
        self, message: P2PMessage, peer_id: str
    ) -> P2PMessage:
        """Process MCP protocol message with full JSON-RPC 2.0 compliance"""
        response = P2PMessage(type="response", id=message.id, method=message.method)

        try:
            # Handle MCP JSON-RPC methods
            if message.method == "initialize":
                # Handle MCP server initialization
                response.result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                    "serverInfo": {"name": "praxis-p2p-mcp-bridge", "version": "1.0.0"},
                }

            elif message.method == "tools/list":
                # Return available tools via event bus
                tools_data = await self.event_bus.publish_and_wait(
                    "mcp.tools_list", {"peer_id": peer_id}, timeout=10.0
                )

                tools = tools_data.get("tools", []) if tools_data else []
                response.result = {"tools": tools}

            elif message.method == "tools/call":
                # Execute tool via MCP integration
                if message.params:
                    tool_name = message.params.get("name")
                    args = message.params.get("arguments", {})

                    if not tool_name:
                        response.error = {
                            "code": -32602,
                            "message": "Missing tool name",
                        }
                    else:
                        result = await self.event_bus.publish_and_wait(
                            "mcp.tool_execute",
                            {
                                "tool_name": tool_name,
                                "arguments": args,
                                "peer_id": peer_id,
                            },
                            timeout=60.0,
                        )

                        if result and "error" in result:
                            response.error = result["error"]
                        else:
                            response.result = result.get("result", {}) if result else {}
                else:
                    response.error = {"code": -32602, "message": "Invalid params"}

            elif message.method == "resources/list":
                # List available resources
                resources_data = await self.event_bus.publish_and_wait(
                    "mcp.resources_list", {"peer_id": peer_id}, timeout=10.0
                )

                resources = (
                    resources_data.get("resources", []) if resources_data else []
                )
                response.result = {"resources": resources}

            elif message.method == "resources/read":
                # Read a resource
                if message.params and "uri" in message.params:
                    uri = message.params["uri"]

                    result = await self.event_bus.publish_and_wait(
                        "mcp.resource_read",
                        {"uri": uri, "peer_id": peer_id},
                        timeout=30.0,
                    )

                    if result and "error" in result:
                        response.error = result["error"]
                    else:
                        response.result = result.get("result", {}) if result else {}
                else:
                    response.error = {"code": -32602, "message": "Missing resource URI"}

            elif message.method == "prompts/list":
                # List available prompts
                prompts_data = await self.event_bus.publish_and_wait(
                    "mcp.prompts_list", {"peer_id": peer_id}, timeout=10.0
                )

                prompts = prompts_data.get("prompts", []) if prompts_data else []

            elif message.method == "prompts/get":
                # Get a prompt
                if message.params and "name" in message.params:
                    prompt_name = message.params["name"]
                    arguments = message.params.get("arguments", {})

                    result = await self.event_bus.publish_and_wait(
                        "mcp.prompt_get",
                        {
                            "name": prompt_name,
                            "arguments": arguments,
                            "peer_id": peer_id,
                        },
                        timeout=30.0,
                    )

                    if result and "error" in result:
                        response.error = result["error"]
                    else:
                        response.result = result.get("result", {}) if result else {}
                else:
                    response.error = {"code": -32602, "message": "Missing prompt name"}

            elif message.method == "ping":
                # Health check
                response.result = {"status": "pong", "timestamp": time.time()}

            else:
                response.error = {
                    "code": -32601,
                    "message": f"Method not found: {message.method}",
                }

        except Exception as e:
            logger.error(f"MCP message processing error: {e}")
            response.error = {"code": -32603, "message": f"Internal error: {str(e)}"}

        return response

    async def _process_a2a_request(
        self, request: JSONRPCRequest, peer_id: str
    ) -> JSONRPCResponse:
        """Process A2A JSON-RPC request"""
        try:
            # Route A2A request through event bus
            result = await self.event_bus.publish_and_wait(
                "a2a.request",
                {
                    "method": request.method,
                    "params": request.params,
                    "peer_id": peer_id,
                    "request_id": request.id,
                },
                timeout=60.0,
            )

            if result and "error" in result:
                from ..a2a.models import RPCError

                return JSONRPCResponse(
                    id=request.id,
                    error=RPCError(
                        code=result["error"].get("code", -32603),
                        message=result["error"].get("message", "Internal error"),
                        data=result["error"].get("data"),
                    ),
                )
            return JSONRPCResponse(
                id=request.id, result=result.get("result") if result else None
            )

        except Exception as e:
            logger.error(f"A2A request processing error: {e}")
            from ..a2a.models import RPCError

            return JSONRPCResponse(
                id=request.id,
                error=RPCError(code=-32603, message="Internal error", data=str(e)),
            )

    async def _get_available_tools(self) -> list[dict[str, Any]]:
        """Get list of available tools"""
        try:
            tools_result = await self.event_bus.publish_and_wait(
                "tools.list", {}, timeout=10.0
            )
            return tools_result.get("tools", []) if tools_result else []
        except:
            return []

    # Public API methods
    async def request_card(self, peer_id: str) -> AgentCard | None:
        """Request agent card from a peer"""
        # Check cache first
        if peer_id in self.peer_cards:
            return self.peer_cards[peer_id]

        try:
            logger.info(f"🎴 Requesting card from peer: {peer_id}")

            # Open stream
            peer_id_obj = PeerID.from_base58(peer_id)
            stream = await self.host.new_stream(peer_id_obj, "/praxis/card/1.0.0")

            try:
                # Send our card
                our_card_json = json.dumps(self.our_card.model_dump())
                await stream.write(our_card_json.encode())

                # Receive peer's card
                data = await stream.read(4096)
                if data:
                    peer_card_data = json.loads(data.decode())
                    peer_card = AgentCard.model_validate(peer_card_data)

                    # Cache the card
                    self.peer_cards[peer_id] = peer_card

                    logger.info(
                        f"✅ Received card: {peer_card.name} v{peer_card.version}"
                    )
                    return peer_card

            finally:
                await stream.close()

        except Exception as e:
            logger.error(f"Failed to request card from {peer_id}: {e}")

        return None

    async def send_mcp_request(
        self, peer_id: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Send MCP request to a peer"""
        try:
            logger.info(f"📡 Sending MCP request to peer: {peer_id}")

            # Create MCP message
            message = P2PMessage(
                type="request",
                id=self._generate_id(),
                method=request.get("method", "unknown"),
                params=request.get("params"),
            )

            # Open stream
            peer_id_obj = PeerID.from_base58(peer_id)
            stream = await self.host.new_stream(peer_id_obj, PROTOCOL_MCP)

            try:
                # Send request
                request_json = json.dumps(asdict(message))
                await stream.write(request_json.encode())

                # Receive response
                data = await stream.read(8192)
                if data:
                    response_data = json.loads(data.decode())
                    response = P2PMessage(**response_data)

                    if response.error:
                        return {
                            "jsonrpc": "2.0",
                            "id": request.get("id"),
                            "error": response.error,
                        }
                    return {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": response.result,
                    }
                raise Exception("No response received")

            finally:
                await stream.close()

        except Exception as e:
            logger.error(f"Failed to send MCP request to {peer_id}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32603, "message": str(e)},
            }

    async def send_mcp_response(self, peer_id: str, response: dict[str, Any]) -> bool:
        """Send MCP response to a peer (for bidirectional communication)"""
        try:
            logger.debug(f"📡 Sending MCP response to peer: {peer_id}")

            # Create MCP response message
            message = P2PMessage(
                type="response",
                id=response.get("id", "unknown"),
                method="response",
                result=response.get("result"),
                error=response.get("error"),
            )

            # Open stream
            peer_id_obj = PeerID.from_base58(peer_id)
            stream = await self.host.new_stream(peer_id_obj, PROTOCOL_MCP)

            try:
                # Send response
                response_json = json.dumps(asdict(message))
                await stream.write(response_json.encode())
                return True

            finally:
                await stream.close()

        except Exception as e:
            logger.error(f"Failed to send MCP response to {peer_id}: {e}")
            return False

    async def broadcast_to_peers(self, data: dict[str, Any]) -> int:
        """Broadcast data to all connected peers"""
        success_count = 0

        # Get list of connected peers
        for peer_id in list(self.peer_cards.keys()):
            try:
                message = P2PMessage(
                    type="broadcast",
                    id=self._generate_id(),
                    method="broadcast",
                    params=data,
                )

                peer_id_obj = PeerID.from_base58(peer_id)
                stream = await self.host.new_stream(peer_id_obj, PROTOCOL_MCP)

                try:
                    message_json = json.dumps(asdict(message))
                    await stream.write(message_json.encode())
                    success_count += 1

                finally:
                    await stream.close()

            except Exception as e:
                logger.error(f"Failed to broadcast to peer {peer_id}: {e}")

        logger.info(f"Broadcast sent to {success_count} peers")
        return success_count

    async def send_tool_response(
        self, peer_id: str, response_data: dict[str, Any]
    ) -> bool:
        """Send tool execution response to a peer"""
        try:
            response = ToolResponse(
                id=response_data.get("request_id", "unknown"),
                result=response_data.get("result")
                if response_data.get("success")
                else None,
                error=response_data.get("error")
                if not response_data.get("success")
                else None,
            )

            peer_id_obj = PeerID.from_base58(peer_id)
            stream = await self.host.new_stream(peer_id_obj, PROTOCOL_TOOL)

            try:
                response_json = json.dumps(asdict(response))
                await stream.write(response_json.encode())
                return True

            finally:
                await stream.close()

        except Exception as e:
            logger.error(f"Failed to send tool response to {peer_id}: {e}")
            return False

    async def invoke_tool(
        self, peer_id: str, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        """Invoke a tool on a remote peer"""
        try:
            logger.info(f"🔧 Invoking tool '{tool_name}' on peer: {peer_id}")

            # Create tool request
            request = ToolRequest(
                id=self._generate_id(),
                name=tool_name,
                arguments=arguments,
                timestamp=int(time.time()),
            )

            # Open stream
            peer_id_obj = PeerID.from_base58(peer_id)
            stream = await self.host.new_stream(peer_id_obj, "/praxis/tool/1.0.0")

            try:
                # Send request
                request_json = json.dumps(asdict(request))
                await stream.write(request_json.encode())

                # Receive response
                data = await stream.read(4096)
                if data:
                    response_data = json.loads(data.decode())
                    response = ToolResponse(**response_data)

                    if response.error:
                        raise RuntimeError(f"Tool execution error: {response.error}")

                    logger.info(f"✅ Tool '{tool_name}' executed successfully")
                    return response.result

            finally:
                await stream.close()

        except Exception as e:
            logger.error(f"Failed to invoke tool {tool_name} on {peer_id}: {e}")
            raise

    async def send_a2a_request(
        self, peer_id: str, request: JSONRPCRequest
    ) -> JSONRPCResponse:
        """Send an A2A request to a peer"""
        try:
            logger.info(f"🔗 Sending A2A request to peer: {peer_id}")

            # Open stream
            peer_id_obj = PeerID.from_base58(peer_id)
            stream = await self.host.new_stream(peer_id_obj, "/praxis/a2a/1.0.0")

            try:
                # Send request
                request_json = json.dumps(request.to_dict())
                await stream.write(request_json.encode())

                # Receive response
                data = await stream.read(4096)
                if data:
                    response_data = json.loads(data.decode())
                    response = JSONRPCResponse.from_dict(response_data)

                    logger.info("✅ A2A request completed")
                    return response

            finally:
                await stream.close()

        except Exception as e:
            logger.error(f"Failed to send A2A request to {peer_id}: {e}")
            raise

    def set_agent_card(self, card_data: dict[str, Any]):
        """Set our agent card"""
        self.our_card = AgentCard.model_validate(card_data)

    def get_our_card(self) -> AgentCard:
        """Get our agent card"""
        return self.our_card

    async def get_peer_cards(self) -> dict[str, dict[str, Any]]:
        """Get all cached peer cards"""
        return {peer_id: card.model_dump() for peer_id, card in self.peer_cards.items()}

    async def handle_tool_request(self, data: dict[str, Any]):
        """Handle tool request event from event bus"""
        # This method is called when the event bus receives a tool request
        # It can be used to route tool requests to appropriate handlers

    async def cleanup(self):
        """Clean up protocol handler resources"""
        self.peer_cards.clear()
        self.pending_requests.clear()

    def _generate_id(self) -> str:
        """Generate a unique request ID"""
        return f"{int(time.time() * 1000000)}"
