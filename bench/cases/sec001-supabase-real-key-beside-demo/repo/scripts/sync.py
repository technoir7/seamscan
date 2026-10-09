from supabase import create_client

LOCAL_KEY = "{{FAKE_SUPABASE_DEMO_SERVICE_JWT}}"
LOCAL = create_client("http://127.0.0.1:54321", LOCAL_KEY)
PROD = create_client("https://qzkvbxtrmplwhaneydcf.supabase.co", "{{FAKE_SUPABASE_SERVICE_JWT}}")
