import pickle
import redis

r = redis.Redis.from_url("redis://localhost:6379/0")


def get_cached(key):
    raw = r.get(key)
    if raw is None:
        return None
    return pickle.loads(raw)


def set_cached(key, value, ttl=300):
    r.setex(key, ttl, pickle.dumps(value))
