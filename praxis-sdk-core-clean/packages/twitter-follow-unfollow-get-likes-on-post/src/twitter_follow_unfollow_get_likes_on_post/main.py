import aiohttp

from agents_tools_logger.main import log


async def get_likes_on_post(access_token: str, tweet_id: str):
    log.info("Getting user notifications")
    url = f"https://api.x.com/2/tweets/{tweet_id}/liking_users"

    headers = {"Authorization": f"Bearer {access_token}"}

    async with (
        aiohttp.ClientSession() as session,
        session.get(url, headers=headers) as response,
    ):
        if response.status == 200:
            result = await response.json()
            log.info(f'Notifications received: {result}')
            return result
        else:
            log.info(f'Notifications not received: {await response.text()}')
