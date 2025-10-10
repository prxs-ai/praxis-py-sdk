"""P2P Communication Module for Praxis SDK

This module provides peer-to-peer communication capabilities using libp2p:
- Service management and host initialization
- Protocol handlers for different communication types
- mDNS-based peer discovery
- Security management with Ed25519 keys
"""

from .discovery import P2PDiscovery, PeerInfo
from .protocols import AgentCard, P2PProtocolHandler, ToolParameter, ToolSpec
from .security import P2PSecurityManager
from .service import P2PConfig
from .service_fixed import P2PServiceFixed, create_p2p_service
from .service_simplified import SimplifiedP2PService, create_simplified_p2p_service

__all__ = [
    "P2PServiceFixed",
    "SimplifiedP2PService",
    "create_p2p_service",
    "create_simplified_p2p_service",
    "P2PConfig",
    "P2PProtocolHandler",
    "P2PDiscovery",
    "P2PSecurityManager",
    "AgentCard",
    "ToolSpec",
    "ToolParameter",
    "PeerInfo",
]
