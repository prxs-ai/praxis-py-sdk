import asyncio
import base64
import hashlib
import os
import re
from datetime import datetime

import hvac
from requests_oauthlib import OAuth2Session
import aiohttp

from redis_client.main import decode_redis, get_redis_db
from twitter_ambassador_utils.config import cipher, get_settings, get_hvac_client
from loguru import logger

settings = get_settings()


async def post_request(url: str, token: str, payload: dict):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.ok:
                data = await response.json()
                logger.info(f"Request successful: {data}")
                return data
            logger.error(f"Request failed. Status: {response.status}, Response: {await response.text()}")
            return await response.json()


async def create_post(
    access_token: str,
    tweet_text: str,
    quote_tweet_id: str | None = None,
    commented_tweet_id: str | None = None,
) -> dict | None:
    logger.info(f'Posting tweet: {tweet_text=} {quote_tweet_id=} {commented_tweet_id=}')
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
                logger.info(f'Tweet posted: {result}')
                return result
            else:
                logger.error(f'Twit not posted: {await response.text()}')


async def retweet(token: str, user_id: str, tweet_id: str):
    url = f"https://api.x.com/2/users/{user_id}/retweets"
    payload = {"tweet_id": tweet_id}
    return await post_request(url, token, payload)


async def set_like(token: str, user_id: str, tweet_id: str):
    url = f"https://api.x.com/2/users/{user_id}/likes"
    payload = {"tweet_id": tweet_id}
    return await post_request(url, token, payload)


