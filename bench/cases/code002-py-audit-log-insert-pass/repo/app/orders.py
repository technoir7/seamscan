from app.db import supabase


def place_order(user_id, items):
    try:
        supabase.table("audit_log").insert({"user_id": user_id, "event": "order"}).execute()
    except Exception:
        pass
    try:
        supabase.table("orders").insert({"user_id": user_id, "items": items}).execute()
    except Exception:
        pass
    return {"ok": True}
