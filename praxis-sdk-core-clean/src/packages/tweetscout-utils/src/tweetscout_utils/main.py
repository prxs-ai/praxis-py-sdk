from tenacity import retry, stop_after_attempt, wait_fixed
import aiohttp
import asyncio
from dataclasses import dataclass

from tweetscout_utils.config import get_settings

settings = get_settings()


@dataclass
class User:
    id_str: str
    name: str
    screen_name: str
    description: str
    followers_count: int
    friends_count: int
    statuses_count: int
    created_at: str
    can_dm: bool = False

    @property
    def info(self):
        return f"Name: {self.name}\nUsername: {self.screen_name}\nDescription: {self.description}"


@dataclass
class QuotedStatus:
    created_at: str
    id_str: str
    full_text: str
    user: User
    retweet_count: int
    favorite_count: int


@dataclass
class RetweetedStatus:
    created_at: str
    id_str: str
    full_text: str
    user: User
    retweet_count: int
    favorite_count: int


@dataclass
class Tweet:
    created_at: str
    id_str: str
    full_text: str
    user: User
    retweeted_status: RetweetedStatus | None
    quoted_status: QuotedStatus | None
    retweet_count: int
    favorite_count: int
    is_quote_status: bool
    conversation_id_str: str
    in_reply_to_status_id_str: str | None


def parse_user(data: dict) -> User:
    return User(
        id_str=data['id_str'],
        name=data['name'],
        screen_name=data['screen_name'],
        description=data['description'],
        followers_count=data['followers_count'],
        friends_count=data['friends_count'],
        statuses_count=data['statuses_count'],
        created_at=data['created_at'],
        can_dm=data.get('can_dm', False),
    )


def parse_retweeted_status(data: dict | None) -> RetweetedStatus | None:
    if data is None:
        return None
    user = parse_user(data['user'])
    return RetweetedStatus(
        created_at=data['created_at'],
        id_str=data['id_str'],
        full_text=data['full_text'],
        user=user,
        retweet_count=data['retweet_count'],
        favorite_count=data['favorite_count'],
    )


def parse_quoted_status(data: dict | None) -> QuotedStatus | None:
    if data is None:
        return None
    user = parse_user(data['user'])
    return QuotedStatus(
        created_at=data['created_at'],
        id_str=data['id_str'],
        full_text=data['full_text'],
        user=user,
        retweet_count=data['retweet_count'],
        favorite_count=data['favorite_count'],
    )


def parse_tweet(data: dict) -> Tweet:
    user = parse_user(data['user'])
    retweeted_status = parse_retweeted_status(data.get('retweeted_status'))
    quoted_status = parse_quoted_status(data.get('quoted_status'))
    return Tweet(
        created_at=data['created_at'],
        id_str=data['id_str'],
        full_text=data['full_text'],
        user=user,
        retweeted_status=retweeted_status,
        quoted_status=quoted_status,
        retweet_count=data['retweet_count'],
        favorite_count=data['favorite_count'],
        is_quote_status=data['is_quote_status'],
        conversation_id_str=data['conversation_id_str'],
        in_reply_to_status_id_str=data.get('in_reply_to_status_id_str'),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
)
async def _make_request(url: str, data: dict):
    headers = {"ApiKey": settings.TWEETSCOUT_API_KEY}

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            async with session.post(url, headers=headers, json=data) as response:
                response.raise_for_status()  # Проверяем статус ответа
                response_json = await response.json()
                return response_json
    except aiohttp.ClientResponseError as e:
        print(f"HTTP error during request to {url}: {e}")
        raise
    except aiohttp.ClientError as e:
        print(f"Client error during request to {url}: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error during request to {url}: {e}")
        raise


async def fetch_user_tweets(username: str) -> list[Tweet]:
    url = "https://api.tweetscout.io/api/user-tweets"
    data = {"link": f"https://x.com/{username}"}
    result = await _make_request(url, data)
    tweets_data = result.get('tweets', [])
    tweets = [parse_tweet(tweet_data) for tweet_data in tweets_data]
    return tweets


async def search_tweets(query: str) -> list[Tweet]:
    url = 'https://api.tweetscout.io/v2/search-tweets'
    data = {'query': query}
    result = await _make_request(url, data)
    tweets_data = result.get('tweets', [])
    tweets = [parse_tweet(tweet_data) for tweet_data in tweets_data]
    return tweets


async def get_tweet_by_link(link: str) -> Tweet:
    url = 'https://api.tweetscout.io/api/tweet-info'
    data = {'tweet_link': link}
    result = await _make_request(url, data)
    return parse_tweet(result)


async def get_conversation_from_tweet(tweet: Tweet) -> list[Tweet]:
    conversation_chain = [tweet]
    tweet_id = tweet.in_reply_to_status_id_str
    while tweet_id:
        reply_tweet = await get_tweet_by_link(f"https://twitter.com/apify/status/{tweet_id}")
        if reply_tweet is None:
            break
        conversation_chain.append(reply_tweet)
        tweet_id = reply_tweet.in_reply_to_status_id_str

    return conversation_chain[::-1]  # first tweet is newest


def create_conversation_string(tweets: list[Tweet]) -> str:
    formatted_messages = []
    for tweet in tweets:
        formatted_messages.append(f'{tweet.user.screen_name}:\n    {tweet.full_text}')

    return '\n'.join(formatted_messages)


if __name__ == '__main__':
    asyncio.run(fetch_user_tweets(''))
