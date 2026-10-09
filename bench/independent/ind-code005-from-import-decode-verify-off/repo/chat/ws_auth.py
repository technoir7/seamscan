from jwt import decode
from starlette.websockets import WebSocket


async def authenticate(ws: WebSocket) -> str | None:
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=4401)
        return None
    claims = decode(token, options={"verify_signature": False})
    return claims.get("sub")
