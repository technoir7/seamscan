def find_orders(cursor, status=None, min_total=None, customer=None):
    query = "SELECT id, status, total FROM orders WHERE 1=1"
    params = []
    if status:
        query += " AND status = %s"
        params.append(status)
    if min_total is not None:
        query += " AND total >= %s"
        params.append(min_total)
    if customer:
        query += " AND customer_id = %s"
        params.append(customer)
    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    return cursor.fetchall()
