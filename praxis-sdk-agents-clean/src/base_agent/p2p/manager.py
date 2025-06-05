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
        from multiaddr import Multiaddr

        from base_agent.p2p.libp2p import LibP2PNode

        # Create the libp2p node
        node = LibP2PNode(self.config)
        host = await node.initialize()
        self._libp2p_node = node

        async with host.run(listen_addrs=[Multiaddr("/ip4/0.0.0.0/tcp/9001")]), trio.open_nursery() as nursery:
            # Set up the listener
            await node.setup_listener(nursery)

            # Connect to relay and keep node running
            while not self._shutdown_event.is_set():
                try:
                    # Connect to the relay node
                    success = await node.connect_to_relay()
                    if not success:
                        await trio.sleep(10)
                        continue

                    # Keep checking if we should shut down
                    while not self._shutdown_event.is_set():
                        await trio.sleep(10)

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

    async def shutdown(self):
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
