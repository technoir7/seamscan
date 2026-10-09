from typing import Annotated
from fastapi import FastAPI, Query

app = FastAPI()


def run(cur, sql, params):
    cur.execute(sql, params)
    return cur.fetchall()


@app.get("/events")
def events(page: Annotated[int, Query(ge=1)] = 1, size: int = 25):
    cur = app.state.cursor
    offset = (page - 1) * size
    return run(cur, f"SELECT id, name FROM events ORDER BY id LIMIT {size} OFFSET {offset}", ())
