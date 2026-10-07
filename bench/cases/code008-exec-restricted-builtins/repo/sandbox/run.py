from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Snippet(BaseModel):
    code: str


@app.post("/run")
def run_snippet(snippet: Snippet):
    namespace: dict = {}
    exec(snippet.code, {"__builtins__": {}}, namespace)
    return {"result": namespace.get("result")}
