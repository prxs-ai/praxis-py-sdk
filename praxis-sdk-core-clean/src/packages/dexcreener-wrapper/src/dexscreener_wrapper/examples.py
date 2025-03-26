import asyncio
import json
from dexscreener_wrapper.main import DexScreenerAPI


async def main():
    api = DexScreenerAPI()
    try:
        # data = await api.get_latest_token_profiles()
        #

        data = await api.get_token_data_by_address("solana", "6xzcGi7rMd12UPD5PJSMnkTgquBZFYhhMz9D5iHgzB1w")
        print(json.dumps(data, indent=4, ensure_ascii=False))
    finally:
        await api.close()


asyncio.run(main())
