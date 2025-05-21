# DexTools API Wrapper

This package is an asynchronous wrapper for the DexTools API. 
It simplifies interaction with the API, automatically manages rate limits, 
and provides a convenient interface for retrieving data.

## Technologies Used
- **aiohttp** – for asynchronous HTTP requests

## Implemented Endpoints
Describe all available endpoints and their functionalities here.
### Available Methods:
- `/v2/blockchain` - Fetch information about all supported blockchains.
Response Example:
```json
{
    "statusCode": 200,
    "data": {
        "page": 1,
        "pageSize": 5,
        "totalPages": 25,
        "results": [
            {
                "name": "Arbitrumnova",
                "website": "https://arbitrum.io/anytrust",
                "id": "arbitrumnova"
            },
            {
                "name": "Astar",
                "website": "https://astar.network/",
                "id": "astar"
            },
            {
                "name": "Aurora",
                "website": "https://www.aurorachain.io/",
                "id": "aurora"
            },
            {
                "name": "Avalanche",
                "website": "https://www.avax.network/",
                "id": "avalanche"
            },
            {
                "name": "Avax DFK",
                "website": "https://subnets.avax.network/defi-kingdoms",
                "id": "dfk"
            }
        ]
    }
}
```
- `/v2/blockchain/{chain}` - Retrieve information about a specific blockchain.
Response Example:
```json
{
    "statusCode": 200,
    "data": {
        "name": "Solana",
        "website": "https://solana.com/es",
        "id": "solana"
    }
}
```
- `/v2/pool/{chain}/{address}` - Fetch details of a specific liquidity pool on a particular blockchain.
Response Example:
```json
{
    "statusCode": 200,
    "data": {
        "creationTime": "2023-11-14T19:08:19.601Z",
        "exchange": {
            "name": "Raydium",
            "factory": "675kpx9mhtjs2zt1qfr1nyhuzelxfqm9h24wfsut1mp8"
        },
        "address": "8f94e3kYk9ZPuEPT5Zgo9tiVJvwaj8zUzbPFPqt2MKK2",
        "mainToken": {
            "name": "TABOO TOKEN",
            "symbol": "TABOO",
            "address": "kWnW2tpHHabrwPFbE1ZhdVQqdqyEfGE1JW9pVeVo3UL"
        },
        "sideToken": {
            "name": "Wrapped SOL",
            "symbol": "SOL",
            "address": "So11111111111111111111111111111111111111112"
        }
    }
}
```
- `/v2/pool/{chain}` - Obtain information about all liquidity pools on a specified blockchain.
Response Example:
```json
{
    "statusCode": 200,
    "data": {
        "page": 0,
        "pageSize": 20,
        "totalPages": 2,
        "results": [
            {
                "creationTime": "2023-11-14T19:08:19.601Z",
                "exchange": {
                    "name": "Raydium",
                    "factory": "675kpx9mhtjs2zt1qfr1nyhuzelxfqm9h24wfsut1mp8"
                },
                "address": "8f94e3kYk9ZPuEPT5Zgo9tiVJvwaj8zUzbPFPqt2MKK2",
                "mainToken": {
                    "name": "TABOO TOKEN",
                    "symbol": "TABOO",
                    "address": "kWnW2tpHHabrwPFbE1ZhdVQqdqyEfGE1JW9pVeVo3UL"
                },
                "sideToken": {
                    "name": "Wrapped SOL",
                    "symbol": "SOL",
                    "address": "So11111111111111111111111111111111111111112"
                }
            },
            {
                "creationTime": "2023-11-14T19:11:27.141Z",
                "exchange": {
                    "name": "Raydium",
                    "factory": "675kpx9mhtjs2zt1qfr1nyhuzelxfqm9h24wfsut1mp8"
                },
                "address": "5GHc6rLEF6wTMxV25ZSgi4RZyx6tKZ1Wb6t8wr8iZ3SU",
                "mainToken": {
                    "name": "@andikrsd",
                    "symbol": "Andi",
                    "address": "CyhmzxvoNNguB8MSpgM9ro7MTQV4gQS3BzPnjMBLJeXZ"
                },
                "sideToken": {
                    "name": "USD Coin",
                    "symbol": "USDC",
                    "address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
                }
            },
            {
                "creationTime": "2023-11-14T19:16:34.340Z",
                "exchange": {
                    "name": "Raydium",
                    "factory": "675kpx9mhtjs2zt1qfr1nyhuzelxfqm9h24wfsut1mp8"
                },
                "address": "Y2cVKQXQBoyRTjPEWjKK652eJ9o798b8V4L9uG4FYdy",
                "mainToken": {
                    "name": "Pizza Coin",
                    "symbol": "PIZZA",
                    "address": "Hp7JGCQouq8p2ZndxNiM1zbn4UJHoivZwrnX7QaRtc29"
                },
                "sideToken": {
                    "name": "Wrapped SOL",
                    "symbol": "SOL",
                    "address": "So11111111111111111111111111111111111111112"
                }
            },
            {
                "creationTime": "2023-11-14T19:19:52.821Z",
                "exchange": {
                    "name": "Raydium",
                    "factory": "675kpx9mhtjs2zt1qfr1nyhuzelxfqm9h24wfsut1mp8"
                },
                "address": "CEDtdJpkVKkUiMk5UB8DtNSom6MXN8Bg2tLSWK4bHNUj",
                "mainToken": {
                    "name": "LOCK",
                    "symbol": "LOCK",
                    "address": "6j4V33jfFNwiD7ZRfJikWi9gTFtTxK4T99WbhMt2vXUk"
                },
                "sideToken": {
                    "name": "Wrapped SOL",
                    "symbol": "SOL",
                    "address": "So11111111111111111111111111111111111111112"
                }
            },
            {
                "creationTime": "2023-11-14T19:20:58.823Z",
                "exchange": {
                    "name": "Raydium",
                    "factory": "675kpx9mhtjs2zt1qfr1nyhuzelxfqm9h24wfsut1mp8"
                },
                "address": "5wAcePZKVRq14jQA71WnSRrvHjq9EPM2xgAgpYnkboH3",
                "mainToken": {
                    "name": "PikaCoin",
                    "symbol": "PIKA",
                    "address": "J1tVfbupemy2CVCSQsCYChyH7f9Q54x5bWd86EAoGczF"
                },
                "sideToken": {
                    "name": "Wrapped SOL",
                    "symbol": "SOL",
                    "address": "So11111111111111111111111111111111111111112"
                }
            },
            {
                "creationTime": "2023-11-14T19:31:50.317Z",
                "exchange": {
                    "name": "Raydium",
                    "factory": "675kpx9mhtjs2zt1qfr1nyhuzelxfqm9h24wfsut1mp8"
                },
                "address": "BVeRqeYoDxBFhSbc3ZBFRLYdWeJbqDFpFxt6hC3ogT1a",
                "mainToken": {
                    "name": " IQ",
                    "symbol": " IQ",
                    "address": "XKDn7j2WZqVDzZ2US1AQwgmpe6MdhJUdGch7XnT4deF"
                },
                "sideToken": {
                    "name": "Wrapped SOL",
                    "symbol": "SOL",
                    "address": "So11111111111111111111111111111111111111112"
                }
            }
        ]
    }
}

```

## Official Documentation:
For more information on the DexTools API, visit the official documentation [here](https://developer.dextools.io/products/http-api/Documentation).