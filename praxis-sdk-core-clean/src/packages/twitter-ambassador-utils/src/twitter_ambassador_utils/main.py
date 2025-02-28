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


async def create_post(
    access_token: str,
    tweet_text: str,
    quote_tweet_id: str | None = None,
    commented_tweet_id: str | None = None,
) -> dict | None:
    print(f'Posting tweet: {tweet_text=} {quote_tweet_id=} {commented_tweet_id=}')
    url = "https://api.x.com/2/tweets"

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    payload = {
        "text": tweet_text,
    }
    if quote_tweet_id:
        payload.update({"quote_tweet_id": quote_tweet_id})

    if commented_tweet_id:
        payload.update({"reply": {"in_reply_to_tweet_id": commented_tweet_id}})

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status == 201:
                result = await response.json()
                print(f'Tweet posted: {result}')
                return result
            else:
                print(f'Twit not posted: {await response.text()}')


async def retweet(token: str, user_id: str, tweet_id: str):
    url = f"https://api.x.com/2/users/{user_id}/retweets"
    payload = {"tweet_id": tweet_id}
    return await post_request(url, token, payload)


async def set_like(token: str, user_id: str, tweet_id: str):
    url = f"https://api.x.com/2/users/{user_id}/likes"
    payload = {"tweet_id": tweet_id}
    return await post_request(url, token, payload)
