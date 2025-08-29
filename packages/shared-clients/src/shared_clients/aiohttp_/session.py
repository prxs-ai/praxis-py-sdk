from __future__ import annotations

from collections.abc import Coroutine
from functools import partial
from types import TracebackType
from typing import Any, Callable, ParamSpec, TypeVar, Generic
from urllib.parse import urlparse

from aiohttp import ClientResponse, ClientSession
from aiohttp.client import _BaseRequestContextManager, _RequestOptions
from shared_clients.exceptions import APIError

P = ParamSpec("P")
R = TypeVar("R", bound=ClientResponse)


def _factory(method: str) -> Callable[..., ResponseWrapper]:
    def wrapper(self: AiohttpSession, url: str, **kwargs: Any) -> ResponseWrapper:
        return ResponseWrapper(self.request(method.upper(), url, **kwargs))  # type: ignore
    return wrapper


class ResponseWrapper(Generic[R]):
    __slots__ = "_coro", "_resp", "_context"  # Добавляем _context

    def __init__(self, context: _BaseRequestContextManager[R]) -> None:
        self._coro = context.__aenter__
        self._context = context

    async def __aenter__(self) -> R:
        self._resp: R = await self._coro()
        if not self._resp.ok:
            raise APIError(self._resp.status, repr(await self._resp.read()))
        return self._resp

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._context.__aexit__(exc_type, exc, tb)


def _create_session() -> ClientSession:
    return ClientSession(raise_for_status=True)


class AiohttpSession:
    __slots__ = (
        "_session_provider",
        "_base_url",
        "_session",
    )

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
        **kwargs: Any,
    ) -> _BaseRequestContextManager[ClientResponse]:
        if not urlparse(url).netloc:
            url = self._base_url + url
        return self._session.request(method, url, **self._handle_kwargs(**kwargs))

    def _handle_kwargs(self, **kwargs: Any) -> _RequestOptions:
        return kwargs

    def get(self, url: str, **kwargs: Any) -> ResponseWrapper[ClientResponse]:
        return ResponseWrapper(self.request("GET", url, **kwargs))

    post = _factory("post")
    delete = _factory("delete")
    put = _factory("put")
    patch = _factory("patch")
    head = _factory("head")
    options = _factory("options")
    trace = _factory("trace")
    connect = _factory("connect")

    async def __aenter__(self):
        if not hasattr(self, "_session") or self._session.closed:
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
