
#!/usr/bin/env python3

import json
import multiaddr
import trio
from libp2p import new_host
from libp2p.custom_types import TProtocol
from libp2p.network.stream.net_stream import INetStream
from libp2p.peer.peerinfo import info_from_p2p_addr

CARD_PROTOCOL_ID = TProtocol("/ai-agent/card/1.0.0")
RELAY_PEER_ID = "12D3KooWNVPSC2WyHJaqGSTmpDwumXt6VJRXV1pyJafJobJZYrKu"
AGENT_PEER_ID = "QmZ4dNhh1RQ2fpuB8MiZv2Hb6C9GN1XheCKov3q5HWjR5E"

async def request_card(stream: INetStream):
    request = {"action": "get_card"}
    await stream.write(json.dumps(request).encode())
    response = await stream.read()
    print(response.decode() if response else "No response")

async def main():
    host = new_host()
    listen_addr = multiaddr.Multiaddr("/ip4/0.0.0.0/tcp/8001")
    
    async with host.run(listen_addrs=[listen_addr]):
        relay_addr = multiaddr.Multiaddr(f"/ip4/52.215.229.36/tcp/9000/p2p/{RELAY_PEER_ID}")
        relay_info = info_from_p2p_addr(relay_addr)
        await host.connect(relay_info)
        
        from libp2p.peer.id import ID
        target_peer_id = ID.from_base58(AGENT_PEER_ID)
        
        circuit_addr = multiaddr.Multiaddr(
            f"/ip4/52.215.229.36/tcp/9000/p2p/{RELAY_PEER_ID}/p2p-circuit/p2p/{AGENT_PEER_ID}"
        )
        host.get_peerstore().add_addrs(target_peer_id, [circuit_addr], 60)
        
        stream = await host.new_stream(target_peer_id, [CARD_PROTOCOL_ID])
        await request_card(stream)
        await stream.close()

if __name__ == "__main__":
    trio.run(main)