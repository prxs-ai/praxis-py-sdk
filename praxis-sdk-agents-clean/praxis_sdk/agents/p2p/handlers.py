from __future__ import annotations

import datetime
import json
from typing import TYPE_CHECKING

import httpx
from loguru import logger

from praxis_sdk.agents.p2p.config import get_p2p_config
from praxis_sdk.agents.p2p.const import PROTOCOL_CARD

if TYPE_CHECKING:
    from libp2p.network.stream.net_stream import INetStream


# ---------- CARD ----------- #
async def handle_card(stream: INetStream) -> None:
    peer_id_obj = stream.muxed_conn.peer_id
    peer_id_str = str(peer_id_obj) if peer_id_obj else "UnknownPeer"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    logger.info(f"[{timestamp}] Received card request on {PROTOCOL_CARD} from peer {peer_id_str}")

    cfg = get_p2p_config()
    card_url = f"{cfg.agent_host.url}/card"

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


# ------- HANDOFF -------- #
async def handle_handoff(stream: INetStream) -> None:
    peer_id: str = str(stream.muxed_conn.peer_id)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    logger.info(f"[{ts}] Received handoff request from peer {peer_id}")

    try:
        payload_bytes = await stream.read()
        if not payload_bytes:
            raise ValueError("Empty payload received")

        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid JSON payload: {str(e)}")

        method = payload.get("method")
        path = payload.get("path")
        params = payload.get("params", {})
        input_data = payload.get("input")

        if not method or not path:
            raise ValueError("Missing required fields: method and/or path")

        cfg = get_p2p_config()
        base_url = f"{cfg.agent_host.url}"

        formatted_path = path.format(**params) if params and isinstance(params, dict) else path

        request_url = f"{base_url}/{formatted_path.lstrip('/')}"

        logger.info(f"[{ts}] Making {method.upper()} request to {request_url} for peer {peer_id}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            request_kwargs = {"method": method.upper(), "url": request_url}

            if input_data is not None:
                if isinstance(input_data, dict | list):
                    request_kwargs["json"] = input_data
                else:
                    request_kwargs["content"] = str(input_data).encode("utf-8")

            response = await client.request(**request_kwargs)
            response.raise_for_status()

            await stream.write(response.content)
            logger.info(f"[{ts}] Successfully handled handoff request for peer {peer_id}")

    except json.JSONDecodeError as e:
        logger.error(f"[{ts}] JSON decode error for handoff from {peer_id}: {str(e)}")
        error_msg = json.dumps({"error": f"Invalid JSON: {str(e)}", "code": 400}).encode()
        await stream.write(error_msg)

    except ValueError as e:
        logger.error(f"[{ts}] Validation error for handoff from {peer_id}: {str(e)}")
        error_msg = json.dumps({"error": str(e), "code": 400}).encode()
        await stream.write(error_msg)

    except httpx.HTTPStatusError as e:
        logger.error(f"[{ts}] HTTP error for handoff from {peer_id}: {e.response.status_code} - {e.response.text}")
        error_msg = json.dumps(
            {"error": f"HTTP error: {e.response.status_code}", "code": e.response.status_code}
        ).encode()
        await stream.write(error_msg)

    except httpx.RequestError as e:
        logger.error(f"[{ts}] Request error for handoff from {peer_id}: {type(e).__name__} - {str(e)}")
        error_msg = json.dumps({"error": f"Request to {path} failed or timed out", "code": 504}).encode()
        await stream.write(error_msg)

    except Exception as e:
        logger.error(f"[{ts}] Unexpected error processing handoff for {peer_id}: {e}", exc_info=True)
        error_msg = json.dumps({"error": "Internal server error", "code": 500}).encode()
        await stream.write(error_msg)

    finally:
        try:
            await stream.close()
        except Exception as e:
            logger.error(f"[{ts}] Error closing stream for handoff with peer {peer_id}: {e}")
        logger.info(f"[{ts}] Closed stream for handoff with peer {peer_id}")
