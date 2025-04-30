from tenacity import retry, stop_after_attempt, wait_fixed, before_sleep_log
import logging
import aiohttp
from dataclasses import dataclass



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


# Helper function to make API requests with retry logic
@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
)
async def _make_request(url: str, access_token: str, method: str = "GET", params: dict = None, json_data: dict = None):
    print(f'Making {method} request to {url}')
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            if method.upper() == "GET":
                async with session.get(url, headers=headers, params=params) as response:
                    response.raise_for_status()
                    if response.status in (200, 201):
                        return await response.json()
                    else:
                        print(f"Unexpected status code: {response.status}")
                        return {}
            elif method.upper() == "POST":
                async with session.post(url, headers=headers, json=json_data) as response:
                    response.raise_for_status()
                    if response.status in (200, 201):
                        return await response.json()
                    else:
                        print(f"Unexpected status code: {response.status}")
                        return {}
    except aiohttp.ClientResponseError as e:
        logging.error(f"HTTP error during {method} request to {url}: {e}")
        raise
    except aiohttp.ClientError as e:
        logging.error(f"Client error during {method} request to {url}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error during {method} request to {url}: {e}")
        raise


async def post_request(url: str, access_token: str, payload: dict):
    """Helper function for making POST requests to Twitter API"""
    return await _make_request(url, access_token, method="POST", json_data=payload)


# Function to convert Twitter API v2 user to our User model
def parse_user_from_twitter_api(user_data: dict) -> User:
    public_metrics = user_data.get('public_metrics', {})
    return User(
        id_str=user_data.get('id', ''),
        name=user_data.get('name', ''),
        screen_name=user_data.get('username', ''),
        description=user_data.get('description', ''),
        followers_count=public_metrics.get('followers_count', 0),
        friends_count=public_metrics.get('following_count', 0),
        statuses_count=public_metrics.get('tweet_count', 0),
        created_at=user_data.get('created_at', ''),
        can_dm=False,  # Default value as Twitter API doesn't expose this directly
    )


# Function to convert Twitter API v2 tweet to our Tweet model
def parse_tweet_from_twitter_api(tweet_data: dict, users: dict, referenced_tweets: dict = None) -> Tweet:
    """
    Parse tweet data from Twitter API v2 to our Tweet model

    Args:
        tweet_data: The tweet data from Twitter API
        users: Dictionary mapping user IDs to user data
        referenced_tweets: Dictionary mapping tweet IDs to referenced tweet data
    """
    if referenced_tweets is None:
        referenced_tweets = {}

    user_id = tweet_data.get('author_id', '')
    user_data = users.get(user_id, {})
    user = parse_user_from_twitter_api(user_data)

    # Handle retweeted status
    retweeted_status = None
    # Handle quoted status
    quoted_status = None

    is_quote_status = False
    referenced_tweet_ids = []

    for ref_tweet in tweet_data.get('referenced_tweets', []):
        ref_type = ref_tweet.get('type')
        ref_id = ref_tweet.get('id')
        referenced_tweet_ids.append(ref_id)

        if ref_type == 'retweeted':
            if ref_id in referenced_tweets:
                rt_data = referenced_tweets[ref_id]
                rt_user_id = rt_data.get('author_id', '')
                rt_user_data = users.get(rt_user_id, {})
                rt_user = parse_user_from_twitter_api(rt_user_data)

                retweeted_status = RetweetedStatus(
                    created_at=rt_data.get('created_at', ''),
                    id_str=rt_data.get('id', ''),
                    full_text=rt_data.get('text', ''),
                    user=rt_user,
                    retweet_count=rt_data.get('public_metrics', {}).get('retweet_count', 0),
                    favorite_count=rt_data.get('public_metrics', {}).get('like_count', 0),
                )

        elif ref_type == 'quoted':
            is_quote_status = True
            if ref_id in referenced_tweets:
                qt_data = referenced_tweets[ref_id]
                qt_user_id = qt_data.get('author_id', '')
                qt_user_data = users.get(qt_user_id, {})
                qt_user = parse_user_from_twitter_api(qt_user_data)

                quoted_status = QuotedStatus(
                    created_at=qt_data.get('created_at', ''),
                    id_str=qt_data.get('id', ''),
                    full_text=qt_data.get('text', ''),
                    user=qt_user,
                    retweet_count=qt_data.get('public_metrics', {}).get('retweet_count', 0),
                    favorite_count=qt_data.get('public_metrics', {}).get('like_count', 0),
                )

    return Tweet(
        created_at=tweet_data.get('created_at', ''),
        id_str=tweet_data.get('id', ''),
        full_text=tweet_data.get('text', ''),
        user=user,
        retweeted_status=retweeted_status,
        quoted_status=quoted_status,
        retweet_count=tweet_data.get('public_metrics', {}).get('retweet_count', 0),
        favorite_count=tweet_data.get('public_metrics', {}).get('like_count', 0),
        is_quote_status=is_quote_status,
        conversation_id_str=tweet_data.get('conversation_id', ''),
        in_reply_to_status_id_str=tweet_data.get('in_reply_to_status_id', None),
    )


