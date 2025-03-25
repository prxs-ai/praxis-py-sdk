import asyncio


async def main():
    api = DexScreenerAPI()
    try:
        data = await api.get_latest_token_profiles()
        print(data)
        data = await api.get_token_data_by_address("solana", "5fGA1os23NNWzhGYLhrWAEnwKDgUX2RSUNmgJACcY5hb")
        print(data)
    finally:
        await api.close()


asyncio.run(main())
