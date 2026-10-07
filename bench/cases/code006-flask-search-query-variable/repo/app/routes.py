import sqlite3

from flask import Flask, jsonify, request

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/api/products/search")
def search_products():
    term = request.args.get("q", "")
    conn = get_db()
    cursor = conn.cursor()
    query = f"SELECT id, name, price FROM products WHERE name LIKE '%{term}%'"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