async def get_user_by_username(access_token: str, username: str) -> dict:
    """Get user data by username using Twitter API v2"""
    url = f"https://api.twitter.com/2/users/by/username/{username}"
    params = {
        "user.fields": "id,name,username,description,created_at,public_metrics"
    }
    result = await _make_request(url, access_token, params=params)
    if not result:
        print(f"Failed to get user data for username: {username}")
        return {}
    return result.get('data', {})


async def fetch_user_tweets(access_token: str, username: str) -> list[Tweet]:
    """Fetch tweets for a user using Twitter API v2"""
    print(f'fetch_user_tweets for {username=}')

    # First get the user ID
    user_data = await get_user_by_username(access_token, username)
    user_id = user_data.get('id')

    if not user_id:
        print(f"Could not find user ID for username {username}")
        return []

    # Then fetch the user's tweets
    url = f"https://api.twitter.com/2/users/{user_id}/tweets"
    params = {
        "max_results": 100,
        "tweet.fields": "created_at,public_metrics,referenced_tweets,conversation_id,in_reply_to_user_id",
        "expansions": "author_id,referenced_tweets.id,referenced_tweets.id.author_id",
        "user.fields": "id,name,username,description,created_at,public_metrics"
    }

    result = await _make_request(url, access_token, params=params)

    tweets_data = result.get('data', [])
    users_data = {user['id']: user for user in result.get('includes', {}).get('users', [])}

    # Create a dictionary of referenced tweets
    referenced_tweets = {}
    for tweet in result.get('includes', {}).get('tweets', []):
        referenced_tweets[tweet['id']] = tweet

    # Parse the tweets
    tweets = []
    for tweet_data in tweets_data:
        try:
            tweet = parse_tweet_from_twitter_api(tweet_data, users_data, referenced_tweets)
            tweets.append(tweet)
        except Exception as e:
            print(f"Error parsing tweet data: {e}")
            print(f"Tweet data: {tweet_data}")

    return tweets


async def search_tweets(access_token: str, query: str) -> list[Tweet]:
    """Search for tweets using Twitter API v2"""
    url = 'https://api.twitter.com/2/tweets/search/recent'
    params = {
        "query": query,
        "max_results": 100,
        "tweet.fields": "created_at,public_metrics,referenced_tweets,conversation_id,in_reply_to_user_id",
        "expansions": "author_id,referenced_tweets.id,referenced_tweets.id.author_id",
        "user.fields": "id,name,username,description,created_at,public_metrics"
    }

    result = await _make_request(url, access_token, params=params)

    tweets_data = result.get('data', [])
    users_data = {user['id']: user for user in result.get('includes', {}).get('users', [])}

    # Create a dictionary of referenced tweets
    referenced_tweets = {}
    for tweet in result.get('includes', {}).get('tweets', []):
        referenced_tweets[tweet['id']] = tweet

    # Parse the tweets
    tweets = [
        parse_tweet_from_twitter_api(tweet_data, users_data, referenced_tweets)
        for tweet_data in tweets_data
    ]

    return tweets


