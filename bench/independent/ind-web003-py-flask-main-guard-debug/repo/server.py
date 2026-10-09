import os

from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["https://app.example.com"])
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]


@app.get("/")
def index():
    return "hello"


if __name__ == "__main__":
    app.run(debug=True)
