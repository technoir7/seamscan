import os

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/api/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__" and os.environ.get("FLASK_ENV") == "development":
    app.run(debug=True)
