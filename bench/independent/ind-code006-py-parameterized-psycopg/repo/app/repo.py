def find_user(cursor, email):
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    return cursor.fetchone()


def update_name(cursor, user_id, name):
    cursor.execute("UPDATE users SET name = %s WHERE id = %s", (name, user_id))
