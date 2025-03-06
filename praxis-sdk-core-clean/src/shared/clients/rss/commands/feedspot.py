from bs4 import BeautifulSoup

from services.shared.clients import APIError
from services.shared.clients.rss.session import RSSSession

from .base import AbstractCommand, Request, Response


class FeedspotRequest(Request):
    url: str


class FeedspotResponse(Response):
    title: str
    content: str
    source: str


class Feedspot(AbstractCommand[FeedspotRequest, list[FeedspotResponse]]):
    async def _execute(self, session: RSSSession) -> list[FeedspotResponse]:
        response = await session.get(self.data.url, json=self.data.dump())
        if response.status != 200:
            raise APIError(response.status, await response.text())

        data = await response.text()
        soup = BeautifulSoup(data, "html.parser")
        container = soup.find("div", class_="entry_wrapper")
        items = container.find_all("div", class_="entry__item")

        posts = []
        for item in items:
            title = item.find("div", class_="entry__item_title").text
            content = item.find("div", class_="entry__item_excerpt").text
            source = item.find("div", class_="entry__item_visit").find("a")["href"]
            posts.append(FeedspotResponse(title=title, content=content, source=source))

        return posts
