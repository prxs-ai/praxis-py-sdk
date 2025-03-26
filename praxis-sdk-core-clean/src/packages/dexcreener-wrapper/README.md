# DexScreener API Wrapper

This package is an asynchronous wrapper for the DexScreener API. It simplifies interaction with the API, automatically manages rate limits, and provides a convenient interface for retrieving data.

## Technologies Used
- **aiohttp** – for asynchronous HTTP requests

## Implemented Endpoints
Describe all available endpoints and their functionalities here.

### Available Methods:
- `/token-profiles/latest/v1` – Get the latest token profiles (rate-limit 60 requests per minute)
 
Response Example:
```json
[
    {
        "url": "https://dexscreener.com/bsc/0x795d2710e383f33fbebe980a155b29757b6703f3",
        "chainId": "bsc",
        "tokenAddress": "0x795d2710e383f33fbebe980a155b29757b6703f3",
        "icon": "https://dd.dexscreener.com/ds-data/tokens/bsc/0x795d2710e383f33fbebe980a155b29757b6703f3.png",
        "openGraph": "https://cdn.dexscreener.com/token-images/og/bsc/0x795d2710e383f33fbebe980a155b29757b6703f3?timestamp=1742991900000",
        "description": "CZ in studio ghibli style",
        "links": [
            {
                "type": "twitter",
                "url": "https://x.com/esatoshiclub/status/1904862456469438881"
            }
        ]
    },
    {
        "url": "https://dexscreener.com/solana/enk9rdxulw4ysaa4zyzhkpr9pbjpgy7q416sfjgxdlfx",
        "chainId": "solana",
        "tokenAddress": "ENK9rDXuLW4YsaA4ZyzHkPR9pBJpgY7Q416SfjGxDLfx",
        "icon": "https://dd.dexscreener.com/ds-data/tokens/solana/ENK9rDXuLW4YsaA4ZyzHkPR9pBJpgY7Q416SfjGxDLfx.png",
        "header": "https://dd.dexscreener.com/ds-data/tokens/solana/ENK9rDXuLW4YsaA4ZyzHkPR9pBJpgY7Q416SfjGxDLfx/header.png",
        "openGraph": "https://cdn.dexscreener.com/token-images/og/solana/ENK9rDXuLW4YsaA4ZyzHkPR9pBJpgY7Q416SfjGxDLfx?timestamp=1742991900000",
        "description": "Quick Solana is an automated rewards token. $QS features a fully automatic reward system that distributes $SOL to holders every 1 minute, with no manual claiming required. 10% tax: 5% to holders, 3% buyback and burn, 2% marketing.",
        "links": [
            {
                "type": "twitter",
                "url": "https://x.com/QuickSolRewards"
            },
            {
                "type": "telegram",
                "url": "https://t.me/QuickSolanaRewards"
            }
        ]
    },
    {
        "url": "https://dexscreener.com/solana/fefkv9xupuhfjtr1gxsqhwxo6etghregqpjtanr4pump",
        "chainId": "solana",
        "tokenAddress": "FeFKV9XUpUHFJTR1gXsQHWxo6eTghREGQpJtanr4pump",
        "icon": "https://dd.dexscreener.com/ds-data/tokens/solana/FeFKV9XUpUHFJTR1gXsQHWxo6eTghREGQpJtanr4pump.png",
        "header": "https://dd.dexscreener.com/ds-data/tokens/solana/FeFKV9XUpUHFJTR1gXsQHWxo6eTghREGQpJtanr4pump/header.png",
        "openGraph": "https://cdn.dexscreener.com/token-images/og/solana/FeFKV9XUpUHFJTR1gXsQHWxo6eTghREGQpJtanr4pump?timestamp=1742991900000",
        "description": "Dogshit",
        "links": [
            {
                "label": "Website",
                "url": "https://pump.fun/coin/FeFKV9XUpUHFJTR1gXsQHWxo6eTghREGQpJtanr4pump"
            },
            {
                "type": "twitter",
                "url": "https://x.com/bull_bnb/status/1904866040313782403#ref=ab83807e-dd51-4245-87c2-51df75b4af80"
            },
            {
                "type": "telegram",
                "url": "https://t.me/DogshitCTOO"
            }
        ]
    }]
```
- `/latest/dex/pairs/{chainId}/{pairId}` – Get one or multiple pairs by chain and pair address (rate-limit 300 requests per minute)

Response Example:
```json
[
    {
        "chainId": "solana",
        "dexId": "raydium",
        "url": "https://dexscreener.com/solana/b7ycuyt8svwb6wfxcborcfqwqkdyh1mzsdusmjgfky3x",
        "pairAddress": "B7ycuYT8sVwb6wfxcBorCfqwQKDYH1MzsdUsMjgfky3x",
        "labels": [
            "CLMM"
        ],
        "baseToken": {
            "address": "6xzcGi7rMd12UPD5PJSMnkTgquBZFYhhMz9D5iHgzB1w",
            "name": "BETH SMITH",
            "symbol": "$MILF"
        },
        "quoteToken": {
            "address": "So11111111111111111111111111111111111111112",
            "name": "Wrapped SOL",
            "symbol": "SOL"
        },
        "priceNative": "0.000001020",
        "priceUsd": "0.0001470",
        "txns": {
            "m5": {
                "buys": 2,
                "sells": 2
            },
            "h1": {
                "buys": 28,
                "sells": 13
            },
            "h6": {
                "buys": 28,
                "sells": 13
            },
            "h24": {
                "buys": 28,
                "sells": 13
            }
        },
        "volume": {
            "h24": 3519.31,
            "h6": 3519.31,
            "h1": 3519.31,
            "m5": 1123.46
        },
        "priceChange": {
            "m5": 20.13,
            "h1": 104,
            "h6": 104,
            "h24": 104
        },
        "liquidity": {
            "usd": 20581.61,
            "base": 69995927,
            "quote": 71.4352
        },
        "fdv": 147018,
        "marketCap": 147018,
        "pairCreatedAt": 1742991620000
    }
]
```

- `/tokens/v1/{chainId}/{tokenAddresses}` - Get one or multiple pairs by token address (rate-limit 300 requests per minute)

Response Example: Response like `/latest/dex/pairs/{chainId}/{pairId}`

## Official Documentation:
For more information on the DexScreener API, visit the official documentation [here](https://docs.dexscreener.com/).
