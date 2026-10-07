import os

from fastapi import FastAPI
from pydantic import BaseModel
from supabase import create_client

app = FastAPI()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


class ProfileUpdate(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None


@app.get("/profiles/{profile_id}")
def get_profile(profile_id: str):
    return supabase.table("profiles").select("*").eq("id", profile_id).single().execute().data


@app.patch("/profiles/{profile_id}")
def update_profile(profile_id: str, body: ProfileUpdate):
    result = (
        supabase.table("profiles")
        .update(body.model_dump(exclude_none=True))
        .eq("id", profile_id)
        .execute()
    )
    return result.data
