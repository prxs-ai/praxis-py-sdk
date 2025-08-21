# HyperLiquid API Manager (Async)

An asynchronous Python client for querying liquidity data from the [Hyperliquid](https://hyperliquid.xyz) API. Built using `aiohttp` and `pandas`, with integration support for FastAPI.

## Installation

### Poetry

```toml
[tool.poetry.dependencies]
python = "^3.11"
aiohttp = ">=3.11.14,<4.0.0"
fastapi = ">=0.115.8,<0.116.0"
pandas = ">=2.2.0,<3.0.0"
```

### Or pip

```bash
pip install aiohttp fastapi pandas
```

## Configuration

Expects a configuration loader in:

```python
from hyperliquid_client.config import get_server_settings

server = get_server_settings()
```

Example structure:

```python
class HyperliquidConfig:
    base_url = "https://api.hyperliquid.xyz"

class ServerSettings:
    hyperliquid = HyperliquidConfig()

def get_server_settings():
    return ServerSettings()
```

## Usage

```python
import asyncio
from aiohttp import ClientSession
from hyperliquid_client.manager import HyperLiquidManager

async def main():
    async with ClientSession() as session:
        manager = HyperLiquidManager(
            base_url="https://api.hyperliquid.xyz", session=session
        )
        df = await manager.get_pool_liquidity("ETH")
        print(df)

asyncio.run(main())
```

### Method: `get_pool_liquidity`

Fetches liquidity data for the given coin. Returns a summary of bids, asks, and total liquidity.

```python
await manager.get_pool_liquidity("ETH")
```

Returns: `pandas.DataFrame` with columns:

* `type` – either `bids`, `asks`, or `sum_liquidity`
* `sz` – total size (float)

## Integration with FastAPI

```python
@app.get("/liquidity/{coin}")
async def liquidity(coin: str, manager = Depends(get_hyperliquid_manager)):
    return await manager.get_pool_liquidity(coin)
```

## License

MIT License
