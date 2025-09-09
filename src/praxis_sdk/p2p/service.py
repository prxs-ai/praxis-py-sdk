"""
P2P Service with proper trio_asyncio bridge pattern.
Based on p2p.md instructions and working example from ai-registry.
"""

import json
import os
import threading
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import trio
import trio_asyncio
from libp2p import new_host
from libp2p.crypto.ed25519 import create_new_key_pair
from libp2p.peer.id import ID as PeerID
from libp2p.security.noise.transport import Transport as NoiseTransport, PROTOCOL_ID as NOISE_PROTOCOL_ID
from libp2p.security.insecure.transport import InsecureTransport, PLAINTEXT_PROTOCOL_ID
from libp2p.custom_types import TProtocol
from multiaddr import Multiaddr
from loguru import logger

from ..config import P2PConfig
from ..bus import EventBus, EventType

if TYPE_CHECKING:
    from ..agent import PraxisAgent
    from libp2p.crypto.keys import KeyPair
    from libp2p.abc import IHost, INetStream


# Protocol definitions
A2A_PROTOCOL: TProtocol = TProtocol("/praxis/a2a/1.0.0")
CARD_PROTOCOL: TProtocol = TProtocol("/praxis/card/1.0.0")
TOOL_PROTOCOL: TProtocol = TProtocol("/praxis/tool/1.0.0")
MCP_PROTOCOL: TProtocol = TProtocol("/praxis/mcp/1.0.0")


