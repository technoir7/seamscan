def list_items(cursor, category, in_stock_only=False):
    query = "SELECT sku, title, qty FROM items"
    query += " WHERE category = '" + category + "'"
    if in_stock_only:
        query += " AND qty > 0"
    cursor.execute(query)
    return cursor.fetchall()
