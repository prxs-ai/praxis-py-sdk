"""Fixed P2P Service based on AI Registry working pattern.
Simplified and robust implementation using trio_asyncio bridge.
"""

import json
import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import trio
import trio_asyncio
from libp2p import new_host
from libp2p.crypto.ed25519 import create_new_key_pair
from libp2p.custom_types import TProtocol
from libp2p.security.insecure.transport import PLAINTEXT_PROTOCOL_ID, InsecureTransport
from libp2p.security.noise.transport import PROTOCOL_ID as NOISE_PROTOCOL_ID
from libp2p.security.noise.transport import Transport as NoiseTransport
from loguru import logger
from multiaddr import Multiaddr

from ..bus import EventBus, EventType
from ..config import P2PConfig

if TYPE_CHECKING:
    from libp2p.abc import IHost, INetStream
    from libp2p.crypto.keys import KeyPair

    from ..agent import PraxisAgent


# Protocol definitions - focusing on core protocols first
A2A_PROTOCOL: TProtocol = TProtocol("/praxis/a2a/1.0.0")
CARD_PROTOCOL: TProtocol = TProtocol("/praxis/card/1.0.0")


class P2PServiceFixed:
    """Simplified P2P Service following AI Registry pattern.

    Key changes from original:
    - Single thread with trio event loop
    - Proper trio_asyncio bridge usage
    - Simplified connection management
    - Focus on core protocols first
    """

    def __init__(self, config: P2PConfig, agent: "PraxisAgent"):
        self.config = config
        self.agent = agent
        self.host: IHost | None = None
        self._running = False

        # Threading components (simplified)
        self._thread: threading.Thread | None = None
        self._ready_event: threading.Event | None = None

        # Initialize keypair
        self.keypair: KeyPair = self._load_or_create_keypair()

        # Peer management
        self.peer_cards: dict[str, dict[str, Any]] = {}

    def _load_or_create_keypair(self) -> "KeyPair":
        """Load or create Ed25519 keypair (following ai-registry pattern)."""
        keystore_path = Path(self.config.keystore_path)
        keystore_path.mkdir(parents=True, exist_ok=True)

        key_file = keystore_path / "node.key"

        if key_file.exists():
            logger.info(f"Using existing keypair from: {key_file}")
            seed = key_file.read_bytes()
        else:
            logger.info(f"Creating new keypair: {key_file}")
            seed = os.urandom(32)
            key_file.write_bytes(seed)

        return create_new_key_pair(seed)

    def _init_host(self):
        """Initialize libp2p host with security options."""
        sec_opt = {}

        if self.config.security.use_noise and self.config.security.noise_key:
            # Use Noise protocol
            sec_opt = {
                NOISE_PROTOCOL_ID: NoiseTransport(
                    libp2p_keypair=self.keypair,
                    noise_privkey=self._decode_noise_key(
                        self.config.security.noise_key
                    ),
                )
            }
        else:
            # Use plaintext for development
            sec_opt = {
                PLAINTEXT_PROTOCOL_ID: InsecureTransport(local_key_pair=self.keypair)
            }

        return new_host(key_pair=self.keypair, sec_opt=sec_opt)

    def _decode_noise_key(self, key_str: str):
        """Decode Noise key from base64 string."""
        import base64

        from libp2p.crypto.ed25519 import Ed25519PrivateKey

        return Ed25519PrivateKey.from_bytes(base64.b64decode(key_str))

    def start(self):
        """Start P2P service (synchronous call from main thread)."""
        if self._running:
            logger.warning("P2P service already running")
            return

        logger.info("Starting P2P service...")
        self._running = True

        # Create ready event to wait for initialization
        self._ready_event = threading.Event()

        # Start thread with trio event loop
        self._thread = threading.Thread(
            target=self._run_in_thread, daemon=True, name="P2P-Trio-Thread"
        )
        self._thread.start()

        # Wait for service to be ready (with timeout)
        if self._ready_event.wait(timeout=15.0):
            logger.success("P2P service started and ready")
        else:
            logger.error("P2P service failed to start within timeout")
            self._running = False
            raise RuntimeError("P2P service startup timeout")

    def stop(self):
        """Stop P2P service (synchronous call from main thread)."""
        if not self._running:
            return

        logger.info("Stopping P2P service...")
        self._running = False

        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
            if self._thread.is_alive():
                logger.warning("P2P thread did not terminate gracefully")

        logger.info("P2P service stopped")

    def _run_in_thread(self):
        """Run trio event loop in thread (following ai-registry pattern)."""
        try:
            logger.info("Starting P2P node in background thread")
            trio_asyncio.run(self._trio_main)
        except KeyboardInterrupt:
            logger.info("P2P thread interrupted")
        except Exception as e:
            logger.error(f"P2P thread error: {e}")
        finally:
            self._running = False
            logger.info("P2P thread exiting")

    async def _trio_main(self):
        """Main trio function (similar to ai-registry)."""
        try:
            # Initialize libp2p host
            self.host = self._init_host()

            # Setup protocol handlers
            self.host.set_stream_handler(A2A_PROTOCOL, self._handle_a2a_stream)
            self.host.set_stream_handler(CARD_PROTOCOL, self._handle_card_stream)

            logger.info("LibP2P host initialized")

            # Start listening
            listen_addr = Multiaddr(f"/ip4/0.0.0.0/tcp/{self.config.port}")

            async with self.host.run(listen_addrs=[listen_addr]):
                peer_id = self.host.get_id()
                addrs = self.host.get_addrs()

                logger.success(f"P2P host started: {peer_id}")
                logger.info(f"Listening on: {addrs}")

                # Signal that service is ready
                if self._ready_event:
                    self._ready_event.set()

                # Connect to bootstrap nodes if configured
                if self.config.bootstrap_nodes:
                    # Small delay to let the host fully initialize
                    await trio.sleep(2)
                    await self._connect_bootstrap_nodes()

                # Keep running until stopped
                while self._running:
                    await trio.sleep(1)

        except Exception as e:
            logger.error(f"Failed to start P2P host: {e}")
            # Signal ready event even on error to prevent hanging
            if self._ready_event:
                self._ready_event.set()

    async def _handle_a2a_stream(self, stream: "INetStream"):
        """Handle A2A protocol stream (with proper bridge)."""
        peer_id = str(stream.muxed_conn.peer_id)

        try:
            # Read request
            request_bytes = await stream.read(8192)
            request = json.loads(request_bytes.decode("utf-8"))

            logger.debug(f"A2A request from {peer_id}: {request.get('method')}")

            # Bridge to asyncio agent method (CORRECT pattern)
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
                "id": None,
            }
            try:
                await stream.write(json.dumps(error_response).encode("utf-8"))
            except:
                pass
        finally:
            await stream.close()

    async def _handle_card_stream(self, stream: "INetStream"):
        """Handle agent card exchange (responder side)."""
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

            logger.info(
                f"Card exchanged with {peer_id}: {peer_card.get('name', 'unknown')}"
            )

        except Exception as e:
            logger.error(f"Error in card exchange with {peer_id}: {e}")
        finally:
            await stream.close()

    async def _connect_bootstrap_nodes(self):
        """Connect to bootstrap nodes with peer ID resolution."""
        logger.info(f"Connecting to bootstrap nodes: {self.config.bootstrap_nodes}")

        for bootstrap_addr_str in self.config.bootstrap_nodes:
            try:
                logger.info(
                    f"Attempting to connect to bootstrap node: {bootstrap_addr_str}"
                )

                # If multiaddr is missing /p2p/<peerid>, try to resolve it
                if "/p2p/" not in bootstrap_addr_str:
                    # Try to resolve peer ID from potential keystore
                    resolved_addr = await self._resolve_bootstrap_peer_id(
                        bootstrap_addr_str
                    )
                    if resolved_addr:
                        bootstrap_addr_str = resolved_addr
                    else:
                        logger.warning(
                            f"Could not resolve peer ID for {bootstrap_addr_str}, skipping"
                        )
                        continue

                from libp2p.peer.peerinfo import info_from_p2p_addr

                peer_info = info_from_p2p_addr(Multiaddr(bootstrap_addr_str))

                # Connect with timeout
                with trio.move_on_after(self.config.connection_timeout):
                    await self.host.connect(peer_info)

                logger.success(f"Connected to bootstrap node: {peer_info.peer_id}")

                # Store connection info
                self.peer_cards[str(peer_info.peer_id)] = {
                    "connected": True,
                    "address": bootstrap_addr_str,
                }

                # Exchange cards after connection (initiator flow)
                try:
                    stream = await self.host.new_stream(
                        peer_info.peer_id, [CARD_PROTOCOL]
                    )
                    await self._exchange_cards_initiator(stream)
                except Exception as e:
                    logger.warning(
                        f"Failed to exchange cards with {peer_info.peer_id}: {e}"
                    )

            except Exception as e:
                logger.error(
                    f"Failed to connect to bootstrap node {bootstrap_addr_str}: {e}"
                )

            # Small delay between connections
            await trio.sleep(1)

    async def _resolve_bootstrap_peer_id(self, addr_str: str) -> str | None:
        """Try to resolve peer ID for bootstrap address by checking common keystore locations."""
        try:
            # Parse the address to extract host/port
            parts = [p for p in addr_str.split("/") if p]
            if len(parts) < 4:
                return None

            # Expected format: /ip4/<host>/tcp/<port>
            if parts[0] == "ip4" and parts[2] == "tcp":
                host = parts[1]
                port = parts[3]

                # Try to find keystore for this host
                keystore_candidates = [
                    f"./keys/{host}/node.key",
                    "./keys/agent1/node.key" if port == "4001" else None,
                    "./keys/agent2/node.key" if port == "4002" else None,
                    "./keys/orchestrator/node.key",
                    "./keys/worker-filesystem/node.key",
                ]

                for keystore_path in keystore_candidates:
                    if keystore_path and os.path.exists(keystore_path):
                        peer_id = self._compute_peer_id_from_seed(keystore_path)
                        if peer_id:
                            resolved_addr = f"{addr_str}/p2p/{peer_id}"
                            logger.info(f"Resolved bootstrap address: {resolved_addr}")
                            return resolved_addr

        except Exception as e:
            logger.debug(f"Failed to resolve peer ID for {addr_str}: {e}")

        return None

    def _compute_peer_id_from_seed(self, seed_path: str) -> str | None:
        """Compute peer ID from seed file."""
        try:
            if not os.path.exists(seed_path):
                return None

            seed = open(seed_path, "rb").read()
            kp = create_new_key_pair(seed)
            from libp2p.peer.id import ID as PeerID

            pid = PeerID.from_pubkey(kp.public_key)
            return pid.to_base58()
        except Exception as e:
            logger.debug(f"Failed to compute peer ID from {seed_path}: {e}")
            return None

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

            logger.info(
                f"Initiated card exchange with {peer_id}: {peer_card.get('name', 'unknown')}"
            )

        except Exception as e:
            logger.error(f"Error during initiator card exchange with {peer_id}: {e}")
        finally:
            await stream.close()

    # Public API methods

    def get_peer_id(self) -> str | None:
        """Get our peer ID."""
        return str(self.host.get_id()) if self.host else None

    def get_listen_addresses(self) -> list[str]:
        """Get our listen addresses."""
        return [str(a) for a in self.host.get_addrs()] if self.host else []

    def get_connected_peers(self) -> list[str]:
        """Get list of connected peer IDs."""
        return list(self.peer_cards.keys())

    def get_peer_card(self, peer_id: str) -> dict[str, Any] | None:
        """Get cached card for a peer."""
        return self.peer_cards.get(peer_id)


# Factory function to create the fixed P2P service
def create_p2p_service(config: P2PConfig, agent: "PraxisAgent") -> P2PServiceFixed:
    """Create a P2P service instance with fixed implementation."""
    return P2PServiceFixed(config, agent)
