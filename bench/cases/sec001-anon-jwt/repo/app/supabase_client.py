from supabase import Client, create_client

SUPABASE_URL = "https://qzkvbxtrmplwhaneydcf.supabase.co"
# The anon key is public by design; row-level security does the gatekeeping.
SUPABASE_ANON_KEY = "{{FAKE_SUPABASE_ANON_JWT}}"


def client_for(user_jwt: str) -> Client:
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    client.postgrest.auth(user_jwt)
    return client