class P2PService:
    """
    P2P Service with proper trio_asyncio bridge.
    Runs libp2p in separate thread with trio event loop.
    """
    
    def __init__(self, config: P2PConfig, agent: "PraxisAgent"):
        self.config = config
        self.agent = agent
        self.host: Optional["IHost"] = None
        self.running = False
        
        # Threading components for trio isolation
        self._thread: Optional[threading.Thread] = None
        self._trio_token: Optional[trio.lowlevel.TrioToken] = None
        self._ready_event = threading.Event()
        
        # Peer management
        self.connected_peers: Dict[str, Dict[str, Any]] = {}
        self.peer_cards: Dict[str, Dict[str, Any]] = {}
        
        # Initialize keypair
        self.keypair: KeyPair = self._load_or_create_keypair()
    
    def _load_or_create_keypair(self) -> "KeyPair":
        """Load or create Ed25519 keypair."""
        from pathlib import Path
        
        keystore_path = Path(self.config.keystore_path)
        keystore_path.mkdir(parents=True, exist_ok=True)
        
        key_file = keystore_path / "node.key"
        
        if key_file.exists():
            try:
                logger.info(f"Using the existing seed from: {key_file}")
                seed = key_file.read_bytes()
                return create_new_key_pair(seed)
            except Exception as e:
                logger.error(f"Failed to load keypair: {e}")
        
        # Create new keypair with random seed
        logger.info(f"Creating random seed: {key_file}")
        seed = os.urandom(32)
        
        # Save seed for future use
        try:
            key_file.write_bytes(seed)
            logger.info(f"Created and saved new keypair to {key_file}")
        except Exception as e:
            logger.warning(f"Failed to save keypair: {e}")
        
        return create_new_key_pair(seed)
    
    def start(self):
        """
        Start P2P service in separate thread.
        Synchronous call that blocks until service is ready.
        """
        if self.running:
            logger.warning("P2P service is already running")
            return
        
        self.running = True
        self._ready_event.clear()
        
        # Start thread with trio event loop
        self._thread = threading.Thread(
            target=self._run_in_thread,
            daemon=True,
            name="P2P-Trio-Thread"
        )
        self._thread.start()
        
        # Wait for service to be ready
        ready = self._ready_event.wait(timeout=15.0)
        if not ready:
            self.running = False
            raise RuntimeError("P2P service failed to start in time")
        
        logger.success("P2P service started and ready")
    
    def stop(self):
        """
        Stop P2P service.
        Synchronous call from main thread.
        """
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping P2P service...")
        
        # Close libp2p host using trio token
        if self.host and self._trio_token:
            try:
                trio.from_thread.run_sync(
                    self._close_host,
                    trio_token=self._trio_token
                )
            except Exception as e:
                logger.error(f"Error closing libp2p host: {e}")
        
        # Wait for thread to finish
        if self._thread:
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logger.warning("P2P thread did not terminate gracefully")
        
        logger.info("P2P service stopped")
    
    def _run_in_thread(self):
        """
        Thread target function.
        Runs trio_asyncio event loop.
        """
        try:
            # Run Trio event loop in this thread
            trio.run(self._trio_main)
        except Exception as e:
            logger.error(f"P2P trio loop crashed: {e}")
        finally:
            self.running = False
            logger.info("P2P trio loop exited")
    
    async def _trio_main(self):
        """
        Main trio async function.
        All libp2p operations happen here.
        """
        try:
            # Setup security
            sec_opt = self._get_security_options()

            # Create libp2p host (synchronous constructor)
            self.host = new_host(
                key_pair=self.keypair,
                sec_opt=sec_opt
            )

            # Setup protocol handlers
            self._setup_protocol_handlers()

            # Save trio token for cross-thread calls
            self._trio_token = trio.lowlevel.current_trio_token()

            # Start listening
            listen_addr = Multiaddr(f"/ip4/0.0.0.0/tcp/{self.config.port}")

            async with self.host.run(listen_addrs=[listen_addr]):
                peer_id = self.host.get_id()
                addrs = self.host.get_addrs()

                logger.success(f"P2P host started: {peer_id}")
                logger.info(f"Listening on: {addrs}")

                # Signal that we're ready
                self._ready_event.set()

                # Publish event to event bus
                await self._publish_p2p_event(
                    EventType.P2P_PEER_CONNECTED,
                    {"peer_id": str(peer_id), "addresses": [str(a) for a in addrs]}
                )

                # Start additional tasks in nursery
                async with trio.open_nursery() as nursery:
                    # Start mDNS discovery if enabled
                    if self.config.peer_discovery:
                        nursery.start_soon(self._run_mdns_discovery)

                    # Connect to bootstrap nodes if configured
                    if self.config.bootstrap_nodes:
                        nursery.start_soon(self._connect_bootstrap_nodes)

                    # Keep running until stopped
                    while self.running:
                        await trio.sleep(1)
                            
        except Exception as e:
            logger.exception(f"Failed to start P2P host: {e}")
            self._ready_event.set()  # Unblock start() even on error
        finally:
            logger.info("P2P host shutting down")
    
    def _get_security_options(self) -> Dict:
        """Get security transport options."""
        if self.config.security.use_noise and self.config.security.noise_key:
            # Use Noise protocol for encryption
            return {
                NOISE_PROTOCOL_ID: NoiseTransport(
                    libp2p_keypair=self.keypair,
                    noise_privkey=self._decode_noise_key(self.config.security.noise_key)
                )
            }
        else:
            # Use plaintext for development
            return {
                PLAINTEXT_PROTOCOL_ID: InsecureTransport(
                    local_key_pair=self.keypair
                )
            }

    def _compute_peer_id_from_seed(self, seed_path: str) -> Optional[str]:
        """Compute a PeerID (base58) from an ed25519 seed file."""
        try:
            if not os.path.exists(seed_path):
                return None
            seed = open(seed_path, "rb").read()
            kp = create_new_key_pair(seed)
            pid = PeerID.from_pubkey(kp.public_key)
            return pid.to_base58()
        except Exception as e:
            logger.warning(f"Failed to compute peer id from seed {seed_path}: {e}")
            return None
    
    def _decode_noise_key(self, key_str: str):
        """Decode Noise key from string."""
        import base64
        from libp2p.crypto.ed25519 import Ed25519PrivateKey
        return Ed25519PrivateKey.from_bytes(base64.b64decode(key_str))
    
    def _setup_protocol_handlers(self):
        """Setup stream handlers for all protocols."""
        self.host.set_stream_handler(A2A_PROTOCOL, self._handle_a2a_stream)
        self.host.set_stream_handler(CARD_PROTOCOL, self._handle_card_stream)
        self.host.set_stream_handler(TOOL_PROTOCOL, self._handle_tool_stream)
        self.host.set_stream_handler(MCP_PROTOCOL, self._handle_mcp_stream)
    
    async def _handle_a2a_stream(self, stream: "INetStream"):
        """
        Handle A2A protocol stream.
        Runs in trio context, needs bridge to call agent methods.
        """
        peer_id = str(stream.muxed_conn.peer_id)
        
        try:
            # Read request
            request_bytes = await stream.read(8192)
            request = json.loads(request_bytes.decode('utf-8'))
            
            logger.debug(f"A2A request from {peer_id}: {request.get('method')}")
            
            # Bridge to asyncio to call agent method
            response = await trio_asyncio.aio_as_trio(
                self.agent.dispatch_a2a_request
            )(request)
            
            # Send response
            response_bytes = json.dumps(response).encode('utf-8')
            await stream.write(response_bytes)
            
        except Exception as e:
            logger.error(f"Error handling A2A stream from {peer_id}: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": str(e)
                },
                "id": None
            }
            await stream.write(json.dumps(error_response).encode('utf-8'))
        finally:
            await stream.close()
    
    async def _handle_card_stream(self, stream: "INetStream"):
        """Handle agent card exchange (responder side).

        Important: The responder must READ first, then WRITE. The initiator
        does the opposite to avoid a write-write deadlock.
        """
        peer_id = str(stream.muxed_conn.peer_id)

        try:
            # Read peer's card first (responder role)
            card_bytes = await stream.read(8192)
            peer_card = json.loads(card_bytes.decode("utf-8"))

            # Store peer card
            self.peer_cards[peer_id] = peer_card

            # Send our card back
            my_card = await trio_asyncio.aio_as_trio(self.agent.get_agent_card)()
            await stream.write(json.dumps(my_card).encode("utf-8"))

            logger.info(f"Card exchanged with {peer_id}: {peer_card.get('name')}")

            # Publish event
            await self._publish_p2p_event(
                EventType.P2P_CARD_EXCHANGE, {"peer_id": peer_id, "card": peer_card}
            )

        except Exception as e:
            logger.error(f"Error in card exchange with {peer_id}: {e}")
        finally:
            await stream.close()

    async def _exchange_cards_initiator(self, stream: "INetStream"):
        """Initiator side of card exchange: WRITE then READ."""
        peer_id = str(stream.muxed_conn.peer_id)
        try:
            # Send our card first (initiator role)
            my_card = await trio_asyncio.aio_as_trio(self.agent.get_agent_card)()
            await stream.write(json.dumps(my_card).encode("utf-8"))

            # Read peer's card
            card_bytes = await stream.read(8192)
            peer_card = json.loads(card_bytes.decode("utf-8"))

            # Store peer card
            self.peer_cards[peer_id] = peer_card

            logger.info(f"Card exchanged with {peer_id}: {peer_card.get('name')}")

            # Publish event
            await self._publish_p2p_event(
                EventType.P2P_CARD_EXCHANGE, {"peer_id": peer_id, "card": peer_card}
            )

        except Exception as e:
            logger.error(f"Error during initiator card exchange with {peer_id}: {e}")
        finally:
            await stream.close()
    
    async def _handle_tool_stream(self, stream: "INetStream"):
        """Handle remote tool invocation."""
        peer_id = str(stream.muxed_conn.peer_id)
        
        try:
            # Read tool request
            request_bytes = await stream.read(8192)
            request = json.loads(request_bytes.decode('utf-8'))
            
            tool_name = request.get("tool")
            arguments = request.get("arguments", {})
            
            logger.info(f"Tool request from {peer_id}: {tool_name}")
            
            # Execute tool via agent
            result = await trio_asyncio.aio_as_trio(
                self.agent.invoke_tool
            )(tool_name, arguments)
            
            # Send result
            response = {"success": True, "result": result}
            await stream.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error handling tool request from {peer_id}: {e}")
            error_response = {"success": False, "error": str(e)}
            await stream.write(json.dumps(error_response).encode('utf-8'))
        finally:
            await stream.close()
    
    async def _handle_mcp_stream(self, stream: "INetStream"):
        """Handle MCP protocol messages."""
        peer_id = str(stream.muxed_conn.peer_id)
        
        try:
            # Read MCP request
            request_bytes = await stream.read(8192)
            request = json.loads(request_bytes.decode('utf-8'))
            
            logger.debug(f"MCP request from {peer_id}: {request}")
            
            # Process MCP request
            # TODO: Implement MCP protocol handling
            response = {"status": "not_implemented"}
            
            await stream.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error handling MCP stream from {peer_id}: {e}")
        finally:
            await stream.close()
    
    async def _run_mdns_discovery(self):
        """Run mDNS peer discovery."""
        logger.info(f"Starting mDNS discovery for service: {self.config.mdns_service}")
        
        # TODO: Implement actual mDNS discovery
        # For now, just log
        while self.running:
            await trio.sleep(30)  # Check every 30 seconds
    
    async def _connect_bootstrap_nodes(self):
        """Connect to bootstrap nodes."""
        logger.info(f"Connecting to bootstrap nodes: {self.config.bootstrap_nodes}")

        # Give the host a moment to fully initialize
        await trio.sleep(2)

        # Try multiple times to tolerate startup races
        max_rounds = 20  # ~20-40s total depending on sleeps
        for round_idx in range(max_rounds):
            if not self.running:
                return

            for bootstrap_addr in self.config.bootstrap_nodes:
                if not self.running:
                    return

                addr_str = str(bootstrap_addr)
                try:
                    logger.info(f"Attempting to connect to bootstrap node: {addr_str}")

                    # If multiaddr is missing /p2p/<peerid>, try to resolve from shared keystore
                    if "/p2p/" not in addr_str:
                        # Extract hostname or ip from multiaddr to locate keystore
                        # Supported patterns: /dns4/<host>/tcp/<port>, /ip4/<ip>/tcp/<port>
                        try:
                            parts = [p for p in addr_str.split("/") if p]
                            # parts like ['dns4', 'orchestrator', 'tcp', '9000'] or ['ip4','1.2.3.4','tcp','9000']
                            host_label = None
                            if len(parts) >= 2 and parts[0] in ("dns4", "ip4"):
                                host_label = parts[1]
                            # Look for keystore at <keystore_root>/<host_label>/node.key
                            # keystore_root is the parent of our own keystore_path (which is agent-specific)
                            if host_label:
                                from pathlib import Path
                                keystore_root = str(Path(self.config.keystore_path).parent)
                                seed_path = os.path.join(keystore_root, host_label, "node.key")
                                pid = self._compute_peer_id_from_seed(seed_path)
                                if pid:
                                    addr_str = addr_str.rstrip("/") + f"/p2p/{pid}"
                                    logger.info(f"Resolved bootstrap addr via keystore -> {addr_str}")
                        except Exception as e:
                            logger.debug(f"Could not resolve peer id for {addr_str}: {e}")

                    from libp2p.peer.peerinfo import info_from_p2p_addr
                    peer_info = info_from_p2p_addr(Multiaddr(addr_str))

                    # Connect with timeout
                    with trio.move_on_after(self.config.connection_timeout) as cancel_scope:
                        await self.host.connect(peer_info)

                    if cancel_scope.cancelled_caught:
                        logger.warning(f"Bootstrap connection to {peer_info.peer_id} timed out")
                        continue

                    logger.success(f"Connected to bootstrap node: {peer_info.peer_id}")
                    self.connected_peers[str(peer_info.peer_id)] = {
                        "addr": addr_str,
                        "connected": True,
                    }

                    # Exchange cards after successful connection (initiator flow)
                    try:
                        stream = await self.host.new_stream(peer_info.peer_id, [CARD_PROTOCOL])
                        await self._exchange_cards_initiator(stream)
                    except Exception as e:
                        logger.warning(f"Failed to exchange cards with bootstrap node: {e}")

                except Exception as e:
                    logger.error(f"Failed to connect to bootstrap node {addr_str}: {e}")

                # Small delay between bootstrap attempts
                await trio.sleep(1)

            # If we connected to at least one peer, we can stop retrying early
            if self.connected_peers:
                break

            # Wait before the next connection round
            await trio.sleep(2)
    
    async def _publish_p2p_event(self, event_type: EventType, data: Dict[str, Any]):
        """
        Publish event to event bus.
        Bridge from trio to asyncio event bus.
        """
        try:
            await trio_asyncio.aio_as_trio(
                self.agent.event_bus.publish_data
            )(event_type, data, source="p2p_service")
        except Exception as e:
            logger.error(f"Failed to publish P2P event: {e}")
    
    def _close_host(self):
        """Close libp2p host. Called from trio context."""
        if self.host:
            # BasicHost.close() is a blocking function
            self.host.close()
    
    # Public API methods (called from asyncio context)
    
    async def connect_to_peer(self, peer_multiaddr: str) -> Dict[str, Any]:
        """
        Connect to a peer. Called from asyncio context.
        """
        if not self.running or not self._trio_token:
            raise RuntimeError("P2P service is not running")
        
        async def _connect_in_trio():
            """Execute in trio context."""
            logger.info(f"Connecting to peer: {peer_multiaddr}")
            
            from libp2p.peer.peerinfo import info_from_p2p_addr
            peer_info = info_from_p2p_addr(Multiaddr(peer_multiaddr))
            
            # Connect with timeout
            with trio.move_on_after(self.config.connection_timeout) as cancel_scope:
                await self.host.connect(peer_info)
            
            if cancel_scope.cancelled_caught:
                raise ConnectionError(f"Connection to {peer_info.peer_id} timed out")
            
            # Exchange cards after connection (initiator flow)
            stream = await self.host.new_stream(peer_info.peer_id, [CARD_PROTOCOL])
            await self._exchange_cards_initiator(stream)
            
            return {
                "status": "connected",
                "peer_id": str(peer_info.peer_id)
            }
        
        # Execute in trio context from asyncio
        return await trio_asyncio.trio_as_aio(_connect_in_trio)()
    
    async def send_a2a_request(self, peer_id_str: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send A2A request to peer. Called from asyncio context.
        """
        if not self.running or not self._trio_token:
            raise RuntimeError("P2P service is not running")
        
        async def _send_in_trio():
            """Execute in trio context."""
            peer_id = PeerID.from_base58(peer_id_str)
            
            stream = await self.host.new_stream(peer_id, [A2A_PROTOCOL])
            try:
                # Send request
                request_bytes = json.dumps(request).encode('utf-8')
                await stream.write(request_bytes)
                
                # Read response
                response_bytes = await stream.read(8192)
                return json.loads(response_bytes.decode('utf-8'))
                
            finally:
                await stream.close()
        
        # Execute in trio context from asyncio
        return await trio_asyncio.trio_as_aio(_send_in_trio)()
    
    async def invoke_remote_tool(self, peer_id_str: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke tool on remote peer. Called from asyncio context.
        """
        if not self.running or not self._trio_token:
            raise RuntimeError("P2P service is not running")
        
        async def _invoke_in_trio():
            """Execute in trio context."""
            peer_id = PeerID.from_base58(peer_id_str)
            
            stream = await self.host.new_stream(peer_id, [TOOL_PROTOCOL])
            try:
                # Send tool request
                request = {"tool": tool_name, "arguments": arguments}
                await stream.write(json.dumps(request).encode('utf-8'))
                
                # Read response
                response_bytes = await stream.read(8192)
                return json.loads(response_bytes.decode('utf-8'))
                
            finally:
                await stream.close()
        
        # Execute in trio context from asyncio
        return await trio_asyncio.trio_as_aio(_invoke_in_trio)()
    
    def get_peer_id(self) -> Optional[str]:
        """Get our peer ID."""
        return str(self.host.get_id()) if self.host else None
    
    def get_listen_addresses(self) -> List[str]:
        """Get our listen addresses."""
        return [str(a) for a in self.host.get_addrs()] if self.host else []
    
    def get_connected_peers(self) -> List[str]:
        """Get list of connected peer IDs."""
        return list(self.connected_peers.keys())
    
    def get_peer_card(self, peer_id: str) -> Optional[Dict[str, Any]]:
        """Get cached card for a peer."""
        return self.peer_cards.get(peer_id)
