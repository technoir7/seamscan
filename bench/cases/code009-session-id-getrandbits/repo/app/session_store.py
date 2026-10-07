import random
import time


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}

    def create(self, user_id: int) -> str:
        session_id = "%032x" % random.getrandbits(128)
        self._sessions[session_id] = {"user_id": user_id, "created": time.time()}
        return session_id
