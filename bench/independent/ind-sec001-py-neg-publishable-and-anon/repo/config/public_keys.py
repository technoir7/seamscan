"""Public identifiers returned to the front end by /config."""

STRIPE_PUBLISHABLE_KEY = "{{FAKE_STRIPE_PK_LIVE}}"
SUPABASE_URL = "https://abcd1234.supabase.co"
SUPABASE_ANON_KEY = "{{FAKE_SUPABASE_ANON_JWT}}"
SUPABASE_PUBLISHABLE = "{{FAKE_SUPABASE_PUBLISHABLE}}"


def public_config() -> dict:
    return {
        "stripe": STRIPE_PUBLISHABLE_KEY,
        "supabase": {"url": SUPABASE_URL, "key": SUPABASE_ANON_KEY},
    }
