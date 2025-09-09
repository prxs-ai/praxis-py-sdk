"""
P2P Communication Module for Praxis SDK

This module provides peer-to-peer communication capabilities using libp2p:
- Service management and host initialization
- Protocol handlers for different communication types
- mDNS-based peer discovery
- Security management with Ed25519 keys
"""

from .service_fixed import P2PServiceFixed, create_p2p_service
from .service_simplified import SimplifiedP2PService, create_simplified_p2p_service
from .service import P2PConfig
from .protocols import P2PProtocolHandler, AgentCard, ToolSpec, ToolParameter
from .discovery import P2PDiscovery, PeerInfo
from .security import P2PSecurityManager

__all__ = [
    'P2PServiceFixed',
    'SimplifiedP2PService',
    'create_p2p_service',
    'create_simplified_p2p_service',
    'P2PConfig', 
    'P2PProtocolHandler',
    'P2PDiscovery',
    'P2PSecurityManager',
    'AgentCard',
    'ToolSpec',
    'ToolParameter',
    'PeerInfo'
]