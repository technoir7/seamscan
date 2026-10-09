from contextlib import suppress

from app.db import session
from app.models import Session as UserSession


def purge_expired():
    with suppress(Exception):
        session.query(UserSession).filter(UserSession.expired).delete()
        session.commit()
