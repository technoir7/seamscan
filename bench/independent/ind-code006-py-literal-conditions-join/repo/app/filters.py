def search_orders(cur, status=None, customer_id=None):
    conditions = []
    params = []
    if status:
        conditions.append("status = %s")
        params.append(status)
    if customer_id:
        conditions.append("customer_id = %s")
        params.append(customer_id)
    where = " AND ".join(conditions) or "TRUE"
    cur.execute(f"SELECT * FROM orders WHERE {where} ORDER BY created_at DESC", params)
    return cur.fetchall()
