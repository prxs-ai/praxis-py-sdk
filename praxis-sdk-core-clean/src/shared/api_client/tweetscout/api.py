from typing import overload

from services.shared.api_client.aiohttp_ import AiohttpAPI

from .commands import (
    GetFollowings,
    GetFollowingsRequest,
    GetFollowingsResponse,
    Search,
    SearchRequest,
    SearchResponse,
)
from .session import TweetScoutSession


class TweetScoutAPI(AiohttpAPI[TweetScoutSession]):
    async def search(self, query: str, next_cursor: str | None = None) -> SearchResponse:
        return await self(Search(SearchRequest(query=query, next_cursor=next_cursor)))

    async def search_by_author(self, author: str, next_cursor: str | None = None) -> SearchResponse:
        return await self(Search(SearchRequest(query=f"from:{author}", next_cursor=next_cursor)))

    async def search_by_theme(self, theme: str, next_cursor: str | None = None) -> SearchResponse:
        return await self(Search(SearchRequest(query=theme, next_cursor=next_cursor)))

    @overload
    async def get_followings(self, user_id: str, link: None = None) -> list[GetFollowingsResponse]: ...
    @overload
    async def get_followings(self, link: str, user_id: None = None) -> list[GetFollowingsResponse]: ...

    async def get_followings(self, user_id: str | None = None, link: str | None = None) -> list[GetFollowingsResponse]:
        return await self(GetFollowings(GetFollowingsRequest(user_id=user_id, link=link)))
