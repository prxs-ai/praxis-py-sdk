from __future__ import annotations

from functools import partialmethod
from typing import TYPE_CHECKING, Any, Generic, ParamSpec, Self, TypeVar, Unpack
from urllib.parse import urlparse

from aiohttp import ClientResponse, ClientSession
from services.shared.clients.exceptions import APIError

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from types import TracebackType

    from aiohttp.client import _BaseRequestContextManager, _RequestOptions

P = ParamSpec("P")
R = TypeVar("R")


def _factory(verb: str, _: Callable[P, R]) -> Callable[P, R]:
    @partialmethod
    def method(*args: P.args, **kwargs: P.kwargs) -> R:
        return args[0].request(verb, *args[1:], **kwargs)  # type: ignore

    return method  # type: ignore


ResponseType = TypeVar("ResponseType", bound=ClientResponse)


class ResponseWrapper(Generic[ResponseType]):
    __slots__ = "_coro", "_resp"

    def __init__(self, coro: Coroutine[Any, None, ResponseType]) -> None:
        self._coro = coro

    async def __aenter__(
        self,
    ) -> ClientResponse:
        self._resp: R = await self._coro
        if not self._resp.ok:
            raise APIError(self._resp.status, repr(await self._resp.read()))
        return await self._resp.__aenter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._resp.__aexit__(exc_type, exc, tb)


def _create_session() -> ClientSession:
    return ClientSession(raise_for_status=True)


class AiohttpSession:
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
        self._session_provider = session_provider or _create_session
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
        kwargs = self._handle_kwargs(**kwargs)
        return self._session.request(method, url, **kwargs)

    def _handle_kwargs(self, **kwargs: Unpack[_RequestOptions]) -> _RequestOptions:
        return kwargs

    def get(
        self, url: str, **kwargs: Unpack[_RequestOptions]
    ) -> ResponseWrapper[ClientResponse]:
        return ResponseWrapper(self.request("GET", url, **kwargs)._coro)

    post = _factory("post", get)
    delete = _factory("delete", get)
    put = _factory("put", get)
    patch = _factory("patch", get)
    head = _factory("head", get)
    options = _factory("options", get)
    trace = _factory("trace", get)
    connect = _factory("connect", get)

    async def __aenter__(self) -> Self:
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
