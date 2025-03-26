import asyncio
import aiohttp
import time
from collections import defaultdict
from typing import Any, Dict


class DexScreenerAPI:
    BASE_URL = "https://api.dexscreener.com/"

    # Limit the number of requests to the API
    RATE_LIMITS = {
        "GET /token-profiles/latest/v1": (60, 60),  # 60  requests per minute
        "GET /latest/dex/pairs": (300, 60),  # 300 requests per minute
    }

    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.request_timestamps = defaultdict(list)

    async def _check_rate_limit(self, endpoint: str):
        """Check if we can send a request to this endpoint.
        If the rate limit is exceeded, sleep for a while.

        param endpoint: The endpoint to check the rate limit for"""
        if endpoint not in self.RATE_LIMITS:
            return  # Если лимит не задан, проверку не делаем

        max_requests, time_window = self.RATE_LIMITS[endpoint]
        now = time.time()

        # Delete old timestamps
        self.request_timestamps[endpoint] = [
            t for t in self.request_timestamps[endpoint] if now - t < time_window
        ]

        if len(self.request_timestamps[endpoint]) >= max_requests:
            sleep_time = time_window - (now - self.request_timestamps[endpoint][0])
            print(f"Rate limit exceeded for {endpoint}. Sleeping for {sleep_time:.2f} seconds...")
            await asyncio.sleep(sleep_time)

        self.request_timestamps[endpoint].append(time.time())

    async def _request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """ Make a request to the API.

            param endpoint: The endpoint to request
            param params: Optional query parameters"""
        await self._check_rate_limit(endpoint)

        async with self.session.get(f"{self.BASE_URL}{endpoint}", params=params) as response:
            if response.status != 200:
                raise Exception(f"Error {response.status}: {await response.text()}")
            return await response.json()

    async def get_latest_token_profiles(self, ) -> Dict[str, Any]:
        """
        Get the latest token profiles (rate-limit 60 requests per minute)
        """
        return await self._request(f"/token-profiles/latest/v1")

    async def get_pairs_data_by_pool_address(self, chain: str, pair_address: str):
        """
        Get one or multiple pairs by chain and pair address (rate-limit 300 requests per minute)

        param chain: The chain to get the pairs from(solana,ether)
        param pair_address: The address of the pair(6xzcGi7rMd12UPD5PJSMnkTgquBZFYhhMz9D5iHgzB1w)
        """
        return await self._request(f"/latest/dex/pairs/{chain}/{pair_address}")

    async def get_token_data_by_address(self, chain: str, token_address: str):
        """
        Get one or multiple pairs by token address (rate-limit 300 requests per minute)
        param chain: The chain to get the pairs from(solana,ether)
        param token_address: The address of the token(6xzcGi7rMd12UPD5PJSMnkTgquBZFYhhMz9D5iHgzB1w)
        """
        return await self._request(f"/tokens/v1/{chain}/{token_address}")

    async def close(self):
        """
        Close the aiohttp session.
        """
        await self.session.close()

