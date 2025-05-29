"""
Mock Relay Node for testing Circuit Relay v2 functionality.
This creates a libp2p node configured as a relay (hop-enabled).
"""

import os
import sys

import multiaddr
import trio
from loguru import logger

# Add local py-libp2p to path
if os.path.exists("/serve_app/py-libp2p"):
    sys.path.insert(0, "/serve_app/py-libp2p")
else:
    sys.path.insert(0, "***REMOVED***")

import libp2p
from libp2p.relay.circuit_v2.config import RelayConfig
from libp2p.relay.circuit_v2.protocol import CircuitV2Protocol
from libp2p.tools.async_service import background_trio_service


async def run_relay_node():
    """Run a relay node for testing."""
    # Create identity
    key_pair_obj = libp2p.create_new_key_pair()

    # Create host using the new_host factory function
    host = libp2p.new_host(key_pair=key_pair_obj)

    logger.info(f"Relay node created with peer_id: {host.get_id()}")

    # Configure as relay (hop-enabled)
    relay_cfg = RelayConfig(
        enable_hop=True,  # Act as a relay
        enable_stop=True,  # Accept relayed connections
        enable_client=False,  # Don't need client functionality
    )

    # Создаем сервис CircuitV2Protocol. Он сам зарегистрирует обработчики.
    # Передаем allow_hop=True, так как это HOP-узел.
    circuit_protocol_service = CircuitV2Protocol(host, limits=None, allow_hop=True)

    # Получаем Multiselect muxer из хоста
    # protocol_muxer = host.get_mux()
    # protocol_muxer.add_handler(PROTOCOL_ID, protocol_handler.handle_hop_stream)
    # protocol_muxer.add_handler(STOP_PROTOCOL_ID, protocol_handler.handle_stop_stream)

    # Создаем CircuitV2Transport
    # circuit_transport = CircuitV2Transport(host, protocol_handler, relay_cfg)

    # TODO: Как добавить circuit_transport к хосту?
    # В p2p.py и ТЗ был host.add_transport(circuit_transport)
    # Если у IHost/BasicHost нет этого метода, это проблема.
    # Пока пропустим этот шаг и посмотрим, запустится ли хост.
    # logger.warning("Skipping circuit_transport.add_transport() as method availability is unclear for IHost.")

    # Адреса для прослушивания
    listen_addr_strs = ["/ip4/127.0.0.1/tcp/4001"]
    listen_maddrs = [multiaddr.Multiaddr(addr_str) for addr_str in listen_addr_strs]

    network = host.get_network()  # Получаем Swarm (INetworkService)
    # Запускаем сервис сети и сервис протокола CircuitV2
    async with background_trio_service(network), background_trio_service(circuit_protocol_service):
        await network.listen(*listen_maddrs)
        await (
            circuit_protocol_service.event_started.wait()
        )  # Ждем, пока сервис протокола запустится и зарегистрирует обработчики

        actual_addrs = host.get_addrs()  # Должен вернуть адреса с /p2p/peer_id
        logger.info(f"Relay node listening with peer_id: {host.get_id()}")
        logger.info(f"Listening on: {[str(addr) for addr in actual_addrs]}")
        logger.info("CircuitV2Protocol service started for HOP relay. Handlers should be registered internally.")
        logger.info(f"Use this peer ID in your .env: {host.get_id()}")

        # Keep running
        try:
            await trio.sleep_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down relay node (KeyboardInterrupt received)...")
        finally:
            logger.info("Relay node shutting down services...")
            logger.info("Relay node shutdown process complete.")


if __name__ == "__main__":
    logger.add(sys.stderr, level="INFO")
    try:
        trio.run(run_relay_node)
    except KeyboardInterrupt:
        logger.info("Relay node main process terminated by KeyboardInterrupt.")
    except Exception as e:
        logger.error(f"Relay node main process failed: {e}", exc_info=True)
