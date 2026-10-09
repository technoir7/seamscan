BASE_QUERY = "SELECT id, title FROM articles"


def get_many(cur, ids: list[int]):
    placeholders = ", ".join(["%s"] * len(ids))
    cur.execute(f"{BASE_QUERY} WHERE id IN ({placeholders})", ids)
    return cur.fetchall()
