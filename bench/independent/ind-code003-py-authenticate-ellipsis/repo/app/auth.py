from flask import request


def authenticate_request(req=None):
    ...


def current_user():
    authenticate_request(request)
    return {"id": 1}
