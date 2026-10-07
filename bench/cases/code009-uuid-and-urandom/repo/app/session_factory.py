import base64
import os
import random
import uuid

COLORS = ["red", "green", "blue"]


def new_session() -> dict:
    session_id = uuid.uuid4().hex
    salt = base64.b64encode(os.urandom(16)).decode()
    return {"session_id": session_id, "salt": salt, "avatar_color": random.choice(COLORS)}
