import asyncio
import json

from dextools_wrapper.main import DextoolsAPIWrapper


async def main():
    API_KEY = "***REMOVED***"  # Укажите ваш API-ключ
    api = DextoolsAPIWrapper(
        api_key=API_KEY, plan="trial"
    )  # Лимит: 2 запроса в секунду

    try:
        data = await api.get_blockchain(chain="solana")
        print(json.dumps(data, indent=4))
        data = await api.get_blockchains(order="asc", sort="name", page=1, pageSize=5)
        print(json.dumps(data, indent=4))
        data = await api.get_pools(
            chain="solana",
            from_="2023-11-14T19:00:00",
            to="2023-11-14T23:00:00",
            order="asc",
            sort="creationTime",
            page=None,
            pageSize=None,
        )
        print(json.dumps(data, indent=4))
        data = await api.get_pool_by_address(
            chain="solana", address="8f94e3kYk9ZPuEPT5Zgo9tiVJvwaj8zUzbPFPqt2MKK2"
        )
        print(json.dumps(data, indent=4))
    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
