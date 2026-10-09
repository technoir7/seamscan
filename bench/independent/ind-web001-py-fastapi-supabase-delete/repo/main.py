import os

from fastapi import FastAPI
from supabase import create_client

app = FastAPI()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


@app.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: int):
    supabase.table("notes").delete().eq("id", note_id).execute()
