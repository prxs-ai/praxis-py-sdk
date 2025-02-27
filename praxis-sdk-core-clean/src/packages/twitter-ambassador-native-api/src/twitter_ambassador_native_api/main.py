import aiohttp


async def post_request(url: str, token: str, payload: dict):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.ok:
                data = await response.json()
                print(f"Request successful: {data}")
                return data
            print(f"Request failed. Status: {response.status}, Response: {await response.text()}")
            return await response.json()
