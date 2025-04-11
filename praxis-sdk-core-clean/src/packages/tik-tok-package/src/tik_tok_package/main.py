from TikTokApi import TikTokApi
import asyncio
import os

ms_token = "ZHTeeVQNmtN4NG-5VqoLzKqojDAcypAeRsYWWAqbBPCJY89vsG-a12T79d427jE5fg-NTBGfU-TbPznvom_t34AQkiNG_uug-BFQmh94R31pgpARcPUN-K_jGVYb5DoAvfsbdqU5I8pHxE0DhatOc9c=" # get your own ms_token from your cookies on tiktok.com

async def trending_videos():
    async with TikTokApi() as api:
        await api.create_sessions(ms_tokens=[ms_token], num_sessions=1, sleep_after=3, browser="webkit", headless=False)
        # async for video in api.trending.videos(count=30):
        #     print(video)
        #     print(video.as_dict)


if __name__ == "__main__":
    asyncio.run(trending_videos())