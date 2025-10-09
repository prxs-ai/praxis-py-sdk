"""Simplified P2P Service to get the system running."""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from loguru import logger

from ..bus import EventBus, EventType
from ..config import P2PConfig


class P2PService:
    """Simplified P2P service without libp2p for initial deployment."""

    def __init__(self, config: P2PConfig, event_bus: EventBus):
        """Initialize P2P service."""
        self.config = config
        self.event_bus = event_bus
        self.peer_id = f"simple-peer-{os.getpid()}"
        self.running = False
        self.connected_peers: list[str] = []

        logger.info(f"P2P Service initialized with peer ID: {self.peer_id}")

    async def start(self):
        """Start P2P service."""
        if self.running:
            return

        self.running = True
        logger.info(f"P2P Service started on port {self.config.port}")

        # Emit event that P2P is ready
        await self.event_bus.emit(
            EventType.PEER_DISCOVERED,
            {"peer_id": self.peer_id, "protocols": self.config.protocols},
        )

    async def stop(self):
        """Stop P2P service."""
        if not self.running:
            return

        self.running = False
        logger.info("P2P Service stopped")

    async def connect_to_peer(self, peer_id: str, multiaddr: str) -> bool:
        """Connect to a peer (simplified)."""
        if peer_id not in self.connected_peers:
            self.connected_peers.append(peer_id)
            logger.info(f"Connected to peer: {peer_id}")

            await self.event_bus.emit(
                EventType.PEER_CONNECTED, {"peer_id": peer_id, "multiaddr": multiaddr}
            )
            return True
        return False

    async def disconnect_from_peer(self, peer_id: str):
        """Disconnect from a peer."""
        if peer_id in self.connected_peers:
            self.connected_peers.remove(peer_id)
            logger.info(f"Disconnected from peer: {peer_id}")

            await self.event_bus.emit(EventType.PEER_DISCONNECTED, {"peer_id": peer_id})

    def get_peer_id(self) -> str:
        """Get our peer ID."""
        return self.peer_id

    def get_multiaddrs(self) -> list[str]:
        """Get our multiaddresses."""
        return [f"/ip4/0.0.0.0/tcp/{self.config.port}/p2p/{self.peer_id}"]

    def get_connected_peers(self) -> list[str]:
        """Get list of connected peers."""
        return self.connected_peers.copy()

    async def send_message(self, peer_id: str, protocol: str, data: bytes) -> bool:
        """Send message to peer (simplified)."""
        if peer_id not in self.connected_peers:
            logger.warning(f"Cannot send message to disconnected peer: {peer_id}")
            return False

        logger.debug(f"Sending message to {peer_id} on protocol {protocol}")

        # Emit event for message handling
        await self.event_bus.emit(
            EventType.MESSAGE_RECEIVED,
            {"peer_id": peer_id, "protocol": protocol, "data": data},
        )

        return True

    async def broadcast_message(self, protocol: str, data: bytes):
        """Broadcast message to all peers."""
        for peer_id in self.connected_peers:
            await self.send_message(peer_id, protocol, data)
