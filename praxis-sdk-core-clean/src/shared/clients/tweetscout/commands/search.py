from services.shared.clients import APIError

from .base import AbstractCommand, Request, Response, TweetScoutSession


class SearchRequest(Request):
    query: str
    next_cursor: str | None = None


class Entity(Response):
    link: str
    preview: str
    type: str


class User(Response):
    avatar: str
    can_dm: bool
    created_at: str
    description: str
    followers_count: int
    friends_count: int
    id_str: str
    name: str
    screen_name: str
    statuses_count: int


class QuoteStatus(Response):
    created_at: str
    favorite_count: int
    full_text: str
    id_str: str
    quote_count: int
    retweet_count: int
    user: User


class RetweetedStatus(Response):
    created_at: str
    favorite_count: int
    full_text: str
    id_str: str
    quote_count: int
    retweet_count: int
    user: User


class Tweet(Response):
    conversation_id_str: str
    created_at: str
    entities: list[Entity] | None
    favorite_count: int
    full_text: str
    id_str: str
    in_reply_to_status_id_str: str | None
    is_quote_status: bool
    quote_count: int
    quoted_status: QuoteStatus | None
    reply_count: int
    retweet_count: int
    retweeted_status: RetweetedStatus | None
    view_count: int
    user: User


class SearchResponse(Response):
    next_cursor: str
    tweets: list[Tweet]


class Search(AbstractCommand[SearchRequest, SearchResponse]):
    async def _execute(self, session: TweetScoutSession) -> SearchResponse:
        response = await session.post("search-tweets", json=self.data.dump())
        if response.status != 200:
            raise APIError(response.status, await response.text())

        return SearchResponse(**(await response.json()))