async def get_tweet_by_link(access_token: str, link: str) -> Tweet:
    """Get a tweet by its link using Twitter API v2"""
    # Extract the tweet ID from the link
    # Links are of the format https://twitter.com/username/status/tweet_id
    # or https://x.com/username/status/tweet_id
    parts = link.strip('/').split('/')
    tweet_id = parts[-1]

    url = f"https://api.twitter.com/2/tweets/{tweet_id}"
    params = {
        "tweet.fields": "created_at,public_metrics,referenced_tweets,conversation_id,in_reply_to_user_id",
        "expansions": "author_id,referenced_tweets.id,referenced_tweets.id.author_id",
        "user.fields": "id,name,username,description,created_at,public_metrics"
    }

    result = await _make_request(url, access_token, params=params)

    tweet_data = result.get('data', {})
    users_data = {user['id']: user for user in result.get('includes', {}).get('users', [])}

    # Create a dictionary of referenced tweets
    referenced_tweets = {}
    for tweet in result.get('includes', {}).get('tweets', []):
        referenced_tweets[tweet['id']] = tweet

    # Parse the tweet
    return parse_tweet_from_twitter_api(tweet_data, users_data, referenced_tweets)


async def get_conversation_from_tweet(access_token: str, tweet: Tweet) -> list[Tweet]:
    """Get the conversation thread from a tweet using Twitter API v2"""
    conversation_chain = [tweet]
    tweet_id = tweet.in_reply_to_status_id_str

    while tweet_id:
        try:
            reply_tweet = await get_tweet_by_link(access_token, f"https://twitter.com/i/status/{tweet_id}")
            if reply_tweet is None:
                break
            conversation_chain.append(reply_tweet)
            tweet_id = reply_tweet.in_reply_to_status_id_str
        except Exception as e:
            print(f"Error getting tweet in conversation: {e}")
            break

    return conversation_chain[::-1]  # first tweet is oldest


def create_conversation_string(tweets: list[Tweet]) -> str:
    """Format a conversation thread as a string"""
    formatted_messages = []
    for tweet in tweets:
        formatted_messages.append(f'{tweet.user.screen_name}:\n    {tweet.full_text}')

    return '\n'.join(formatted_messages)


# Additional useful functions from the user's examples

async def post_tweet(
        access_token: str,
        tweet_text: str,
        quote_tweet_id: str | None = None,
        commented_tweet_id: str | None = None,
) -> dict | None:
    """Post a new tweet using Twitter API v2"""
    print(f'Posting tweet: {tweet_text=} {quote_tweet_id=} {commented_tweet_id=}')
    url = "https://api.twitter.com/2/tweets"

    payload = {
        "text": tweet_text,
    }

    if quote_tweet_id:
        payload.update({"quote_tweet_id": quote_tweet_id})
    if commented_tweet_id:
        payload.update({"reply": {"in_reply_to_tweet_id": commented_tweet_id}})

    return await _make_request(url, access_token, method="POST", json_data=payload)


async def follow(access_token: str, user_id: str, target_user_id: str):
    """Follow a user using Twitter API v2"""
    url = f"https://api.twitter.com/2/users/{user_id}/following"
    payload = {"target_user_id": target_user_id}
    return await _make_request(url, access_token, method="POST", json_data=payload)


async def get_likes_on_post(access_token: str, tweet_id: str):
    """Get users who liked a tweet using Twitter API v2"""
    print(f"Getting likes for tweet {tweet_id}")
    url = f"https://api.twitter.com/2/tweets/{tweet_id}/liking_users"
    params = {
        "user.fields": "id,name,username,description,created_at,public_metrics"
    }
    return await _make_request(url, access_token, params=params)


async def retweet(access_token: str, user_id: str, tweet_id: str):
    """Retweet a tweet using Twitter API v2"""
    url = f"https://api.twitter.com/2/users/{user_id}/retweets"
    payload = {"tweet_id": tweet_id}
    return await _make_request(url, access_token, method="POST", json_data=payload)


async def set_like(access_token: str, user_id: str, tweet_id: str):
    """Like a tweet using Twitter API v2"""
    url = f"https://api.twitter.com/2/users/{user_id}/likes"
    payload = {"tweet_id": tweet_id}
    return await _make_request(url, access_token, method="POST", json_data=payload)
