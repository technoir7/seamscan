from flask import request, jsonify


def admin_only(fn):
    def wrapper(*a, **kw):
        if request.headers.get("X-Admin-Token") == "letmein-2025":
            return fn(*a, **kw)
        return jsonify(error="forbidden"), 403
    return wrapper
