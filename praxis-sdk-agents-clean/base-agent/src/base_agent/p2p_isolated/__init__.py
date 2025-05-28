"""Isolated P2P module to avoid serialization issues."""

import asyncio
import os
import sys
from typing import Optional

from loguru import logger


class P2PManager:
    """Manager for P2P operations that isolates libp2p imports."""
    
    _instance: Optional['P2PManager'] = None
    _libp2p_node: Optional[object] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _ensure_libp2p_path(self):
        """Ensure libp2p is in the Python path."""
        if "/serve_app/py-libp2p" not in sys.path and "***REMOVED***/agents/base-agent/py-libp2p" not in sys.path:
            if os.path.exists("/serve_app/py-libp2p"):
                sys.path.insert(0, "/serve_app/py-libp2p")
            else:
                sys.path.insert(0, "***REMOVED***/agents/base-agent/py-libp2p")
    
    async def setup(self):
        """Setup libp2p node."""
        if self._libp2p_node is not None:
            logger.warning("libp2p_node already initialized. Skipping setup.")
            return
        
        # Import inside method to avoid issues
        from base_agent.p2p import setup_libp2p
        await setup_libp2p()
        logger.info("P2P setup completed via isolated manager.")
    
    async def shutdown(self):
        """Shutdown libp2p node."""
        # Import inside method to avoid issues
        from base_agent.p2p import shutdown_libp2p
        await shutdown_libp2p()
        logger.info("P2P shutdown completed via isolated manager.")


# Global instance
_p2p_manager = P2PManager()


async def setup_p2p():
    """Setup P2P connections."""
    await _p2p_manager.setup()


async def shutdown_p2p():
    """Shutdown P2P connections."""
    await _p2p_manager.shutdown()
