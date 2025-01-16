from services.shared.api_client.aiohttp_ import AiohttpAPI

from .commands import Feedspot, FeedspotRequest, FeedspotResponse
from .session import RSSSession


class RSSAPI(AiohttpAPI[RSSSession]):
    async def get_feedspot(self, url: str) -> list[FeedspotResponse]:
        return self(Feedspot(FeedspotRequest(url=url)))
