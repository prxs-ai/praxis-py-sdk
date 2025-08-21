import aiohttp


class HttpClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def post(
        self, endpoint: str, data: dict, headers: dict = None
    ) -> aiohttp.ClientResponse:
        url = f"{self.base_url}{endpoint}"
        async with aiohttp.ClientSession() as session:
            response = await session.post(url, data=data, headers=headers)
            response.raise_for_status()
            return response

    async def get(self, endpoint: str, headers: dict) -> aiohttp.ClientResponse:
        url = f"{self.base_url}{endpoint}"
        async with aiohttp.ClientSession() as session:
            response = await session.get(url, headers=headers)
            response.raise_for_status()
            return response
