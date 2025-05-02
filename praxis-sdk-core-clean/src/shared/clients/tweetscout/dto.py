from typing import Any

from msgspec import Struct


class DTO(Struct):
    def to_dict(self, exclude_none: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for field in self.__struct_fields__:
            value = getattr(self, field)
            if exclude_none and value is None:
                continue
            data[field] = value
        return data


class TypesAccount(DTO):
    avatar: str | None = None
    banner: str | None = None
    canDM: bool | None = None
    description: str | None = None
    followersCount: int | None = None
    friendsCount: int | None = None
    id: str | None = None
    name: str | None = None
    protected: bool | None = None
    registerDate: str | None = None
    score: float | None = None
    screeName: str | None = None
    statuses_count: int | None = None
    verified: bool | None = None


class TypesFollower(DTO):
    avatar: str | None = None
    banner: str | None = None
    canDM: bool | None = None
    description: str | None = None
    followerDate: str | None = None
    followersCount: int | None = None
    friendsCount: int | None = None
    id: str | None = None
    name: str | None = None
    protected: bool | None = None
    registerDate: str | None = None
    score: float | None = None
    screeName: str | None = None
    statuses_count: int | None = None
    verified: bool | None = None


class TypesListItemEntity(DTO):
    link: str | None = None
    preview: str | None = None
    type: str | None = None


class TypesListItemUser(DTO):
    avatar: str | None = None
    can_dm: bool | None = None
    created_at: str | None = None
    description: str | None = None
    followers_count: int | None = None
    friends_count: int | None = None
    id_str: str | None = None
    name: str | None = None
    screen_name: str | None = None
    statuses_count: int | None = None


class TypesListItemQuotedStatus(DTO):
    created_at: str | None = None
    favorite_count: int | None = None
    full_text: str | None = None
    id_str: str | None = None
    quote_count: int | None = None
    retweet_count: int | None = None
    user: TypesListItemUser | None = None


class TypesListItemRetweetedStatus(DTO):
    created_at: str | None = None
    favorite_count: int | None = None
    full_text: str | None = None
    id_str: str | None = None
    quote_count: int | None = None
    retweet_count: int | None = None
    user: TypesListItemUser | None = None


class TypesListItem(DTO):
    bookmark_count: int | None = None
    conversation_id_str: str | None = None
    created_at: str | None = None
    entities: list[TypesListItemEntity] | None = None
    favorite_count: int | None = None
    full_text: str | None = None
    id_str: str | None = None
    in_reply_to_status_id_str: str | None = None
    is_quote_status: bool | None = None
    quote_count: int | None = None
    quoted_status: TypesListItemQuotedStatus | None = None
    reply_count: int | None = None
    retweet_count: int | None = None
    retweeted_status: TypesListItemRetweetedStatus | None = None
    user: TypesListItemUser | None = None
    view_count: int | None = None


class HandlerCheckCommentResp(DTO):
    commented: bool | None = None
    tweet: TypesListItem | None = None


class HandlerCheckFollowReq(DTO):
    project_handle: str | None = None
    project_id: str | None = None
    user_handle: str | None = None
    user_id: str | None = None


class HandlerCheckFollowResp(DTO):
    follow: bool | None = None
    user_protected: bool | None = None


class HandlerCheckQuotedReq(DTO):
    tweet_link: str | None = None
    user_handle: str | None = None
    user_id: str | None = None


class HandlerCheckQuotedResp(DTO):
    date: str | None = None
    status: str | None = None
    text: str | None = None
    user_protected: bool | None = None


class HandlerCheckRetweetReq(DTO):
    next_cursor: str | None = None
    tweet_link: str | None = None
    user_handle: str | None = None
    user_id: str | None = None


class HandlerCheckRetweetResp(DTO):
    next_cursor: str | None = None
    retweet: bool | None = None
    user_protected: bool | None = None


class HandlerErrorResponse(DTO):
    message: str | None = None


class HandlerFollowDateResp(DTO):
    follow: bool | None = None
    follow_date: str | None = None
    user_protected: bool | None = None


class HandlerFollowersStatsResp(DTO):
    followers_count: int | None = None
    influencers_count: int | None = None
    projects_count: int | None = None
    user_protected: bool | None = None
    venture_capitals_count: int | None = None


class HandlerHandleHistoriesResp(DTO):
    handles: list["HandlerHandleHistory"] | None = None


class HandlerHandleHistory(DTO):
    date: str | None = None
    handle: str | None = None


class HandlerHandleRes(DTO):
    handle: str | None = None


class HandlerIDRes(DTO):
    id: str | None = None


class HandlerListMember(DTO):
    avatar: str | None = None
    id: str | None = None
    name: str | None = None
    screen_name: str | None = None


class HandlerListTweetsRes(DTO):
    next_cursor: str | None = None
    tweets: list[TypesListItem] | None = None


class HandlerLookupRes(DTO):
    avatar: str | None = None
    banner: str | None = None
    can_dm: bool | None = None
    description: str | None = None
    followers_count: int | None = None
    friends_count: int | None = None
    id: str | None = None
    name: str | None = None
    register_date: str | None = None
    screen_name: str | None = None
    tweets_count: int | None = None
    verified: bool | None = None


class HandlerScoreChangesResp(DTO):
    month_delta: float | None = None
    week_delta: float | None = None


class HandlerScoreResp(DTO):
    score: float | None = None


class HandlerSearchTweetsReq(DTO):
    next_cursor: str | None = None
    order: str | None = None
    query: str | None = None


class HandlerSearchTweetsRes(DTO):
    next_cursor: str | None = None
    tweets: list[TypesListItem] | None = None


class HandlerTweetInfoReq(DTO):
    tweet_link: str | None = None


class HandlerTweetInfoResp(DTO):
    bookmark_count: int | None = None
    conversation_id_str: str | None = None
    created_at: str | None = None
    entities: list[TypesListItemEntity] | None = None
    favorite_count: int | None = None
    full_text: str | None = None
    id_str: str | None = None
    in_reply_to_status_id_str: str | None = None
    is_quote_status: bool | None = None
    quote_count: int | None = None
    quoted_status: TypesListItemQuotedStatus | None = None
    reply_count: int | None = None
    retweet_count: int | None = None
    retweeted_status: TypesListItemRetweetedStatus | None = None
    user: TypesListItemUser | None = None
    view_count: int | None = None


class HandlerUserTweetsReq(DTO):
    cursor: str | None = None
    link: str | None = None
    user_id: str | None = None


class HandlerUserTweetsRes(DTO):
    next_cursor: str | None = None
    tweets: list[TypesListItem] | None = None
