from functools import partial
from types import TracebackType
from typing import Callable, Self, Unpack
from urllib.parse import urlparse

from aiohttp import ClientResponse, ClientSession
from aiohttp.client import _BaseRequestContextManager, _RequestOptions


class Session:
    __slots__ = (
        "_session_provider",
        "_base_url",
        "_session",
    )

    _session: ClientSession

    def __init__(
        self,
        session_provider: Callable[[], ClientSession] | None = None,
        base_url: str = "",
    ) -> None:
        self._session_provider = session_provider or ClientSession
        self._base_url = base_url
        self._create_session()

    def request(
        self,
        method: str,
        url: str,
        **kwargs: Unpack[_RequestOptions],
    ) -> _BaseRequestContextManager[ClientResponse]:
        if not urlparse(url).netloc:
            url = self._base_url + url
        return self._session.request(method, url, **kwargs)

    get = partial(request, method="GET")
    post = partial(request, method="POST")
    delete = partial(request, method="DELETE")
    put = partial(request, method="PUT")
    patch = partial(request, method="PATCH")
    head = partial(request, method="HEAD")
    options = partial(request, method="OPTIONS")
    trace = partial(request, method="TRACE")
    connect = partial(request, method="CONNECT")

    async def __enter__(self) -> Self:
        if not self._session or self._session.closed:
            self._create_session()
        await self._session.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._session.__aexit__(exc_type, exc_val, exc_tb)

    def _create_session(self) -> None:
        self._session = self._session_provider()
