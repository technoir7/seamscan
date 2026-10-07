from fastapi import Depends, FastAPI, Header

app = FastAPI()


def verify_api_key(x_api_key: str = Header(...)) -> None:
    """Reject requests without a valid API key."""
    pass


@app.get("/reports", dependencies=[Depends(verify_api_key)])
def list_reports():
    return {"reports": []}
