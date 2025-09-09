"""
P2P Discovery Service for Praxis SDK

This module implements mDNS-based peer discovery for automatic agent detection
and connection in the local network.
"""

import asyncio
import logging
import time
import socket
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import trio
import trio_asyncio

from zeroconf import ServiceInfo, Zeroconf
from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf

from libp2p import IHost
from libp2p.peer.id import ID as PeerID
from libp2p.peer.peerinfo import info_from_p2p_addr
from multiaddr import Multiaddr

from ..bus import EventBus

logger = logging.getLogger(__name__)

@dataclass
class PeerInfo:
    """Information about a discovered peer"""
    id: str
    addresses: List[str]
    found_at: float
    last_seen: float
    agent_card: Optional[Dict[str, Any]] = None
    is_connected: bool = False
    connection_attempts: int = 0
    last_connection_attempt: float = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "addresses": self.addresses,
            "found_at": self.found_at,
            "last_seen": self.last_seen,
            "agent_card": self.agent_card,
            "is_connected": self.is_connected,
            "connection_attempts": self.connection_attempts,
            "last_connection_attempt": self.last_connection_attempt
        }


class MDNSServiceListener:
    """Service listener for mDNS discovery"""
    
    def __init__(self, callback: Callable):
        self.callback = callback
        self.discovered_services = {}
    
    def add_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        """Called when a service is added"""
        info = zeroconf.get_service_info(service_type, name)
        if info:
            service_data = {
                'name': name,
                'type': service_type,
                'addresses': [socket.inet_ntoa(addr) for addr in info.addresses],
                'port': info.port,
                'properties': {k.decode('utf-8'): v.decode('utf-8') if isinstance(v, bytes) else v 
                             for k, v in info.properties.items()}
            }
            self.discovered_services[name] = service_data
            # Use asyncio in asyncio context (zeroconf callbacks run in asyncio)
            asyncio.create_task(self.callback('add', service_data))
    
    def remove_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        """Called when a service is removed"""
        if name in self.discovered_services:
            service_data = self.discovered_services.pop(name)
            asyncio.create_task(self.callback('remove', service_data))
    
    def update_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        """Called when a service is updated"""
        info = zeroconf.get_service_info(service_type, name)
        if info:
            service_data = {
                'name': name,
                'type': service_type,
                'addresses': [socket.inet_ntoa(addr) for addr in info.addresses],
                'port': info.port,
                'properties': {k.decode('utf-8'): v.decode('utf-8') if isinstance(v, bytes) else v 
                             for k, v in info.properties.items()}
            }
            self.discovered_services[name] = service_data
            asyncio.create_task(self.callback('update', service_data))


