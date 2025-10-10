"""Simplified P2P Service based on the working Agent class from agents.py.
Uses direct trio_asyncio.run() approach without complex threading.
Integrates A2A protocol and card exchange functionality.
"""

import asyncio
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional

import trio
import trio_asyncio
from libp2p import new_host
from libp2p.crypto.ed25519 import create_new_key_pair
from libp2p.custom_types import TProtocol
from libp2p.network.stream.net_stream import INetStream
from libp2p.peer.id import ID as PeerID
from libp2p.peer.peerinfo import info_from_p2p_addr
from libp2p.security.insecure.transport import PLAINTEXT_PROTOCOL_ID, InsecureTransport
from loguru import logger
from multiaddr import Multiaddr

from ..bus import EventBus, EventType
from ..config import P2PConfig

if TYPE_CHECKING:
    from libp2p.abc import IHost
    from libp2p.crypto.keys import KeyPair

    from ..agent import PraxisAgent


# Protocol definitions matching our A2A implementation
A2A_PROTOCOL: TProtocol = TProtocol("/praxis/a2a/1.0.0")
CARD_PROTOCOL: TProtocol = TProtocol("/praxis/card/1.0.0")
TOOL_PROTOCOL: TProtocol = TProtocol("/praxis/tool/1.0.0")
EXCHANGE_PROTOCOL: TProtocol = TProtocol("/praxis/exchange/1.0.0")

MAX_READ_LEN = 2**32 - 1


# Connection states for persistent connections
class ConnectionState:
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    EXCHANGING = "exchanging"
    READY = "ready"
    ERROR = "error"


@dataclass
class Message:
    """Simple message format for P2P communication."""

    type: str
    payload: dict[str, Any]

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self)).encode("utf-8")

    @staticmethod
    def from_bytes(data: bytes) -> "Message":
        raw = json.loads(data.decode("utf-8"))
        return Message(raw["type"], raw.get("payload", {}))


