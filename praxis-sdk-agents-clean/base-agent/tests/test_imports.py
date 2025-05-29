"""Test basic imports and configuration for libp2p integration."""

import sys
import os

# Add local py-libp2p to path for testing
sys.path.insert(0, '***REMOVED***')


def test_imports():
    """Test that all required imports work."""
    try:
        # Test multiaddr
        from multiaddr import Multiaddr
        addr = Multiaddr("/ip4/127.0.0.1/tcp/4001")
        print(f"✓ Multiaddr import successful: {addr}")
        
        # Test libp2p core
        from libp2p import create_new_key_pair
        from libp2p.host.basic_host import BasicHost
        from libp2p.peer.id import ID
        print("✓ Core libp2p imports successful")
        
        # Test Circuit Relay v2
        from libp2p.relay.circuit_v2.config import RelayConfig
        from libp2p.relay.circuit_v2.protocol import CircuitV2Protocol
        from libp2p.relay.circuit_v2.transport import CircuitV2Transport
        print("✓ Circuit Relay v2 imports successful")
        
        # Test base_agent imports
        from base_agent.config import get_agent_config
        config = get_agent_config()
        print(f"✓ Agent config loaded: {config.agent_name}")
        
        # Test p2p module
        from base_agent.p2p import setup_libp2p, shutdown_libp2p
        print("✓ P2P module imports successful")
        
        print("\n✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        return False


if __name__ == "__main__":
    # Change to project root
    os.chdir('***REMOVED***')
    
    # Add src to path
    sys.path.insert(0, 'src')
    
    # Run test
    success = test_imports()
    sys.exit(0 if success else 1)
