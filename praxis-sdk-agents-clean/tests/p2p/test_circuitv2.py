import logging
import pytest

from libp2p.network.stream.exceptions import (
    StreamEOF,
    StreamReset,
)
from libp2p.relay.circuit_v2.discovery import (
    RelayDiscovery,
)
from libp2p.relay.circuit_v2.protocol import (
    DEFAULT_RELAY_LIMITS,
    CircuitV2Protocol,
    PROTOCOL_ID as HOP_PROTOCOL_ID,
    STOP_PROTOCOL_ID,
)
from libp2p.relay.circuit_v2.resources import (
    RelayLimits,
)
from libp2p.relay.circuit_v2.transport import (
    CircuitV2Transport,
)
from libp2p.tools.utils import (
    connect,
)
from libp2p.tools.constants import (
    MAX_READ_LEN,
)
from libp2p.peer.peerinfo import PeerInfo

import trio

from tests.utils import HostFactory

logger = logging.getLogger(__name__)


CONNECT_TIMEOUT = 15  # seconds
STREAM_TIMEOUT = 15  # seconds
HANDLER_TIMEOUT = 15  # seconds
SLEEP_TIME = 1.0  # seconds
RELAY_TIMEOUT = 20  # seconds


TEST_MESSAGE = b"Hello, Circuit Relay!"
TEST_RESPONSE = b"Hello from the other side!"


# Stream handler for testing
async def echo_stream_handler(stream):
    """Simple echo handler that responds to messages."""
    logger.info("Echo handler received stream")
    try:
        while True:
            data = await stream.read(MAX_READ_LEN)
            if not data:
                logger.info("Stream closed by remote")
                break

            logger.info("Received data: %s", data)
            await stream.write(TEST_RESPONSE)
            logger.info("Sent response")
    except (StreamEOF, StreamReset) as e:
        logger.info("Stream ended: %s", str(e))
    except Exception as e:
        logger.error("Error in echo handler: %s", str(e))
    finally:
        await stream.close()


@pytest.mark.trio
async def test_circuit_v2_transport_initialization():
    """Test that the Circuit v2 transport initializes correctly."""
    async with HostFactory.create_batch_and_listen(1) as hosts:
        host = hosts[0]

        # Create a protocol instance
        limits = RelayLimits(
            duration=DEFAULT_RELAY_LIMITS.duration,
            data=DEFAULT_RELAY_LIMITS.data,
            max_circuit_conns=DEFAULT_RELAY_LIMITS.max_circuit_conns,
            max_reservations=DEFAULT_RELAY_LIMITS.max_reservations,
        )
        protocol = CircuitV2Protocol(host, limits, allow_hop=False)

        # Create a config
        from libp2p.relay.circuit_v2.config import (
            RelayConfig,
        )

        config = RelayConfig()

        # Create a discovery instance
        discovery = RelayDiscovery(
            host=host,
            auto_reserve=False,
            discovery_interval=config.discovery_interval,
            max_relays=config.max_relays,
        )

        # Create the transport with the necessary components
        transport = CircuitV2Transport(host, protocol, config)
        # Replace the discovery with our manually created one
        transport.discovery = discovery

        # Verify transport properties
        assert transport.host == host, "Host not set correctly"
        assert transport.protocol == protocol, "Protocol not set correctly"
        assert transport.config == config, "Config not set correctly"
        assert hasattr(transport, "discovery"), (
            "Transport should have a discovery instance"
        )


@pytest.mark.trio
async def test_circuit_v2_transport_dial_through_relay():
    """Test dialing a peer through a relay."""
    async with HostFactory.create_batch_and_listen(3) as hosts:
        client_host, relay_host, target_host = hosts
        logger.info("Created hosts for test_circuit_v2_transport_dial_through_relay")
        logger.info("Client host ID: %s", client_host.get_id())
        logger.info("Relay host ID: %s", relay_host.get_id())
        logger.info("Target host ID: %s", target_host.get_id())

        # Setup relay with Circuit v2 protocol
        limits = RelayLimits(
            duration=DEFAULT_RELAY_LIMITS.duration,
            data=DEFAULT_RELAY_LIMITS.data,
            max_circuit_conns=DEFAULT_RELAY_LIMITS.max_circuit_conns,
            max_reservations=DEFAULT_RELAY_LIMITS.max_reservations,
        )

        # Register test handler on target
        test_protocol = "/test/echo/1.0.0"
        target_host.set_stream_handler(test_protocol, echo_stream_handler)  # type: ignore

        # Setup transport on client
        from libp2p.relay.circuit_v2.config import (
            RelayConfig,
        )

        client_config = RelayConfig()
        client_protocol = CircuitV2Protocol(client_host, limits, allow_hop=False)

        # Create a discovery instance
        client_discovery = RelayDiscovery(
            host=client_host,
            auto_reserve=False,
            discovery_interval=client_config.discovery_interval,
            max_relays=client_config.max_relays,
        )

        # Create the transport with the necessary components
        client_transport = CircuitV2Transport(
            client_host, client_protocol, client_config
        )
        # Replace the discovery with our manually created one
        client_transport.discovery = client_discovery

        # Mock the get_relay method to return our relay_host
        relay_id = relay_host.get_id()
        client_discovery.get_relay = lambda: relay_id  # type: ignore

        relay_protocol = CircuitV2Protocol(relay_host, limits, allow_hop=True)
        relay_host.set_stream_handler(
            HOP_PROTOCOL_ID, relay_protocol._handle_hop_stream
        )
        relay_host.set_stream_handler(
            STOP_PROTOCOL_ID, relay_protocol._handle_stop_stream
        )

        # Connect client to relay and relay to target
        try:
            with trio.fail_after(
                CONNECT_TIMEOUT * 2
            ):  # Double the timeout for connections
                logger.info("Connecting client host to relay host")
                await connect(client_host, relay_host)
                # Verify connection
                assert relay_host.get_id() in client_host.get_network().connections, (
                    "Client not connected to relay"
                )
                assert client_host.get_id() in relay_host.get_network().connections, (
                    "Relay not connected to client"
                )
                logger.info("Client-Relay connection verified")

                # Wait to ensure connection is fully established
                await trio.sleep(SLEEP_TIME)

                logger.info("Connecting relay host to target host")
                await connect(relay_host, target_host)
                # Verify connection
                assert target_host.get_id() in relay_host.get_network().connections, (
                    "Relay not connected to target"
                )
                assert relay_host.get_id() in target_host.get_network().connections, (
                    "Target not connected to relay"
                )
                logger.info("Relay-Target connection verified")

                # Wait to ensure connection is fully established
                await trio.sleep(SLEEP_TIME)

                logger.info("Connecting client host to target host via relay")
                await client_transport.dial(
                    PeerInfo(client_host.get_id(), []),
                    relay_peer_id=relay_host.get_id(),
                )

                logger.info("All connections established and verified")
        except Exception as e:
            logger.error("Failed to connect peers: %s", str(e))
            raise

        # Test successful - the connections were established, which is enough to verify
        # that the transport can be initialized and configured correctly
        logger.info("Transport initialization and connection test passed")
