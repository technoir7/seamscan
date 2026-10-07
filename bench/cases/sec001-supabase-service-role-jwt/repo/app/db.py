from supabase import Client, create_client

SUPABASE_URL = "https://qzkvbxtrmplwhaneydcf.supabase.co"
# service role so the backend can bypass RLS for admin jobs
SUPABASE_KEY = "{{FAKE_SUPABASE_SERVICE_JWT}}"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_profile(user_id: str) -> dict:
    return supabase.table("profiles").select("*").eq("id", user_id).single().execute().data
