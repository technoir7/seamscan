import sys

from inventory.db import connect


def test_connection():
    conn = connect()
    print("connected", conn.dsn)


if __name__ == "__main__":
    test_connection()
    sys.exit(0)
