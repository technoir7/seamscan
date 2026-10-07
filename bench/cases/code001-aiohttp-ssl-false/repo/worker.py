import aiohttp


async def ping(session, url):
    async with session.get(url) as r:
        return r.status


async def main(url):
    async with aiohttp.ClientSession() as s:
        return await aiohttp.request("GET", url, ssl=False)
