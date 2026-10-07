import logging

import httpx

logger = logging.getLogger(__name__)


async def fetch_avatar(url: str) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception:
        logger.warning("avatar fetch failed for %s", url, exc_info=True)
        return None
