"""Isolated P2P module to avoid serialization issues."""

import threading
from typing import Any

import trio
from loguru import logger

from base_agent.p2p.config import P2PConfig, get_p2p_config


class P2PManager:
    """Manager for P2P operations that isolates libp2p imports."""

    def __init__(self, config: P2PConfig) -> None:
        self.config = config
        self._libp2p_node: Any = None
        self._thread: threading.Thread | None = None
        self._running: bool = False
        self._shutdown_event: threading.Event = threading.Event()

    def __getstate__(self) -> object:
        odict = self.__dict__.copy()  # get attribute dictionary

        for k in ["_libp2p_node", "_thread", "_running", "_shutdown_event"]:
            del odict[k]

        return odict

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
        self._libp2p_node = None
        self._thread = None
        self._running = False
        self._shutdown_event = threading.Event()

    @property
    def node(self) -> Any:
        if self._libp2p_node is not None:
            return self._libp2p_node
        raise RuntimeError("libp2p node is not initialized yet. Call start()")

    def _run_in_thread(self) -> None:
        """Run the P2P node in a separate thread using Trio."""
        try:
            # Run the Trio event loop in this thread
            trio.run(self._start)
        except Exception as e:
            logger.error(f"Error in P2P thread: {e}")
            raise
        finally:
            logger.info("P2P thread exiting")
            self._running = False

    async def _start(self) -> None:
        """Trio-based implementation of the P2P node."""
        from libp2p import new_host
        from libp2p.peer.peerinfo import info_from_p2p_addr
        from libp2p.relay.circuit_v2.config import RelayConfig
        from libp2p.relay.circuit_v2.protocol import CircuitV2Protocol
        from libp2p.relay.circuit_v2.transport import CircuitV2Transport
        from multiaddr import Multiaddr

        from .const import PROTOCOL_CARD
        from .handlers import handle_card

        host = new_host()
        self._libp2p_node = host

        host.set_stream_handler(PROTOCOL_CARD, handle_card)
        # Print host information
        logger.info(f"Destination node started with ID: {host.get_id()}")
        logger.info(f"Listening on: {host.get_addrs()}")

        config = RelayConfig(
            enable_stop=True,  # Accept relayed connections
            enable_client=True,  # Use relays for outbound connections
        )
        # Initialize the relay protocol
        protocol = CircuitV2Protocol(host)

        async with host.run(listen_addrs=[Multiaddr("/ip4/0.0.0.0/tcp/9001")]), trio.open_nursery() as nursery:
            transport = CircuitV2Transport(host, protocol, config)
            listener = transport.create_listener(lambda stream: handle_card(stream))  # type: ignore[misc]

            # start listening
            await listener.listen(None, nursery)  # type: ignore[misc]
            logger.info("Destination node ready to accept relayed connections")

            # Connect to relay and keep node running
            while not self._shutdown_event.is_set():
                try:
                    # Connect to the relay node
                    relay_addr = self.config.relay_addr
                    logger.info(f"Connecting to relay at {relay_addr}")
                    try:
                        await host.connect(info_from_p2p_addr(Multiaddr(relay_addr)))
                        logger.info("Connected to relay successfully")
                    except Exception as e:
                        logger.error(f"Failed to connect to relay: {e}")
                        await trio.sleep(10)
                        continue

                    # Keep checking if we should shut down
                    while not self._shutdown_event.is_set():
                        await trio.sleep(5)

                except Exception as e:
                    logger.error(f"Error in p2p node loop: {e}")
                    await trio.sleep(10)

    async def start(self) -> None:
        """Start the P2P node in a separate thread."""
        if self._running:
            logger.warning("P2P manager is already running")
            return

        self._running = True
        self._shutdown_event.clear()

        # Create and start the thread
        self._thread = threading.Thread(target=self._run_in_thread, daemon=True)
        self._thread.start()

        logger.info("P2P manager started in separate thread")

    async def shutdown(self) -> None:
        """Shutdown libp2p node."""
        if not self._running:
            logger.warning("P2P manager is not running")
            return

        logger.info("Shutting down P2P manager...")
        self._shutdown_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)  # Wait up to 10 seconds for thread to exit

        self._libp2p_node = None
        self._running = False
        logger.info("P2P shutdown completed.")


def get_p2p_manager() -> P2PManager:
    return P2PManager(config=get_p2p_config())
