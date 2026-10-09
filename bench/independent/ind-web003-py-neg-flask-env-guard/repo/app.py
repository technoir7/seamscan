import os

from flask import Flask

app = Flask(__name__)


@app.get("/")
def index():
    return "ok"


if __name__ == "__main__" and os.environ.get("FLASK_ENV") == "development":
    app.run(debug=True)
