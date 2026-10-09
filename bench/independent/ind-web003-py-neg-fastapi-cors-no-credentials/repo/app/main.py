from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

public_api = FastAPI()
public_api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])

admin_api = FastAPI()
admin_api.add_middleware(
    CORSMiddleware,
    allow_origins=["https://admin.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
)
