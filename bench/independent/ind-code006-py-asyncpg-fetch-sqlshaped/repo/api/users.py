from aiohttp import web


async def get_user(request: web.Request):
    pool = request.app["pool"]
    email = request.query["email"]
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT id, email, plan FROM users WHERE email = '{email}'")
    if row is None:
        raise web.HTTPNotFound()
    return web.json_response(dict(row))
