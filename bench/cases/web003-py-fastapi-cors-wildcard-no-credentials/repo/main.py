from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Public exchange rates")

# Public, unauthenticated data: any site may read it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/rates/{base}")
def rates(base: str):
    return {"base": base.upper(), "rates": {}}
