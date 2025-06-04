from typing import Any

import aiohttp


class RugCheckAPI:
    BASE_URL = "https://api.rugcheck.xyz/v1"

    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def _request(self, endpoint: str) -> dict[str, Any]:
        """Completes a request to the API."""
        async with self.session.get(f"{self.BASE_URL}{endpoint}") as response:
            if response.status != 200:
                raise Exception(f"Error {response.status}: {await response.text()}")
            return await response.json()

    async def get_token_report(self, token_address: str) -> dict[str, Any]:
        """Generate a detailed report for given token mint."""
        endpoint = f"/tokens/{token_address}/report"
        return await self._request(endpoint)

    async def close(self):
        """Closes the session."""
        await self.session.close()
