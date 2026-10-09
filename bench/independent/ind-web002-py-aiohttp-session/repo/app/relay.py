import aiohttp
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Relay(BaseModel):
    callback: str
    payload: dict


@app.post("/relay")
async def relay(body: Relay):
    async with aiohttp.ClientSession() as session:
        async with session.post(body.callback, json=body.payload) as resp:
            return {"status": resp.status}
