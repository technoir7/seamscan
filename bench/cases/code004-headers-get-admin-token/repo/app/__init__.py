from flask import Flask, abort, request

app = Flask(__name__)


@app.before_request
def require_admin_token():
    if request.path.startswith("/admin"):
        if request.headers.get("X-Admin-Token") != "letmein-admin":
            abort(403)
