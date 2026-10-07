import os

from flask import Flask

app = Flask(__name__)


@app.get("/")
def index():
    return "hello"


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
