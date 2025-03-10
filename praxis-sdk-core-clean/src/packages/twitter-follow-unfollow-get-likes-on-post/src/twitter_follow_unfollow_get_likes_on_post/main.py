import aiohttp

from infrastructure.configs.logger import get_logger

logger = get_logger(__name__)


async def get_likes_on_post(access_token: str, tweet_id: str):
    logger.info("Getting user notifications")
    url = f"https://api.x.com/2/tweets/{tweet_id}/liking_users"

    headers = {"Authorization": f"Bearer {access_token}"}

    async with (
        aiohttp.ClientSession() as session,
        session.get(url, headers=headers) as response,
    ):
        if response.status == 200:
            result = await response.json()
            logger.info(f'Notifications received: {result}')
            return result
        else:
            logger.info(f'Notifications not received: {await response.text()}')
