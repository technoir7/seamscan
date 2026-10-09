from flask import Flask

app = Flask(__name__)


def run_manually():
    app.run(debug=True)
