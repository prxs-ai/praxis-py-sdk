from typing import Any

import aiohttp
from aiolimiter import AsyncLimiter


class DextoolsAPIWrapper:
    def __init__(
        self,
        api_key: str,
        plan: str,
        useragent: str = "API-Wrapper/0.3",
        requests_per_second: int = 1,
    ):
        self._headers = None
        self.url = None
        self._api_key = api_key
        self._useragent = useragent
        self.plan = plan
        self._limiter = AsyncLimiter(
            requests_per_second, 1
        )  # Limit requests per second

        self.set_plan(plan)
        self._session = aiohttp.ClientSession()

    def set_plan(self, plan):
        """The method sets the plan for the API.
        param plan: str.
        """
        plan = plan.lower()
        plans = ["free", "trial", "standard", "advanced", "pro"]
        if plan in plans:
            self.plan = plan
            self.url = f"https://public-api.dextools.io/{plan}/v2"
        elif plan == "partner":
            self.plan = plan
            self.url = "https://api.dextools.io/v2"
        else:
            raise ValueError("Plan not found")

        self._headers = {
            "X-API-Key": self._api_key,
            "Accept": "application/json",
            "User-Agent": self._useragent,
        }
        print(f"Plan URL: {self.url}")
        print(f"Set up plan: {plan}")

    async def __aenter__(self):
        """The method is called when entering the context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """The method is called when exiting the context manager."""
        await self.close()

    async def close(self):
        """The method closes the session."""
        await self._session.close()

    async def _request(self, endpoint: str, params: dict[str, Any] | None = None):
        """The method sends a request to the API.
        param endpoint: str
        param params: Optional[Dict[str, Any]].
        """
        async with self._limiter:  # Limit requests
            url = f"{self.url}{endpoint}"
            async with self._session.get(
                url, headers=self._headers, params=params
            ) as response:
                if response.status == 403:
                    response.raise_for_status()
                    raise Exception(
                        "Access denied (403). Check your API key or request limits."
                    )
                response.raise_for_status()
                return await response.json()

    async def get_blockchain(self, chain: str):
        """Retrieve information about a specific blockchain.
        param chain: str.
        """
        return await self._request(f"/blockchain/{chain}")

    async def get_blockchains(self, order="asc", sort="name", page=None, pageSize=None):
        """Fetch information about all supported blockchains.

        param order: str
        param sort: str
        param page: Optional[int]
        param pageSize: Optional[int]
        """
        return await self._request(
            "/blockchain",
            params={"order": order, "sort": sort, "page": page, "pageSize": pageSize},
        )

    async def get_pool_by_address(self, chain: str, address: str):
        return await self._request(f"/pool/{chain}/{address}")

    async def get_pools(
        self,
        chain,
        from_,
        to,
        order="asc",
        sort="creationTime",
        page=None,
        pageSize=None,
    ):
        """{'creationTime': '2023-11-14T19:08:19.601Z',
        'exchange': {'
                    name': 'Raydium',
                    'factory': '675kpx9mhtjs2zt1qfr1nyhuzelxfqm9h24wfsut1mp8'
                    },
        'address': '8f94e3kYk9ZPuEPT5Zgo9tiVJvwaj8zUzbPFPqt2MKK2',
        'mainToken': {
                'name': 'TABOO TOKEN',
                'symbol': 'TABOO',
                'address': 'kWnW2tpHHabrwPFbE1ZhdVQqdqyEfGE1JW9pVeVo3UL'
        },
        'sideToken': {
                'name': 'Wrapped SOL',
                'symbol': 'SOL',
                'address': 'So11111111111111111111111111111111111111112'}
        }.
        """
        params = {
            "from": from_,
            "to": to,
            "order": order,
            "sort": sort,
            "page": page,
            "pageSize": pageSize,
        }

        params = {k: v for k, v in params.items() if v is not None}
        return await self._request(f"/pool/{chain}", params=params)
