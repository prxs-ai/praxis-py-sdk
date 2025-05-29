import os
import sys
import datetime
from typing import List, Optional, TYPE_CHECKING

import httpx
import multiaddr
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    import libp2p
    from libp2p.peer.id import ID
    from libp2p.peer.peerinfo import PeerInfo
    from libp2p.abc import INetStream
    from libp2p.custom_types import TProtocol
    from libp2p.relay.circuit_v2.transport import CircuitV2Transport
    from libp2p.relay.circuit_v2.protocol import STOP_PROTOCOL_ID, CircuitV2Protocol
    from libp2p.relay.circuit_v2.config import RelayConfig

from base_agent.config import get_agent_config

libp2p_node: Optional['libp2p.IHost'] = None

PROTOCOL_CARD: Optional['TProtocol'] = None


def _ensure_libp2p_path():
    """Ensure libp2p is in the Python path."""
    if "/serve_app/py-libp2p" not in sys.path and "/Users/hexavor/Desktop/PraxisAI/agents/base-agent/py-libp2p" not in sys.path:
        if os.path.exists("/serve_app/py-libp2p"):
            sys.path.insert(0, "/serve_app/py-libp2p")
        else:
            sys.path.insert(0, "/Users/hexavor/Desktop/PraxisAI/agents/base-agent/py-libp2p")


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=5),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    reraise=True,
)
async def register_with_registry(peer_id: 'ID', addrs: List[str], agent_name: str, registry_url: str) -> None:
    payload = {"agent_name": agent_name, "peer_id": str(peer_id), "addrs": addrs}
    logger.info(f"Attempting to register with registry: peer_id={peer_id}, addrs={addrs}, agent_name={agent_name}")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{registry_url}/register", json=payload, timeout=5.0)
            resp.raise_for_status()
            logger.info(f"Successfully registered with registry: peer_id={peer_id}, response_status={resp.status_code}")
        except httpx.HTTPStatusError as e:
            attempt = getattr(register_with_registry.retry, "statistics", {}).get("attempt_number", 1)
            logger.error(
                f"HTTP error during registration for {peer_id} (attempt {attempt}): {e.response.status_code} - {e.response.text}"
            )
            raise
        except httpx.RequestError as e:
            attempt = getattr(register_with_registry.retry, "statistics", {}).get("attempt_number", 1)
            logger.error(f"Request error during registration for {peer_id} (attempt {attempt}): {e}")
            raise
        except Exception as e:
            attempt = getattr(register_with_registry.retry, "statistics", {}).get("attempt_number", 1)
            logger.error(f"Unexpected error during registration for {peer_id} (attempt {attempt}): {e}")
            raise


async def handle_card(stream: 'INetStream') -> None:
    """
    Обработчик для протокола /ai-agent/card/1.0.0
    Проксирует запрос к локальному HTTP эндпоинту /card
    """
    peer_id_obj = stream.muxed_conn.peer_id
    peer_id_str = str(peer_id_obj) if peer_id_obj else "UnknownPeer"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    logger.info(f"[{timestamp}] Received card request on {PROTOCOL_CARD} from peer {peer_id_str}")
    
    card_url = "http://localhost:8000/card"
    
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(card_url)
            response.raise_for_status()

        await stream.write(response.content)
        logger.info(f"[{timestamp}] Sent card data to peer {peer_id_str} for protocol {PROTOCOL_CARD}")

    except httpx.HTTPStatusError as e:
        logger.error(f"[{timestamp}] HTTP error for {PROTOCOL_CARD} from {peer_id_str}: {e.response.status_code} - {e.response.text}")
        error_msg = f'{{"error":"HTTP error: {e.response.status_code}","code":{e.response.status_code}}}'.encode()
        await stream.write(error_msg)
    except httpx.RequestError as e:
        logger.error(f"[{timestamp}] Request error for {PROTOCOL_CARD} from {peer_id_str}: {type(e).__name__} - {str(e)}")
        await stream.write(b'{"error":"Request to /card failed or timed out","code":504}') # 504 Gateway Timeout
    except Exception as e:
        logger.error(f"[{timestamp}] Unexpected error processing {PROTOCOL_CARD} for {peer_id_str}: {e}", exc_info=True)
        await stream.write(b'{"error":"Internal server error","code":500}')
    finally:
        try:
            await stream.close()
        except Exception as e:
            logger.error(f"[{timestamp}] Error closing stream for {PROTOCOL_CARD} with peer {peer_id_str}: {e}")
        logger.info(f"[{timestamp}] Closed stream for {PROTOCOL_CARD} with peer {peer_id_str}")


