import asyncio
import aiohttp


async def poll(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, ssl=False) as resp:
            return await resp.json()


if __name__ == "__main__":
    print(asyncio.run(poll("https://10.0.4.7/status")))
