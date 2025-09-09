"""
P2P Integration Example

This example demonstrates how to integrate the P2P service with the Praxis SDK,
including event bus integration and tool execution across peers.
"""

import asyncio
import logging
from typing import Dict, Any

from praxis_sdk.config import PraxisConfig, load_config
from praxis_sdk.bus import EventBus
from praxis_sdk.p2p import P2PService, AgentCard, ToolSpec, ToolParameter

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class P2PExample:
    """Example P2P integration"""
    
    def __init__(self, config_path: str):
        self.config = load_config(config_path)
        self.event_bus = EventBus()
        self.p2p_service = P2PService(self.config, self.event_bus)
        
        # Setup event handlers
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        """Setup event handlers for P2P and tool events"""
        
        # P2P event handlers
        self.event_bus.subscribe("p2p.peer_discovered", self.on_peer_discovered)
        self.event_bus.subscribe("p2p.peer_connected", self.on_peer_connected)
        self.event_bus.subscribe("p2p.peer_disconnected", self.on_peer_disconnected)
        self.event_bus.subscribe("p2p.card_exchanged", self.on_card_exchanged)
        
        # Tool execution handlers
        self.event_bus.subscribe("tool.execute_remote", self.on_tool_execute)
        self.event_bus.subscribe("tools.list", self.on_tools_list)
        
        # A2A protocol handlers
        self.event_bus.subscribe("a2a.request", self.on_a2a_request)
    
    async def on_peer_discovered(self, data: Dict[str, Any]):
        """Handle peer discovered event"""
        peer_id = data.get("id")
        logger.info(f"🔍 Peer discovered: {peer_id}")
        
        # You can implement custom logic here
        # For example, automatically try to connect or request capabilities
    
    async def on_peer_connected(self, data: Dict[str, Any]):
        """Handle peer connected event"""
        peer_id = data.get("id")
        logger.info(f"🔗 Peer connected: {peer_id}")
        
        # Example: Request peer's capabilities after connection
        try:
            card = await self.p2p_service.protocol_handler.request_card(peer_id)
            if card:
                logger.info(f"Received capabilities from {peer_id}: {card.name}")
        except Exception as e:
            logger.error(f"Failed to request card from {peer_id}: {e}")
    
    async def on_peer_disconnected(self, data: Dict[str, Any]):
        """Handle peer disconnected event"""
        peer_id = data.get("id")
        logger.info(f"💔 Peer disconnected: {peer_id}")
    
    async def on_card_exchanged(self, data: Dict[str, Any]):
        """Handle card exchange event"""
        peer_id = data.get("peer_id")
        card = data.get("card")
        logger.info(f"🎴 Card exchanged with {peer_id}: {card.get('name', 'Unknown')}")
        
        # Log available tools
        tools = card.get("tools", [])
        if tools:
            tool_names = [tool.get("name", "Unknown") for tool in tools]
            logger.info(f"Available tools from {peer_id}: {tool_names}")
    
    async def on_tool_execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution request"""
        tool_name = data.get("tool_name")
        arguments = data.get("arguments", {})
        peer_id = data.get("peer_id")
        
        logger.info(f"🔧 Executing tool '{tool_name}' for peer {peer_id}")
        
        # Example tool implementations
        if tool_name == "echo":
            return {
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Echo: {arguments.get('message', '')}"
                        }
                    ]
                }
            }
        
        elif tool_name == "get_time":
            import time
            return {
                "result": {
                    "content": [
                        {
                            "type": "text", 
                            "text": f"Current time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            }
        
        elif tool_name == "write_file":
            filename = arguments.get("filename")
            content = arguments.get("content", "")
            
            try:
                # Write to shared directory
                shared_path = self.config.shared_directory / filename
                shared_path.write_text(content)
                
                return {
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"File '{filename}' written successfully"
                            }
                        ]
                    }
                }
            except Exception as e:
                return {
                    "error": f"Failed to write file: {e}"
                }
        
        else:
            return {
                "error": f"Unknown tool: {tool_name}"
            }
    
    async def on_tools_list(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools list request"""
        tools = [
            {
                "name": "echo",
                "description": "Echo a message back",
                "parameters": [
                    {
                        "name": "message",
                        "type": "string", 
                        "description": "Message to echo",
                        "required": True
                    }
                ]
            },
            {
                "name": "get_time",
                "description": "Get current system time",
                "parameters": []
            },
            {
                "name": "write_file",
                "description": "Write content to a file",
                "parameters": [
                    {
                        "name": "filename",
                        "type": "string",
                        "description": "Name of the file to write",
                        "required": True
                    },
                    {
                        "name": "content",
                        "type": "string",
                        "description": "Content to write to the file",
                        "required": True
                    }
                ]
            }
        ]
        
        return {"tools": tools}
    
    async def on_a2a_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle A2A protocol request"""
        method = data.get("method")
        params = data.get("params")
        peer_id = data.get("peer_id")
        
        logger.info(f"🔗 A2A request '{method}' from peer {peer_id}")
        
        # Example A2A method handling
        if method == "message/send":
            message = params.get("message", {})
            content = message.get("parts", [{}])[0].get("text", "")
            
            logger.info(f"Received A2A message: {content}")
            
            # Process the message and return a task
            from praxis_sdk.a2a.types import Task, TaskStatus
            
            task = Task(
                id=f"task_{int(asyncio.get_event_loop().time())}",
                context_id=f"context_{peer_id}",
                status=TaskStatus(state="completed", timestamp=asyncio.get_event_loop().time()),
                kind="task"
            )
            
            return {"result": task.to_dict()}
        
        else:
            return {
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found"
                }
            }
    
    async def start(self):
        """Start the P2P service and example"""
        logger.info("Starting P2P integration example...")
        
        # Initialize and start P2P service
        if await self.p2p_service.start():
            logger.info("P2P service started successfully")
            
            # Set our agent card
            our_card_data = {
                "name": "example-agent",
                "version": "1.0.0",
                "peer_id": self.p2p_service.get_peer_id(),
                "capabilities": ["mcp", "p2p", "a2a", "tools"],
                "tools": [
                    {
                        "name": "echo",
                        "description": "Echo a message back",
                        "parameters": [
                            {
                                "name": "message",
                                "type": "string",
                                "description": "Message to echo",
                                "required": True
                            }
                        ]
                    },
                    {
                        "name": "get_time", 
                        "description": "Get current system time",
                        "parameters": []
                    },
                    {
                        "name": "write_file",
                        "description": "Write content to a file", 
                        "parameters": [
                            {
                                "name": "filename",
                                "type": "string",
                                "description": "Name of the file to write",
                                "required": True
                            },
                            {
                                "name": "content",
                                "type": "string", 
                                "description": "Content to write to the file",
                                "required": True
                            }
                        ]
                    }
                ],
                "timestamp": int(asyncio.get_event_loop().time())
            }
            
            self.p2p_service.protocol_handler.set_agent_card(our_card_data)
            
            # Print connection info
            peer_id = self.p2p_service.get_peer_id()
            addresses = self.p2p_service.get_listen_addresses()
            
            logger.info(f"🆔 Peer ID: {peer_id}")
            logger.info(f"📍 Listen addresses: {addresses}")
            
            return True
        else:
            logger.error("Failed to start P2P service")
            return False
    
    async def stop(self):
        """Stop the P2P service"""
        logger.info("Stopping P2P integration example...")
        await self.p2p_service.stop()
        logger.info("P2P integration example stopped")
    
    async def demonstrate_tool_call(self, peer_id: str):
        """Demonstrate calling a tool on a remote peer"""
        try:
            logger.info(f"📞 Calling 'get_time' tool on peer {peer_id}")
            
            result = await self.p2p_service.invoke_tool(
                peer_id=peer_id,
                tool_name="get_time",
                arguments={}
            )
            
            logger.info(f"✅ Tool result: {result}")
            
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
    
    async def demonstrate_a2a_message(self, peer_id: str, message: str):
        """Demonstrate sending an A2A message to a peer"""
        try:
            from praxis_sdk.a2a.types import JSONRPCRequest, Message, MessagePart
            
            # Create A2A message
            message_obj = Message(
                role="user",
                parts=[MessagePart(kind="text", text=message)],
                message_id=f"msg_{int(asyncio.get_event_loop().time())}",
                kind="message"
            )
            
            # Create JSON-RPC request
            request = JSONRPCRequest(
                jsonrpc="2.0",
                id=1,
                method="message/send",
                params={"message": message_obj.to_dict()}
            )
            
            logger.info(f"📨 Sending A2A message to peer {peer_id}: {message}")
            
            response = await self.p2p_service.send_a2a_request(peer_id, request)
            
            logger.info(f"✅ A2A response: {response.to_dict()}")
            
        except Exception as e:
            logger.error(f"A2A message failed: {e}")


async def main():
    """Main example function"""
    # Create example with config
    example = P2PExample("sample_config.yaml")
    
    try:
        # Start the example
        if await example.start():
            logger.info("P2P example running...")
            
            # Keep running and show status
            while True:
                await asyncio.sleep(10)
                
                # Show connected peers
                peers = await example.p2p_service.get_connected_peers()
                if peers:
                    logger.info(f"Connected peers: {len(peers)}")
                    for peer in peers:
                        logger.info(f"  - {peer['id']}")
                        
                        # Demonstrate tool call on first peer
                        if len(peers) == 1:
                            await example.demonstrate_tool_call(peer['id'])
                            await example.demonstrate_a2a_message(
                                peer['id'], 
                                "Hello from P2P example!"
                            )
                else:
                    logger.info("No connected peers")
                
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await example.stop()


if __name__ == "__main__":
    asyncio.run(main())