import os

import multiaddr
import trio
from libp2p import new_host
from libp2p.custom_types import TProtocol
from libp2p.network.stream.net_stream import INetStream
from libp2p.peer.id import ID
from libp2p.peer.peerinfo import PeerInfo, info_from_p2p_addr
from libp2p.relay.circuit_v2.config import RelayConfig
from libp2p.relay.circuit_v2.protocol import CircuitV2Protocol
from libp2p.relay.circuit_v2.transport import CircuitV2Transport

CARD_PROTOCOL_ID = TProtocol("/ai-agent/card/1.0.0")
AGENT_PEER_ID = "QmYQQD9nqGNMGbxUSmypo6aqk7G52gpk6UvtCh6EHZqRAP"


async def request_card(stream: INetStream) -> None:
    request_data = b"GET_CARD"
    print(f"Sending card request to {stream.muxed_conn.peer_id}")
    await stream.write(request_data)

    with trio.fail_after(30):
        response = await stream.read()

    if response:
        print("Card response:")
        print(response.decode())
    else:
        print("Empty response")


async def main() -> None:
    # listen_addr = multiaddr.Multiaddr("/ip4/0.0.0.0/tcp/9002")
    host = new_host()
    relay_info = info_from_p2p_addr(multiaddr.Multiaddr(os.environ["P2P_RELAY_ADDR"]))
    # Configure as a relay client
    config = RelayConfig(
        enable_client=True,  # Use relays for outbound connections
        bootstrap_relays=[relay_info],
    )

    # Initialize the relay protocol
    protocol = CircuitV2Protocol(host)
    transport = CircuitV2Transport(host, protocol, config)
    transport.discovery.get_relays = lambda: [relay_info.peer_id]

    async with host.run(listen_addrs=[]):
        await host.connect(relay_info)
        print("Connected to relay successfully")

        peer_info = PeerInfo(ID.from_base58(AGENT_PEER_ID), [])

        print(f"Attempting to connect to {AGENT_PEER_ID} via relay")
        connection = await transport.dial(peer_info)
        print("Connection established through relay!")

        stream = await connection.new_stream(CARD_PROTOCOL_ID)

        await request_card(stream)
        await stream.close()


if __name__ == "__main__":
    trio.run(main)
