from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from svc.auth import get_current_user

app = FastAPI(title="Review Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {"username": user["sub"]}