async def setup_libp2p() -> None:
    global libp2p_node
    if libp2p_node is not None:
        logger.warning("libp2p_node already initialized. Skipping setup.")
        return

    try:
        _ensure_libp2p_path()
        
        import libp2p
        from libp2p.peer.id import ID
        from libp2p.peer.peerinfo import PeerInfo
        from libp2p.relay.circuit_v2.config import RelayConfig
        from libp2p.relay.circuit_v2.protocol import STOP_PROTOCOL_ID, CircuitV2Protocol
        from libp2p.relay.circuit_v2.transport import CircuitV2Transport
        from libp2p.tools.utils import info_from_p2p_addr
        from multiaddr import Multiaddr

        config = get_agent_config()
        
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            logger.info(f"Found running event loop: {loop}")
        except RuntimeError as e:
            logger.error(f"No running event loop found: {e}")
            raise RuntimeError("setup_libp2p must be called from async context") from e

        import trio_asyncio
        import trio

        key_pair_obj = libp2p.create_new_key_pair()
        current_host = libp2p.new_host(key_pair=key_pair_obj)
        logger.info(f"Libp2p host created: peer_id={current_host.get_id()}")

        relay_cfg_for_agent = RelayConfig(
            enable_hop=False,
            enable_stop=True,
            enable_client=True,
            bootstrap_relays=[info_from_p2p_addr(Multiaddr("/dns4/relay-service.dev.prxs.ai/tcp/9000/p2p/12D3KooWR2ykSpRSRoqdVmrqrm55sWuLz8jQPrnGoUPsiwTQ7Dd2"))],
        )
        circuit_protocol_handler = CircuitV2Protocol(
            current_host, limits=getattr(relay_cfg_for_agent, "limits", None), allow_hop=False
        )
        circuit_transport = CircuitV2Transport(current_host, circuit_protocol_handler, config=relay_cfg_for_agent)
        
        async def _setup_libp2p_in_trio():
            from libp2p.relay.circuit_v2.transport import CircuitV2Transport
            from libp2p.relay.circuit_v2.protocol import STOP_PROTOCOL_ID, CircuitV2Protocol
            from libp2p.relay.circuit_v2.config import RelayConfig
            from multiaddr import Multiaddr
            from libp2p.tools.utils import info_from_p2p_addr

            try:
                registry_pid = ID.from_base58(config.registry_relay_peer_id)
            except Exception as e:
                logger.error(f"Invalid REGISTRY_RELAY_PEER_ID: {config.registry_relay_peer_id}. Error: {e}")
                raise

            registry_addr_str = config.registry_relay_multiaddr_template.format(str(registry_pid))
            registry_multiaddr_val = multiaddr.Multiaddr(registry_addr_str)
            relay_peer_info = PeerInfo(registry_pid, [registry_multiaddr_val])

            # # Временно закомментируем relay config, так как circuit transport не используется
            # relay_cfg_for_agent = RelayConfig(
            #     enable_hop=False,
            #     enable_stop=True,
            #     enable_client=True,
            #     bootstrap_relays=[relay_peer_info],
            # )
            

            network = current_host.get_network()

            protocol_muxer = current_host.get_mux()
            protocol_muxer.add_handler(STOP_PROTOCOL_ID, circuit_protocol_handler._handle_stop_stream)
            logger.info("Manually registered _handle_stop_stream for agent.")

            global PROTOCOL_CARD
            from libp2p.custom_types import TProtocol
            PROTOCOL_CARD = TProtocol("/ai-agent/card/1.0.0")
            
            current_host.set_stream_handler(PROTOCOL_CARD, handle_card)
            logger.info(f"Registered stream handler for {PROTOCOL_CARD}")

            listen_maddr_val = multiaddr.Multiaddr(config.agent_p2p_listen_addr)
            network = current_host.get_network()

            listen_success = False
            
            try:
                logger.info(f"Attempting to listen on {listen_maddr_val}")
                
                import trio
                with trio.move_on_after(10) as cancel_scope:  
                    await network.listen(listen_maddr_val)
                
                if cancel_scope.cancelled_caught:
                    logger.warning("Network listen operation timed out after 10 seconds")
                    logger.info("Continuing without network listening - libp2p host is still functional")
                else:
                    logger.info("Libp2p network started listening successfully.")
                    listen_success = True
                    
            except Exception as e:
                logger.warning(f"Failed to listen on {listen_maddr_val}: {e}")
                logger.info("Continuing without network listening - libp2p host is still functional")

            peer_id = current_host.get_id()
            actual_addrs = current_host.get_addrs()
            addrs_str_list = [str(addr) for addr in actual_addrs]
            
            if listen_success:
                logger.info(f"Libp2p node started and listening: peer_id={peer_id} on addrs={addrs_str_list}")
            else:
                logger.info(f"Libp2p host created (no listening): peer_id={peer_id}")

            if listen_success:
                try:
                    await register_with_registry(peer_id, addrs_str_list, config.agent_name, config.registry_http_url)
                    logger.info("Successfully registered with relay registry")
                except Exception as e:
                    logger.warning(f"Failed to register with registry (continuing anyway): {e}")
            else:
                logger.info("Skipping registry registration since network listening failed")

            return current_host

        logger.info("Starting libp2p in trio-asyncio context...")
        
        import concurrent.futures
        import threading
        
        result_future = concurrent.futures.Future()
        
        def run_trio():
            try:
                logger.info("Trio thread started, running libp2p initialization...")
                result = trio.run(_setup_libp2p_in_trio)
                logger.info("Trio initialization completed successfully!")
                result_future.set_result(result)
            except Exception as e:
                logger.error(f"Trio thread failed with exception: {e}")
                import traceback
                traceback.print_exc()
                result_future.set_exception(e)
        
        trio_thread = threading.Thread(target=run_trio, daemon=True)
        trio_thread.start()
        
        try:
            libp2p_node = result_future.result(timeout=15)  # Уменьшили до 15 секунд
            libp2p_node.add_transport(circuit_transport)

            logger.info("Libp2p successfully initialized via trio thread!")
        except concurrent.futures.TimeoutError:
            logger.error("Libp2p initialization timed out after 15 seconds") 
            if trio_thread.is_alive():
                logger.error("Trio thread is still running - likely stuck on network.listen()")
            raise RuntimeError("Libp2p initialization timeout")

    except Exception as e:
        logger.error(f"Failed to setup libp2p: {e}")
        libp2p_node = None
        import traceback
        traceback.print_exc()
        raise


