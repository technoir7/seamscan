import random

from fastapi import FastAPI, Response

app = FastAPI()
FAILURE_CODES = [500, 502, 503]


@app.get("/flaky")
def flaky(response: Response):
    if random.random() < 0.2:
        response.status_code = random.choice(FAILURE_CODES)
        return {"ok": False}
    return {"ok": True}