class TwitterAuthClient:
    _CLIENT = OAuth2Session(
        client_id=settings.TWITTER_CLIENT_ID,
        redirect_uri=settings.TWITTER_REDIRECT_URI,
        scope="tweet.read users.read follows.write tweet.write like.write like.read follows.read offline.access",
    )
    _DB = get_redis_db()
    HVAC_CLIENT = get_hvac_client()
    AUTH_PATH = "{user_id}/twitter"
    SESSION_PATH = "sessions/{session_id}"

    @classmethod
    def create_auth_link(cls, user_id: str = None):
        code_verifier = cls._generate_code_verifier()
        code_challenge = cls._generate_code_challenge(code_verifier)

        url, state = cls._CLIENT.authorization_url(
            url='https://twitter.com/i/oauth2/authorize',
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

        cls._store_session_data_in_vault(
            session_id=state,
            data={
                # "user_id": str(user_id),
                "code_challenge": code_challenge,
                "code_verifier": code_verifier,
                "created_at": datetime.now().timestamp(),
                "expires_at": datetime.now().timestamp() + 60 * 60,  # 1 hour expiration
            },
        )
        return url

    @classmethod
    async def callback(cls, state: str, code: str):
        """Twitter send here after user allow to connect to his account"""
        session_data = cls.get_session_data_from_vault(state)
        if not session_data:
            logger.error(f"No session data found for state: {state}")
            return False

        tokens_data = await cls.get_tokens(state, code)
        if not tokens_data:
            logger.error(f"Failed to get tokens for state: {state}")
            return False

        user_data = await cls.get_me(tokens_data['access_token'])
        if not user_data:
            logger.error(f"Failed to get user data for user: {tokens_data['user_id']}")
            return False

        # Combine and encrypt sensitive data
        combined_data = {**tokens_data}
        # Encrypt sensitive data before storing
        combined_data['access_token'] = cipher.encrypt(tokens_data['access_token'].encode()).decode()
        combined_data['refresh_token'] = cipher.encrypt(tokens_data['refresh_token'].encode()).decode()

        # Add user profile data
        combined_data.update(user_data)

        # Save to Vault
        cls.save_twitter_data(tokens_data['user_id'], combined_data)

        # Clean up session data
        cls.delete_session_from_vault(state)

        return True

    @classmethod
    async def get_tokens(cls, state: str, code: str):
        """get tokens from state and code that twitter had sent to callback"""
        if not (data := cls.get_session_data_from_vault(state)):
            logger.error(f"No session data found in Vault for state: {state}")
            return

        # Check if session has expired
        current_time = datetime.now().timestamp()
        if current_time > data.get("expires_at", 0):
            logger.error(f"Session expired for state: {state}")
            cls.delete_session_from_vault(state)
            return

        loop = asyncio.get_running_loop()
        try:
            tokens_data = await loop.run_in_executor(
                None,
                lambda: cls._CLIENT.fetch_token(
                    token_url='https://api.twitter.com/2/oauth2/token',
                    code=code,
                    client_secret=settings.TWITTER_CLIENT_SECRET,
                    code_verifier=data["code_verifier"],
                ),
            )
            return {
                # "user_id": data["user_id"],
                "access_token": tokens_data["access_token"],
                "refresh_token": tokens_data["refresh_token"],
                "expires_at": tokens_data["expires_at"],
            }
        except Exception as e:
            logger.error(f"Error fetching tokens: {e}")
            return None

    @classmethod
    async def get_me(cls, access_token: str) -> dict | None:
        logger.info("Get me twitter")
        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {access_token}"},
                                         timeout=aiohttp.ClientTimeout(10)) as session:
            async with session.get("https://api.twitter.com/2/users/me") as response:
                data = await response.json()
                if response.status == 403 and "suspended" in data.get("detail", ""):
                    response.raise_for_status()

                if not response.ok:
                    logger.error(f"Bad request to twitter get_me - {data}")
                    return None

                return {
                    "name": data["data"]["name"],
                    "username": data["data"]["username"],
                    'twitter_id': data["data"]["id"],
                }

    @classmethod
    def _generate_code_verifier(cls) -> str:
        code_verifier = base64.urlsafe_b64encode(os.urandom(30)).decode("utf-8")
        return re.sub("[^a-zA-Z0-9]+", "", code_verifier)

    @classmethod
    def _generate_code_challenge(cls, code_verifier: str) -> str:
        code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
        return code_challenge.replace("=", "")

    @classmethod
    def _store_session_data_in_vault(cls, session_id: str, data: dict) -> None:
        """Store session data in Vault instead of Redis"""
        try:
            cls.HVAC_CLIENT.secrets.kv.v2.create_or_update_secret(
                path=cls.SESSION_PATH.format(session_id=session_id),
                secret=data,
                mount_point="dev/",
            )
            logger.info(f"Session data stored in Vault for session ID: {session_id}")
        except Exception as e:
            logger.error(f"Failed to store session data in Vault: {e}")
            # Fallback to Redis if Vault fails
            cls._store_session_data_in_redis(session_id, data, ex=3600)  # 1 hour expiration

    @classmethod
    def _store_session_data_in_redis(cls, session_id: str, data: dict, ex: int) -> None:
        """Legacy method to store data in Redis as fallback"""
        try:
            cls._DB.r.hmset(f"session:{session_id}", mapping=data)
            cls._DB.r.expire(f"session:{session_id}", ex)
            logger.info(f"Session data stored in Redis for session ID: {session_id}")
        except Exception as e:
            logger.error(f"Failed to store session data in Redis: {e}")

    @classmethod
    def get_session_data_from_vault(cls, session_id: str) -> dict | None:
        """Get session data from Vault"""
        try:
            response = cls.HVAC_CLIENT.secrets.kv.v2.read_secret_version(
                path=cls.SESSION_PATH.format(session_id=session_id),
                mount_point="dev/"
            )
            return response['data']['data']
        except Exception as e:
            logger.error(f"Failed to get session data from Vault: {e}")
            # Try fallback to Redis
            return cls.get_session_data_from_redis(session_id)

    @classmethod
    def get_session_data_from_redis(cls, session_id: str) -> dict | None:
        """Legacy method to get data from Redis as fallback"""
        if session_data := cls._DB.r.hgetall(f"session:{session_id}"):
            return decode_redis(session_data)
        return None

    @classmethod
    def get_session_data(cls, session_id: str) -> dict | None:
        """Combined method to get session data, prioritizing Vault"""
        # Try Vault first, then fallback to Redis
        data = cls.get_session_data_from_vault(session_id)
        if not data:
            logger.warning(f"Session data not found in Vault, trying Redis for session ID: {session_id}")
            data = cls.get_session_data_from_redis(session_id)
        return data

    @classmethod
    def delete_session_from_vault(cls, session_id: str) -> None:
        """Delete session data from Vault after use"""
        try:
            cls.HVAC_CLIENT.secrets.kv.v2.delete_metadata_and_all_versions(
                path=cls.SESSION_PATH.format(session_id=session_id),
                mount_point="dev/",
            )
            logger.info(f"Session data deleted from Vault for session ID: {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete session data from Vault: {e}")
            # Also try to clean up Redis if it exists there
            cls._DB.r.delete(f"session:{session_id}")

    @classmethod
    def save_twitter_data(cls, data: dict,  user_id: str = None):
        """Сохраняет OAuth-данные Twitter для пользователя в Vault."""
        try:
            cls.HVAC_CLIENT.secrets.kv.v2.create_or_update_secret(
                path=cls.AUTH_PATH.format(user_id=data['username']),
                secret=data,
                mount_point="dev/",
            )
            logger.info(f"Twitter data saved in Vault for user ID: {data['username']}")
        except Exception as e:
            logger.error(f"Failed to save Twitter data in Vault: {e}")

    @classmethod
    async def _refresh_tokens(cls, refresh_token: str):
        """Refresh tokens with proper error handling"""
        try:
            # Decrypt refresh token if it's encrypted
            if isinstance(refresh_token, str) and refresh_token.startswith("b'"):
                refresh_token = cipher.decrypt(refresh_token.encode()).decode()

            loop = asyncio.get_running_loop()
            tokens_data = await loop.run_in_executor(
                None,
                lambda: cls._CLIENT.refresh_token(
                    token_url='https://api.twitter.com/2/oauth2/token',
                    refresh_token=refresh_token,
                    client_id=settings.TWITTER_CLIENT_ID,
                    client_secret=settings.TWITTER_CLIENT_SECRET,
                    headers={
                        "Authorization": f"Basic {settings.TWITTER_BASIC_BEARER_TOKEN}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                ),
            )

            # Encrypt new tokens for storage
            return {
                "access_token": tokens_data["access_token"],
                "refresh_token": tokens_data["refresh_token"],
                "expires_at": tokens_data["expires_at"],
            }
        except Exception as e:
            logger.error(f"Error refreshing tokens: {e}")
            return None

    @classmethod
    async def update_tokens(cls, username: str, new_tokens: dict):
        """Обновляет access_token, refresh_token и expires_at для пользователя."""
        try:
            # Encrypt tokens before storing
            encrypted_tokens = {
                'access_token': cipher.encrypt(new_tokens['access_token'].encode()).decode(),
                'refresh_token': cipher.encrypt(new_tokens['refresh_token'].encode()).decode(),
                'expires_at': new_tokens['expires_at']
            }

            cls.HVAC_CLIENT.secrets.kv.v2.patch(
                path=cls.AUTH_PATH.format(user_id=username),
                secret=encrypted_tokens,
                mount_point="dev/",
            )
            logger.info(f"Tokens updated in Vault for user ID: {username}")
        except Exception as e:
            logger.error(f"Failed to update tokens in Vault: {e}")

    @classmethod
    async def disconnect_twitter(cls, username: str):
        """Delete Twitter data for a user"""
        try:
            # Delete from Vault
            cls.HVAC_CLIENT.secrets.kv.v2.delete_metadata_and_all_versions(
                path=cls.AUTH_PATH.format(user_id=username),
                mount_point="dev/",
            )
            logger.info(f"Twitter data deleted from Vault for user ID: {username}")

            # Also delete from Redis if it exists
            cls._DB.r.delete(f'twitter_data:{username}')
            logger.info(f"Twitter data deleted from Redis for user ID: {username}")

            return True
        except Exception as e:
            logger.error(f"Failed to disconnect Twitter for user {username}: {e}")
            return False

    @classmethod
    async def get_twitter_data(cls, username: str) -> dict:
        """Возвращает словарь со всеми сохранёнными данными Twitter из Vault."""
        try:
            resp = cls.HVAC_CLIENT.secrets.kv.v2.read_secret_version(
                path=cls.AUTH_PATH.format(user_id=username),
                mount_point="dev/"
            )
            logger.info(f"Retrieved Twitter data from Vault for user ID: {username}")
            return resp['data']['data']
        except Exception as e:
            logger.error(f"Failed to get Twitter data from Vault for user {username}: {e}")
            return {}

    @classmethod
    async def get_static_data(cls, username: str) -> dict:
        """Get non-sensitive Twitter user data"""
        try:
            data = await cls.get_twitter_data(username)
            if not data:
                logger.warning(f"No Twitter data found for user ID: {username}")
                return {}

            return {
                'name': data.get('name', ''),
                'username': data.get('username', ''),
                'twitter_id': data.get('twitter_id', ''),
                'connected_at': data.get('connected_at', datetime.now().timestamp()),
            }
        except Exception as e:
            logger.error(f"Error getting static data for user {username}: {e}")
            return {}

    @classmethod
    async def get_access_token(cls, username: str) -> str:
        """Get and possibly refresh the access token"""
        twitter_data = await cls.get_twitter_data(username)
        if not twitter_data:
            logger.error(f"No twitter data found for {username}")
            raise ValueError(f"Twitter data not found for user {username}")

        try:
            # Check if token is expired
            current_time = datetime.now().timestamp()
            expires_at = twitter_data.get("expires_at", 0)

            # If token expires in less than 5 minutes, refresh it
            if current_time + 300 > expires_at:
                logger.info(f"Token expired or expiring soon for user {username}, refreshing...")
                new_tokens = await cls._refresh_tokens(twitter_data.get("refresh_token"))
                if new_tokens:
                    await cls.update_tokens(username, new_tokens)
                    access_token = new_tokens["access_token"]
                else:
                    # If refresh failed, try to use existing token if not expired yet
                    if current_time < expires_at:
                        access_token = cipher.decrypt(twitter_data["access_token"].encode()).decode()
                    else:
                        raise ValueError("Failed to refresh expired token")
            else:
                access_token = cipher.decrypt(twitter_data["access_token"].encode()).decode()

            logger.info(f'Access token retrieved successfully for user {username}')
            return access_token
        except Exception as e:
            logger.error(f"Error processing access token for {username}: {e}")
            raise e

    @classmethod
    async def check_token_validity(cls, username: str) -> bool:
        """Check if the stored tokens are still valid"""
        try:
            access_token = await cls.get_access_token(username)
            user_data = await cls.get_me(access_token)
            return user_data is not None
        except Exception as e:
            logger.error(f"Token validity check failed for user {username}: {e}")
            return False
