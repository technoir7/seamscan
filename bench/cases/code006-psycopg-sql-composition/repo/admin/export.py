from psycopg2 import sql


def export_rows(conn, table: str, columns: list[str], row_id: int):
    query = sql.SQL("SELECT {fields} FROM {table} WHERE id = %s").format(
        fields=sql.SQL(", ").join(map(sql.Identifier, columns)),
        table=sql.Identifier(table),
    )
    with conn.cursor() as cur:
        cur.execute(query, (row_id,))
        return cur.fetchall()