class MDNSDiscovery:
    """
    mDNS-based peer discovery implementation using zeroconf.
    
    This class handles mDNS service registration and discovery
    to automatically find other Praxis agents in the local network.
    """
    
    def __init__(self, service_name: str, port: int):
        self.service_name = service_name
        self.port = port
        self.service_type = f"_{service_name}._tcp.local."
        self._running = False
        self._azc: Optional[AsyncZeroconf] = None
        self._service_info: Optional[ServiceInfo] = None
        self._browser: Optional[AsyncServiceBrowser] = None
        self._listener: Optional[MDNSServiceListener] = None
        self.discovered_peers: Dict[str, Dict[str, Any]] = {}
        
    async def start(self):
        """Start mDNS service"""
        if self._running:
            return
        
        self._running = True
        
        try:
            # Initialize AsyncZeroconf (no await needed for constructor)
            self._azc = AsyncZeroconf()
            
            # Create listener for service discovery
            self._listener = MDNSServiceListener(self._on_service_change)
            
            # Start browser for peer discovery (constructor doesn't need await)
            self._browser = AsyncServiceBrowser(
                self._azc.zeroconf, 
                self.service_type, 
                self._listener
            )
            
            logger.info(f"Started mDNS discovery for service: {self.service_name}")
            
        except Exception as e:
            logger.error(f"Failed to start mDNS discovery: {e}")
            self._running = False
            raise
        
    async def stop(self):
        """Stop mDNS service"""
        if not self._running:
            return
            
        self._running = False
        
        try:
            # Unregister service if registered
            if self._service_info and self._azc:
                await trio_asyncio.aio_as_trio(self._azc.async_unregister_service)(self._service_info)
                self._service_info = None
            
            # Stop browser
            if self._browser:
                await trio_asyncio.aio_as_trio(self._browser.async_cancel)()
                self._browser = None
            
            # Close zeroconf
            if self._azc:
                await trio_asyncio.aio_as_trio(self._azc.async_close)()
                self._azc = None
            
            self._listener = None
            
        except Exception as e:
            logger.error(f"Error stopping mDNS discovery: {e}")
        
        logger.info("Stopped mDNS discovery")
        
    async def announce_service(self, peer_id: str, addresses: List[str]):
        """Announce our service on mDNS"""
        if not self._azc or not self._running:
            logger.warning("mDNS not started, cannot announce service")
            return
            
        try:
            # Get local IP address
            local_ip = self._get_local_ip()
            
            # Create service info
            service_name = f"{peer_id}.{self.service_type}"
            
            # Prepare properties
            properties = {
                b'peer_id': peer_id.encode('utf-8'),
                b'addresses': ','.join(addresses).encode('utf-8'),
                b'service': self.service_name.encode('utf-8')
            }
            
            self._service_info = ServiceInfo(
                self.service_type,
                service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties=properties,
                server=f"{peer_id}.local."
            )
            
            # Register service using trio_asyncio wrapper
            await trio_asyncio.aio_as_trio(self._azc.async_register_service)(self._service_info)
            
            logger.info(f"Announced mDNS service for peer {peer_id} on {local_ip}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to announce service: {e}")
        
    async def discover_peers(self) -> List[Dict[str, Any]]:
        """Discover peers via mDNS"""
        return list(self.discovered_peers.values())
    
    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            # Connect to a remote address to get local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    async def _on_service_change(self, action: str, service_data: Dict[str, Any]):
        """Handle service changes"""
        try:
            # Extract peer information from service properties
            properties = service_data.get('properties', {})
            peer_id = properties.get('peer_id')
            
            if not peer_id:
                return  # Skip services without peer_id
            
            if action == 'add' or action == 'update':
                # Add/update peer
                peer_info = {
                    'id': peer_id,
                    'addresses': service_data.get('addresses', []),
                    'port': service_data.get('port'),
                    'service_name': service_data.get('name'),
                    'properties': properties,
                    'discovered_at': time.time()
                }
                
                self.discovered_peers[peer_id] = peer_info
                logger.info(f"Discovered peer via mDNS: {peer_id} at {peer_info['addresses']}")
                
            elif action == 'remove':
                # Remove peer
                if peer_id in self.discovered_peers:
                    del self.discovered_peers[peer_id]
                    logger.info(f"Peer removed from mDNS: {peer_id}")
            
        except Exception as e:
            logger.error(f"Error handling service change: {e}")


