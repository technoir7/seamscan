import MySQLdb


def delete_sessions(db: MySQLdb.Connection, user_id: str) -> int:
    cursor = db.cursor()
    cursor.execute("DELETE FROM sessions WHERE user_id = '%s'" % user_id)
    db.commit()
    return cursor.rowcount
