import uuid


def new_session_id() -> str:
    session_id = uuid.uuid4().hex
    return session_id


def new_invite(team):
    return {"team": team, "invite_token": str(uuid.uuid4())}
