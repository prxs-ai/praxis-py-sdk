from typing import Any

from services.shared.api_client import APIError

from .base import AbstractCommand, Request, Response, TweetScoutSession


class SearchRequest(Request):
    query: str
    next_cursor: str | None = None


class SearchResponse(Response):
    next_cursor: str
    tweets: list[dict[str, Any]]


class Search(AbstractCommand[SearchRequest, SearchResponse]):
    async def _execute(self, session: TweetScoutSession) -> SearchResponse:
        response = await session.post("search-tweets", json=self.data.dump())
        if response.status != 200:
            raise APIError(response.status, await response.text())

        return SearchResponse(**(await response.json()))
