from functools import wraps

import jwt
from flask import g, jsonify, request


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return jsonify({"message": "Token is missing"}), 401
        data = jwt.decode(token, verify=False)
        g.user_id = data["user_id"]
        return f(*args, **kwargs)

    return decorated
