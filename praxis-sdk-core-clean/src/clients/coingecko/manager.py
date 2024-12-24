from aiohttp import ClientSession

from infrastructure.configs.config import CoingeckoSettings, server
from pandas import DataFrame
import pandas as pd


class CoinGeckoApiManager:

    def __init__(
        self, api_key: str, session: ClientSession, base_url: str
    ):
        self.api_key = api_key
        self.session = session
        self.base_url = base_url

    async def _send_response(
        self, endpoint: str, params: dict | None = None,
        method: str = "POST"
    ):
        headers = {"x-cg-demo-api-key": self.api_key}
        response = await self.session.request(
            method=method, url=f"{self.base_url}{endpoint}",
            headers=headers, params=params
        )
        return await response.json()

    async def get_historical_prices(
        self, token_name: str, days: int = 3, vs_currency: str = "usd"
    ) -> DataFrame:
        token_df = await self.get_tokens(token_name=token_name)
        token_id = token_df["id"].iloc[0]
        endpoint = f"/coins/{token_id}/markets"
        params = {
            'vs_currency': vs_currency, 'days': days
        }
        historical_data = await self._send_response(endpoint, params=params)
        return await prepare_historical_prices(data=historical_data)

    async def get_tokens(
        self, token_name:str | None = None
    ) -> DataFrame:
        endpoint = "/coins/list"
        response = await self._send_response(method="GET", endpoint=endpoint)
        data = await response.json()
        df = DataFrame(data)
        if token_name is not None:
            df = df[df.name == token_name]
        return df


async def prepare_historical_prices(data: dict[str, list]) -> DataFrame:
    prices_df = DataFrame(data["prices"], columns=["timestamp", "price"])
    market_caps_df = DataFrame(
        data["market_caps"], columns=["timestamp", "market_cap"]
    )
    total_volumes_df = DataFrame(
        data["total_volumes"], columns=["timestamp", "total_volume"]
    )
    summary_df = prices_df.merge(market_caps_df, on="timestamp").merge(
        total_volumes_df, on="timestamp"
    )
    summary_df.timestamp = pd.to_datetime(summary_df.timestamp, unit="ms")
    summary_df.total_volume = summary_df.total_volume.apply(lambda x: f"{x:.0f}")
    summary_df.market_cap = summary_df.market_cap.apply(lambda x: f"{x:.0f}")
    return summary_df


async def get_coingecko_manager():
    async with ClientSession() as session:
        yield CoinGeckoApiManager(
            api_key=server.coingecko.api_key,
            session=session, base_url=server.coingecko.base_url
        )
