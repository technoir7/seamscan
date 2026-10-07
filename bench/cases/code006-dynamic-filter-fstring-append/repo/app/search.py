def search_users(cursor, name=None, city=None):
    query = "SELECT id, name, city FROM users WHERE 1=1"
    params = []
    if name:
        query += f" AND name = '{name}'"
    if city:
        query += " AND city = %s"
        params.append(city)
    cursor.execute(query, params)
    return cursor.fetchall()
