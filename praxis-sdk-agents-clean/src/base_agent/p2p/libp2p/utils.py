from pathlib import Path
from libp2p.crypto.keys import KeyPair, PrivateKey
from libp2p.crypto.ed25519 import create_new_key_pair, Ed25519PrivateKey
from loguru import logger
from base64 import b64decode
import os


def load_or_create_node_key(seed_path: str) -> KeyPair:
    path = Path(seed_path)
    if path.exists():
        logger.info(f"Using the existing seed from: {seed_path}")
        seed = path.read_bytes()
    else:
        logger.info(f"Creating random seed: {seed_path}")
        seed = os.urandom(32)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(seed)

    return create_new_key_pair(seed)


def decode_noise_key(key: str) -> PrivateKey:
    return Ed25519PrivateKey.from_bytes(b64decode(key))
