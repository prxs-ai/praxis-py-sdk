from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import httpx
from loguru import logger

from base_agent.p2p.const import PROTOCOL_CARD

if TYPE_CHECKING:
    from libp2p.network.stream.net_stream import INetStream


async def handle_card(stream: INetStream) -> None:
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
        logger.error(
            f"[{timestamp}] HTTP error for {PROTOCOL_CARD} from {peer_id_str}: {e.response.status_code} - {e.response.text}"
        )
        error_msg = f'{{"error":"HTTP error: {e.response.status_code}","code":{e.response.status_code}}}'.encode()
        await stream.write(error_msg)
    except httpx.RequestError as e:
        logger.error(
            f"[{timestamp}] Request error for {PROTOCOL_CARD} from {peer_id_str}: {type(e).__name__} - {str(e)}"
        )
        await stream.write(b'{"error":"Request to /card failed or timed out","code":504}')  # 504 Gateway Timeout
    except Exception as e:
        logger.error(f"[{timestamp}] Unexpected error processing {PROTOCOL_CARD} for {peer_id_str}: {e}", exc_info=True)
        await stream.write(b'{"error":"Internal server error","code":500}')
    finally:
        try:
            await stream.close()
        except Exception as e:
            logger.error(f"[{timestamp}] Error closing stream for {PROTOCOL_CARD} with peer {peer_id_str}: {e}")
        logger.info(f"[{timestamp}] Closed stream for {PROTOCOL_CARD} with peer {peer_id_str}")
