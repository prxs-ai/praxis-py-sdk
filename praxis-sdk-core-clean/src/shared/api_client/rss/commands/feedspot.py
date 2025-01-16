from bs4 import BeautifulSoup

from services.shared.api_client import APIError
from services.shared.api_client.rss.session import RSSSession

from .base import AbstractCommand, Request, Response


class FeedspotRequest(Request):
    url: str


class FeedspotResponse(Response):
    title: str
    content: str
    link: str


class Feedspot(AbstractCommand[FeedspotRequest, list[FeedspotResponse]]):
    async def _execute(self, session: RSSSession) -> list[FeedspotResponse]:
        response = await session.et(self.data.url, json=self.data.dump())
        if response.status != 200:
            raise APIError(response.status, await response.text())

        data = await response.text()
        soup = BeautifulSoup(data, "html.parser")
        container = soup.find("div", class_="entry__wrapper")
        items = container.find_all("div", class_="etnry__item")

        posts = []
        for item in items:
            title = item.find("div", class_="entry__item_title").text
            text = item.find("div", class_="entry__item_excerpt").text
            link = item.find("div", class_="entry__item_visit").find("a")["href"]
            posts.append(FeedspotResponse(title=title, text=text, link=link))

        return posts
