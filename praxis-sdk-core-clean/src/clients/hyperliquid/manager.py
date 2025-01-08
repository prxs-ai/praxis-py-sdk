from fastapi import HTTPException
from aiohttp import ClientSession
import pandas as pd

from infrastructure.configs.config import server

class HyperLiquidManager:
    def __init__(
        self, session: ClientSession, base_url: str = "https://api.hyperliquid.xyz/info"
    ):
        self.session = session
        self.base_url = base_url

    async def _send_request(
        self,
        params: dict | None = None,
        method: str = "POST"
    ):
        response = await self.session.request(
            method=method,
            url=f"{self.base_url}",
            params=params
        )
        return await response.json()

    async def get_pool_liquidity(
        self, coin: str
    ) -> pd.DataFrame:
        params = {
            "type": "l2Book",
            "coin": coin
        }
        response = await self._send_request(params=params)
        if response.status != 200:
            raise HTTPException(
                detail="Get pool liquidity failed", status_code=400
            )
        data = await response.json()
        levels = data["levels"]
        bids_df = pd.DataFrame(levels[0])
        bids_df["type"] = "bids"
        asks_df = pd.DataFrame(levels[1])
        asks_df["type"] = "asks"
        merged_df = pd.concat([bids_df, asks_df])
        merged_df["sz"] = pd.to_numeric(merged_df["sz"])
        merged_df = merged_df.groupby(by=["type"]).sum().reset_index()
        merged_df = pd.concat(
            [merged_df, pd.DataFrame(
                [{"type": "sum_liquidity", "sz": merged_df["sz"].sum()}]
            )]
        )
        return merged_df.loc[:, ["type", "sz"]]

async def get_hyperliquid_manager():
    async with ClientSession() as session:
        yield HyperLiquidManager(
            base_url=server.hyperliquid.base_url, session=session
        )