class SimplifiedP2PService:
    """Simplified P2P Service using direct trio_asyncio approach.
    Based on the working Agent class from agents.py.
    """

    def __init__(self, config: P2PConfig, agent: "PraxisAgent"):
        self.config = config
        self.agent = agent
        self.host: IHost | None = None
        self.running = False

        # Peer management with persistent connections
        self.connected_peers: dict[str, dict[str, Any]] = {}
        self.peer_cards: dict[str, dict[str, Any]] = {}
        self.peer_tools: dict[str, list[dict[str, Any]]] = {}
        self.persistent_streams: dict[str, INetStream] = {}
        self.connection_states: dict[str, str] = {}
        self._pause_keepalive: dict[str, bool] = {}
        self.peer_addresses: dict[str, str] = {}

        # Initialize persistent keypair using keystore
        self.keypair: KeyPair = self._load_or_create_keypair()

        logger.info(f"Simplified P2P service initialized for {agent.agent_name}")
        logger.debug("Supported protocols: A2A, CARD, TOOL, EXCHANGE")
        logger.debug("Persistent connections enabled: True")

    def _load_or_create_keypair(self) -> "KeyPair":
        """Load or create Ed25519 keypair."""
        keystore_path = Path(self.config.keystore_path)
        keystore_path.mkdir(parents=True, exist_ok=True)

        key_file = keystore_path / "node.key"

        if key_file.exists():
            try:
                logger.info(f"Loading keypair from: {key_file}")
                seed = key_file.read_bytes()
                return create_new_key_pair(seed)
            except Exception as e:
                logger.error(f"Failed to load keypair: {e}")

        # Create new keypair with random seed
        logger.info(f"Creating new keypair: {key_file}")
        seed = os.urandom(32)

        # Save seed for future use
        try:
            key_file.write_bytes(seed)
            logger.info(f"Saved new keypair to {key_file}")
        except Exception as e:
            logger.warning(f"Failed to save keypair: {e}")

        return create_new_key_pair(seed)

    async def handle_stream(self, stream: INetStream) -> None:
        """Handle incoming stream based on protocol.
        This is the main stream handler that routes to specific protocol handlers.
        """
        peer_id = str(stream.muxed_conn.peer_id)
        protocol = str(stream.get_protocol())

        try:
            if protocol == str(A2A_PROTOCOL):
                await self._handle_a2a_stream(stream)
            elif protocol == str(CARD_PROTOCOL):
                await self._handle_card_stream(stream)
            elif protocol == str(TOOL_PROTOCOL):
                await self._handle_tool_stream(stream)
            elif protocol == str(EXCHANGE_PROTOCOL):
                # Handle persistent exchange protocol - don't close stream
                await self._handle_exchange_stream(stream)
                return  # Don't close this stream
            else:
                logger.warning(f"Unknown protocol from {peer_id}: {protocol}")

        except Exception as e:
            logger.error(f"Error handling {protocol} stream from {peer_id}: {e}")
        finally:
            # Only close if not a persistent exchange stream
            if protocol != str(EXCHANGE_PROTOCOL):
                await stream.close()

    async def _handle_a2a_stream(self, stream: INetStream):
        """Handle A2A protocol messages."""
        peer_id = str(stream.muxed_conn.peer_id)

        try:
            # Read A2A request
            data = await stream.read(MAX_READ_LEN)
            request = json.loads(data.decode("utf-8"))

            logger.debug(f"A2A request from {peer_id}: {request.get('method')}")

            # Process A2A request via agent
            response = await trio_asyncio.aio_as_trio(self.agent.dispatch_a2a_request)(
                request
            )

            # Send response
            response_bytes = json.dumps(response).encode("utf-8")
            await stream.write(response_bytes)

        except Exception as e:
            logger.error(f"Error handling A2A stream from {peer_id}: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": str(e)},
                "id": request.get("id") if "request" in locals() else None,
            }
            await stream.write(json.dumps(error_response).encode("utf-8"))

    async def _handle_card_stream(self, stream: INetStream):
        """Handle card exchange (responder side - READ first, then WRITE)."""
        peer_id = str(stream.muxed_conn.peer_id)

        try:
            remote_addr = getattr(
                getattr(stream.muxed_conn.muxed_conn.conn, "transport_conn", None),
                "remote_multiaddr",
                None,
            )
            if remote_addr:
                self.peer_addresses[peer_id] = str(remote_addr)
                logger.debug(
                    f"Responder recorded peer address for {peer_id}: {remote_addr}"
                )
        except Exception:
            pass

        try:
            logger.info(f"🔄 Starting card exchange with {peer_id} (responder)")

            # Read peer's card first (responder role)
            data = await stream.read(MAX_READ_LEN)
            peer_card = json.loads(data.decode("utf-8"))

            # Handle missing or malformed card fields gracefully
            if not peer_card:
                logger.error(f"❌ Received empty card from {peer_id}")
                return

            # Enhanced logging for received peer card
            try:
                peer_name = peer_card.get("name", "unknown")
                peer_version = peer_card.get("version", "unknown")
                peer_skills = peer_card.get("skills", [])
                peer_capabilities = peer_card.get("capabilities", {})
                peer_transports = peer_card.get("supportedTransports", [])
                peer_provider = peer_card.get("provider", {})

                logger.info(f"📥 Received peer card: {peer_name} v{peer_version}")
                if peer_skills:
                    skill_names = []
                    for skill in peer_skills:
                        if isinstance(skill, dict):
                            skill_names.append(
                                skill.get("name", skill.get("id", "unknown"))
                            )
                        else:
                            skill_names.append(str(skill))
                    logger.info(
                        f"🔧 Peer skills: {skill_names} ({len(peer_skills)} total)"
                    )
                else:
                    logger.info("🔧 Peer skills: [] (0 total)")
                logger.info(
                    f"⚡ Peer capabilities: streaming={peer_capabilities.get('streaming', False)}, pushNotifications={peer_capabilities.get('pushNotifications', False)}"
                )
                if peer_transports:
                    logger.info(f"🌐 Peer transports: {peer_transports}")
                if peer_provider.get("name"):
                    logger.info(
                        f"🏢 Peer provider: {peer_provider.get('name')} v{peer_provider.get('version', 'unknown')}"
                    )

            except Exception as e:
                logger.warning(f"⚠️ Error parsing peer card from {peer_id}: {e}")
                logger.debug(f"Raw peer card data: {peer_card}")

            # Store peer card
            self.peer_cards[peer_id] = peer_card

            # Send our card back
            my_card = await trio_asyncio.aio_as_trio(self.agent.get_agent_card)()

            # Enhanced logging for our card being sent
            my_name = my_card.get("name", "unknown")
            my_version = my_card.get("version", "unknown")
            my_skills = my_card.get("skills", [])
            my_capabilities = my_card.get("capabilities", {})
            my_transports = my_card.get("supportedTransports", [])
            my_provider = my_card.get("provider", {})

            logger.info(f"📤 Sending our agent card: {my_name} v{my_version}")
            if my_skills:
                skill_names = []
                for skill in my_skills:
                    if isinstance(skill, dict):
                        skill_names.append(
                            skill.get("name", skill.get("id", "unknown"))
                        )
                    else:
                        skill_names.append(str(skill))
                logger.info(f"🔧 Our skills: {skill_names} ({len(my_skills)} total)")
            else:
                logger.info("🔧 Our skills: [] (0 total)")
            logger.info(
                f"⚡ Our capabilities: streaming={my_capabilities.get('streaming', False)}, pushNotifications={my_capabilities.get('pushNotifications', False)}"
            )
            if my_transports:
                logger.info(f"🌐 Our transports: {my_transports}")
            if my_provider.get("name"):
                logger.info(
                    f"🏢 Our provider: {my_provider.get('name')} v{my_provider.get('version', 'unknown')}"
                )

            await stream.write(json.dumps(my_card).encode("utf-8"))

            # Final success message
            logger.success(
                f"🔄 Card exchange completed with {peer_name} ({peer_id[:8]}...) (responder)"
            )

            # Publish event
            await self._publish_event(
                EventType.P2P_CARD_EXCHANGE, {"peer_id": peer_id, "card": peer_card}
            )

        except Exception as e:
            logger.error(f"❌ Error in card exchange with {peer_id}: {e}")

    async def _handle_tool_stream(self, stream: INetStream):
        """Handle tool invocation requests."""
        peer_id = str(stream.muxed_conn.peer_id)

        try:
            # Read tool request
            data = await stream.read(MAX_READ_LEN)
            request = json.loads(data.decode("utf-8"))

            tool_name = request.get("tool")
            arguments = request.get("arguments", {})

            logger.info(f"Tool request from {peer_id}: {tool_name}")

            # Execute tool via agent
            result = await trio_asyncio.aio_as_trio(self.agent.invoke_tool)(
                tool_name, arguments
            )

            # Send result
            response = {"success": True, "result": result}
            await stream.write(json.dumps(response).encode("utf-8"))

        except Exception as e:
            logger.error(f"Error handling tool request from {peer_id}: {e}")
            error_response = {"success": False, "error": str(e)}
            await stream.write(json.dumps(error_response).encode("utf-8"))

    async def _handle_exchange_stream(self, stream: INetStream):
        """Handle persistent exchange stream for cards and tools."""
        peer_id = str(stream.muxed_conn.peer_id)

        try:
            logger.info(f"Starting exchange stream with {peer_id}")

            # Store persistent stream
            self.persistent_streams[peer_id] = stream
            self.connection_states[peer_id] = ConnectionState.EXCHANGING

            # Exchange cards and tools automatically
            await self._perform_full_exchange(stream, peer_id)

            # Mark connection as ready
            self.connection_states[peer_id] = ConnectionState.READY

            # Keep stream alive - listen for future requests
            await self._keep_stream_alive(stream, peer_id)

        except Exception as e:
            logger.error(f"Error in exchange stream with {peer_id}: {e}")
            self.connection_states[peer_id] = ConnectionState.ERROR
            # Clean up
            if peer_id in self.persistent_streams:
                del self.persistent_streams[peer_id]

    async def _perform_full_exchange(self, stream: INetStream, peer_id: str):
        """Perform full card and tools exchange."""
        try:
            # Step 1: Exchange cards
            logger.info(f"🔄 Starting card exchange with {peer_id}")

            # Send our card first
            my_card = self.agent.get_agent_card()

            # Enhanced logging for our card (responder side)
            my_name = my_card.get("name", "unknown")
            my_version = my_card.get("version", "unknown")
            my_skills = my_card.get("skills", [])
            my_capabilities = my_card.get("capabilities", {})
            my_transports = my_card.get("supportedTransports", [])
            my_provider = my_card.get("provider", {})

            logger.info(f"📤 Sending our agent card: {my_name} v{my_version}")
            if my_skills:
                skill_names = []
                for skill in my_skills:
                    if isinstance(skill, dict):
                        skill_names.append(
                            skill.get("name", skill.get("id", "unknown"))
                        )
                    else:
                        skill_names.append(str(skill))
                logger.info(f"🔧 Our skills: {skill_names} ({len(my_skills)} total)")
            else:
                logger.info("🔧 Our skills: [] (0 total)")
            logger.info(
                f"⚡ Our capabilities: streaming={my_capabilities.get('streaming', False)}, pushNotifications={my_capabilities.get('pushNotifications', False)}"
            )
            if my_transports:
                logger.info(f"🌐 Our transports: {my_transports}")
            if my_provider.get("name"):
                logger.info(
                    f"🏢 Our provider: {my_provider.get('name')} v{my_provider.get('version', 'unknown')}"
                )

            card_message = {"type": "card_exchange", "payload": my_card}
            await stream.write(json.dumps(card_message).encode("utf-8"))

            # Read peer's card
            data = await stream.read(MAX_READ_LEN)
            peer_message = json.loads(data.decode("utf-8"))

            if peer_message.get("type") == "card_exchange":
                peer_card = peer_message.get("payload")

                # Handle missing or malformed card fields gracefully
                if not peer_card:
                    logger.error(f"❌ Received empty card from {peer_id}")
                    return

                self.peer_cards[peer_id] = peer_card

                # Enhanced logging for received peer card
                try:
                    peer_name = peer_card.get("name", "unknown")
                    peer_version = peer_card.get("version", "unknown")
                    peer_skills = peer_card.get("skills", [])
                    peer_capabilities = peer_card.get("capabilities", {})
                    peer_transports = peer_card.get("supportedTransports", [])
                    peer_provider = peer_card.get("provider", {})

                    logger.info(f"📥 Received peer card: {peer_name} v{peer_version}")
                    if peer_skills:
                        skill_names = []
                        for skill in peer_skills:
                            if isinstance(skill, dict):
                                skill_names.append(
                                    skill.get("name", skill.get("id", "unknown"))
                                )
                            else:
                                skill_names.append(str(skill))
                        logger.info(
                            f"🔧 Peer skills: {skill_names} ({len(peer_skills)} total)"
                        )
                    else:
                        logger.info("🔧 Peer skills: [] (0 total)")
                    logger.info(
                        f"⚡ Peer capabilities: streaming={peer_capabilities.get('streaming', False)}, pushNotifications={peer_capabilities.get('pushNotifications', False)}"
                    )
                    if peer_transports:
                        logger.info(f"🌐 Peer transports: {peer_transports}")
                    if peer_provider.get("name"):
                        logger.info(
                            f"🏢 Peer provider: {peer_provider.get('name')} v{peer_provider.get('version', 'unknown')}"
                        )

                except Exception as e:
                    logger.warning(f"⚠️ Error parsing peer card from {peer_id}: {e}")
                    logger.debug(f"Raw peer card data: {peer_card}")
            else:
                logger.error(
                    f"❌ Invalid card exchange message from {peer_id}: expected 'card_exchange', got '{peer_message.get('type')}'"
                )
                return

            # Step 2: Exchange tools
            logger.info(f"🔧 Starting tools exchange with {peer_id}")

            # Send our tools
            my_tools = self.agent.get_available_tools()
            tools_message = {"type": "tools_exchange", "payload": my_tools}
            await stream.write(json.dumps(tools_message).encode("utf-8"))

            # Read peer's tools
            data = await stream.read(MAX_READ_LEN)
            peer_tools_message = json.loads(data.decode("utf-8"))

            if peer_tools_message.get("type") == "tools_exchange":
                peer_tools = peer_tools_message.get("payload", [])
                self.peer_tools[peer_id] = peer_tools
                logger.info(f"Received {len(peer_tools)} tools from {peer_id}")

                # Log available tools from peer
                for tool in peer_tools[:5]:  # Show first 5 tools
                    logger.debug(
                        f"  - {tool.get('name')}: {tool.get('description', 'No description')}"
                    )

            # Final success message with summary
            peer_card = self.peer_cards.get(peer_id, {})
            peer_name = peer_card.get("name", "unknown")
            logger.success(
                f"🔄 Card exchange completed with {peer_name} ({peer_id[:8]}...)"
            )
            logger.info(
                f"✅ Exchange summary: {peer_name} has {len(peer_tools)} tools and {len(peer_card.get('skills', []))} skills"
            )

            # Publish successful exchange event
            await self._publish_event(
                EventType.P2P_CARD_EXCHANGE,
                {
                    "peer_id": peer_id,
                    "card": peer_card,
                    "tools_count": len(peer_tools),
                    "exchange_type": "full_exchange",
                },
            )

        except Exception as e:
            logger.error(f"Error during full exchange with {peer_id}: {e}")
            raise

    async def _keep_stream_alive(self, stream: INetStream, peer_id: str):
        """Keep stream alive and handle future requests."""
        logger.info(f"Keeping exchange stream alive with {peer_id}")

        try:
            while peer_id in self.persistent_streams and self.running:
                if self._pause_keepalive.get(peer_id):
                    await trio.sleep(0.1)
                    continue
                # Send periodic heartbeat
                heartbeat_message = {
                    "type": "heartbeat",
                    "timestamp": trio.current_time(),
                }
                try:
                    await stream.write(json.dumps(heartbeat_message).encode("utf-8"))
                except Exception as e:
                    msg = str(e).lower()
                    if "closed" in msg and "write" in msg:
                        logger.info(
                            f"Heartbeat write failed; stream closed by peer {peer_id}"
                        )
                    else:
                        logger.error(f"Heartbeat write error with {peer_id}: {e}")
                    break

                # Wait for response or timeout
                with trio.move_on_after(30) as cancel_scope:  # 30 second timeout
                    data = await stream.read(MAX_READ_LEN)
                    if data:
                        response = json.loads(data.decode("utf-8"))
                        if response.get("type") == "tool_request":
                            # Handle remote tool request via persistent stream
                            await self._handle_persistent_tool_request(
                                stream, response, peer_id
                            )

                if cancel_scope.cancelled_caught:
                    logger.debug(f"Heartbeat timeout with {peer_id}, continuing...")

                # Sleep before next heartbeat
                await trio.sleep(30)

        except Exception as e:
            logger.error(f"Error keeping stream alive with {peer_id}: {e}")
        finally:
            # Clean up persistent stream
            if peer_id in self.persistent_streams:
                del self.persistent_streams[peer_id]
            self.connection_states[peer_id] = ConnectionState.DISCONNECTED
            logger.info(f"Persistent stream with {peer_id} closed")

    async def _handle_persistent_tool_request(
        self, stream: INetStream, request: dict[str, Any], peer_id: str
    ):
        """Handle tool request via persistent stream."""
        try:
            # Avoid concurrent writes from keepalive
            self._pause_keepalive[peer_id] = True
            payload = request.get("payload", {})
            tool_name = payload.get("tool")
            arguments = payload.get("arguments", {})
            request_id = payload.get("request_id")

            logger.info(f"Persistent tool request from {peer_id}: {tool_name}")

            # Execute tool
            result = await trio_asyncio.aio_as_trio(self.agent.invoke_tool)(
                tool_name, arguments
            )

            # Send response
            response_message = {
                "type": "tool_response",
                "payload": {
                    "request_id": request_id,
                    "success": True,
                    "result": result,
                },
            }
            await stream.write(json.dumps(response_message).encode("utf-8"))

        except Exception as e:
            logger.error(f"Error handling persistent tool request from {peer_id}: {e}")
            error_response = {
                "type": "tool_response",
                "payload": {
                    "request_id": request.get("payload", {}).get("request_id"),
                    "success": False,
                    "error": str(e),
                },
            }
            await stream.write(json.dumps(error_response).encode("utf-8"))
        finally:
            # Resume keepalive
            self._pause_keepalive[peer_id] = False

    async def _exchange_cards_initiator(self, stream: INetStream):
        """Initiator side of card exchange: WRITE then read."""
        peer_id = str(stream.muxed_conn.peer_id)

        try:
            logger.info(
                f"🔄 Starting card exchange with {peer_id} (card-only initiator)"
            )

            # Send our card first (initiator role)
            my_card = await trio_asyncio.aio_as_trio(self.agent.get_agent_card)()

            # Enhanced logging for our card being sent
            my_name = my_card.get("name", "unknown")
            my_version = my_card.get("version", "unknown")
            my_skills = my_card.get("skills", [])
            my_capabilities = my_card.get("capabilities", {})
            my_transports = my_card.get("supportedTransports", [])
            my_provider = my_card.get("provider", {})

            logger.info(f"📤 Sending our agent card: {my_name} v{my_version}")
            if my_skills:
                skill_names = []
                for skill in my_skills:
                    if isinstance(skill, dict):
                        skill_names.append(
                            skill.get("name", skill.get("id", "unknown"))
                        )
                    else:
                        skill_names.append(str(skill))
                logger.info(f"🔧 Our skills: {skill_names} ({len(my_skills)} total)")
            else:
                logger.info("🔧 Our skills: [] (0 total)")
            logger.info(
                f"⚡ Our capabilities: streaming={my_capabilities.get('streaming', False)}, pushNotifications={my_capabilities.get('pushNotifications', False)}"
            )
            if my_transports:
                logger.info(f"🌐 Our transports: {my_transports}")
            if my_provider.get("name"):
                logger.info(
                    f"🏢 Our provider: {my_provider.get('name')} v{my_provider.get('version', 'unknown')}"
                )

            await stream.write(json.dumps(my_card).encode("utf-8"))

            # Read peer's card
            data = await stream.read(MAX_READ_LEN)
            peer_card = json.loads(data.decode("utf-8"))

            # Handle missing or malformed card fields gracefully
            if not peer_card:
                logger.error(f"❌ Received empty card from {peer_id}")
                return

            # Store peer card
            self.peer_cards[peer_id] = peer_card

            # Enhanced logging for received peer card
            try:
                peer_name = peer_card.get("name", "unknown")
                peer_version = peer_card.get("version", "unknown")
                peer_skills = peer_card.get("skills", [])
                peer_capabilities = peer_card.get("capabilities", {})
                peer_transports = peer_card.get("supportedTransports", [])
                peer_provider = peer_card.get("provider", {})

                logger.info(f"📥 Received peer card: {peer_name} v{peer_version}")
                if peer_skills:
                    skill_names = []
                    for skill in peer_skills:
                        if isinstance(skill, dict):
                            skill_names.append(
                                skill.get("name", skill.get("id", "unknown"))
                            )
                        else:
                            skill_names.append(str(skill))
                    logger.info(
                        f"🔧 Peer skills: {skill_names} ({len(peer_skills)} total)"
                    )
                else:
                    logger.info("🔧 Peer skills: [] (0 total)")
                logger.info(
                    f"⚡ Peer capabilities: streaming={peer_capabilities.get('streaming', False)}, pushNotifications={peer_capabilities.get('pushNotifications', False)}"
                )
                if peer_transports:
                    logger.info(f"🌐 Peer transports: {peer_transports}")
                if peer_provider.get("name"):
                    logger.info(
                        f"🏢 Peer provider: {peer_provider.get('name')} v{peer_provider.get('version', 'unknown')}"
                    )

                # Final success message
                logger.success(
                    f"🔄 Card exchange completed with {peer_name} ({peer_id[:8]}...) (card-only initiator)"
                )

            except Exception as e:
                logger.warning(f"⚠️ Error parsing peer card from {peer_id}: {e}")
                logger.debug(f"Raw peer card data: {peer_card}")

            # Publish event
            await self._publish_event(
                EventType.P2P_CARD_EXCHANGE, {"peer_id": peer_id, "card": peer_card}
            )

        except Exception as e:
            logger.error(f"❌ Error during initiator card exchange with {peer_id}: {e}")

    async def _initiate_persistent_exchange(self, peer_id: PeerID) -> bool:
        """Initiate persistent exchange stream with peer."""
        peer_id_str = str(peer_id)

        try:
            logger.info(f"Initiating persistent exchange with {peer_id_str}")

            # Create persistent exchange stream
            stream = await self.host.new_stream(peer_id, [EXCHANGE_PROTOCOL])

            # Store stream and update state
            self.persistent_streams[peer_id_str] = stream
            self.connection_states[peer_id_str] = ConnectionState.EXCHANGING

            # Perform exchange as initiator
            await self._perform_full_exchange_initiator(stream, peer_id_str)

            # Mark as ready
            self.connection_states[peer_id_str] = ConnectionState.READY

            # Start background task to keep stream alive.
            # trio_asyncio.trio_as_aio returns an asyncio.Future, so schedule it with ensure_future
            import asyncio

            asyncio.ensure_future(
                trio_asyncio.trio_as_aio(self._keep_stream_alive_initiator)(
                    stream, peer_id_str
                )
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to initiate persistent exchange with {peer_id_str}: {e}"
            )
            self.connection_states[peer_id_str] = ConnectionState.ERROR
            return False

    async def _perform_full_exchange_initiator(self, stream: INetStream, peer_id: str):
        """Perform full exchange as initiator."""
        try:
            try:
                remote_addr = getattr(
                    getattr(stream.muxed_conn.muxed_conn.conn, "transport_conn", None),
                    "remote_multiaddr",
                    None,
                )
                if remote_addr:
                    self.peer_addresses[peer_id] = str(remote_addr)
                    logger.debug(
                        f"Initiator recorded peer address for {peer_id}: {remote_addr}"
                    )
            except Exception:
                pass

            # Step 1: Send our card
            logger.info(f"🔄 Starting card exchange with {peer_id} (initiator)")

            my_card = self.agent.get_agent_card()

            # Enhanced logging for our card (initiator side)
            my_name = my_card.get("name", "unknown")
            my_version = my_card.get("version", "unknown")
            my_skills = my_card.get("skills", [])
            my_capabilities = my_card.get("capabilities", {})
            my_transports = my_card.get("supportedTransports", [])
            my_provider = my_card.get("provider", {})

            logger.info(f"📤 Sending our agent card: {my_name} v{my_version}")
            if my_skills:
                skill_names = []
                for skill in my_skills:
                    if isinstance(skill, dict):
                        skill_names.append(
                            skill.get("name", skill.get("id", "unknown"))
                        )
                    else:
                        skill_names.append(str(skill))
                logger.info(f"🔧 Our skills: {skill_names} ({len(my_skills)} total)")
            else:
                logger.info("🔧 Our skills: [] (0 total)")
            logger.info(
                f"⚡ Our capabilities: streaming={my_capabilities.get('streaming', False)}, pushNotifications={my_capabilities.get('pushNotifications', False)}"
            )
            if my_transports:
                logger.info(f"🌐 Our transports: {my_transports}")
            if my_provider.get("name"):
                logger.info(
                    f"🏢 Our provider: {my_provider.get('name')} v{my_provider.get('version', 'unknown')}"
                )

            card_message = {"type": "card_exchange", "payload": my_card}
            await stream.write(json.dumps(card_message).encode("utf-8"))

            # Read peer's card
            data = await stream.read(MAX_READ_LEN)
            peer_message = json.loads(data.decode("utf-8"))

            if peer_message.get("type") == "card_exchange":
                peer_card = peer_message.get("payload")

                # Handle missing or malformed card fields gracefully
                if not peer_card:
                    logger.error(f"❌ Received empty card from {peer_id}")
                    return

                self.peer_cards[peer_id] = peer_card

                # Enhanced logging for received peer card
                try:
                    peer_name = peer_card.get("name", "unknown")
                    peer_version = peer_card.get("version", "unknown")
                    peer_skills = peer_card.get("skills", [])
                    peer_capabilities = peer_card.get("capabilities", {})
                    peer_transports = peer_card.get("supportedTransports", [])
                    peer_provider = peer_card.get("provider", {})

                    logger.info(f"📥 Received peer card: {peer_name} v{peer_version}")
                    if peer_skills:
                        skill_names = []
                        for skill in peer_skills:
                            if isinstance(skill, dict):
                                skill_names.append(
                                    skill.get("name", skill.get("id", "unknown"))
                                )
                            else:
                                skill_names.append(str(skill))
                        logger.info(
                            f"🔧 Peer skills: {skill_names} ({len(peer_skills)} total)"
                        )
                    else:
                        logger.info("🔧 Peer skills: [] (0 total)")
                    logger.info(
                        f"⚡ Peer capabilities: streaming={peer_capabilities.get('streaming', False)}, pushNotifications={peer_capabilities.get('pushNotifications', False)}"
                    )
                    if peer_transports:
                        logger.info(f"🌐 Peer transports: {peer_transports}")
                    if peer_provider.get("name"):
                        logger.info(
                            f"🏢 Peer provider: {peer_provider.get('name')} v{peer_provider.get('version', 'unknown')}"
                        )

                except Exception as e:
                    logger.warning(f"⚠️ Error parsing peer card from {peer_id}: {e}")
                    logger.debug(f"Raw peer card data: {peer_card}")
            else:
                logger.error(
                    f"❌ Invalid card exchange message from {peer_id}: expected 'card_exchange', got '{peer_message.get('type')}'"
                )
                return

            # Step 2: Send our tools
            logger.info(f"🔧 Starting tools exchange with {peer_id} (initiator)")
            my_tools = self.agent.get_available_tools()
            tools_message = {"type": "tools_exchange", "payload": my_tools}
            await stream.write(json.dumps(tools_message).encode("utf-8"))

            # Read peer's tools
            data = await stream.read(MAX_READ_LEN)
            peer_tools_message = json.loads(data.decode("utf-8"))

            if peer_tools_message.get("type") == "tools_exchange":
                peer_tools = peer_tools_message.get("payload", [])
                self.peer_tools[peer_id] = peer_tools
                logger.info(f"Received {len(peer_tools)} tools from {peer_id}")

                # Log available tools from peer
                for tool in peer_tools[:5]:  # Show first 5 tools
                    logger.debug(
                        f"  - {tool.get('name')}: {tool.get('description', 'No description')}"
                    )

            # Final success message with summary
            peer_card = self.peer_cards.get(peer_id, {})
            peer_name = peer_card.get("name", "unknown")
            logger.success(
                f"🔄 Card exchange completed with {peer_name} ({peer_id[:8]}...) (initiator)"
            )
            logger.info(
                f"✅ Exchange summary: {peer_name} has {len(peer_tools)} tools and {len(peer_card.get('skills', []))} skills"
            )

        except Exception as e:
            logger.error(f"Error during initiator full exchange with {peer_id}: {e}")
            raise

    async def _keep_stream_alive_initiator(self, stream: INetStream, peer_id: str):
        """Keep stream alive as initiator."""
        logger.info(f"Keeping initiator stream alive with {peer_id}")

        try:
            while peer_id in self.persistent_streams and self.running:
                if self._pause_keepalive.get(peer_id):
                    await trio.sleep(0.1)
                    continue
                # Wait for heartbeat from responder
                with trio.move_on_after(60) as cancel_scope:  # 60 second timeout
                    data = await stream.read(MAX_READ_LEN)
                    if data:
                        message = json.loads(data.decode("utf-8"))
                        msg_type = message.get("type")
                        if msg_type == "heartbeat":
                            # Respond to heartbeat
                            response = {"type": "heartbeat_ack"}
                            try:
                                await stream.write(json.dumps(response).encode("utf-8"))
                            except Exception as e:
                                msg = str(e).lower()
                                if "closed" in msg and "write" in msg:
                                    logger.info(
                                        f"Heartbeat ack write failed; stream closed by peer {peer_id}"
                                    )
                                else:
                                    logger.error(
                                        f"Heartbeat ack write error with {peer_id}: {e}"
                                    )
                                break
                        elif msg_type == "tool_request":
                            # Support tool invocation initiated by responder over persistent stream
                            await self._handle_persistent_tool_request(
                                stream, message, peer_id
                            )

                if cancel_scope.cancelled_caught:
                    logger.debug(
                        f"Heartbeat timeout with {peer_id}, continuing to wait..."
                    )
                    # Do not close stream aggressively on a single timeout; continue waiting
                    continue

        except Exception as e:
            logger.error(f"Error in initiator stream with {peer_id}: {e}")
        finally:
            # Clean up
            if peer_id in self.persistent_streams:
                del self.persistent_streams[peer_id]
            self.connection_states[peer_id] = ConnectionState.DISCONNECTED
            logger.info(f"Initiator stream with {peer_id} closed")

    async def connect_to_peer(self, peer_multiaddr: str) -> dict[str, Any]:
        """Connect to a peer and exchange cards."""
        if not self.running:
            raise RuntimeError("P2P service is not running")

        logger.info(f"Connecting to peer: {peer_multiaddr}")

        # Resolve container name to IP if needed
        resolved_addr = await self._resolve_docker_dns(peer_multiaddr)
        logger.debug(f"Resolved address: {resolved_addr}")

        peer_info = info_from_p2p_addr(Multiaddr(resolved_addr))

        # Connect with timeout
        with trio.move_on_after(self.config.connection_timeout) as cancel_scope:
            await self.host.connect(peer_info)

        if cancel_scope.cancelled_caught:
            raise ConnectionError(f"Connection to {peer_info.peer_id} timed out")

        logger.success(f"Connected to peer: {peer_info.peer_id}")

        # Store connection info
        self.connected_peers[str(peer_info.peer_id)] = {
            "addr": peer_multiaddr,
            "connected": True,
        }

        # Initiate persistent exchange after connection
        try:
            # We are already in trio context; call trio coroutine directly
            success = await self._initiate_persistent_exchange(peer_info.peer_id)
            if not success:
                logger.warning(
                    f"Failed to establish persistent exchange with {peer_info.peer_id}"
                )
        except Exception as e:
            logger.warning(f"Failed to initiate persistent exchange: {e}")

        self.peer_addresses[str(peer_info.peer_id)] = peer_multiaddr
        logger.debug(f"Recorded peer address for {peer_info.peer_id}: {peer_multiaddr}")
        return {"status": "connected", "peer_id": str(peer_info.peer_id)}

    async def send_a2a_request(
        self, peer_id_str: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Send A2A request to peer."""
        if not self.running:
            raise RuntimeError("P2P service is not running")

        async def _trio_invoke() -> dict[str, Any]:
            peer_id = PeerID.from_base58(peer_id_str)

            addr = self.peer_addresses.get(peer_id_str)
            if not addr and peer_id_str in self.connected_peers:
                addr = self.connected_peers[peer_id_str].get("addr")
            if addr:
                try:
                    peer_info = info_from_p2p_addr(Multiaddr(addr))
                    await self.host.connect(peer_info)
                except Exception as e:
                    logger.debug(f"Ensure connection to {peer_id_str} failed: {e}")

            try:
                stream = await self.host.new_stream(peer_id, [A2A_PROTOCOL])
            except Exception as e:
                logger.error(f"Failed to open A2A stream to {peer_id_str}: {e}")
                raise
            try:
                request_bytes = json.dumps(request).encode("utf-8")
                await stream.write(request_bytes)

                response_bytes = await stream.read(MAX_READ_LEN)
                return json.loads(response_bytes.decode("utf-8"))
            finally:
                await stream.close()

        # Bridge trio call from asyncio context
        return await trio_asyncio.trio_as_aio(_trio_invoke)()

    async def invoke_remote_tool(
        self, peer_id_str: str, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Invoke tool on remote peer from asyncio context via trio bridge using one-time TOOL protocol stream."""
        if not self.running:
            raise RuntimeError("P2P service is not running")

        async def _ensure_connected_trio() -> bool:
            """Ensure we have a live connection and (re)established exchange with peer."""
            try:
                # Fast path
                if self.connection_states.get(peer_id_str) == ConnectionState.READY:
                    return True

                # Try reconnect using known address
                addr = None
                if peer_id_str in self.connected_peers:
                    addr = self.connected_peers[peer_id_str].get("addr")
                if not addr:
                    addr = self.peer_addresses.get(peer_id_str)

                # If not known, try to find bootstrap entry that matches peer id
                if not addr:
                    for baddr in self.config.bootstrap_nodes or []:
                        if peer_id_str in baddr:
                            addr = baddr
                            break

                if addr:
                    await self.connect_to_peer(addr)
                    return self.connection_states.get(peer_id_str) in (
                        ConnectionState.READY,
                        ConnectionState.CONNECTED,
                    )
                return False
            except Exception as e:
                logger.warning(f"Ensure-connected failed for {peer_id_str}: {e}")
                return False

        # If we have a persistent exchange stream, use it to avoid address issues
        if (
            peer_id_str in self.persistent_streams
            and self.connection_states.get(peer_id_str) == ConnectionState.READY
        ):
            try:
                # Run trio coroutine from asyncio via trio-asyncio bridge to avoid scheduler traps
                return await trio_asyncio.trio_as_aio(self._invoke_tool_persistent)(
                    peer_id_str, tool_name, arguments
                )
            except Exception as e:
                logger.warning(
                    f"Persistent tool call failed with {peer_id_str}: {e}. Falling back to on-demand stream."
                )

        async def _trio_invoke() -> dict[str, Any]:
            peer_id = PeerID.from_base58(peer_id_str)
            # Try to ensure connection first
            if not await _ensure_connected_trio():
                logger.debug(
                    f"Could not ensure connection to {peer_id_str} before opening TOOL stream"
                )
            try:
                stream = await self.host.new_stream(peer_id, [TOOL_PROTOCOL])
            except Exception as e:
                logger.error(f"Failed to open TOOL stream to {peer_id_str}: {e}")
                await _ensure_connected_trio()
                stream = await self.host.new_stream(peer_id, [TOOL_PROTOCOL])
            try:
                request = {"tool": tool_name, "arguments": arguments}
                await stream.write(json.dumps(request).encode("utf-8"))
                response_bytes = await stream.read(MAX_READ_LEN)
                return json.loads(response_bytes.decode("utf-8"))
            finally:
                await stream.close()

        # Run trio coroutine from asyncio using trio-asyncio bridge
        return await trio_asyncio.trio_as_aio(_trio_invoke)()

    async def _invoke_tool_persistent(
        self, peer_id_str: str, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Invoke tool using persistent stream."""
        stream = self.persistent_streams[peer_id_str]
        request_id = f"tool_req_{trio.current_time()}_{tool_name}"

        try:
            # Pause keepalive for this peer to avoid concurrent access
            self._pause_keepalive[peer_id_str] = True
            # Send tool request via persistent stream
            request_message = {
                "type": "tool_request",
                "payload": {
                    "request_id": request_id,
                    "tool": tool_name,
                    "arguments": arguments,
                },
            }
            await stream.write(json.dumps(request_message).encode("utf-8"))

            # Wait for response with timeout
            with trio.move_on_after(
                180
            ) as cancel_scope:  # extend timeout to accommodate long-running tool
                while True:
                    data = await stream.read(MAX_READ_LEN)
                    if data:
                        response = json.loads(data.decode("utf-8"))
                        if (
                            response.get("type") == "tool_response"
                            and response.get("payload", {}).get("request_id")
                            == request_id
                        ):
                            payload = response.get("payload", {})
                            if payload.get("success"):
                                return payload.get("result", {})
                            raise Exception(payload.get("error", "Unknown error"))
                        # Ignore heartbeat and other message types
                        continue

            if cancel_scope.cancelled_caught:
                raise Exception("Tool invocation timeout")

        except Exception as e:
            logger.error(f"Error in persistent tool call to {peer_id_str}: {e}")
            raise
        finally:
            # Resume keepalive
            self._pause_keepalive[peer_id_str] = False

    async def _connect_bootstrap_nodes(self):
        """Connect to bootstrap nodes."""
        if not self.config.bootstrap_nodes:
            logger.info("No bootstrap nodes configured")
            return

        logger.info(
            f"Connecting to {len(self.config.bootstrap_nodes)} bootstrap nodes..."
        )

        # Give the host a moment to initialize and wait for other agents to start
        await trio.sleep(10)

        successful_connections = 0
        for i, bootstrap_addr in enumerate(self.config.bootstrap_nodes):
            if not self.running:
                return

            addr_str = str(bootstrap_addr)
            try:
                logger.info(
                    f"Connecting to bootstrap node {i + 1}/{len(self.config.bootstrap_nodes)}: {addr_str}"
                )

                # Resolve peer ID if needed
                if "/p2p/" not in addr_str:
                    addr_str = self._resolve_peer_id(addr_str)

                result = await self.connect_to_peer(addr_str)
                if result.get("status") == "connected":
                    successful_connections += 1
                    logger.success(
                        f"Successfully connected to bootstrap node: {result.get('peer_id')}"
                    )

            except Exception as e:
                logger.error(f"Failed to connect to bootstrap node {addr_str}: {e}")

            # Small delay between attempts
            await trio.sleep(1)

        logger.info(
            f"Bootstrap connection summary: {successful_connections}/{len(self.config.bootstrap_nodes)} successful"
        )

    def _resolve_peer_id(self, addr_str: str) -> str:
        """Resolve peer ID from keystore for bootstrap address."""
        try:
            parts = [p for p in addr_str.split("/") if p]
            if len(parts) >= 2 and parts[0] in ("dns4", "ip4"):
                host_label = parts[1]
                keystore_root = str(Path(self.config.keystore_path).parent)
                seed_path = os.path.join(keystore_root, host_label, "node.key")

                if os.path.exists(seed_path):
                    seed = open(seed_path, "rb").read()
                    kp = create_new_key_pair(seed)
                    pid = PeerID.from_pubkey(kp.public_key)
                    resolved_addr = addr_str.rstrip("/") + f"/p2p/{pid.to_base58()}"
                    logger.debug(f"Resolved bootstrap addr: {resolved_addr}")
                    return resolved_addr
        except Exception as e:
            logger.debug(f"Could not resolve peer id for {addr_str}: {e}")

        return addr_str

    async def _publish_event(self, event_type: EventType, data: dict[str, Any]):
        """Publish event to event bus."""
        try:
            await trio_asyncio.aio_as_trio(self.agent.event_bus.publish_data)(
                event_type, data, source="simplified_p2p_service"
            )
        except Exception as e:
            logger.error(f"Failed to publish P2P event: {e}")

    async def run(self, listen_port: int) -> None:
        """Run the P2P service (trio main function)."""
        listen_addr = Multiaddr(f"/ip4/0.0.0.0/tcp/{listen_port}")

        # Create libp2p host with security transport
        sec_opt = {
            PLAINTEXT_PROTOCOL_ID: InsecureTransport(
                local_key_pair=self.keypair,
            )
        }
        self.host = new_host(key_pair=self.keypair, sec_opt=sec_opt)

        async with self.host.run(listen_addrs=[listen_addr]):
            peer_id = self.host.get_id().to_base58()
            logger.success(f"P2P host started: {peer_id}")
            logger.info(f"Listening on: {listen_addr}")

            # Set up stream handlers
            self.host.set_stream_handler(A2A_PROTOCOL, self.handle_stream)
            self.host.set_stream_handler(CARD_PROTOCOL, self.handle_stream)
            self.host.set_stream_handler(TOOL_PROTOCOL, self.handle_stream)
            self.host.set_stream_handler(EXCHANGE_PROTOCOL, self.handle_stream)

            self.running = True

            # Publish started event
            await self._publish_event(
                EventType.P2P_PEER_CONNECTED,
                {
                    "peer_id": peer_id,
                    "addresses": [str(listen_addr)],
                    "protocols": ["A2A", "CARD", "TOOL", "EXCHANGE"],
                    "persistent_connections": True,
                },
            )

            # Connect to bootstrap nodes in background
            async with trio.open_nursery() as nursery:
                if self.config.bootstrap_nodes:
                    nursery.start_soon(self._connect_bootstrap_nodes)

                # Keep running
                while self.running:
                    await trio.sleep(1)

    # Synchronous interface methods for compatibility

    def start(self):
        """Start the P2P service (synchronous interface)."""
        if self.running:
            logger.warning("Simplified P2P service is already running")
            return

        logger.info(f"Starting simplified P2P service on port {self.config.port}")

        # Run trio_asyncio event loop directly (no threading)
        try:
            trio_asyncio.run(self.run, self.config.port)
        except Exception as e:
            logger.error(f"P2P service crashed: {e}")
            raise

    def stop(self):
        """Stop the P2P service (synchronous interface)."""
        if not self.running:
            return

        logger.info("Stopping simplified P2P service...")
        self.running = False

        if self.host:
            # Close will be handled by trio context manager
            pass

        logger.info("Simplified P2P service stopped")

    async def _resolve_docker_dns(self, multiaddr_str: str) -> str:
        """Resolve Docker container DNS names to IP addresses in multiaddr."""
        import re
        import socket

        # Check if it's a DNS multiaddr that needs resolution
        if "/dns4/" in multiaddr_str:
            # Extract hostname from /dns4/hostname/...
            dns_match = re.search(r"/dns4/([^/]+)/", multiaddr_str)
            if dns_match:
                hostname = dns_match.group(1)
                try:
                    # Resolve DNS to IP
                    ip = socket.gethostbyname(hostname)
                    # Replace /dns4/hostname with /ip4/ip
                    resolved = multiaddr_str.replace(f"/dns4/{hostname}", f"/ip4/{ip}")
                    logger.debug(f"Resolved {hostname} -> {ip}")
                    return resolved
                except socket.gaierror as e:
                    logger.error(f"Failed to resolve hostname {hostname}: {e}")
                    # Fallback to original address
                    return multiaddr_str

        return multiaddr_str

    def get_peer_id(self) -> str | None:
        """Get our peer ID."""
        return str(self.host.get_id()) if self.host else None

    def get_listen_addresses(self) -> list[str]:
        """Get our listen addresses."""
        return [str(a) for a in self.host.get_addrs()] if self.host else []

    def get_connected_peers(self) -> list[str]:
        """Get list of connected peer IDs."""
        return list(self.connected_peers.keys())

    def get_peer_card(self, peer_id: str) -> dict[str, Any] | None:
        """Get cached card for a peer."""
        return self.peer_cards.get(peer_id)

    def get_peer_tools(self, peer_id: str) -> list[dict[str, Any]]:
        """Get cached tools list for a peer."""
        return self.peer_tools.get(peer_id, [])

    def get_all_peer_tools(self) -> dict[str, list[dict[str, Any]]]:
        """Get all cached peer tools."""
        return dict(self.peer_tools)

    def get_connection_state(self, peer_id: str) -> str:
        """Get connection state for a peer."""
        return self.connection_states.get(peer_id, ConnectionState.DISCONNECTED)

    def list_available_remote_tools(self) -> dict[str, list[dict[str, Any]]]:
        """List all available tools from connected peers."""
        available_tools = {}

        for peer_id, tools in self.peer_tools.items():
            if self.connection_states.get(peer_id) == ConnectionState.READY:
                peer_name = "unknown"
                if peer_id in self.peer_cards:
                    peer_name = self.peer_cards[peer_id].get("name", peer_id)

                available_tools[f"{peer_name} ({peer_id[:8]}...)"] = tools

        return available_tools

    async def call_remote_tool_by_peer_name(
        self, peer_name: str, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call remote tool by peer name instead of peer ID."""
        # Find peer ID by name
        target_peer_id = None
        for peer_id, card in self.peer_cards.items():
            if card.get("name") == peer_name:
                target_peer_id = peer_id
                break

        if not target_peer_id:
            raise ValueError(f"Peer with name '{peer_name}' not found")

        return await self.invoke_remote_tool(target_peer_id, tool_name, arguments)

    def get_peer_status_summary(self) -> dict[str, Any]:
        """Get comprehensive status of all peer connections."""
        summary = {
            "total_peers": len(self.connected_peers),
            "peers_with_cards": len(self.peer_cards),
            "peers_with_tools": len(self.peer_tools),
            "persistent_connections": len(self.persistent_streams),
            "ready_connections": len(
                [
                    p
                    for p, s in self.connection_states.items()
                    if s == ConnectionState.READY
                ]
            ),
            "peers": [],
        }

        for peer_id in self.connected_peers:
            peer_info = {
                "peer_id": peer_id,
                "short_id": peer_id[:8] + "...",
                "name": self.peer_cards.get(peer_id, {}).get("name", "unknown"),
                "state": self.connection_states.get(
                    peer_id, ConnectionState.DISCONNECTED
                ),
                "has_card": peer_id in self.peer_cards,
                "tools_count": len(self.peer_tools.get(peer_id, [])),
                "persistent_stream": peer_id in self.persistent_streams,
            }
            summary["peers"].append(peer_info)

        return summary

    async def force_reconnect_peer(self, peer_id: str) -> bool:
        """Force reconnect to a peer and re-establish exchange."""
        if not self.running:
            return False

        try:
            logger.info(f"Force reconnecting to peer {peer_id}")

            # Clean up existing connection
            if peer_id in self.persistent_streams:
                try:
                    await self.persistent_streams[peer_id].close()
                except:
                    pass
                del self.persistent_streams[peer_id]

            self.connection_states[peer_id] = ConnectionState.DISCONNECTED

            # Find peer info from connected_peers
            if peer_id not in self.connected_peers:
                logger.error(f"Peer {peer_id} not in connected peers list")
                return False

            peer_addr = self.connected_peers[peer_id].get("addr")
            if not peer_addr:
                logger.error(f"No address found for peer {peer_id}")
                return False

            # Reconnect
            result = await self.connect_to_peer(peer_addr)
            return result.get("status") == "connected"

        except Exception as e:
            logger.error(f"Failed to reconnect to peer {peer_id}: {e}")
            return False


# Factory function for compatibility
def create_simplified_p2p_service(
    config: P2PConfig, agent: "PraxisAgent"
) -> SimplifiedP2PService:
    """Create a simplified P2P service instance."""
    return SimplifiedP2PService(config, agent)
