import os

from flask import Flask, request

app = Flask(__name__)


@app.route("/ping")
def ping():
    host = request.args.get("host", "127.0.0.1")
    exit_code = os.system("ping -c 1 " + host)
    return {"reachable": exit_code == 0}
