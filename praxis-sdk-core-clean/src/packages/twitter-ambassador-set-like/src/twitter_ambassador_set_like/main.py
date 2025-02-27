from twitter_ambassador_native_api.main import post_request


async def set_like(token: str, user_id: str, tweet_id: str):
    url = f"https://api.x.com/2/users/{user_id}/likes"
    payload = {"tweet_id": tweet_id}
    return await post_request(url, token, payload)
