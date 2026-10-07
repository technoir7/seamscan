BASE_QUERY = "SELECT id, name, price FROM products"


def products_in_category(cur, category: str):
    cur.execute(BASE_QUERY + " WHERE category = %s ORDER BY name", (category,))
    return cur.fetchall()


def products_by_ids(cur, ids: list[int]):
    placeholders = ", ".join(["%s"] * len(ids))
    cur.execute(f"{BASE_QUERY} WHERE id IN ({placeholders})", ids)
    return cur.fetchall()
