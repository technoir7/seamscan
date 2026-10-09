import os

from supabase import create_client

# Local stack from `supabase start`; CI points these at a throwaway project.
url = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "{{FAKE_SUPABASE_DEMO_SERVICE_JWT}}")
supabase = create_client(url, key)

supabase.table("plans").upsert([{"id": "free"}, {"id": "pro"}]).execute()
