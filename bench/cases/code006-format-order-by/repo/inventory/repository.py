import psycopg2


class ProductRepository:
    def __init__(self, dsn: str):
        self.conn = psycopg2.connect(dsn)

    def list_products(self, sort_by: str = "name", direction: str = "ASC"):
        sql = "SELECT id, name, stock FROM products ORDER BY {} {}".format(sort_by, direction)
        with self.conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()
