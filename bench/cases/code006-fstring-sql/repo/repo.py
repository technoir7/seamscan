def find_user(conn, email):
    return conn.execute(f"SELECT * FROM users WHERE email = '{email}'").fetchone()
