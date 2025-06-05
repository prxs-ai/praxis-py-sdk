import multiaddr
import pytest
import trio
from libp2p import new_host
from libp2p.network.stream.net_stream import INetStream # type: ignore
from libp2p.peer.peerinfo import info_from_p2p_addr
from libp2p.relay.circuit_v2.config import RelayConfig
from libp2p.relay.circuit_v2.protocol import CircuitV2Protocol
from libp2p.relay.circuit_v2.transport import CircuitV2Transport
from libp2p.peer.peerinfo import PeerInfo
from libp2p.peer.id import ID

import os

async def main():
    host = new_host()
    relay_info = info_from_p2p_addr(multiaddr.Multiaddr(os.environ['P2P_RELAY_ADDR']))
    # Configure as a relay client
    config = RelayConfig(
        enable_client=True,  # Use relays for outbound connections
    )

    # Initialize the relay protocol
    protocol = CircuitV2Protocol(host)
    transport = CircuitV2Transport(host, protocol, config)

    async with host.run(listen_addrs=[]):

        await host.connect(relay_info)
        print("Connected to relay successfully")

        peer_info = PeerInfo(ID.from_base58(AGENT_PEER_ID), [])

        print(f"Attempting to connect to {AGENT_PEER_ID} via relay")
        await transport.dial(peer_info, relay_peer_id=relay_info.peer_id)
        print("Connection established through relay!")

if __name__ == "__main__":
    trio.run(main)