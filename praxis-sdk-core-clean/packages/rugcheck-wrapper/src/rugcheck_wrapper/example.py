import json

from rugcheck_wrapper.main import RugCheckAPI


async def main():
    api = RugCheckAPI()

    try:
        data = await api.get_token_report(
            "5fGA1os23NNWzhGYLhrWAEnwKDgUX2RSUNmgJACcY5hb"
        )  # Пример адреса токена
        print(json.dumps(data, indent=4))
    finally:
        await api.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
