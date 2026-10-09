from urllib.parse import urlparse
import webbrowser

from app.cache import cache


def domain_of(url):
    try:
        return urlparse(url).netloc or None
    except Exception:
        return None


def cached_profile(user_id):
    try:
        return cache.get(f"profile:{user_id}")
    except Exception:
        pass
    return None


def open_docs(url):
    print(f"Docs: {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass


def summary_for(supabase, evaluation_id):
    try:
        resp = supabase.table("summaries").select("*").eq("evaluation_id", evaluation_id).execute()
        return resp.data[0]["text"] if resp.data else None
    except Exception:
        pass
    return None


def count_users(cur):
    try:
        cur.execute("SELECT count(*) FROM users")
        return cur.fetchone()[0]
    except Exception:
        return None
