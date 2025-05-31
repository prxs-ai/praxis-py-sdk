# RugCheck API Wrapper

This package is an asynchronous wrapper for the RugCheck API. 
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
    "mint": "5fGA1os23NNWzhGYLhrWAEnwKDgUX2RSUNmgJACcY5hb",
    "tokenProgram": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "creator": "ufVXqJjGLi3VQzVWgjvMaKd4XdoibPz77eAieMYrp8t",
    "token": {
        "mintAuthority": null,
        "supply": 13520753934085,
        "decimals": 6,
        "isInitialized": true,
        "freezeAuthority": null
    },
    "token_extensions": null,
    "tokenMeta": {
        "name": "Barron Trump",
        "symbol": "Barron",
        "uri": "https://gateway.pinata.cloud/ipfs/Qmc58aQcqwSJ24jFu1zsvK8KFLJkpoJnMZ3xbgR1Etranf",
        "mutable": true,
        "updateAuthority": "ufVXqJjGLi3VQzVWgjvMaKd4XdoibPz77eAieMYrp8t"
    },
    "topHolders": [
        {
            "address": "E5whYx5pYAyRoFzxxtV2noNbedYRNu59nfygGaiTjd8F",
            "amount": 4849524447778,
            "decimals": 6,
            "pct": 35.86726355216511,
            "uiAmount": 4849524.447778,
            "uiAmountString": "4849524.447778",
            "owner": "8V8ZpWxnW57JyuXJuanH1bbYpgdHnbUheJQrLVwKToyj",
            "insider": false
        },
        {
            "address": "7i1EV9ewssCuU1rmWX6AgWWxyz9npKjEbZE2pL4K2L1A",
            "amount": 4497486981933,
            "decimals": 6,
            "pct": 33.26358133472948,
            "uiAmount": 4497486.981933,
            "uiAmountString": "4497486.981933",
            "owner": "GSx4ss7pM8icUS5tP9qqfgEaRtFpihmdiHeEJjgiWhnJ",
            "insider": false
        },
        {
            "address": "BWV3dp9xAfGr4kqUADub7s1mhTjtEaohXuzyhtx1M3H2",
            "amount": 3922428113279,
            "decimals": 6,
            "pct": 29.010424510358085,
            "uiAmount": 3922428.113279,
            "uiAmountString": "3922428.113279",
            "owner": "GAG6DiQku69WAVnfZSTt6gJU7ECzqR2py8kDJjggf3VP",
            "insider": false
        },
        {
            "address": "DHo2Qor4VsWseWGaYn9YC7KepgnrTWtVqcULfQgshC77",
            "amount": 201410995412,
            "decimals": 6,
            "pct": 1.489643228431627,
            "uiAmount": 201410.995412,
            "uiAmountString": "201410.995412",
            "owner": "8V7pTNEcNDRHEsm5iE5XNDfH4BqanyUM4vVY2WTY2LNY",
            "insider": false
        },
        {
            "address": "FtX7NFK4d7t2ihwer3vV1dYdH6wPAkDkFnnBVQVRhQLS",
            "amount": 49903395683,
            "decimals": 6,
            "pct": 0.36908737431569233,
            "uiAmount": 49903.395683,
            "uiAmountString": "49903.395683",
            "owner": "FiENyoReioEcghLhLvdNrnGCYjyburgpv9mSZeifjkCV",
            "insider": false
        }
    ],
    "freezeAuthority": null,
    "mintAuthority": null,
    "risks": [
        {
            "name": "Creator history of rugged tokens",
            "value": "",
            "description": "Creator has a history of rugging tokens.",
            "score": 26400,
            "level": "danger"
        },
        {
            "name": "Large Amount of LP Unlocked",
            "value": "100.00%",
            "description": "A large amount of LP tokens are unlocked, allowing the owner to remove liquidity at any point.",
            "score": 11000,
            "level": "danger"
        },
        {
            "name": "Top 10 holders high ownership",
            "value": "",
            "description": "The top 10 users hold more than 70% token supply",
            "score": 10063,
            "level": "danger"
        },
        {
            "name": "Single holder ownership",
            "value": "29.01%",
            "description": "One user holds a large amount of the token supply",
            "score": 9814,
            "level": "warn"
        },
        {
            "name": "Single holder ownership",
            "value": "33.26%",
            "description": "One user holds a large amount of the token supply",
            "score": 6913,
            "level": "warn"
        },
        {
            "name": "Single holder ownership",
            "value": "35.87%",
            "description": "One user holds a large amount of the token supply",
            "score": 3586,
            "level": "warn"
        },
        {
            "name": "Low Liquidity",
            "value": "$1.00",
            "description": "Low amount of liquidity in the token pool",
            "score": 2999,
            "level": "danger"
        },
        {
            "name": "High ownership",
            "value": "",
            "description": "The top users hold more than 80% token supply",
            "score": 1496,
            "level": "danger"
        },
        {
            "name": "Low amount of LP Providers",
            "value": "",
            "description": "Only a few users are providing liquidity",
            "score": 500,
            "level": "warn"
        },
        {
            "name": "Mutable metadata",
            "value": "",
            "description": "Token metadata can be changed by the owner",
            "score": 100,
            "level": "warn"
        }
    ],
    "score": 72872,
    "score_normalised": 75,
    "fileMeta": {
        "description": "",
        "name": "Barron Trump",
        "symbol": "Barron",
        "image": "https://dd.dexscreener.com/ds-data/tokens/solana/6Ee2R6XhB1VDsJjPKcE4RL3BbewgC1SHjeosxAjDV81h.png?size=lg&key=d54bd4"
    },
    "lockerOwners": {},
    "lockers": {},
    "markets": [
        {
            "pubkey": "FiENyoReioEcghLhLvdNrnGCYjyburgpv9mSZeifjkCV",
            "marketType": "raydium_clmm",
            "mintA": "So11111111111111111111111111111111111111112",
            "mintB": "5fGA1os23NNWzhGYLhrWAEnwKDgUX2RSUNmgJACcY5hb",
            "mintLP": "11111111111111111111111111111111",
            "liquidityA": "9dsn84BfL8mXM29LoLLf6s2yeZwsDMSC3wKDHiW1wy5F",
            "liquidityB": "FtX7NFK4d7t2ihwer3vV1dYdH6wPAkDkFnnBVQVRhQLS",
            "mintAAccount": {
                "mintAuthority": null,
                "supply": 0,
                "decimals": 9,
                "isInitialized": true,
                "freezeAuthority": null
            },
            "mintBAccount": {
                "mintAuthority": null,
                "supply": 13520753934085,
                "decimals": 6,
                "isInitialized": true,
                "freezeAuthority": null
            },
            "mintLPAccount": {
                "mintAuthority": null,
                "supply": 100,
                "decimals": 0,
                "isInitialized": false,
                "freezeAuthority": null
            },
            "liquidityAAccount": {
                "mint": "So11111111111111111111111111111111111111112",
                "owner": "FiENyoReioEcghLhLvdNrnGCYjyburgpv9mSZeifjkCV",
                "amount": 4100394,
                "delegate": null,
                "state": 1,
                "delegatedAmount": 0,
                "closeAuthority": null
            },
            "liquidityBAccount": {
                "mint": "5fGA1os23NNWzhGYLhrWAEnwKDgUX2RSUNmgJACcY5hb",
                "owner": "FiENyoReioEcghLhLvdNrnGCYjyburgpv9mSZeifjkCV",
                "amount": 49903395683,
                "delegate": null,
                "state": 1,
                "delegatedAmount": 0,
                "closeAuthority": null
            },
            "lp": {
                "baseMint": "So11111111111111111111111111111111111111112",
                "quoteMint": "5fGA1os23NNWzhGYLhrWAEnwKDgUX2RSUNmgJACcY5hb",
                "lpMint": "11111111111111111111111111111111",
                "quotePrice": 8.571516710429699e-06,
                "basePrice": 138.76154695832258,
                "base": 0.004100394,
                "quote": 49903.395683,
                "reserveSupply": 0,
                "currentSupply": 100,
                "quoteUSD": 0.4277477900040198,
                "baseUSD": 0.5689770145786242,
                "pctReserve": 200,
                "pctSupply": 100,
                "holders": null,
                "totalTokensUnlocked": 100,
                "tokenSupply": 100,
                "lpLocked": 0,
                "lpUnlocked": 100,
                "lpLockedPct": 0,
                "lpLockedUSD": 0,
                "lpMaxSupply": 0,
                "lpCurrentSupply": 0,
                "lpTotalSupply": 100
            }
        }
    ],
    "totalMarketLiquidity": 0.996724804582644,
    "totalLPProviders": 0,
    "totalHolders": 1,
    "price": 8.571516710429699e-06,
    "rugged": false,
    "tokenType": "",
    "transferFee": {
        "pct": 0,
        "maxAmount": 0,
        "authority": "11111111111111111111111111111111"
    },
    "knownAccounts": {
        "FiENyoReioEcghLhLvdNrnGCYjyburgpv9mSZeifjkCV": {
            "name": "Raydium CLMM Pool",
            "type": "AMM"
        },
        "ufVXqJjGLi3VQzVWgjvMaKd4XdoibPz77eAieMYrp8t": {
            "name": "Creator",
            "type": "CREATOR"
        }
    },
    "events": [],
    "verification": null,
    "graphInsidersDetected": 100,
    "insiderNetworks": [
        {
            "id": "tall-green-seahorse",
            "size": 100,
            "type": "transfer",
            "tokenAmount": 940500000000000,
            "activeAccounts": 100
        }
    ],
    "detectedAt": "2025-03-20T14:48:00.32795024Z",
    "creatorTokens": [
        {
            "mint": "93dRzaqi5L51BxRQqbnCMa4W5TogkeV48rHpbs9eFFJg",
            "marketCap": 9.407392599046561,
            "createdAt": "2025-03-20T14:58:25.983218879Z"
        },
        {
            "mint": "AmimCuSZy6SzLZhbvYZcZvdGuKTqBjQWp7NCWzGfQYE7",
            "marketCap": 6.533223237938587,
            "createdAt": "2025-03-20T13:57:29.992455236Z"
        },
        {
            "mint": "3KixnRuPsdDKphcuirWdQHsnyjh76Hy36BVZ5hiyp1kP",
            "marketCap": 17.421505537252482,
            "createdAt": "2025-03-20T13:40:01.535393323Z"
        },
        {
            "mint": "XcqnUjebtpzZtRGhdgAtofvZUpNmGwQVoVLTzrxg9no",
            "marketCap": 1.3338106370928045,
            "createdAt": "2025-03-20T12:48:51.567308449Z"
        },
        {
            "mint": "DbZiwRBiNuPhMmjLffSMFVGjHtviXdgSX2sc87BwH8eA",
            "marketCap": 3.126051450775824,
            "createdAt": "2025-03-20T12:22:18.303468801Z"
        },
        {
            "mint": "wWVuaQUkviSeMPHjwBsodyLT1vY3TvuggTrHYBseoYA",
            "marketCap": 6.623501256583866,
            "createdAt": "2025-03-20T12:01:53.208448569Z"
        },
        {
            "mint": "GUzKYbtwcMJCmx9NZ36aKUrHSpnppYrU54iCbtFkbkrU",
            "marketCap": 18.324687132145215,
            "createdAt": "2025-03-20T11:32:00.539845938Z"
        },
        {
            "mint": "Db9qnBi2vKVoAsp9YLkVjccaVLgbu9tgkBqhHt36pump",
            "marketCap": 10.031290860488983,
            "createdAt": "2025-03-20T09:41:15.185015092Z"
        },
        {
            "mint": "583iumREtW7SR1PJcLoXCf1xMcvT9iCfLYL1JcMSqy3i",
            "marketCap": 174.44312479858272,
            "createdAt": "2025-03-20T09:01:16.18279578Z"
        },
        {
            "mint": "5GwH2F8JqfbHvkwFFN5d5C1TFfjd6D678GaufRxKTdxA",
            "marketCap": 193.96375878915356,
            "createdAt": "2025-03-20T08:27:19.217393564Z"
        },
        {
            "mint": "6BRPXSMyc5MCV2XVnNcPDLiiPpu4AMUyNc5b1Aweorzr",
            "marketCap": 29.025227255669442,
            "createdAt": "2025-03-20T07:47:00.770193885Z"
        }
    ]
}


```

## Official Documentation:
For more information on the RugCheck API, visit the official documentation [here](https://api.rugcheck.xyz/swagger/index.html#/).