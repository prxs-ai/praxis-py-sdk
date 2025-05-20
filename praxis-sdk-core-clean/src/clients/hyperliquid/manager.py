from fastapi import HTTPException
from aiohttp import ClientSession
import pandas as pd

from infrastructure.configs.config import server

class HyperLiquidManager:
    def __init__(
        self, session: ClientSession, base_url: str
    ):
        self.session = session
        self.base_url = base_url
        self.headers = {'Content-Type': 'application/json'}

    async def _send_request(
        self,
        headers: dict,
        params: dict | None = None,
        body: dict | None = None,
        method: str = "POST"
    ):

        response = await self.session.request(
            method=method,
            url=self.base_url,
            json=body,
            params=params,
            headers=headers
        )
        if response.status != 200:
            raise HTTPException(
                detail="Problem with hyperliquid request", status_code=400
            )
        return await response.json()

    async def get_pool_liquidity(
        self, coin: str
    ) -> pd.DataFrame:
        body = {
            "type": "l2Book",
            "coin": coin
        }
        data = await self._send_request(
            body=body, headers=self._make_headers()
        )
        levels = data["levels"]
        bids_df = pd.DataFrame(levels[0])
        bids_df["type"] = "bids"
        asks_df = pd.DataFrame(levels[1])
        asks_df["type"] = "asks"
        merged_df = pd.concat([bids_df, asks_df])
        merged_df["sz"] = pd.to_numeric(merged_df["sz"])
        merged_df = merged_df.groupby(by=["type"]).sum().reset_index()
        merged_df = pd.concat(
            [
                merged_df,
                pd.DataFrame(
                    [{"type": "sum_liquidity", "sz": merged_df["sz"].sum()}]
                )
            ],
            ignore_index=True
        )
        return merged_df.loc[:, ["type", "sz"]]

    def _make_headers(self, headers: dict = {}) -> dict:
        if not headers:
            return self.headers
        headers = self.headers | headers
        return headers

async def get_hyperliquid_manager():
    async with ClientSession() as session:
        yield HyperLiquidManager(
            base_url=server.hyperliquid.base_url, session=session
        )
