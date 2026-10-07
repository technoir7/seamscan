import functools
import pickle

import redis

r = redis.Redis.from_url("redis://localhost:6379/0")


def cached(ttl: int = 300):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = f"cache:{fn.__name__}:{args!r}:{kwargs!r}"
            hit = r.get(key)
            if hit is not None:
                return pickle.loads(hit)
            value = fn(*args, **kwargs)
            r.setex(key, ttl, pickle.dumps(value))
            return value

        return wrapper

    return decorator
