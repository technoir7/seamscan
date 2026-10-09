import random


class SessionStore:
    def __init__(self):
        self._data = {}

    def create(self, user_id):
        session_id = "%032x" % random.getrandbits(128)
        self._data[session_id] = {"user_id": user_id}
        return session_id
