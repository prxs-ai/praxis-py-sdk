#!/bin/bash
# Check if all libp2p dependencies are available

echo "Checking libp2p dependencies..."

python3 -c "
import sys
deps = [
    'multiaddr',
    'trio',
    'trio_typing',
    'base58',
    'coincurve',
    'grpcio',
    'lru',
    'noiseprotocol',
    'protobuf',
    'Crypto',
    'multihash',
    'nacl',
    'rpcudp'
]

missing = []
for dep in deps:
    try:
        __import__(dep)
        print(f'✓ {dep}')
    except ImportError:
        print(f'✗ {dep}')
        missing.append(dep)

if missing:
    print(f'\\nMissing dependencies: {missing}')
    sys.exit(1)
else:
    print('\\nAll dependencies installed!')
"
