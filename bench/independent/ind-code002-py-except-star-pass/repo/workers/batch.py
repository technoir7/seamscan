import asyncio


async def run_all(jobs):
    try:
        async with asyncio.TaskGroup() as tg:
            for j in jobs:
                tg.create_task(j.save())
    except* Exception:
        pass
