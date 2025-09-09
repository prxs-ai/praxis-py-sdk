"""
P2P Security Manager for Praxis SDK

This module handles security-related operations for P2P communication:
- Ed25519 key management
- Noise protocol configuration
- Key generation and storage
"""

import os
import logging
from pathlib import Path
from base64 import b64decode
from typing import Optional

from libp2p.crypto.ed25519 import Ed25519PrivateKey, create_new_key_pair
from libp2p.crypto.keys import KeyPair

logger = logging.getLogger(__name__)


class P2PSecurityManager:
    """
    Manages security aspects of P2P communication.
    
    Features:
    - Ed25519 keypair generation and loading
    - Secure key storage
    - Noise protocol key handling
    """
    
    def __init__(self, config):
        self.config = config
        self.keystore_path = Path(config.keystore_path)
        self.keystore_path.mkdir(parents=True, exist_ok=True)
    
    def load_or_create_keypair(self, key_filename: str = "node.key") -> KeyPair:
        """Load existing keypair or create a new one"""
        key_path = self.keystore_path / key_filename
        
        if key_path.exists():
            logger.info(f"Loading existing keypair from: {key_path}")
            seed = key_path.read_bytes()
        else:
            logger.info(f"Creating new keypair: {key_path}")
            seed = os.urandom(32)
            key_path.write_bytes(seed)
        
        return create_new_key_pair(seed)
    
    def decode_noise_key(self, key: str) -> Ed25519PrivateKey:
        """Decode a base64-encoded Noise private key"""
        return Ed25519PrivateKey.from_bytes(b64decode(key))
    
    def get_noise_key(self) -> Optional[Ed25519PrivateKey]:
        """Get the Noise private key if configured"""
        if self.config.noise_key:
            return self.decode_noise_key(self.config.noise_key)
        return None