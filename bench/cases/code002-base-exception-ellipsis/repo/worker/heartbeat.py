import time

import redis

r = redis.Redis()


def heartbeat(worker_id: str) -> None:
    while True:
        try:
            r.set(f"worker:{worker_id}:alive", int(time.time()), ex=30)
        except BaseException:
            ...
        time.sleep(10)
