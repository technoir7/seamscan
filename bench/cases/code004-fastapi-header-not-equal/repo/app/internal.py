from fastapi import FastAPI, Header, HTTPException

app = FastAPI()


@app.post("/internal/reindex")
def reindex(x_api_key: str = Header(...)):
    if x_api_key != "dev-key-12345":
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"status": "queued"}
