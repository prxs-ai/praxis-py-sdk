"""
Example demonstrating integration of the event bus with P2P services
using the trio_asyncio.aio_as_trio pattern from the working ai-registry implementation.
"""

import trio
import trio_asyncio
import json
import threading
from typing import Any, Dict, Optional
from dataclasses import dataclass

from libp2p import new_host, IHost
from libp2p.typing import TProtocol
from libp2p.network.stream.net_stream_interface import INetStream
from multiaddr import Multiaddr
from loguru import logger

from praxis_sdk.bus import (
    EventBus, EventType, EventMetadata,
    get_event_bus, set_event_bus
)


# P2P Protocol definitions
CARD_PROTOCOL = TProtocol("/praxis/card/1.0.0")
TOOL_PROTOCOL = TProtocol("/praxis/tool/1.0.0")
REGISTER_PROTOCOL = TProtocol("/praxis/register/1.0.0")


@dataclass
class P2PConfig:
    """P2P service configuration."""
    p2p_port: int = 4001
    keystore_path: str = "./keys"
    noise_key: Optional[str] = None


@dataclass 
class AgentCard:
    """Agent capability card."""
    name: str
    version: str
    peer_id: str
    tools: list
    capabilities: list


class P2PEventService:
    """
    P2P service with comprehensive event bus integration.
    
    This follows the pattern from praxis-internal/services/ai-registry/src/p2p/host.py
    but adds extensive event bus integration for all P2P operations.
    """
    
    def __init__(self, config: P2PConfig, event_bus: Optional[EventBus] = None):
        self.config = config
        self.event_bus = event_bus or get_event_bus()
        self.host: Optional[IHost] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.peer_cards: Dict[str, AgentCard] = {}
        
        # Agent's own card
        self.agent_card = AgentCard(
            name="praxis-python-agent",
            version="1.0.0", 
            peer_id="",  # Will be set after host creation
            tools=["write_file", "read_file", "python_analyzer"],
            capabilities=["file_operations", "code_analysis"]
        )
        
        # Subscribe to system events
        self._setup_event_subscriptions()
    
    def _setup_event_subscriptions(self):
        """Set up event bus subscriptions."""
        # Subscribe to system shutdown
        self.event_bus.subscribe(
            EventType.SYSTEM_SHUTDOWN,
            self._handle_shutdown_event
        )
        
        # Subscribe to tool requests from other components
        self.event_bus.subscribe(
            EventType.P2P_TOOL_REQUEST,
            self._handle_local_tool_request
        )
    
    async def _handle_shutdown_event(self, event_type: str, payload: Any):
        """Handle system shutdown event."""
        logger.info("P2P service received shutdown signal")
        await self.shutdown()
    
    async def _handle_local_tool_request(self, event_type: str, payload: Any):
        """Handle tool execution request from local components."""
        try:
            peer_id = payload.get("peer_id")
            tool_name = payload.get("tool_name")
            args = payload.get("args", {})
            request_id = payload.get("request_id")
            
            if not peer_id or not tool_name:
                logger.error("Invalid tool request: missing peer_id or tool_name")
                return
            
            # Execute remote tool via P2P
            result = await self._execute_remote_tool(peer_id, tool_name, args)
            
            # Publish tool response event
            metadata = EventMetadata(
                source="p2p_service",
                correlation_id=request_id,
                tags={"peer_id": peer_id, "tool": tool_name}
            )
            
            await self.event_bus.publish(
                EventType.P2P_TOOL_RESPONSE,
                {
                    "request_id": request_id,
                    "peer_id": peer_id,
                    "tool_name": tool_name,
                    "result": result,
                    "status": "success" if result.get("success") else "error"
                },
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error handling local tool request: {e}")
            
            # Publish error event
            await self.event_bus.publish(
                EventType.P2P_ERROR,
                {"error": str(e), "context": "local_tool_request"},
                EventMetadata(source="p2p_service")
            )
    
    def _init_host(self) -> IHost:
        """Initialize libp2p host."""
        # For demo purposes, use simple configuration
        return new_host()
    
    async def initialize(self):
        """Initialize the libp2p node with event integration."""
        try:
            self.host = self._init_host()
            
            # Set stream handlers
            self.host.set_stream_handler(CARD_PROTOCOL, self._handle_card_exchange)
            self.host.set_stream_handler(TOOL_PROTOCOL, self._handle_tool_request)
            self.host.set_stream_handler(REGISTER_PROTOCOL, self._handle_register_request)
            
            # Update agent card with peer ID
            self.agent_card.peer_id = str(self.host.get_id())
            
            # Publish initialization event
            metadata = EventMetadata(
                source="p2p_service",
                tags={"peer_id": self.agent_card.peer_id}
            )
            
            await self.event_bus.publish(
                EventType.P2P_PEER_CONNECTED,
                {
                    "peer_id": self.agent_card.peer_id,
                    "agent_card": self.agent_card.__dict__,
                    "status": "initialized"
                },
                metadata=metadata
            )
            
            logger.info(f"P2P host initialized with ID: {self.host.get_id()}")
            return self.host
            
        except Exception as e:
            logger.error(f"Failed to initialize P2P host: {e}")
            
            # Publish error event
            await self.event_bus.publish(
                EventType.P2P_ERROR,
                {"error": str(e), "context": "initialization"},
                EventMetadata(source="p2p_service")
            )
            raise
    
    async def _handle_card_exchange(self, stream: INetStream):
        """Handle agent card exchange protocol."""
        peer_id = str(stream.muxed_conn.peer_id)
        logger.info(f"Card exchange request from {peer_id}")
        
        try:
            # Publish card exchange start event
            metadata = EventMetadata(
                source="p2p_service",
                tags={"peer_id": peer_id, "protocol": "card_exchange"}
            )
            
            await self.event_bus.publish(
                EventType.P2P_CARD_EXCHANGE,
                {
                    "peer_id": peer_id,
                    "status": "started",
                    "direction": "incoming"
                },
                metadata=metadata
            )
            
            # Read peer's card
            card_data = await stream.read(4096)
            if card_data:
                peer_card_dict = json.loads(card_data.decode())
                peer_card = AgentCard(**peer_card_dict)
                
                # Store peer card
                self.peer_cards[peer_id] = peer_card
                
                # Send our card
                our_card_json = json.dumps(self.agent_card.__dict__)
                await stream.write(our_card_json.encode())
                
                # Publish successful card exchange
                await self.event_bus.publish(
                    EventType.P2P_CARD_EXCHANGE,
                    {
                        "peer_id": peer_id,
                        "status": "completed",
                        "peer_card": peer_card.__dict__,
                        "our_card": self.agent_card.__dict__
                    },
                    metadata=metadata
                )
                
                logger.info(f"Card exchange completed with {peer_id}: {peer_card.name}")
            
        except Exception as e:
            logger.error(f"Error in card exchange with {peer_id}: {e}")
            
            # Publish error event
            await self.event_bus.publish(
                EventType.P2P_ERROR,
                {
                    "error": str(e),
                    "context": "card_exchange",
                    "peer_id": peer_id
                },
                EventMetadata(source="p2p_service", tags={"peer_id": peer_id})
            )
        
        finally:
            await stream.close()
    
    async def _handle_tool_request(self, stream: INetStream):
        """Handle tool execution request from remote peer."""
        peer_id = str(stream.muxed_conn.peer_id)
        logger.info(f"Tool request from {peer_id}")
        
        try:
            # Read tool request
            request_data = await stream.read(4096)
            if not request_data:
                await stream.write(json.dumps({"error": "Empty request"}).encode())
                return
            
            tool_request = json.loads(request_data.decode())
            tool_name = tool_request.get("tool_name")
            args = tool_request.get("args", {})
            request_id = tool_request.get("request_id")
            
            # Publish tool request received event
            metadata = EventMetadata(
                source="p2p_service",
                correlation_id=request_id,
                tags={"peer_id": peer_id, "tool": tool_name}
            )
            
            await self.event_bus.publish(
                EventType.P2P_TOOL_REQUEST,
                {
                    "peer_id": peer_id,
                    "tool_name": tool_name,
                    "args": args,
                    "request_id": request_id,
                    "direction": "incoming"
                },
                metadata=metadata
            )
            
            # Execute tool locally
            result = await self._execute_local_tool(tool_name, args)
            
            # Send response
            response = {
                "request_id": request_id,
                "result": result,
                "status": "success" if result.get("success") else "error"
            }
            
            await stream.write(json.dumps(response).encode())
            
            # Publish tool response event
            await self.event_bus.publish(
                EventType.P2P_TOOL_RESPONSE,
                {**response, "peer_id": peer_id, "tool_name": tool_name, "direction": "outgoing"},
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error handling tool request from {peer_id}: {e}")
            
            # Send error response
            error_response = {
                "request_id": tool_request.get("request_id", "unknown"),
                "error": str(e),
                "status": "error"
            }
            await stream.write(json.dumps(error_response).encode())
            
            # Publish error event
            await self.event_bus.publish(
                EventType.P2P_ERROR,
                {**error_response, "peer_id": peer_id, "context": "tool_execution"},
                EventMetadata(source="p2p_service", tags={"peer_id": peer_id})
            )
        
        finally:
            await stream.close()
    
    async def _handle_register_request(self, stream: INetStream):
        """Handle agent registration request."""
        peer_id = str(stream.muxed_conn.peer_id)
        logger.info(f"Registration request from {peer_id}")
        
        try:
            # Read registration data
            reg_data = await stream.read(4096)
            if reg_data:
                registration = json.loads(reg_data.decode())
                
                # Publish registration event
                metadata = EventMetadata(
                    source="p2p_service",
                    tags={"peer_id": peer_id, "protocol": "register"}
                )
                
                await self.event_bus.publish(
                    EventType.P2P_PEER_DISCOVERED,
                    {
                        "peer_id": peer_id,
                        "registration_data": registration,
                        "discovery_method": "direct_registration"
                    },
                    metadata=metadata
                )
                
                # Send acknowledgment
                response = {
                    "status": "registered",
                    "peer_id": self.agent_card.peer_id,
                    "agent_name": self.agent_card.name
                }
                await stream.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Error handling registration from {peer_id}: {e}")
            await stream.write(json.dumps({"error": str(e)}).encode())
        
        finally:
            await stream.close()
    
    async def _execute_local_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool locally."""
        logger.info(f"Executing local tool: {tool_name} with args: {args}")
        
        # Mock tool execution - in real implementation, this would delegate to MCP server
        if tool_name == "write_file":
            filename = args.get("filename", "default.txt")
            content = args.get("content", "")
            
            # Simulate file writing
            await trio.sleep(0.1)  # Simulate I/O
            
            return {
                "success": True,
                "message": f"File {filename} written successfully",
                "bytes_written": len(content)
            }
        
        elif tool_name == "read_file":
            filename = args.get("filename", "default.txt")
            
            # Simulate file reading
            await trio.sleep(0.1)
            
            return {
                "success": True,
                "content": f"Content of {filename}",
                "filename": filename
            }
        
        elif tool_name == "python_analyzer":
            code = args.get("code", "")
            
            # Simulate code analysis
            await trio.sleep(0.2)
            
            return {
                "success": True,
                "analysis": f"Analysis of {len(code)} characters of code",
                "complexity": "low",
                "suggestions": ["Use more descriptive variable names"]
            }
        
        else:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }
    
    async def _execute_remote_tool(self, peer_id: str, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on a remote peer."""
        if peer_id not in self.peer_cards:
            return {"success": False, "error": f"Unknown peer: {peer_id}"}
        
        try:
            # Open stream to peer
            peer_info = self.host.peerstore.peer_info(peer_id)
            stream = await self.host.new_stream(peer_info.peer_id, [TOOL_PROTOCOL])
            
            # Send tool request
            request = {
                "tool_name": tool_name,
                "args": args,
                "request_id": f"req_{trio.current_time()}"
            }
            
            await stream.write(json.dumps(request).encode())
            
            # Read response
            response_data = await stream.read(4096)
            response = json.loads(response_data.decode())
            
            await stream.close()
            return response
            
        except Exception as e:
            logger.error(f"Error executing remote tool on {peer_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _run_in_thread(self):
        """Run P2P service in separate thread using trio_asyncio pattern."""
        try:
            logger.info("Starting P2P service in background thread")
            trio_asyncio.run(self._start)
            
        except KeyboardInterrupt:
            logger.info("P2P thread interrupted by user")
        except Exception as e:
            logger.error(f"Critical error in P2P thread: {e}")
            self._running = False
            raise
        finally:
            logger.info("P2P thread exiting gracefully")
            self._running = False
    
    async def _start(self):
        """Trio-based P2P service implementation."""
        try:
            # Initialize host
            await self.initialize()
            
            # Start listening
            listen_addr = Multiaddr(f"/ip4/0.0.0.0/tcp/{self.config.p2p_port}")
            
            async with self.host.run(listen_addrs=[listen_addr]):
                logger.info(f"P2P service listening on: {self.host.get_addrs()}")
                
                # Publish service started event
                metadata = EventMetadata(
                    source="p2p_service",
                    tags={"peer_id": self.agent_card.peer_id}
                )
                
                await self.event_bus.publish(
                    EventType.AGENT_STARTED,
                    {
                        "service": "p2p",
                        "peer_id": self.agent_card.peer_id,
                        "listening_addresses": [str(addr) for addr in self.host.get_addrs()]
                    },
                    metadata=metadata
                )
                
                # Keep running
                await trio.sleep_forever()
                
        except Exception as e:
            logger.error(f"Failed to start P2P service: {e}")
            await self.event_bus.publish(
                EventType.P2P_ERROR,
                {"error": str(e), "context": "service_start"},
                EventMetadata(source="p2p_service")
            )
            raise
    
    async def start(self):
        """Start P2P service in background thread."""
        if self._running:
            logger.warning("P2P service already running")
            return
        
        try:
            self._running = True
            
            # Start in background thread
            self._thread = threading.Thread(
                target=self._run_in_thread,
                daemon=True,
                name="P2P-Service-Thread"
            )
            self._thread.start()
            
            logger.info("P2P service started in background thread")
            
        except Exception as e:
            self._running = False
            logger.error(f"Failed to start P2P service: {e}")
            
            # Publish error event
            await self.event_bus.publish(
                EventType.P2P_ERROR,
                {"error": str(e), "context": "service_start"},
                EventMetadata(source="p2p_service")
            )
            raise
    
    async def shutdown(self):
        """Shutdown P2P service."""
        if not self._running:
            logger.warning("P2P service is not running")
            return
        
        try:
            logger.info("Shutting down P2P service...")
            
            # Publish shutdown event
            metadata = EventMetadata(
                source="p2p_service",
                tags={"peer_id": self.agent_card.peer_id}
            )
            
            await self.event_bus.publish(
                EventType.AGENT_STOPPING,
                {"service": "p2p", "peer_id": self.agent_card.peer_id},
                metadata=metadata
            )
            
            # Wait for thread to finish
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=10)
                
                if self._thread.is_alive():
                    logger.warning("P2P thread did not shutdown gracefully")
            
            self._running = False
            
            # Publish stopped event
            await self.event_bus.publish(
                EventType.AGENT_STOPPED,
                {"service": "p2p", "peer_id": self.agent_card.peer_id},
                metadata=metadata
            )
            
            logger.info("P2P service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during P2P shutdown: {e}")
            self._running = False
            raise


class EventDrivenAgent:
    """Example agent that uses event-driven architecture."""
    
    def __init__(self):
        self.event_bus = get_event_bus()
        self.p2p_service: Optional[P2PEventService] = None
        self.components = []
        
        # Set up event subscriptions
        self._setup_subscriptions()
    
    def _setup_subscriptions(self):
        """Set up agent-level event subscriptions."""
        # Subscribe to P2P events for coordination
        self.event_bus.subscribe(
            [EventType.P2P_PEER_DISCOVERED, EventType.P2P_PEER_CONNECTED],
            self._handle_peer_events
        )
        
        # Subscribe to task events
        self.event_bus.subscribe(
            [EventType.TASK_CREATED, EventType.TASK_COMPLETED],
            self._handle_task_events
        )
        
        # Subscribe to system events
        self.event_bus.subscribe(
            EventType.SYSTEM_SHUTDOWN,
            self._handle_shutdown
        )
    
    async def _handle_peer_events(self, event_type: str, payload: Any):
        """Handle P2P peer events."""
        if event_type == EventType.P2P_PEER_DISCOVERED.value:
            logger.info(f"Agent: Peer discovered - {payload.get('peer_id')}")
            
            # Could trigger automatic card exchange here
            
        elif event_type == EventType.P2P_PEER_CONNECTED.value:
            logger.info(f"Agent: Peer connected - {payload.get('peer_id')}")
            
            # Could update routing tables or capabilities
    
    async def _handle_task_events(self, event_type: str, payload: Any):
        """Handle task lifecycle events."""
        if event_type == EventType.TASK_CREATED.value:
            logger.info(f"Agent: Task created - {payload.get('task_id')}")
            
            # Could trigger task distribution logic
            
        elif event_type == EventType.TASK_COMPLETED.value:
            logger.info(f"Agent: Task completed - {payload.get('task_id')}")
            
            # Could update metrics or trigger cleanup
    
    async def _handle_shutdown(self, event_type: str, payload: Any):
        """Handle system shutdown."""
        logger.info("Agent: Received shutdown signal")
        await self.stop()
    
    async def start(self):
        """Start the agent."""
        logger.info("Starting event-driven agent")
        
        # Publish agent starting event
        await self.event_bus.publish(
            EventType.AGENT_STARTING,
            {"agent_type": "event_driven", "components": ["p2p", "task_manager"]}
        )
        
        # Start P2P service
        p2p_config = P2PConfig(p2p_port=4001)
        self.p2p_service = P2PEventService(p2p_config, self.event_bus)
        await self.p2p_service.start()
        
        # Wait for P2P to initialize
        await trio.sleep(1)
        
        # Publish agent started event
        await self.event_bus.publish(
            EventType.AGENT_STARTED,
            {
                "agent_type": "event_driven",
                "peer_id": self.p2p_service.agent_card.peer_id if self.p2p_service else None,
                "services": ["p2p"]
            }
        )
        
        logger.info("Event-driven agent started successfully")
    
    async def stop(self):
        """Stop the agent."""
        logger.info("Stopping event-driven agent")
        
        # Stop P2P service
        if self.p2p_service:
            await self.p2p_service.shutdown()
        
        # Cleanup event bus
        await self.event_bus.cleanup()
        
        logger.info("Event-driven agent stopped")


async def main():
    """Main example runner."""
    logger.info("Starting P2P Event Bus Integration Example")
    
    # Initialize event bus
    event_bus = EventBus()
    set_event_bus(event_bus)
    
    # Set up global event logger
    async def global_event_logger(event_type: str, payload: Any):
        logger.info(f"EVENT: {event_type} - {payload}")
    
    # Start main application
    async with trio.open_nursery() as nursery:
        # Set nursery for event bus
        event_bus.set_nursery(nursery)
        
        # Subscribe to all events for logging
        event_bus.subscribe_global(global_event_logger)
        
        # Create and start agent
        agent = EventDrivenAgent()
        await agent.start()
        
        # Simulate some activity
        await trio.sleep(2)
        
        # Simulate task creation
        await event_bus.publish(
            EventType.TASK_CREATED,
            {"task_id": "demo_task", "command": "analyze code", "priority": "high"}
        )
        
        # Simulate tool request
        if agent.p2p_service:
            await event_bus.publish(
                EventType.P2P_TOOL_REQUEST,
                {
                    "peer_id": agent.p2p_service.agent_card.peer_id,
                    "tool_name": "python_analyzer",
                    "args": {"code": "print('hello world')"},
                    "request_id": "demo_req_123"
                }
            )
        
        # Let it run for a while
        await trio.sleep(3)
        
        # Trigger shutdown
        await event_bus.publish(EventType.SYSTEM_SHUTDOWN, {"reason": "demo_complete"})
        
        # Wait for cleanup
        await trio.sleep(1)
    
    logger.info("P2P Event Bus Integration Example completed")


if __name__ == "__main__":
    trio.run(main)