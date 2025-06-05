import os
import tempfile
from pathlib import Path
from base64 import b64encode

from base_agent.p2p.libp2p.utils import load_or_create_node_key, decode_noise_key
from libp2p.crypto.keys import KeyPair
from libp2p.crypto.ed25519 import Ed25519PrivateKey, create_new_key_pair


class TestP2PUtils:

    def test_load_or_create_node_key_creates_new_key(self):
        # Test with a path that doesn't exist
        with tempfile.TemporaryDirectory() as tmpdirname:
            seed_path = os.path.join(tmpdirname, "non_existent_dir", "seed_file")
            
            # Ensure the file doesn't exist initially
            assert not Path(seed_path).exists()
            
            # Call the function which should create the key
            key_pair = load_or_create_node_key(seed_path)
            
            # Verify file was created
            assert Path(seed_path).exists()
            
            # Verify return type
            assert isinstance(key_pair, KeyPair)
    
    def test_load_or_create_node_key_loads_existing_key(self):
        # Test with a path that exists
        with tempfile.TemporaryDirectory() as tmpdirname:
            seed_path = os.path.join(tmpdirname, "seed_file")
            
            # Create a seed file
            seed = os.urandom(32)
            Path(seed_path).write_bytes(seed)
            
            # Call the function which should load the existing key
            key_pair = load_or_create_node_key(seed_path)
            
            # Verify the key_pair matches what we expect from the seed
            expected_key_pair = create_new_key_pair(seed)
            assert key_pair.private_key.to_bytes() == expected_key_pair.private_key.to_bytes()
            assert key_pair.public_key.to_bytes() == expected_key_pair.public_key.to_bytes()
    
    def test_decode_noise_key(self):
        # Generate a valid Ed25519 key
        key_pair = create_new_key_pair(os.urandom(32))
        private_key_bytes = key_pair.private_key.to_bytes()
        
        # Encode it as we would in the application
        encoded_key = b64encode(private_key_bytes).decode()
        
        # Use our function to decode it
        decoded_key = decode_noise_key(encoded_key)
        
        # Verify type and content
        assert isinstance(decoded_key, Ed25519PrivateKey)
        assert decoded_key.to_bytes() == private_key_bytes