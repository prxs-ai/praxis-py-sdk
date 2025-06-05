from base_agent.p2p.config import P2PConfig
from base_agent.p2p.libp2p.utils import decode_noise_key, load_or_create_node_key
from libp2p import new_host
from libp2p.crypto.keys import KeyPair
from libp2p.relay.circuit_v2.protocol import CircuitV2Protocol
from libp2p.relay.circuit_v2.transport import CircuitV2Transport
from libp2p.security.noise.transport import PROTOCOL_ID as NOISE_PROTOCOL_ID
from libp2p.security.noise.transport import Transport as NoiseTransport
from libp2p.relay.circuit_v2.config import RelayConfig
from base_agent.p2p.handlers import handle_card
from base_agent.p2p.const import PROTOCOL_CARD
from libp2p.peer.peerinfo import info_from_p2p_addr
from multiaddr import Multiaddr
import os

from loguru import logger


class LibP2PNode:
    """Encapsulates all libp2p-related functionality."""

    def __init__(self, config: P2PConfig) -> None:
        self.config = config
        self.host = None
        self.shutdown_requested = False

        self._init_keypair()

    def _init_keypair(self, host_key_filename: str = "node.key"):
        self.keypair: KeyPair = load_or_create_node_key(
            os.path.join(self.config.keystore_path, host_key_filename)
        )

    def _init_host(self):
        """Initialize libp2p host"""
        sec_opt = None

        if self.config.noise_key is not None:
            sec_opt = {
                NOISE_PROTOCOL_ID: NoiseTransport(
                    libp2p_keypair=self.keypair,
                    noise_privkey=decode_noise_key(self.config.noise_key),
                )
            }
        return new_host(key_pair=self.keypair, sec_opt=sec_opt)

    async def initialize(self):
        """Initialize the libp2p node."""

        self.host = self._init_host()
        self.host.set_stream_handler(PROTOCOL_CARD, handle_card)

        # Print host information
        logger.info(f"Node started with ID: {self.host.get_id()}")
        logger.info(f"Listening on: {self.host.get_addrs()}")

        config = RelayConfig(
            enable_stop=True,  # Accept relayed connections
            enable_client=True,  # Use relays for outbound connections
        )
        # Initialize the relay protocol
        self.protocol = CircuitV2Protocol(self.host)
        self.transport = CircuitV2Transport(self.host, self.protocol, config)

        return self.host

    async def connect_to_relay(self):
        """Connect to the relay node."""

        relay_addr = self.config.relay_addr
        logger.info(f"Connecting to relay at {relay_addr}")
        try:
            await self.host.connect(info_from_p2p_addr(Multiaddr(relay_addr)))  # type: ignore
            logger.info("Connected to relay successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to relay: {e}")
            return False

    async def setup_listener(self, nursery):
        """Set up the listener for incoming connections."""

        listener = self.transport.create_listener(lambda stream: handle_card(stream))  # type: ignore
        # start listening
        await listener.listen(None, nursery)  # type: ignore
        logger.info("Destination node ready to accept relayed connections")
