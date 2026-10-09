import sqlite3


def test_insert_rows():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (id INTEGER, name TEXT)")
    for i, name in enumerate(["a", "b"]):
        conn.execute(f"INSERT INTO t VALUES ({i}, '{name}')")
    assert conn.execute("SELECT count(*) FROM t").fetchone()[0] == 2
