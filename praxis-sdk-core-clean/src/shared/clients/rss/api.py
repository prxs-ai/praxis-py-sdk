from services.shared.clients.aiohttp_ import AiohttpAPI

from .commands import Feedspot, FeedspotRequest, FeedspotResponse
from .session import RSSSession


class RSSAPI(AiohttpAPI[RSSSession]):
    async def get_feedspot(self, url: str) -> list[FeedspotResponse]:
        return await self(Feedspot(FeedspotRequest(url=url)))
