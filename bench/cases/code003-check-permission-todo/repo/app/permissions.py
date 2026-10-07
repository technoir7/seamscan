from functools import wraps

from flask import abort, g


def check_permission(user, action: str) -> bool:
    # TODO: look up the user's role and the role the action needs
    return True


def require(action: str):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not check_permission(g.user, action):
                abort(403)
            return view(*args, **kwargs)

        return wrapper

    return decorator
