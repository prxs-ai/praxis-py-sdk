from typing import Any, Self

from pydantic import model_validator

from services.shared.api_client import APIError

from .base import AbstractCommand, Request, Response, TweetScoutSession


class GetFollowingsRequest(Request):
    user_id: str | None = None
    link: str | None = None

    @model_validator(mode="after")
    def check_exactly_one(self) -> Self:
        user_id_provided = self.user_id is not None
        link_provided = self.link is not None
        if user_id_provided and link_provided:
            raise ValueError("Either user_id or link must be provided")
        elif not (user_id_provided or link_provided):
            raise ValueError("One of user_id or link must be provided")
        return self


class GetFollowingsResponse(Response):
    avatar: str
    can_dm: bool
    description: str
    followers_count: int
    friends_count: int
    id: str
    name: str
    register_date: str
    screen_name: str
    tweets_count: int
    verified: bool


class GetFollowings(AbstractCommand[GetFollowingsRequest, list[GetFollowingsResponse]]):
    async def _execute(self, session: TweetScoutSession) -> list[GetFollowingsResponse]:
        response = await session.get("follows", params=self.data.dump(), json={})
        if response.status != 200:
            raise APIError(response.status, await response.text())

        data: list[dict[str, Any]] = await response.json()
        return [GetFollowingsResponse(**values) for values in data]
