import aiohttp


async def follow(token: str, user_id: str, target_user_id: str):
    """Follows a user with the given user_id.

    param token: Access token for the user.
    param user_id: User ID of the user who will follow the target user.
    param target_user_id: User ID of the user to be followed.
    """
    url = f"https://api.x.com/2/users/{user_id}/following"
    payload = {"target_user_id": target_user_id}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.ok:
                data = await response.json()
                print(f"Request successful: {data}")
                return data
            error_text = await response.text()
            print(f"Request failed. Status: {response.status}, Response: {error_text}")
            return {"error": error_text, "status": response.status}
