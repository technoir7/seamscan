import os
from functools import wraps

import jwt
from flask import request, jsonify, g

SECRET = os.environ["JWT_SECRET"]


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="missing token"), 401
        token = header.split(" ", 1)[1]
        try:
            g.claims = jwt.decode(token, SECRET, algorithms=["HS256", "none"])
        except jwt.InvalidTokenError:
            return jsonify(error="bad token"), 401
        return fn(*args, **kwargs)
    return wrapper
