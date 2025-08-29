"""Isolated P2P module to avoid serialization issues."""

import asyncio
import json
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Final

import requests
import trio
from libp2p.node import LibP2PNode
from libp2p.peer.id import ID as PeerID  # noqa: N811
from libp2p.peer.peerinfo import PeerInfo
from loguru import logger
from multiaddr import Multiaddr

from praxis_sdk.agents.exceptions import P2PConnectionError
from praxis_sdk.agents.p2p.config import P2PConfig, get_p2p_config


class P2PManager:
    """Manager for P2P operations with improved error handling and resource management."""

    def __init__(self, config: P2PConfig) -> None:
        """Initialize P2P manager with configuration.
        
        Args:
            config: P2P configuration instance
            
        Raises:
            P2PConnectionError: If configuration is invalid
        """
        if not isinstance(config, P2PConfig):
            raise P2PConnectionError("Invalid P2P configuration provided")
            
        self.config = config
        self._libp2p_node: Any = None
        self._thread: threading.Thread | None = None
        self._running: bool = False
        self._shutdown_event: threading.Event = threading.Event()
        self._startup_time: float | None = None
        self._connection_attempts: int = 0

    def __getstate__(self) -> dict[str, Any]:
        """Prepare object for serialization by excluding non-serializable components."""
        odict = self.__dict__.copy()
        
        # Remove non-serializable components
        non_serializable_keys = [
            "_libp2p_node", 
            "_thread", 
            "_running", 
            "_shutdown_event",
            "_startup_time",
            "_connection_attempts"
        ]
        
        for key in non_serializable_keys:
            odict.pop(key, None)

        return odict

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore object from serialized state."""
        self.__dict__.update(state)
        self._libp2p_node = None
        self._thread = None
        self._running = False
        self._shutdown_event = threading.Event()
        self._startup_time = None
        self._connection_attempts = 0

    @property
    def node(self) -> Any:
        """Get the libp2p node instance.
        
        Returns:
            The libp2p node instance
            
        Raises:
            P2PConnectionError: If node is not initialized
        """
        if self._libp2p_node is not None:
            return self._libp2p_node
        raise P2PConnectionError("libp2p node is not initialized yet. Call start() first")

    @property
    def is_running(self) -> bool:
        """Check if the P2P manager is currently running.
        
        Returns:
            True if running, False otherwise
        """
        return self._running

    @property 
    def uptime(self) -> float | None:
        """Get the uptime of the P2P manager in seconds.
        
        Returns:
            Uptime in seconds if running, None otherwise
        """
        if self._startup_time is None:
            return None
        return time.time() - self._startup_time

    def _run_in_thread(self) -> None:
        """Run the P2P node in a separate thread using Trio with enhanced error handling."""
        try:
            self._startup_time = time.time()
            logger.info("Starting P2P node in background thread")
            
            # Run the Trio event loop in this thread
            trio.run(self._start)
            
        except KeyboardInterrupt:
            logger.info("P2P thread interrupted by user")
        except Exception as e:
            logger.error(f"Critical error in P2P thread: {e}")
            self._running = False
            raise P2PConnectionError(f"P2P thread failed: {e}") from e
        finally:
            logger.info("P2P thread exiting gracefully")
            self._running = False
            self._startup_time = None

    async def _start(self) -> None:
        """Trio-based implementation of the P2P node with improved error handling."""
        try:
            # Create and initialize the libp2p node
            node = LibP2PNode(self.config)
            host = await node.initialize()
            self._libp2p_node = node
            
            logger.info("LibP2P node initialized successfully")

            async with host.run(listen_addrs=[Multiaddr(f"/ip4/0.0.0.0/tcp/{DEFAULT_P2P_PORT}")]), trio.open_nursery() as nursery:
                # Set up the listener
                await node.setup_listener(nursery)
                logger.info(f"P2P listener set up on port {DEFAULT_P2P_PORT}")

                # Main connection loop with exponential backoff
                backoff_delay = 1
                max_backoff = 60
                
                while not self._shutdown_event.is_set():
                    try:
                        self._connection_attempts += 1
                        logger.debug(f"Connection attempt #{self._connection_attempts}")
                        
                        # Attempt to connect to the relay node
                        success = await node.connect_to_relay()
                        
                        if success:
                            logger.info("Successfully connected to relay node")
                            backoff_delay = 1  # Reset backoff on successful connection
                            
                            # Keep connection alive and monitor for shutdown
                            while not self._shutdown_event.is_set():
                                await trio.sleep(DEFAULT_SLEEP_INTERVAL)
                                
                        else:
                            logger.warning(f"Failed to connect to relay, retrying in {backoff_delay}s")
                            await trio.sleep(backoff_delay)
                            
                            # Exponential backoff with jitter
                            backoff_delay = min(backoff_delay * 2, max_backoff)

                    except trio.Cancelled:
                        logger.info("P2P node operation cancelled")
                        break
                    except Exception as e:
                        logger.error(f"Error in P2P node connection loop: {e}")
                        await trio.sleep(backoff_delay)
                        backoff_delay = min(backoff_delay * 2, max_backoff)
                        
        except Exception as e:
            logger.error(f"Failed to start P2P node: {e}")
            raise P2PConnectionError(f"P2P node initialization failed: {e}") from e

    async def start(self) -> None:
        """Start the P2P node in a separate thread."""
        if self._running:
            logger.warning("P2P manager is already running")
            return

        try:
            self._running = True
            self._shutdown_event.clear()
            self._connection_attempts = 0

            # Create and start the thread
            self._thread = threading.Thread(
                target=self._run_in_thread, 
                daemon=True,
                name="P2P-Manager-Thread"
            )
            self._thread.start()

            # Wait for node initialization with timeout
            logger.info("Waiting for P2P node initialization...")
            
            for attempt in range(INITIALIZATION_TIMEOUT):
                if self._libp2p_node is not None:
                    logger.info("P2P manager started successfully")
                    return
                    
                await trio.sleep(0.1)
                
                # Check if thread crashed during initialization
                if not self._thread.is_alive():
                    self._running = False
                    raise P2PConnectionError("P2P thread died during initialization")
            
            # Timeout reached
            self._running = False
            raise P2PConnectionError(
                f"P2P node failed to initialize within {INITIALIZATION_TIMEOUT}s timeout"
            )
            
        except Exception as e:
            self._running = False
            raise P2PConnectionError(f"Failed to start P2P manager: {e}") from e

    async def shutdown(self) -> None:
        """Shutdown libp2p node with proper cleanup."""
        if not self._running:
            logger.warning("P2P manager is not running")
            return

        try:
            logger.info("Initiating P2P manager shutdown...")
            self._shutdown_event.set()

            # Wait for thread to finish gracefully
            if self._thread and self._thread.is_alive():
                logger.info("Waiting for P2P thread to finish...")
                self._thread.join(timeout=10)
                
                if self._thread.is_alive():
                    logger.warning("P2P thread did not shut down gracefully within timeout")

            # Clean up resources
            self._libp2p_node = None
            self._running = False
            self._startup_time = None
            self._connection_attempts = 0
            
            logger.info("P2P shutdown completed successfully")
            
        except Exception as e:
            logger.error(f"Error during P2P shutdown: {e}")
            # Ensure we're marked as stopped even if cleanup fails
            self._running = False
            raise P2PConnectionError(f"P2P shutdown failed: {e}") from e

    @asynccontextmanager
    async def connection_context(self) -> AsyncGenerator[None, None]:
        """Context manager for P2P connection lifecycle.
        
        Yields:
            None during active connection
            
        Raises:
            P2PConnectionError: If connection setup or teardown fails
        """
        try:
            await self.start()
            yield
        finally:
            await self.shutdown()

    async def discover_peer_addrs(self, agent_name: str) -> list[str]:
        """Discover peer addresses for a given agent name.
        
        Args:
            agent_name: Name of the agent to discover
            
        Returns:
            List of peer addresses
            
        Raises:
            P2PConnectionError: If discovery fails
        """
        if not agent_name or not agent_name.strip():
            raise P2PConnectionError("Agent name cannot be empty")
            
        try:
            url = f"{self.config.relay_service.url}/peers"
            params = {"agent_name": agent_name.strip()}
            
            logger.debug(f"Discovering peer addresses for '{agent_name}' at {url}")
            
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            
            info = resp.json()
            addresses = info.get("addresses", [])
            
            if not addresses:
                logger.warning(f"No addresses found for agent '{agent_name}'")
            else:
                logger.info(f"Found {len(addresses)} addresses for agent '{agent_name}'")
                
            return addresses
            
        except requests.exceptions.Timeout as e:
            raise P2PConnectionError(f"Timeout discovering peer addresses for {agent_name}: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise P2PConnectionError(f"Connection error discovering peer addresses for {agent_name}: {e}") from e
        except requests.exceptions.HTTPError as e:
            raise P2PConnectionError(f"HTTP error discovering peer addresses for {agent_name}: {e}") from e
        except requests.exceptions.RequestException as e:
            raise P2PConnectionError(f"Request failed for peer discovery {agent_name}: {e}") from e
        except (ValueError, KeyError) as e:
            raise P2PConnectionError(f"Invalid response format for peer discovery {agent_name}: {e}") from e

    async def delegate(self, agent_name: str, target_peer_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Delegate a task to another peer via P2P communication.
        
        Args:
            agent_name: Name of the target agent
            target_peer_id: Base58 encoded peer ID of the target
            payload: Task payload to send
            
        Returns:
            Response from the target peer
            
        Raises:
            P2PConnectionError: If delegation fails
        """
        if not self._running or self._libp2p_node is None:
            raise P2PConnectionError("P2P manager is not running. Call start() first.")
            
        if not agent_name or not target_peer_id or not payload:
            raise P2PConnectionError("Agent name, target peer ID, and payload are required")

        try:
            logger.info(f"Delegating task to agent '{agent_name}' (peer: {target_peer_id})")
            
            # 1. Discover target addresses
            addrs = await self.discover_peer_addrs(agent_name)
            if not addrs:
                raise P2PConnectionError(f"No addresses found for agent '{agent_name}' (peer: {target_peer_id})")

            # 2. Create peer info
            try:
                pid = PeerID.from_base58(target_peer_id)
                peerinfo = PeerInfo(pid, addrs)
            except Exception as e:
                raise P2PConnectionError(f"Invalid peer ID format '{target_peer_id}': {e}") from e

            # 3. Establish connection via relay
            try:
                conn = await self._libp2p_node.transport.dial(
                    peerinfo, 
                    relay_peer_id=self._libp2p_node.get_peer_id()
                )
            except Exception as e:
                raise P2PConnectionError(f"Failed to dial peer {target_peer_id}: {e}") from e

            # 4. Send payload and receive response
            try:
                payload_data = json.dumps(payload).encode("utf-8")
                await conn.stream.write(payload_data)
                logger.debug(f"Sent payload ({len(payload_data)} bytes) to {target_peer_id}")

                # Read response with timeout
                response_data = await conn.stream.read()
                if not response_data:
                    raise P2PConnectionError("Received empty response from peer")
                    
                response = json.loads(response_data.decode("utf-8"))
                logger.info(f"Received response from {target_peer_id}")
                
                return response
                
            except json.JSONEncodeError as e:
                raise P2PConnectionError(f"Failed to encode payload as JSON: {e}") from e
            except json.JSONDecodeError as e:
                raise P2PConnectionError(f"Failed to decode response from peer: {e}") from e
            finally:
                # Always close the stream
                try:
                    await conn.stream.close()
                except Exception as e:
                    logger.warning(f"Failed to close stream: {e}")

        except P2PConnectionError:
            raise
        except Exception as e:
            raise P2PConnectionError(f"Unexpected error during delegation to {target_peer_id}: {e}") from e


# Constants
DEFAULT_P2P_PORT: Final[int] = 9001
DEFAULT_SLEEP_INTERVAL: Final[int] = 10
INITIALIZATION_TIMEOUT: Final[int] = 30

def get_p2p_manager() -> P2PManager:
    """Factory function to create a P2P manager instance."""
    return P2PManager(config=get_p2p_config())
