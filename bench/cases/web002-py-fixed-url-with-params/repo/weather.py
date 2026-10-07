import os

import requests
from fastapi import FastAPI

app = FastAPI()


@app.get("/weather")
def weather(city: str):
    r = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"q": city, "appid": os.environ["OWM_KEY"], "units": "metric"},
        timeout=5,
    )
    return r.json()
