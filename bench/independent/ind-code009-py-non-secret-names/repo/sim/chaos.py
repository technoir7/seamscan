import random

FAILURE_CODES = [500, 502, 503]


def inject(response, page_id, shards=8):
    response.status_code = random.choice(FAILURE_CODES)
    cache_key = f"views:{page_id}:{random.randrange(shards)}"
    product_key = random.choice(["a", "b", "c"])
    return cache_key, product_key