async def shutdown_libp2p() -> None:
    global libp2p_node
    if libp2p_node:
        logger.info("Shutting down libp2p node...")
        try:
            network = libp2p_node.get_network()
            if hasattr(network, "is_running") and network.is_running:
                await network.close()
            elif not hasattr(network, "is_running"):
                await network.close()
            logger.info("Libp2p network closed.")
        except Exception as e:
            logger.error(f"Error during libp2p_node.get_network().close(): {e}")

        libp2p_node = None
        logger.info("Libp2p node resources cleared.")
    else:
        logger.info("Libp2p node already shut down or not initialized.")


def get_libp2p_status() -> dict:
    """Get the current status of the libp2p node."""
    global libp2p_node
    
    if libp2p_node is None:
        return {"initialized": False, "peer_id": None, "addrs": []}
    
    try:
        peer_id = libp2p_node.get_id()
        addrs = [str(addr) for addr in libp2p_node.get_addrs()]
        
        network = libp2p_node.get_network()
        network_info = {
            "connections": len(network.connections) if hasattr(network, 'connections') else 0,
            "is_started": hasattr(network, 'is_started') and getattr(network, 'is_started', False)
        }
        
        return {
            "initialized": True,
            "peer_id": str(peer_id),
            "addrs": addrs,
            "network": network_info
        }
    except Exception as e:
        return {"initialized": False, "error": str(e), "peer_id": None, "addrs": []}


def diagnose_libp2p_environment() -> dict:
    import sys
    import os
    
    diagnosis = {
        "python_version": sys.version,
        "platform": sys.platform,
        "py_libp2p_paths": []
    }
    
    # Проверяем доступные пути для py-libp2p
    possible_paths = [
        "/serve_app/py-libp2p",
        "/Users/hexavor/Desktop/PraxisAI/agents/base-agent/py-libp2p",
        os.path.join(os.getcwd(), "py-libp2p")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            diagnosis["py_libp2p_paths"].append(path)
    
    try:
        _ensure_libp2p_path()
        import libp2p
        diagnosis["libp2p_available"] = True
        diagnosis["libp2p_version"] = getattr(libp2p, "__version__", "unknown")
    except Exception as e:
        diagnosis["libp2p_available"] = False
        diagnosis["libp2p_error"] = str(e)
    
    # Проверяем async контекст
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        diagnosis["async_context"] = True
        diagnosis["event_loop"] = str(loop)
    except RuntimeError:
        diagnosis["async_context"] = False
        diagnosis["event_loop"] = None
    
    return diagnosis


def get_peer_info_formatted() -> dict | None:
    global libp2p_node
    
    if libp2p_node is None:
        return None
    
    try:
        _ensure_libp2p_path()
        from libp2p.peer.peerinfo import PeerInfo
        
        peer_id = libp2p_node.get_id()
        addrs = libp2p_node.get_addrs()
        
        peer_info = PeerInfo(peer_id, addrs)
        
        return {
            "peer_id": str(peer_info.peer_id),
            "addrs": [str(addr) for addr in peer_info.addrs],
            "peer_info_object": peer_info
        }
    except Exception as e:
        logger.error(f"Failed to get peer info: {e}")
        return None


def print_peer_info() -> None:
    peer_info_data = get_peer_info_formatted()
    
    if peer_info_data:
        print("\n" + "="*60)
        print("🌐 LIBP2P AGENT PEER INFO")
        print("="*60)
        print(f" Peer ID: {peer_info_data['peer_id']}")
        print(f" Addresses ({len(peer_info_data['addrs'])}):")
        for i, addr in enumerate(peer_info_data['addrs'], 1):
            print(f"   {i}. {addr}")
        print("="*60 + "\n")
    else:
        print("\n⚠️  LibP2P peer info not available\n")
