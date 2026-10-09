from psycopg import sql


def fetch_rows(cur, table: str, cols: list[str], row_id: int):
    query = sql.SQL("SELECT {f} FROM {t} WHERE id = %s").format(
        f=sql.SQL(", ").join(map(sql.Identifier, cols)),
        t=sql.Identifier(table),
    )
    cur.execute(query, (row_id,))
    return cur.fetchall()
