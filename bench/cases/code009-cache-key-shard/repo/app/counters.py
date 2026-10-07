import random

from .cache import redis_client

SHARDS = 8


def incr_page_views(page_id: int) -> None:
    cache_key = f"views:{page_id}:{random.randrange(SHARDS)}"
    redis_client.incr(cache_key)