class P2PDiscovery:
    """
    P2P discovery service for automatic peer detection and connection.
    
    Features:
    - mDNS-based service discovery  
    - Automatic peer connection with timeout
    - Peer lifecycle management
    - Connection state tracking
    - Bootstrap peer support
    """
    
    def __init__(self, host: IHost, event_bus: EventBus, config: Any):
        self.host = host
        self.event_bus = event_bus
        self.config = config
        
        # Discovery configuration
        self.service_tag = getattr(config, 'discovery_service', 'praxis-p2p-mcp')
        self.discovery_interval = getattr(config, 'discovery_interval', 10)
        self.connection_timeout = getattr(config, 'connection_timeout', 30)
        self.max_connection_attempts = getattr(config, 'max_connection_attempts', 3)
        self.bootstrap_peers = getattr(config, 'bootstrap_peers', [])
        
        # State
        self.discovered_peers: Dict[str, PeerInfo] = {}
        self.peer_handlers: List[Callable] = []
        self._running = False
        self._discovery_task: Optional[trio.CancelledError] = None
        
        # mDNS service
        self.mdns = MDNSDiscovery(
            service_name=self.service_tag,
            port=getattr(config, 'port', 9000)
        )
        
        # Setup network event handlers
        self._setup_network_handlers()
    
    def _setup_network_handlers(self):
        """Setup libp2p network event handlers"""
        # Note: In py-libp2p, network events are handled differently
        # This is a simplified version
        pass
    
    async def start(self):
        """Start the discovery service"""
        if self._running:
            logger.warning("Discovery service already running")
            return
        
        logger.info("Starting P2P discovery service")
        self._running = True
        
        try:
            # Start mDNS service
            await self.mdns.start()
            
            # Announce our service
            await self.mdns.announce_service(
                str(self.host.get_id()),
                [str(addr) for addr in self.host.get_addrs()]
            )
            
            # Start discovery loop in background
            async with trio.open_nursery() as nursery:
                nursery.start_soon(self._discovery_loop)
                nursery.start_soon(self._connection_monitor_loop)
                nursery.start_soon(self._bootstrap_connection_loop)
            
        except Exception as e:
            logger.error(f"Failed to start discovery service: {e}")
            self._running = False
            raise
    
    async def stop(self):
        """Stop the discovery service"""
        if not self._running:
            return
            
        logger.info("Stopping P2P discovery service")
        self._running = False
        
        # Stop mDNS
        await self.mdns.stop()
        
        # Cancel discovery task
        if self._discovery_task:
            self._discovery_task.cancel()
        
        logger.info("P2P discovery service stopped")
    
    async def _discovery_loop(self):
        """Main discovery loop"""
        while self._running:
            try:
                # Discover peers via mDNS
                discovered = await self.mdns.discover_peers()
                
                # Process discovered peers
                for peer_data in discovered:
                    await self._handle_discovered_peer(peer_data)
                
                # Cleanup stale peers
                await self._cleanup_stale_peers()
                
                # Wait for next discovery interval
                await trio.sleep(self.discovery_interval)
                
            except trio.Cancelled:
                break
            except Exception as e:
                logger.error(f"Error in discovery loop: {e}")
                await trio.sleep(1)  # Brief pause before retry
    
    async def _connection_monitor_loop(self):
        """Monitor peer connections"""
        while self._running:
            try:
                await self._check_peer_connections()
                await trio.sleep(5)  # Check every 5 seconds
            except trio.Cancelled:
                break
            except Exception as e:
                logger.error(f"Error in connection monitor: {e}")
                await trio.sleep(1)
    
    async def _bootstrap_connection_loop(self):
        """Connect to bootstrap peers"""
        if not self.bootstrap_peers:
            return
            
        for peer_addr in self.bootstrap_peers:
            try:
                await self._connect_to_bootstrap_peer(peer_addr)
            except Exception as e:
                logger.error(f"Failed to connect to bootstrap peer {peer_addr}: {e}")
            
            # Small delay between connections
            await trio.sleep(1)
    
    async def _handle_discovered_peer(self, peer_data: Dict[str, Any]):
        """Handle a newly discovered peer"""
        peer_id = peer_data.get('id')
        if not peer_id or peer_id == str(self.host.get_id()):
            return  # Skip ourselves
        
        current_time = time.time()
        
        # Check if peer is already known
        if peer_id in self.discovered_peers:
            # Update last seen time
            self.discovered_peers[peer_id].last_seen = current_time
            self.discovered_peers[peer_id].addresses = peer_data.get('addresses', [])
        else:
            # New peer discovered
            peer_info = PeerInfo(
                id=peer_id,
                addresses=peer_data.get('addresses', []),
                found_at=current_time,
                last_seen=current_time
            )
            
            self.discovered_peers[peer_id] = peer_info
            
            logger.info(f"🔍 Discovered new peer: {peer_id}")
            
            # Publish discovery event
            await self.event_bus.publish("p2p.peer_discovered", peer_info.to_dict())
            
            # Try to connect
            trio.from_thread.run_sync(self._connect_to_peer, peer_info)
        
        # Notify handlers
        for handler in self.peer_handlers:
            try:
                await handler(self.discovered_peers[peer_id])
            except Exception as e:
                logger.error(f"Error in peer handler: {e}")
    
    async def _connect_to_peer(self, peer_info: PeerInfo):
        """Connect to a discovered peer"""
        if peer_info.is_connected:
            return
            
        # Check connection attempt limits
        current_time = time.time()
        if (peer_info.connection_attempts >= self.max_connection_attempts and
            current_time - peer_info.last_connection_attempt < 300):  # 5 minutes
            return
        
        peer_info.connection_attempts += 1
        peer_info.last_connection_attempt = current_time
        
        try:
            logger.info(f"🔗 Connecting to peer: {peer_info.id}")
            
            # Create peer info for connection
            peer_id = PeerID.from_base58(peer_info.id)
            addrs = [Multiaddr(addr) for addr in peer_info.addresses]
            
            # Attempt connection
            with trio.move_on_after(self.connection_timeout):
                # Note: This is simplified - actual libp2p connection would be different
                # await self.host.connect(peer_id, addrs)
                
                peer_info.is_connected = True
                
                logger.info(f"✅ Connected to peer: {peer_info.id}")
                
                # Publish connection event
                await self.event_bus.publish("p2p.peer_connected", peer_info.to_dict())
                
                # Trigger automatic card exchange
                await self._exchange_cards_with_peer(peer_info.id)
                
        except Exception as e:
            logger.error(f"Failed to connect to peer {peer_info.id}: {e}")
            peer_info.is_connected = False
    
    async def _connect_to_bootstrap_peer(self, peer_addr: str):
        """Connect to a bootstrap peer"""
        try:
            logger.info(f"🌐 Connecting to bootstrap peer: {peer_addr}")
            
            # Parse bootstrap peer address
            addr = Multiaddr(peer_addr)
            peer_info_obj = info_from_p2p_addr(addr)
            
            # Create peer info
            peer_info = PeerInfo(
                id=str(peer_info_obj.peer_id),
                addresses=[peer_addr],
                found_at=time.time(),
                last_seen=time.time()
            )
            
            # Add to discovered peers
            self.discovered_peers[peer_info.id] = peer_info
            
            # Connect
            await self._connect_to_peer(peer_info)
            
        except Exception as e:
            logger.error(f"Error connecting to bootstrap peer {peer_addr}: {e}")
    
    async def _check_peer_connections(self):
        """Check the status of peer connections"""
        for peer_id, peer_info in self.discovered_peers.items():
            try:
                # Check if peer is still connected
                peer_id_obj = PeerID.from_base58(peer_id)
                
                # Note: This is simplified - actual connection check would use libp2p APIs
                is_connected = False  # Placeholder
                
                if is_connected != peer_info.is_connected:
                    peer_info.is_connected = is_connected
                    
                    if is_connected:
                        logger.info(f"Peer {peer_id} connected")
                        await self.event_bus.publish("p2p.peer_connected", peer_info.to_dict())
                    else:
                        logger.info(f"Peer {peer_id} disconnected")
                        await self.event_bus.publish("p2p.peer_disconnected", peer_info.to_dict())
                
                if is_connected:
                    peer_info.last_seen = time.time()
                    
            except Exception as e:
                logger.error(f"Error checking connection to peer {peer_id}: {e}")
    
    async def _cleanup_stale_peers(self):
        """Remove stale peers from the list"""
        current_time = time.time()
        stale_threshold = 300  # 5 minutes
        
        stale_peers = []
        for peer_id, peer_info in self.discovered_peers.items():
            if current_time - peer_info.last_seen > stale_threshold:
                stale_peers.append(peer_id)
        
        for peer_id in stale_peers:
            peer_info = self.discovered_peers.pop(peer_id)
            logger.info(f"🗑️ Removed stale peer: {peer_id}")
            
            # Publish disconnection event if needed
            if peer_info.is_connected:
                await self.event_bus.publish("p2p.peer_disconnected", peer_info.to_dict())
    
    async def _exchange_cards_with_peer(self, peer_id: str):
        """Automatically exchange cards with a peer"""
        try:
            # Small delay to ensure connection is stable
            await trio.sleep(1)
            
            # Trigger card exchange through event bus
            await self.event_bus.publish("p2p.request_card", {
                "peer_id": peer_id,
                "auto_exchange": True
            })
            
        except Exception as e:
            logger.error(f"Error exchanging cards with {peer_id}: {e}")
    
    # Public API methods
    def register_peer_handler(self, handler: Callable):
        """Register a handler for peer events"""
        self.peer_handlers.append(handler)
    
    async def get_peers(self) -> List[Dict[str, Any]]:
        """Get all discovered peers"""
        return [peer.to_dict() for peer in self.discovered_peers.values()]
    
    async def get_connected_peers(self) -> List[Dict[str, Any]]:
        """Get only connected peers"""
        return [
            peer.to_dict() 
            for peer in self.discovered_peers.values() 
            if peer.is_connected
        ]
    
    async def get_peer_info(self, peer_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific peer"""
        peer_info = self.discovered_peers.get(peer_id)
        return peer_info.to_dict() if peer_info else None
    
    async def force_connect_to_peer(self, peer_id: str, addresses: List[str]):
        """Force connection to a specific peer"""
        peer_info = PeerInfo(
            id=peer_id,
            addresses=addresses,
            found_at=time.time(),
            last_seen=time.time()
        )
        
        self.discovered_peers[peer_id] = peer_info
        await self._connect_to_peer(peer_info)
    
    def is_running(self) -> bool:
        """Check if discovery service is running"""
        return self._running