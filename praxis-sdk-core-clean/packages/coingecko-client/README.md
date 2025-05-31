# CoinGecko API Manager (Async)

An asynchronous Python client for interacting with the CoinGecko API using `aiohttp` and `pandas`. Designed for integration with FastAPI-based projects and supports fetching historical cryptocurrency market data.

## Installation

### Using [Poetry](https://python-poetry.org/)

```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = ">=0.115.8,<0.116.0"
aiohttp = ">=3.11.14,<4.0.0"
pandas = ">=2.2.0,<3.0.0"
```

Then run:

```bash
poetry install
```

### Or using pip

```bash
pip install fastapi aiohttp pandas
```

## Dependencies

* `aiohttp` — for asynchronous HTTP requests
* `pandas` — for working with tabular data
* `fastapi` — for HTTPException (optional)

## Configuration

The module expects a configuration available at:

```python
from infrastructure.configs.config import server
```

Example structure:

```python
class ServerConfig:
    class CoinGecko:
        api_key = "your_api_key"
        base_url = "https://api.coingecko.com/api/v3"
    coingecko = CoinGecko()

server = ServerConfig()
```

## Usage

```python
import asyncio
from aiohttp import ClientSession
from coingecko_client import CoinGeckoApiManager

async def main():
    async with ClientSession() as session:
        manager = CoinGeckoApiManager(
            api_key="your_api_key",
            session=session,
            base_url="https://api.coingecko.com/api/v3"
        )
        df = await manager.get_historical_prices("bitcoin", days=7)
        print(df)

asyncio.run(main())
```

### Method: `get_historical_prices`

Fetches historical price, market cap, and volume data.

```python
await manager.get_historical_prices(token_name="bitcoin", days=7)
```

Returns: `pandas.DataFrame` with the following columns:

* `timestamp` (as datetime)
* `price`
* `market_cap`
* `total_volume`

### Method: `get_tokens`

Fetches the list of all available tokens. Optionally filters by name.

```python
await manager.get_tokens("bitcoin")
```

## Integration with FastAPI

The client is designed to be used as a FastAPI dependency:

```python
@app.get("/prices")
async def prices(manager = Depends(get_coingecko_manager)):
    return await manager.get_historical_prices("bitcoin")
```

## License

MIT License
